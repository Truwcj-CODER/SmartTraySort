#!/bin/sh
# Ha quyen xuong nguoi dung thuong nhung giu lai NET_ADMIN de tu dat dia chi mang.
set -e

APP_UID=${APP_UID:-1000}
APP_GID=${APP_GID:-1000}
set -- uvicorn app.main:app --host "${HTTP_HOST:-0.0.0.0}" --port "${HTTP_PORT:-8000}"

[ "$(id -u)" = "0" ] || exec "$@"

DROP="setpriv --reuid=$APP_UID --regid=$APP_GID --clear-groups"
CAPS="--inh-caps=+net_admin --ambient-caps=+net_admin"

# Khong duoc cap NET_ADMIN thi van chay, chi la phai tu dat IP ben ngoai.
if $DROP $CAPS true 2>/dev/null; then
    exec $DROP $CAPS "$@"
fi
echo "canh bao: khong co NET_ADMIN, se khong tu dat duoc dia chi mang" >&2
exec $DROP "$@"
