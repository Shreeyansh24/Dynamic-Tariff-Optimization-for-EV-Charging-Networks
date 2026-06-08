"""Pre-submission verification against OP'26 case standards."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd

from config import METRIC_STANDARDS

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"
results: list[tuple[str, str, str]] = []


def check(name: str, ok: bool, detail: str, warn_only: bool = False) -> None:
    results.append((PASS if ok else (WARN if warn_only else FAIL), name, detail))


def main() -> int:
    print("=" * 60)
    print("OP'26 Pre-Submission Verification")
    print("=" * 60)

    required_files = [
        "notebooks/01_data_preprocessing.ipynb",
        "notebooks/02_eda.ipynb",
        "notebooks/03_demand_prediction_agent.ipynb",
        "notebooks/04_tariff_pricing_agent.ipynb",
        "notebooks/05_monitoring_learning_agent.ipynb",
        "scripts/run_pipeline.py",
        "requirements.txt",
        "data/outputs/evaluation_metrics.csv",
        "data/outputs/demand_forecasts.csv",
        "data/outputs/pricing_decisions.csv",
        "data/outputs/monitoring_episodes.csv",
        "data/outputs/results_summary.json",
        "data/outputs/robustness_checks.csv",
        "docs/OP26_Analytics_Presentation.pptx",
        "docs/EXECUTIVE_SUMMARY.md",
        "docs/APPENDIX.md",
        "docs/ASSUMPTIONS_AND_LIMITATIONS.md",
    ]
    for rel in required_files:
        check(f"Deliverable: {rel}", (ROOT / rel).exists(), str(ROOT / rel))

    for png in [
        "eda_utilization_by_hour.png", "eda_weekday_weekend.png",
        "eda_dataset_comparison.png", "eda_pricing_outcomes.png",
        "eda_monitoring_learning.png",
    ]:
        p = ROOT / "data" / "outputs" / png
        check(f"Chart: {png}", p.exists() and p.stat().st_size > 5000,
              f"{p.stat().st_size if p.exists() else 0} bytes")

    metrics_path = ROOT / "data" / "outputs" / "evaluation_metrics.csv"
    md: dict[str, float] = {}
    if metrics_path.exists():
        m = pd.read_csv(metrics_path)
        md = dict(zip(m["metric"], m["value"]))

        check("Demand R2 >= standard",
              md.get("r2", 0) >= METRIC_STANDARDS["demand_r2_min"],
              f"R2={md.get('r2', 0):.4f} (min {METRIC_STANDARDS['demand_r2_min']})")
        check("Demand RMSE <= standard",
              md.get("rmse", 1) <= METRIC_STANDARDS["demand_rmse_max"],
              f"RMSE={md.get('rmse', 0):.4f} (max {METRIC_STANDARDS['demand_rmse_max']})")
        check("Demand MAE <= standard",
              md.get("mae", 1) <= METRIC_STANDARDS["demand_mae_max"],
              f"MAE={md.get('mae', 0):.4f} (max {METRIC_STANDARDS['demand_mae_max']})")
        check("Revenue gain >= standard",
              md.get("revenue_gain_pct", 0) >= METRIC_STANDARDS["revenue_gain_min_pct"],
              f"{md.get('revenue_gain_pct', 0):+.2f}% (min +{METRIC_STANDARDS['revenue_gain_min_pct']}%)")
        check("Off-peak uplift >= standard",
              md.get("off_peak_uplift_pct", 0) >= METRIC_STANDARDS["off_peak_uplift_min_pct"],
              f"{md.get('off_peak_uplift_pct', 0):+.2f}% (min +{METRIC_STANDARDS['off_peak_uplift_min_pct']}%)")
        check("Wait reduction >= standard",
              md.get("avg_wait_reduction_pct", 0) >= METRIC_STANDARDS["wait_reduction_min_pct"],
              f"{md.get('avg_wait_reduction_pct', 0):.1f}% (min {METRIC_STANDARDS['wait_reduction_min_pct']}%)")
        check("Customer response >= standard",
              md.get("customer_response_rate", 0) >= METRIC_STANDARDS["customer_response_min"],
              f"{md.get('customer_response_rate', 0):+.4f} (min {METRIC_STANDARDS['customer_response_min']})")
        check("Efficiency improvement >= standard",
              md.get("efficiency_improvement_pct", 0) >= METRIC_STANDARDS["efficiency_improvement_min_pct"],
              f"{md.get('efficiency_improvement_pct', 0):+.2f}% (min +{METRIC_STANDARDS['efficiency_improvement_min_pct']}%)")

    mon_path = ROOT / "data" / "outputs" / "monitoring_episodes.csv"
    if mon_path.exists():
        mon = pd.read_csv(mon_path)
        check("5 monitoring episodes", len(mon) == 5, f"{len(mon)} episodes")
        check("Learning curve improves efficiency",
              mon["pricing_efficiency_score"].iloc[-1] > mon["pricing_efficiency_score"].iloc[0],
              f"ep1={mon['pricing_efficiency_score'].iloc[0]:.2f} ep5={mon['pricing_efficiency_score'].iloc[-1]:.2f}")

    sub = ROOT / "submission"
    check("Submission folder", sub.exists(), str(sub))
    check("PPT in submission", (sub / "docs" / "OP26_Analytics_Presentation.pptx").exists(), "OK", warn_only=True)
    viz = len(list((sub / "visualizations").glob("*.png"))) if (sub / "visualizations").exists() else 0
    check("Charts in submission", viz >= 5, f"{viz} PNGs", warn_only=True)

    print()
    fails = warns = passes = 0
    for status, name, detail in results:
        icon = {"PASS": "+", "WARN": "!", "FAIL": "X"}[status]
        print(f"  [{icon}] {name}: {detail}")
        fails += status == FAIL
        warns += status == WARN
        passes += status == PASS

    print()
    print("=" * 60)
    print(f"Results: {passes} passed, {warns} warnings, {fails} failed")
    print("VERDICT:", "READY FOR SUBMISSION" if fails == 0 else "NEEDS FIXES")
    print("=" * 60)
    return fails


if __name__ == "__main__":
    sys.exit(main())
