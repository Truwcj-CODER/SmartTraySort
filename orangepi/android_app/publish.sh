#!/usr/bin/env bash
# Dong goi ban phat hanh roi dat len server de dien thoai tu tai ve.
#
# Mot lenh lam het: build ban release da ky, chep sang app/updates/, va viet to
# khai latest.json canh no. App dang chay se thay ban moi ngay lan mo ke tiep.
#
#   ./publish.sh                 build roi phat hanh
#   ./publish.sh --notes "..."   kem theo cau mo ta hien trong hop thoai
#
# Doi so hieu ban truoc khi chay: versionCode va versionName trong
# app/build.gradle.kts. Quen tang versionCode thi app coi nhu khong co gi moi.
set -euo pipefail

cd "$(dirname "$0")"

NOTES=""
while [[ $# -gt 0 ]]; do
    case "$1" in
        --notes) NOTES="${2:-}"; shift 2 ;;
        *) echo "tham so la: $1" >&2; exit 2 ;;
    esac
done

: "${JAVA_HOME:=$HOME/.jdk/jdk-17.0.19+10}"
: "${ANDROID_HOME:=$HOME/Android/Sdk}"
export JAVA_HOME ANDROID_HOME

if [[ ! -f keystore.properties ]]; then
    echo "thieu keystore.properties - khong ky duoc ban phat hanh" >&2
    exit 1
fi

echo "==> build ban release"
./gradlew :app:assembleRelease --console=plain -q

APK="app/build/outputs/apk/release/app-release.apk"
[[ -f "$APK" ]] || { echo "khong thay $APK" >&2; exit 1; }

# Doc so hieu tu chinh file APK, khong doc tu build.gradle.kts: cai nam trong
# APK moi la cai dien thoai nhin thay.
AAPT="$(ls -d "$ANDROID_HOME"/build-tools/* | sort -V | tail -1)/aapt2"
BADGING="$("$AAPT" dump badging "$APK")"
VERSION_CODE="$(sed -n "s/.*versionCode='\([0-9]*\)'.*/\1/p" <<<"$BADGING" | head -1)"
VERSION_NAME="$(sed -n "s/.*versionName='\([^']*\)'.*/\1/p" <<<"$BADGING" | head -1)"

DEST="../app/updates"
FILE="smarttraysort-${VERSION_NAME}.apk"
mkdir -p "$DEST"

# Don ban cu di: thu muc nay duoc gan thang vao container, de lai chi ton the.
rm -f "$DEST"/*.apk
cp "$APK" "$DEST/$FILE"

SHA="$(sha256sum "$DEST/$FILE" | cut -d' ' -f1)"
SIZE="$(stat -c%s "$DEST/$FILE")"
NOW="$(date -Iseconds)"

python3 - "$DEST/latest.json" <<PY
import json, sys
json.dump({
    "version_code": $VERSION_CODE,
    "version_name": "$VERSION_NAME",
    "file": "$FILE",
    "sha256": "$SHA",
    "size": $SIZE,
    "notes": """$NOTES""",
    "published_at": "$NOW",
    "url": "/api/app/download",
}, open(sys.argv[1], "w", encoding="utf-8"), ensure_ascii=False, indent=2)
PY

echo
echo "==> da phat hanh $VERSION_NAME (code $VERSION_CODE)"
echo "    $DEST/$FILE"
echo "    $(numfmt --to=iec "$SIZE")  sha256 ${SHA:0:16}…"
echo
echo "Dien thoai se thay ban nay ngay lan mo app ke tiep."
echo "Tai thang bang trinh duyet: http://<ip-server>:8000/api/app/download"
