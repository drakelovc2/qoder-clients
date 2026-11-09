#!/usr/bin/env bash
# qoder-autoreg — регистратор Qoder. Капча Aliyun: окно headful, проходится руками.
#   bash start.sh                    # 1 аккаунт
#   bash start.sh --email a@b.c      # свой адрес
set -u
cd "$(dirname "$0")" || exit 1
unset PYTHONHOME PYTHONPATH LD_LIBRARY_PATH 2>/dev/null
mkdir -p data
[ -f config.json ] || { echo "[!] cp config.example.json config.json и заполни mail.*"; exit 1; }

DISPLAY_NUM="${QODER_DISPLAY:-:99}"
if ! command -v xdpyinfo >/dev/null 2>&1 || ! xdpyinfo -display "$DISPLAY_NUM" >/dev/null 2>&1; then
  XVFB_BIN="$(command -v Xvfb || true)"; [ -n "$XVFB_BIN" ] || XVFB_BIN="$HOME/.local/bin/Xvfb"
  if [ -x "$XVFB_BIN" ]; then
    echo "[start] Xvfb $DISPLAY_NUM"
    setsid nohup "$XVFB_BIN" "$DISPLAY_NUM" -screen 0 1280x900x24 -nolisten tcp >> data/xvfb.log 2>&1 &
    sleep 1
  fi
fi
export DISPLAY="$DISPLAY_NUM"
exec env -u PYTHONHOME -u PYTHONPATH -u LD_LIBRARY_PATH python3 -X utf8 qoder_register.py "$@"
