from __future__ import annotations

import sys
from pathlib import Path


def bundled_root() -> Path:
    if getattr(sys, "frozen", False):
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parents[2]


def assets_dir() -> Path:
    return bundled_root() / "assets"


def app_icon_path() -> Path | None:
    for name in ("app_icon.ico", "app_icon.png"):
        candidate = assets_dir() / name
        if candidate.exists():
            return candidate
    return None


def sevenzip_dir() -> Path:
    return bundled_root() / "vendor" / "7zip"


def sevenzip_binary() -> Path:
    candidates = [
        sevenzip_dir() / "7zz.exe",
        sevenzip_dir() / "7z.exe",
        sevenzip_dir() / "7za.exe",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "未找到内置 7-Zip 可执行文件。请先运行 scripts/fetch_7zip.py 下载供应商资源。"
    )


def sevenzip_license() -> Path | None:
    license_path = sevenzip_dir() / "License.txt"
    return license_path if license_path.exists() else None
