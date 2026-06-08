"""Download ACN-Data and UrbanEV datasets."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.preprocessing.acn_loader import download_acn_data
from src.preprocessing.urbanev_loader import download_urbanev_data


def main() -> None:
    print("=" * 60)
    print("OP'26 Data Download")
    print("=" * 60)

    print("\n[1/2] Downloading UrbanEV / ST-EVCDP datasets...")
    urbanev_files = download_urbanev_data()

    print("\n[2/2] Downloading ACN-Data sessions...")
    acn_files = download_acn_data(max_pages_per_site=400)

    print("\nDownload complete.")
    print(f"  UrbanEV files: {len(urbanev_files)}")
    print(f"  ACN sites:     {len(acn_files)}")


if __name__ == "__main__":
    main()
