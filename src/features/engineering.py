"""Feature engineering for EV charging analytics."""

from __future__ import annotations

import numpy as np
import pandas as pd

from config import BASELINE_TARIFF_INR, ENERGY_COST_INR


def engineer_features(unified_df: pd.DataFrame) -> pd.DataFrame:
    """Add economically meaningful features per case specification."""
    df = unified_df.copy()
    df["timestamp"] = pd.to_datetime(df["timestamp"])

    # Temporal features (cyclical encoding improves ML performance)
    df["hour"] = df["timestamp"].dt.hour
    df["day_of_week"] = df["timestamp"].dt.dayofweek
    df["is_weekend"] = (df["day_of_week"] >= 5).astype(int)
    df["month"] = df["timestamp"].dt.month
    df["hour_sin"] = np.sin(2 * np.pi * df["hour"] / 24)
    df["hour_cos"] = np.cos(2 * np.pi * df["hour"] / 24)
    df["dow_sin"] = np.sin(2 * np.pi * df["day_of_week"] / 7)
    df["dow_cos"] = np.cos(2 * np.pi * df["day_of_week"] / 7)
    df["is_acn"] = (df["dataset"] == "ACN").astype(int)

    # Core operational features — use harmonized utilization when available
    if "utilization_rate" in df.columns:
        df["charger_utilization_rate"] = df["utilization_rate"].fillna(0).clip(0, 1)
    else:
        df["charger_utilization_rate"] = (
            df["charging_time_hr"] / df["available_time_hr"].replace(0, np.nan)
        ).fillna(0).clip(0, 1)

    df["revenue_per_session"] = (
        df["kwh_delivered"] * BASELINE_TARIFF_INR / df["session_count"].replace(0, np.nan)
    ).fillna(0)

    df["energy_cost_per_kwh"] = ENERGY_COST_INR
    df["revenue_per_kwh"] = BASELINE_TARIFF_INR

    df["queue_length_proxy"] = np.maximum(df["charger_utilization_rate"] - 0.8, 0) * 10

    df["occupancy_density"] = (
        df["session_count"] / df["available_time_hr"].replace(0, np.nan)
    ).fillna(0)

    df["period"] = pd.cut(
        df["hour"],
        bins=[-1, 6, 10, 16, 20, 23],
        labels=["off_peak_night", "morning_peak", "shoulder", "afternoon_peak", "evening"],
    )

    df = df.sort_values(["station_id", "timestamp"])
    for lag in [1, 2, 24]:
        df[f"util_lag_{lag}"] = df.groupby("station_id")["charger_utilization_rate"].shift(lag)
        df[f"kwh_lag_{lag}"] = df.groupby("station_id")["kwh_delivered"].shift(lag)

    df["util_roll_24h"] = (
        df.groupby("station_id")["charger_utilization_rate"]
        .transform(lambda s: s.rolling(24, min_periods=1).mean())
    )
    df["kwh_roll_24h"] = (
        df.groupby("station_id")["kwh_delivered"]
        .transform(lambda s: s.rolling(24, min_periods=1).mean())
    )

    df["target_utilization"] = (
        df.groupby("station_id")["charger_utilization_rate"].shift(-1)
    )

    lag_cols = [c for c in df.columns if "lag_" in c or "roll_" in c]
    for col in lag_cols:
        df[col] = df[col].fillna(df[col].median())

    df = df.dropna(subset=["target_utilization"])
    return df.reset_index(drop=True)


def get_feature_columns() -> list[str]:
    return [
        "hour",
        "day_of_week",
        "is_weekend",
        "month",
        "hour_sin",
        "hour_cos",
        "dow_sin",
        "dow_cos",
        "is_acn",
        "charger_utilization_rate",
        "kwh_delivered",
        "session_count",
        "occupancy_density",
        "queue_length_proxy",
        "util_lag_1",
        "util_lag_2",
        "util_lag_24",
        "kwh_lag_1",
        "kwh_lag_24",
        "util_roll_24h",
        "kwh_roll_24h",
    ]
