#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""qoder_register.py — регистрация аккаунта Qoder (qoder.com).

Что автоматизировано:
  * открытие /users/sign-up и заполнение формы (имя, фамилия, email, пароль);
  * ожидание AliyunCaptcha: капчу решает человек в открытом окне браузера;
  * чтение 6-значного кода из catch-all почты и ввод его в форму;
  * сохранение email/пароля в data/accounts.jsonl.

Что НЕ автоматизировано: сама AliyunCaptcha (SceneId в web-приложении Qoder).
Без внешнего солвера это assisted-режим: окно браузера остаётся открытым,
капчу нужно пройти руками. После неё скрипт доходит до конца сам.

Usage:
    python qoder_register.py                 # 1 аккаунт
    python qoder_register.py --email a@b.c   # свой адрес
    python qoder_register.py --headless      # не сработает на капче, для отладки
"""
import argparse
import email as email_module
import email.utils
import json
import random
import re
import string
import sys
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent
CFG = json.loads((ROOT / "config.json").read_text(encoding="utf-8")) if (ROOT / "config.json").exists() else {}
DATA = ROOT / "data"
DATA.mkdir(exist_ok=True)
OUT = DATA / "accounts.jsonl"

CODE_RE = re.compile(r"(?<!\d)(\d{6})(?!\d)")


def cfg(path, default=None):
    cur = CFG
    for part in path.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return default
        cur = cur[part]
    return cur


def new_email():
    mail = cfg("mail", {}) or {}
    domain = mail.get("domain") or "example.com"
    local = "qoder" + "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
    return f"{local}@{domain}"


def list_mails(address, limit=10):
    mail = cfg("mail", {}) or {}
    base = (mail.get("api_base") or "").rstrip("/")
    key = mail.get("admin_key") or ""
    if not base or not key:
        raise RuntimeError("config.json → mail.api_base / mail.admin_key не заполнены")
    r = requests.get(f"{base}/admin/mails",
                     params={"address": address, "limit": limit, "offset": 0},
                     headers={"x-admin-auth": key, "User-Agent": "curl/8.5.0"},
                     timeout=25)
    r.raise_for_status()
    return r.json().get("results", [])


def _plain(msg):
    out = []
    for part in msg.walk():
        if part.get_content_type() in ("text/plain", "text/html"):
            payload = part.get_payload(decode=True)
            if payload:
                out.append(payload.decode("utf-8", "ignore"))
    return "\n".join(out)


def wait_code(address, since_epoch, timeout=180):
    deadline = time.time() + timeout
    seen = set()
    while time.time() < deadline:
        try:
            mails = sorted(list_mails(address), key=lambda m: m.get("id", 0), reverse=True)
        except Exception as exc:
            print(f"  [mail] {str(exc)[:120]}")
            mails = []
        for m in mails:
            mid = m.get("id")
            if mid in seen:
                continue
            seen.add(mid)
            raw = m.get("raw", "")
            msg = email_module.message_from_string(raw)
            try:
                ts = email_module.utils.mktime_tz(email_module.utils.parsedate_tz(str(msg.get("Date", ""))))
            except Exception:
                ts = None
            if ts and ts < since_epoch - 60:
                continue
            subj = str(msg.get("Subject", ""))
            body = _plain(msg)
            match = CODE_RE.search(subj) or CODE_RE.search(body)
            if match:
                return match.group(1)
        print(f"  [mail] кода нет ({int(deadline - time.time())}s)...")
        time.sleep(5)
    return None


def _fill(page, placeholder, value):
    loc = page.locator(f'input[placeholder="{placeholder}"]')
    loc.wait_for(state="visible", timeout=20000)
    loc.fill(value)


def register_one(address=None, headless=False):
    from playwright.sync_api import sync_playwright

    base = (cfg("base_url") or "https://qoder.com").rstrip("/")
    path = cfg("signup_path") or "/users/sign-up"
    password = cfg("password") or "QoderPass12345!"
    names = cfg("names") or ["Alex", "Qoder"]
    address = address or new_email()
    since = time.time()
    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    print(f"[*] email: {address}")

    with sync_playwright() as p:
        exe = cfg("chrome_path") or None
        browser = p.chromium.launch(headless=headless, executable_path=exe,
                                    args=["--no-sandbox"])
        page = browser.new_page()
        page.goto(base + path, wait_until="domcontentloaded", timeout=60000)
        time.sleep(5)

        _fill(page, "Enter your first name", names[0])
        _fill(page, "Enter your Last Name", names[1])
        _fill(page, "Enter your email address", address)
        _fill(page, "Enter your password", password)
        cb = page.query_selector("input[type=checkbox]")
        if cb:
            cb.click()
        page.click("button[type=submit]")
        time.sleep(5)

        # AliyunCaptcha: ждём, пока человек пройдёт её в окне, и появится поле кода.
        captcha_timeout = int(cfg("captcha_timeout_sec") or 300)
        deadline = time.time() + captcha_timeout
        code_input = None
        while time.time() < deadline:
            body = page.inner_text("body").lower()
            if "captcha" in body or "verify the user is human" in body:
                print("  [captcha] пройди капчу в открытом окне браузера...")
            inputs = page.query_selector_all("input")
            for inp in inputs:
                ph = (inp.get_attribute("placeholder") or "").lower()
                if any(x in ph for x in ("code", "verification", "verify")):
                    code_input = inp
                    break
            if code_input:
                break
            if "sign out" in body or "dashboard" in body:
                break
            time.sleep(3)

        if code_input:
            print("  [mail] ждём код из письма...")
            code = wait_code(address, since, timeout=int(cfg("mail_timeout_sec") or 180))
            if not code:
                browser.close()
                return {"email": address, "password": password, "started_at": started,
                        "error": "verification code not received"}
            code_input.fill(code)
            for sel in ("button[type=submit]", "button:has-text('Continue')",
                        "button:has-text('Verify')"):
                try:
                    page.click(sel, timeout=3000)
                    break
                except Exception:
                    continue
            time.sleep(8)

        print("  [*] URL после регистрации:", page.url)
        page.screenshot(path=str(DATA / "last_signup.png"))
        browser.close()

    rec = {"email": address, "password": password, "started_at": started,
           "base_url": base, "status": "registered"}
    with open(OUT, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    print(f"[+] сохранено: {OUT}")
    return rec


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--email", default=None)
    ap.add_argument("--count", type=int, default=1)
    ap.add_argument("--headless", action="store_true")
    args = ap.parse_args()
    for i in range(args.count):
        rec = register_one(args.email if i == 0 else None, headless=args.headless)
        print(json.dumps(rec, ensure_ascii=False))


if __name__ == "__main__":
    main()