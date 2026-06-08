"""Consolidate and export evaluation metrics."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def save_all_metrics(
    demand_metrics: dict,
    tariff_metrics: dict,
    monitoring_metrics: dict,
    output_dir: Path,
) -> Path:
    """Write all agent metrics to a single CSV."""
    rows = []

    for name, value in demand_metrics.items():
        rows.append({"agent": "Demand Prediction", "metric": name, "value": value})

    for name, value in tariff_metrics.items():
        rows.append({"agent": "Tariff Pricing", "metric": name, "value": value})

    for name, value in monitoring_metrics.items():
        rows.append({"agent": "Monitoring & Learning", "metric": name, "value": value})

    df = pd.DataFrame(rows)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "evaluation_metrics.csv"
    df.to_csv(out_path, index=False)
    return out_path
