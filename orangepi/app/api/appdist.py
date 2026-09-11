# Phat ban app Android qua chinh server nay.
#
# Nha xuong khong co Play Store, ma di cam cap tung may thi khong ai lam noi.
# Nen server giu san mot file APK va mot to khai ben canh; app tu hoi, tu tai,
# tu goi trinh cai dat.
#
# Hai duong:
#   GET /api/app/latest    to khai: so hieu ban, ten ban, ma bam, dung luong
#   GET /api/app/download  chinh file APK
#
# To khai do scripts/publish_apk.sh sinh ra luc dong goi - server khong tu doc
# duoc so hieu ban trong file APK, va cung khong nen doc: mot cho sinh ra, moi
# noi doc lai, thi khong bao gio co chuyen so hieu mot dang ma file mot neo.
from __future__ import annotations

import json
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/app", tags=["app"])

UPDATES_DIR = Path(__file__).resolve().parent.parent / "updates"
MANIFEST = UPDATES_DIR / "latest.json"

APK_MEDIA_TYPE = "application/vnd.android.package-archive"


def _manifest() -> dict:
    if not MANIFEST.is_file():
        raise HTTPException(status_code=404, detail="chua co ban app nao duoc phat hanh")
    try:
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        log.warning("khong doc duoc %s: %s", MANIFEST, exc)
        raise HTTPException(status_code=500, detail="to khai ban app hong") from exc


@router.get("/latest")
async def latest() -> dict:
    return _manifest()


@router.get("/download")
async def download() -> FileResponse:
    data = _manifest()

    # Chi lay TEN file tu to khai, khong lay duong dan: to khai bi sua bay thi
    # cung khong doc duoc file nao ngoai thu muc nay.
    name = Path(data.get("file", "")).name
    apk = UPDATES_DIR / name
    if not name or not apk.is_file():
        raise HTTPException(status_code=404, detail="khong tim thay file APK")

    return FileResponse(apk, media_type=APK_MEDIA_TYPE, filename=name)
