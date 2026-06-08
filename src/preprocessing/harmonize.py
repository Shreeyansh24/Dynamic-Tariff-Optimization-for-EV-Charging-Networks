"""Harmonize ACN session data and UrbanEV interval data."""

from __future__ import annotations

import numpy as np
import pandas as pd

from config import TIME_SLOT_MINUTES


def _hour_floor(ts: pd.Series) -> pd.Series:
    return ts.dt.floor(f"{TIME_SLOT_MINUTES}min")


def acn_to_hourly_slots(acn_df: pd.DataFrame) -> pd.DataFrame:
    """Expand ACN sessions across occupied hours for realistic utilization."""
    df = acn_df.copy()
    df["connection_time"] = pd.to_datetime(df["connection_time"], utc=True).dt.tz_localize(None)
    df["disconnect_time"] = pd.to_datetime(df["disconnect_time"], utc=True, errors="coerce").dt.tz_localize(None)
    df["disconnect_time"] = df["disconnect_time"].fillna(
        df["connection_time"] + pd.to_timedelta(df["session_duration_hr"], unit="h")
    )

    rows: list[dict] = []
    for _, s in df.iterrows():
        start = s["connection_time"].floor("h")
        end = s["disconnect_time"].ceil("h")
        if pd.isna(start) or pd.isna(end) or end <= start:
            end = start + pd.Timedelta(hours=1)

        hours = pd.date_range(start, end - pd.Timedelta(seconds=1), freq="h")
        if len(hours) == 0:
            hours = pd.DatetimeIndex([start])

        share = s["kwh_delivered"] / len(hours) if len(hours) else s["kwh_delivered"]
        duration_share = s["session_duration_hr"] / len(hours)

        for ts in hours:
            rows.append({
                "dataset": "ACN",
                "site_id": s["site_id"],
                "station_id": s["station_id"],
                "timestamp": ts,
                "session_count": 1,
                "kwh_delivered": share,
                "charging_time_hr": min(duration_share, 1.0),
            })

    if not rows:
        return pd.DataFrame()

    expanded = pd.DataFrame(rows)
    grouped = (
        expanded.groupby(["dataset", "site_id", "station_id", "timestamp"], as_index=False)
        .agg(
            session_count=("session_count", "sum"),
            kwh_delivered=("kwh_delivered", "sum"),
            charging_time_hr=("charging_time_hr", "sum"),
        )
    )
    grouped["available_time_hr"] = 1.0
    grouped["utilization_rate"] = grouped["charging_time_hr"].clip(0, 1)
    return grouped


def urbanev_to_hourly_slots(urbanev_long: pd.DataFrame) -> pd.DataFrame:
    """Aggregate UrbanEV 5-minute data to hourly station slots."""
    df = urbanev_long.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True).dt.tz_localize(None)
    df["timestamp"] = _hour_floor(df["timestamp"])

    if "count" in df.columns:
        df["capacity"] = df["count"].fillna(1).replace(0, 1)
    else:
        df["capacity"] = 1.0

    df["occupancy"] = df["occupancy"].fillna(0)
    df["volume_kwh"] = df.get("volume_kwh", 0).fillna(0)
    df["duration_hr"] = df.get("duration_hr", 0).fillna(0)

    agg_spec: dict = {
        "session_count": ("occupancy", "mean"),
        "kwh_delivered": ("volume_kwh", "sum"),
        "charging_time_hr": ("duration_hr", "sum"),
        "occupancy": ("occupancy", "mean"),
        "capacity": ("capacity", "first"),
    }
    if "price" in df.columns:
        agg_spec["price"] = ("price", "mean")

    grouped = df.groupby(
        ["dataset", "site_id", "station_id", "timestamp"], as_index=False
    ).agg(**agg_spec)

    grouped["available_time_hr"] = 1.0
    grouped["utilization_rate"] = (
        grouped["occupancy"] / grouped["capacity"].replace(0, 1)
    ).clip(0, 1)
    grouped["session_count"] = grouped["occupancy"]

    return grouped[
        [
            "dataset", "site_id", "station_id", "timestamp",
            "session_count", "kwh_delivered", "charging_time_hr",
            "available_time_hr", "utilization_rate",
        ]
    ].copy()


def build_unified_dataset(
    acn_df: pd.DataFrame,
    urbanev_long: pd.DataFrame,
) -> pd.DataFrame:
    """Create unified analytical base aligned by timestamp and station."""
    acn_slots = acn_to_hourly_slots(acn_df)
    urbanev_slots = urbanev_to_hourly_slots(urbanev_long)

    common_cols = [
        "dataset", "site_id", "station_id", "timestamp",
        "session_count", "kwh_delivered", "charging_time_hr",
        "available_time_hr", "utilization_rate",
    ]

    unified = pd.concat(
        [acn_slots[common_cols], urbanev_slots[common_cols]],
        ignore_index=True,
    )
    unified["timestamp"] = pd.to_datetime(unified["timestamp"], utc=True).dt.tz_localize(None)
    unified = unified.sort_values(["timestamp", "station_id"]).reset_index(drop=True)
    return unified
