"""Load UrbanEV / ST-EVCDP charging pile data."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import requests

from config import DATA_RAW, ST_EVCDP_BASE, ST_EVCDP_FILES


def download_urbanev_data(
    files: list[str] | None = None,
    output_dir: Path | None = None,
    timeout: int = 300,
) -> dict[str, Path]:
    """Download ST-EVCDP CSV files from GitHub."""
    files = files or ST_EVCDP_FILES
    output_dir = output_dir or (DATA_RAW / "urbanev")
    output_dir.mkdir(parents=True, exist_ok=True)

    saved: dict[str, Path] = {}
    for fname in files:
        url = f"{ST_EVCDP_BASE}/{fname}"
        out_path = output_dir / fname
        print(f"[UrbanEV] Downloading {fname}...")
        try:
            resp = requests.get(url, timeout=timeout, stream=True)
            resp.raise_for_status()
            with open(out_path, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
            saved[fname] = out_path
            print(f"[UrbanEV] Saved {fname} ({out_path.stat().st_size / 1e6:.1f} MB)")
        except requests.RequestException as exc:
            print(f"[UrbanEV] Failed to download {fname}: {exc}")

    return saved


def load_urbanev_data(data_dir: Path | None = None) -> dict[str, pd.DataFrame]:
    """Load ST-EVCDP CSV files into dataframes."""
    data_dir = data_dir or (DATA_RAW / "urbanev")
    result: dict[str, pd.DataFrame] = {}

    for fname in ST_EVCDP_FILES:
        path = data_dir / fname
        if not path.exists():
            continue
        key = fname.replace(".csv", "")
        result[key] = pd.read_csv(path)

    if "time" in result:
        t = result["time"]
        if {"year", "month", "day", "hour", "minute", "second"}.issubset(t.columns):
            result["time"]["timestamp"] = pd.to_datetime(
                t[["year", "month", "day", "hour", "minute", "second"]].rename(
                    columns={
                        "year": "year",
                        "month": "month",
                        "day": "day",
                        "hour": "hour",
                        "minute": "minute",
                        "second": "second",
                    }
                )
            )
        else:
            time_col = t.columns[0]
            result["time"]["timestamp"] = pd.to_datetime(t[time_col])

    return result


def urbanev_to_long_format(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Melt zone-level wide matrices into long 5-minute interval records."""
    if "occupancy" not in data or "time" not in data:
        raise ValueError("occupancy.csv and time.csv are required")

    timestamps = data["time"]["timestamp"].reset_index(drop=True)
    zone_cols = [
        c for c in data["occupancy"].columns
        if str(c).lower() not in {"time", "timestamp"}
    ]

    frames = []
    for metric_name, df_key in [
        ("occupancy", "occupancy"),
        ("volume_kwh", "volume"),
        ("duration_hr", "duration"),
        ("price", "price"),
    ]:
        if df_key not in data:
            continue
        metric_df = data[df_key][zone_cols].copy()
        metric_df["row_idx"] = range(len(metric_df))
        long_df = metric_df.melt(
            id_vars=["row_idx"],
            value_vars=zone_cols,
            var_name="zone_id",
            value_name=metric_name,
        )
        long_df["timestamp"] = long_df["row_idx"].map(timestamps)
        frames.append(long_df.drop(columns=["row_idx"]))

    merged = frames[0]
    for frame in frames[1:]:
        metric_col = [c for c in frame.columns if c not in {"zone_id", "timestamp"}][0]
        merged = merged.merge(
            frame[["zone_id", "timestamp", metric_col]],
            on=["zone_id", "timestamp"],
            how="left",
        )

    if "information" in data:
        # Occupancy CSV columns are traffic-zone grid IDs, not information.num
        info = data["information"].rename(columns={"grid": "zone_id"})
        info["zone_id"] = info["zone_id"].astype(str)
        merged["zone_id"] = merged["zone_id"].astype(str)
        merged = merged.merge(info, on="zone_id", how="left")

    merged["dataset"] = "UrbanEV"
    merged["site_id"] = "shenzhen"
    merged["station_id"] = merged["zone_id"].astype(str)
    merged = merged.sort_values(["timestamp", "zone_id"]).reset_index(drop=True)
    return merged
