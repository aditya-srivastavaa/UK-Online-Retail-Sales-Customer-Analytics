"""Download the UCI Online Retail II workbook to data/raw."""

from __future__ import annotations

import urllib.request
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
ARCHIVE = RAW_DIR / "online_retail_ii.zip"
SOURCE = RAW_DIR / "online_retail_II.xlsx"
URL = "https://archive.ics.uci.edu/static/public/502/online%2Bretail%2Bii.zip"


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    if SOURCE.exists():
        print(f"Dataset already present: {SOURCE}")
        return
    print("Downloading the UCI Online Retail II dataset...")
    request = urllib.request.Request(URL, headers={"User-Agent": "retail-analytics-portfolio/1.0"})
    with urllib.request.urlopen(request, timeout=90) as response, ARCHIVE.open("wb") as output:
        output.write(response.read())
    with zipfile.ZipFile(ARCHIVE) as archive:
        member = next((name for name in archive.namelist() if name.lower().endswith(".xlsx")), None)
        if member is None:
            raise RuntimeError("The UCI archive did not contain an Excel workbook.")
        SOURCE.write_bytes(archive.read(member))
    print(f"Dataset ready: {SOURCE}")


if __name__ == "__main__":
    main()
