from __future__ import annotations

import shutil
import subprocess
import tempfile
import urllib.request
from pathlib import Path

SEVENZIP_VERSION = "26.00"
SEVENZIP_MSI_URL = (
    "https://github.com/ip7z/7zip/releases/download/26.00/7z2600-x64.msi"
)


def main() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    vendor_dir = repo_root / "vendor" / "7zip"

    with tempfile.TemporaryDirectory(prefix="autounzip-7zip-") as temp_dir_name:
        temp_dir = Path(temp_dir_name)
        msi_path = temp_dir / "7zip.msi"
        expanded_dir = temp_dir / "expanded"
        expanded_dir.mkdir(parents=True, exist_ok=True)

        print(f"Downloading {SEVENZIP_MSI_URL}")
        urllib.request.urlretrieve(SEVENZIP_MSI_URL, msi_path)
        subprocess.run(
            [
                "msiexec.exe",
                "/a",
                str(msi_path),
                "/qn",
                f"TARGETDIR={expanded_dir}",
            ],
            check=True,
        )

        extracted = expanded_dir / "Files" / "7-Zip"
        if not extracted.exists():
            raise FileNotFoundError(f"未找到 MSI 解包目录：{extracted}")

        if vendor_dir.exists():
            shutil.rmtree(vendor_dir)
        shutil.copytree(extracted, vendor_dir)
        (vendor_dir / "VERSION.txt").write_text(SEVENZIP_VERSION, encoding="utf-8")

    print(f"7-Zip vendor files extracted to {vendor_dir}")


if __name__ == "__main__":
    main()
