"""Monitoring & Learning Agent — feedback loop for pricing decisions."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

import config
from src.agents.pricing_utils import calculate_dynamic_tariffs


@dataclass
class EpisodeResult:
    episode: int
    avg_wait_reduction_pct: float
    customer_response_rate: float
    pricing_efficiency_score: float
    revenue_gain_pct: float
    utilization_rate: float


@dataclass
class MonitoringLearningAgent:
    """Evaluates pricing outcomes and refines agent parameters over episodes."""

    learning_rate: float = 0.08
    episode_history: list[EpisodeResult] = field(default_factory=list)
    surge_adjustment: float = 0.0
    discount_adjustment: float = 0.0
    metrics: dict[str, float] = field(default_factory=dict)

    def _apply_learned_pricing(self, pricing_df: pd.DataFrame) -> pd.DataFrame:
        df = pricing_df.copy()
        if "hour" not in df.columns:
            df["hour"] = pd.to_datetime(df["timestamp"]).dt.hour

        surge_mult = config.SURGE_MULTIPLIER + self.surge_adjustment
        discount_mult = max(config.DISCOUNT_MULTIPLIER + self.discount_adjustment, 0.65)
        shoulder_mult = config.SHOULDER_MULTIPLIER + self.surge_adjustment * 0.55

        df["dynamic_tariff"] = calculate_dynamic_tariffs(
            predicted_utilization=df["predicted_utilization"].values,
            congestion_probability=df["congestion_probability"].values,
            hours=df["hour"].values,
            surge_multiplier=surge_mult,
            discount_multiplier=discount_mult,
            shoulder_multiplier=shoulder_mult,
        )

        surge_mask = df["predicted_utilization"] >= config.SURGE_UTILIZATION_THRESHOLD
        discount_mask = (
            (df["predicted_utilization"] <= config.DISCOUNT_UTILIZATION_THRESHOLD)
            & df["hour"].isin(config.OFF_PEAK_HOURS)
        )
        shoulder_mask = (
            (df["predicted_utilization"] >= config.SHOULDER_UTILIZATION_THRESHOLD)
            & (df["predicted_utilization"] < config.SURGE_UTILIZATION_THRESHOLD)
            & df["hour"].isin(config.SHOULDER_HOURS)
        )
        price_ratio = df["dynamic_tariff"] / config.BASELINE_TARIFF_INR
        elasticity = np.select(
            [surge_mask, discount_mask, shoulder_mask],
            [
                config.SURGE_ELASTICITY + self.surge_adjustment * 0.08,
                config.DISCOUNT_ELASTICITY - self.discount_adjustment * 0.5,
                config.SHOULDER_ELASTICITY,
            ],
            default=config.STANDARD_ELASTICITY,
        )
        demand_factor = np.clip(1 + elasticity * (price_ratio - 1), 0.70, 1.55)

        idle_mask = df["charger_utilization_rate"] < config.DISCOUNT_UTILIZATION_THRESHOLD
        idle_shift = np.where(
            idle_mask,
            config.IDLE_CAPACITY_SHIFT + self.discount_adjustment * 0.15,
            1.0,
        )
        idle_shift = np.clip(idle_shift, 1.0, 1.12)

        df["adjusted_kwh"] = df["kwh_delivered"] * demand_factor * idle_shift
        df["dynamic_revenue"] = df["adjusted_kwh"] * df["dynamic_tariff"]
        df["baseline_revenue"] = df["kwh_delivered"] * config.BASELINE_TARIFF_INR
        df["pricing_signal"] = np.select(
            [surge_mask, discount_mask, shoulder_mask],
            ["surge", "discount", "shoulder"],
            default="standard",
        )
        return df

    def evaluate_episode(self, episode: int, pricing_df: pd.DataFrame) -> EpisodeResult:
        ep_df = self._apply_learned_pricing(pricing_df)

        peak_mask = ep_df["predicted_utilization"] >= 0.8
        queue_before = ep_df.loc[peak_mask, "charger_utilization_rate"].apply(
            lambda u: max(u - 0.8, 0) * 10
        )
        surge_at_peak = ep_df.loc[peak_mask, "pricing_signal"] == "surge"
        queue_after = queue_before * np.where(surge_at_peak, 0.78, 1.0)

        wait_before = queue_before.mean() if len(queue_before) else 0.0
        wait_after = queue_after.mean() if len(queue_before) else 0.0
        wait_reduction_pct = (
            ((wait_before - wait_after) / wait_before) * 100 if wait_before else 0.0
        )

        discount_mask = ep_df["pricing_signal"] == "discount"
        if discount_mask.any():
            volume_change = (
                ep_df.loc[discount_mask, "adjusted_kwh"] - ep_df.loc[discount_mask, "kwh_delivered"]
            ) / ep_df.loc[discount_mask, "kwh_delivered"].replace(0, np.nan)
            response_rate = float(volume_change.mean())
        else:
            response_rate = 0.0

        total_kwh = ep_df["adjusted_kwh"].sum()
        total_rev = ep_df["dynamic_revenue"].sum()
        baseline_rev = ep_df["baseline_revenue"].sum()
        efficiency = total_rev / total_kwh if total_kwh else 0.0
        revenue_gain = (
            ((total_rev - baseline_rev) / baseline_rev) * 100 if baseline_rev else 0.0
        )

        util_shift = np.where(
            ep_df["pricing_signal"] == "surge", -0.04,
            np.where(ep_df["pricing_signal"] == "discount", 0.10,
            np.where(ep_df["pricing_signal"] == "shoulder", -0.02, 0.0)),
        )
        post_util = float((ep_df["charger_utilization_rate"] + util_shift).clip(0, 1).mean())

        return EpisodeResult(
            episode=episode,
            avg_wait_reduction_pct=float(wait_reduction_pct),
            customer_response_rate=float(response_rate),
            pricing_efficiency_score=float(efficiency),
            revenue_gain_pct=float(revenue_gain),
            utilization_rate=post_util,
        )

    def learn(self, episode_result: EpisodeResult) -> dict[str, float]:
        target_rev = config.METRIC_STANDARDS["revenue_gain_min_pct"]

        if episode_result.revenue_gain_pct < target_rev:
            self.surge_adjustment += self.learning_rate
        else:
            self.surge_adjustment += self.learning_rate * 0.65

        if episode_result.avg_wait_reduction_pct < 15:
            self.surge_adjustment += self.learning_rate * 0.25

        if (
            episode_result.customer_response_rate
            < config.METRIC_STANDARDS["customer_response_min"]
            and episode_result.revenue_gain_pct < target_rev
        ):
            self.discount_adjustment -= self.learning_rate * 0.35

        if (
            episode_result.utilization_rate < 0.32
            and episode_result.revenue_gain_pct < target_rev
        ):
            self.discount_adjustment -= self.learning_rate * 0.25

        self.surge_adjustment = float(np.clip(self.surge_adjustment, 0.0, 0.30))
        self.discount_adjustment = float(np.clip(self.discount_adjustment, -0.10, 0.05))
        return {
            "surge_adjustment": self.surge_adjustment,
            "discount_adjustment": self.discount_adjustment,
        }

    def run_feedback_loop(
        self,
        pricing_df: pd.DataFrame,
        tariff_metrics: dict[str, float],
        n_episodes: int = 5,
    ) -> pd.DataFrame:
        del tariff_metrics  # retained for API compatibility
        self.surge_adjustment = 0.0
        self.discount_adjustment = 0.0
        self.episode_history = []
        records = []

        for ep in range(1, n_episodes + 1):
            result = self.evaluate_episode(ep, pricing_df)
            self.episode_history.append(result)
            adjustments = self.learn(result)
            records.append({
                "episode": result.episode,
                "avg_wait_reduction_pct": result.avg_wait_reduction_pct,
                "customer_response_rate": result.customer_response_rate,
                "pricing_efficiency_score": result.pricing_efficiency_score,
                "revenue_gain_pct": result.revenue_gain_pct,
                "utilization_rate": result.utilization_rate,
                "surge_adjustment": adjustments["surge_adjustment"],
                "discount_adjustment": adjustments["discount_adjustment"],
            })

        history_df = pd.DataFrame(records)
        ep1_eff = history_df["pricing_efficiency_score"].iloc[0]
        ep5_eff = history_df["pricing_efficiency_score"].iloc[-1]
        self.metrics = {
            "avg_wait_reduction_pct": float(history_df["avg_wait_reduction_pct"].mean()),
            "customer_response_rate": float(history_df["customer_response_rate"].mean()),
            "pricing_efficiency_score": float(ep5_eff),
            "final_revenue_gain_pct": float(history_df["revenue_gain_pct"].iloc[-1]),
            "efficiency_improvement_pct": float(
                ((ep5_eff - ep1_eff) / ep1_eff) * 100
            ) if ep1_eff else 0.0,
            "episode_count": int(len(history_df)),
        }
        return history_df
