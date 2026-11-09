# qoder-autoreg

Регистратор аккаунтов **Qoder** (`qoder.com`) для последующей выдачи PAT в
[Qoder2Api](https://github.com/drakelovc2/qoder2api).

## Статус: assisted, не fully-unattended

Web-форма Qoder закрыта **AliyunCaptcha** (`Click to verify`, SceneId в
`g.alicdn.com/qbase/qoder/.../index.js`). Без внешнего солвера капчу проходит
человек в открытом окне браузера. Скрипт автоматизирует всё остальное:

1. открывает `/users/sign-up`;
2. заполняет First Name / Last Name / Email / Password и чекбокс Terms;
3. ждёт, пока в окне пройдут капчу;
4. читает 6-значный код из catch-all почты и вводит его;
5. сохраняет `email`/`password` в `data/accounts.jsonl`.

Для полностью автоматического прогона нужно подключить солвер AliyunCaptcha
(SceneId + `CertifyId` из страницы) — в этом репозитории его нет.

## Цепочка

```
qoder-autoreg  →  аккаунт Qoder  →  Settings → PAT (pt-…)
                                      ↓
                              Qoder2Api pool
```

PAT выдаётся в настройках аккаунта Qoder (`https://qoder.com/account`) и
добавляется в пул Qoder2Api (`QODER_PAT_LIST` или дашборд на `:8963`).

## Установка

```bash
cp config.example.json config.json   # mail.api_base / admin_key / domain, password
pip install -r requirements.txt
python3 -m playwright install chromium
```

## Запуск

```bash
bash start.sh                 # Xvfb + headful Chrome, 1 аккаунт
bash start.sh --email a@b.c   # свой адрес
```

Окно браузера открывается на Xvfb `:99`. Если хочешь видеть его на рабочем
столе — убери `Xvfb` из `start.sh` и выстави `DISPLAY` своего сеанса.

## Конфиг

| Ключ | Что задаёт |
|---|---|
| `base_url` / `signup_path` | `https://qoder.com` + `/users/sign-up` |
| `password` | пароль создаваемого аккаунта |
| `names` | First Name / Last Name |
| `chrome_path` | пусто = автопоиск Chromium (PATH / Playwright cache) |
| `captcha_timeout_sec` | сколько ждать ручного прохождения капчи |
| `mail_timeout_sec` | сколько ждать письмо с кодом |
| `mail` | apimail-совместимый admin API (`x-admin-auth`) и домен |

## Данные

`data/accounts.jsonl` — email, password, статус. `data/last_signup.png` —
скрин последнего шага. Всё в `.gitignore`.

## Ограничения

- Только собственные/разрешённые аккаунты.
- AliyunCaptcha не обходится: это assisted-режим.
- Qoder может менять форму/капчу — селекторы в `qoder_register.py` стоит
  перепроверять после обновлений сайта.

## Лицензия

MIT + условие добросовестного использования — см. [LICENSE](LICENSE).