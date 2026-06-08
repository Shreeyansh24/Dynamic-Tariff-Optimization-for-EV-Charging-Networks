"""Tariff Pricing Agent — dynamic per-kWh pricing from demand forecasts."""

from __future__ import annotations

import numpy as np
import pandas as pd

import config
from src.agents.pricing_utils import calculate_dynamic_tariffs


class TariffPricingAgent:
    """Translates demand forecasts into optimal dynamic tariffs."""

    def __init__(self, baseline_tariff: float | None = None) -> None:
        self.baseline_tariff = baseline_tariff or config.BASELINE_TARIFF_INR
        self.metrics: dict[str, float] = {}

    def apply_pricing(
        self,
        forecasts: pd.DataFrame,
        actual_df: pd.DataFrame,
    ) -> pd.DataFrame:
        feature_cols = [
            "timestamp", "station_id", "kwh_delivered",
            "charger_utilization_rate", "session_count",
        ]
        if "hour" in actual_df.columns:
            feature_cols.append("hour")

        merged = forecasts.merge(actual_df[feature_cols], on=["timestamp", "station_id"], how="left")

        if "hour" in merged.columns:
            merged["hour"] = pd.to_numeric(merged["hour"], errors="coerce")
            merged["hour"] = merged["hour"].fillna(
                pd.to_datetime(merged["timestamp"]).dt.hour
            ).astype(int)
        else:
            merged["hour"] = pd.to_datetime(merged["timestamp"]).dt.hour

        merged["dynamic_tariff"] = calculate_dynamic_tariffs(
            predicted_utilization=merged["predicted_utilization"].values,
            congestion_probability=merged["congestion_probability"].values,
            hours=merged["hour"].values,
        )
        merged["baseline_tariff"] = self.baseline_tariff

        is_surge = merged["predicted_utilization"] >= config.SURGE_UTILIZATION_THRESHOLD
        is_discount = (
            merged["predicted_utilization"] <= config.DISCOUNT_UTILIZATION_THRESHOLD
        ) & merged["hour"].isin(config.OFF_PEAK_HOURS)
        is_shoulder = (
            (merged["predicted_utilization"] >= config.SHOULDER_UTILIZATION_THRESHOLD)
            & (merged["predicted_utilization"] < config.SURGE_UTILIZATION_THRESHOLD)
            & merged["hour"].isin(config.SHOULDER_HOURS)
        )

        elasticity = np.select(
            [is_surge, is_discount, is_shoulder],
            [
                config.SURGE_ELASTICITY,
                config.DISCOUNT_ELASTICITY,
                config.SHOULDER_ELASTICITY,
            ],
            default=config.STANDARD_ELASTICITY,
        )
        price_ratio = merged["dynamic_tariff"] / self.baseline_tariff
        demand_factor = np.clip(1 + elasticity * (price_ratio - 1), 0.70, 1.55)

        idle_mask = merged["charger_utilization_rate"] < config.DISCOUNT_UTILIZATION_THRESHOLD
        idle_shift = np.where(idle_mask, config.IDLE_CAPACITY_SHIFT, 1.0)

        merged["adjusted_kwh"] = merged["kwh_delivered"] * demand_factor * idle_shift
        merged["dynamic_revenue"] = merged["adjusted_kwh"] * merged["dynamic_tariff"]
        merged["baseline_revenue"] = merged["kwh_delivered"] * self.baseline_tariff
        merged["pricing_signal"] = np.select(
            [is_surge, is_discount, is_shoulder],
            ["surge", "discount", "shoulder"],
            default="standard",
        )
        return merged

    def evaluate(
        self,
        pricing_df: pd.DataFrame,
        off_peak_threshold: float | None = None,
    ) -> dict[str, float]:
        off_peak_threshold = off_peak_threshold or config.DISCOUNT_UTILIZATION_THRESHOLD

        baseline_rev = pricing_df["baseline_revenue"].sum()
        dynamic_rev = pricing_df["dynamic_revenue"].sum()
        revenue_gain_pct = (
            ((dynamic_rev - baseline_rev) / baseline_rev) * 100 if baseline_rev else 0.0
        )

        baseline_util = pricing_df["charger_utilization_rate"].mean()
        util_shift = np.where(
            pricing_df["pricing_signal"] == "surge", -0.04,
            np.where(pricing_df["pricing_signal"] == "discount", 0.10,
            np.where(pricing_df["pricing_signal"] == "shoulder", -0.02, 0.0)),
        )
        post_util = (pricing_df["charger_utilization_rate"] + util_shift).clip(0, 1)

        off_peak_mask = pricing_df["charger_utilization_rate"] < off_peak_threshold
        off_peak_before = pricing_df.loc[off_peak_mask, "kwh_delivered"].sum()
        off_peak_after = pricing_df.loc[off_peak_mask, "adjusted_kwh"].sum()
        off_peak_uplift_pct = (
            ((off_peak_after - off_peak_before) / off_peak_before) * 100
            if off_peak_before else 0.0
        )

        self.metrics = {
            "revenue_gain_pct": float(revenue_gain_pct),
            "baseline_utilization_rate": float(baseline_util),
            "post_pricing_utilization_rate": float(post_util.mean()),
            "off_peak_uplift_pct": float(off_peak_uplift_pct),
            "surge_slot_pct": float((pricing_df["pricing_signal"] == "surge").mean() * 100),
            "discount_slot_pct": float((pricing_df["pricing_signal"] == "discount").mean() * 100),
            "avg_dynamic_tariff_inr": float(pricing_df["dynamic_tariff"].mean()),
            "total_dynamic_revenue_inr": float(dynamic_rev),
            "total_baseline_revenue_inr": float(baseline_rev),
        }
        return self.metrics
