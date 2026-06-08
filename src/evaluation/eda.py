"""Exploratory data analysis visualizations."""

from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

sns.set_theme(style="whitegrid", palette="deep")
plt.rcParams.update({
    "figure.facecolor": "white",
    "axes.titlesize": 13,
    "axes.labelsize": 11,
    "font.family": "sans-serif",
})


def plot_demand_by_hour(df: pd.DataFrame, output_dir: Path) -> Path:
    hourly = df.groupby("hour")["charger_utilization_rate"].mean().reset_index()
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.barplot(data=hourly, x="hour", y="charger_utilization_rate", ax=ax, color="#2E86AB")
    ax.set_title("Average Charger Utilization by Hour of Day")
    ax.set_xlabel("Hour")
    ax.set_ylabel("Utilization Rate")
    ax.axhline(0.8, color="red", linestyle="--", label="Surge threshold (80%)")
    ax.axhline(0.3, color="green", linestyle="--", label="Discount threshold (30%)")
    ax.legend()
    out = output_dir / "eda_utilization_by_hour.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def plot_weekday_weekend(df: pd.DataFrame, output_dir: Path) -> Path:
    compare = (
        df.groupby(["is_weekend", "hour"])["charger_utilization_rate"]
        .mean()
        .reset_index()
    )
    compare["day_type"] = compare["is_weekend"].map({0: "Weekday", 1: "Weekend"})
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.lineplot(
        data=compare, x="hour", y="charger_utilization_rate", hue="day_type", ax=ax
    )
    ax.set_title("Weekday vs Weekend Utilization Patterns")
    ax.set_xlabel("Hour")
    ax.set_ylabel("Utilization Rate")
    out = output_dir / "eda_weekday_weekend.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def plot_dataset_comparison(df: pd.DataFrame, output_dir: Path) -> Path:
    compare = df.groupby("dataset")["charger_utilization_rate"].mean().reset_index()
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.barplot(data=compare, x="dataset", y="charger_utilization_rate", ax=ax)
    ax.set_title("Average Utilization: ACN vs UrbanEV")
    ax.set_ylabel("Utilization Rate")
    out = output_dir / "eda_dataset_comparison.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def plot_pricing_outcomes(pricing_df: pd.DataFrame, output_dir: Path) -> Path:
    by_signal = (
        pricing_df.groupby("pricing_signal")
        .agg(
            avg_tariff=("dynamic_tariff", "mean"),
            total_revenue=("dynamic_revenue", "sum"),
        )
        .reset_index()
    )
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))
    sns.barplot(data=by_signal, x="pricing_signal", y="avg_tariff", ax=axes[0])
    axes[0].set_title("Average Tariff by Pricing Signal")
    axes[0].set_ylabel("₹/kWh")
    sns.barplot(data=by_signal, x="pricing_signal", y="total_revenue", ax=axes[1])
    axes[1].set_title("Total Revenue by Pricing Signal")
    axes[1].set_ylabel("Revenue (₹)")
    out = output_dir / "eda_pricing_outcomes.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def plot_monitoring_learning(history_df: pd.DataFrame, output_dir: Path) -> Path:
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(
        history_df["episode"],
        history_df["pricing_efficiency_score"],
        marker="o",
        label="Pricing Efficiency",
    )
    ax.plot(
        history_df["episode"],
        history_df["revenue_gain_pct"],
        marker="s",
        label="Revenue Gain %",
    )
    ax.set_title("Monitoring Agent: Learning Loop Performance")
    ax.set_xlabel("Episode")
    ax.legend()
    out = output_dir / "eda_monitoring_learning.png"
    fig.tight_layout()
    fig.savefig(out, dpi=150)
    plt.close(fig)
    return out


def run_eda(
    feature_df: pd.DataFrame,
    pricing_df: pd.DataFrame | None = None,
    monitoring_df: pd.DataFrame | None = None,
    output_dir: Path | None = None,
) -> list[Path]:
    from config import DATA_OUTPUTS

    output_dir = output_dir or DATA_OUTPUTS
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = [
        plot_demand_by_hour(feature_df, output_dir),
        plot_weekday_weekend(feature_df, output_dir),
        plot_dataset_comparison(feature_df, output_dir),
    ]
    if pricing_df is not None:
        paths.append(plot_pricing_outcomes(pricing_df, output_dir))
    if monitoring_df is not None:
        paths.append(plot_monitoring_learning(monitoring_df, output_dir))
    return paths
