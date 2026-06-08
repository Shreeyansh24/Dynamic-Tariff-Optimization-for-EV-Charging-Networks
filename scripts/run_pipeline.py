"""End-to-end OP'26 EV Charging Analytics pipeline."""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Avoid Windows console Unicode errors
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd

from config import DATA_OUTPUTS, DATA_PROCESSED, DATA_RAW, MODELS_DIR
from src.agents.demand_prediction import DemandPredictionAgent
from src.agents.monitoring_learning import MonitoringLearningAgent
from src.agents.tariff_pricing import TariffPricingAgent
from src.evaluation.eda import run_eda
from src.evaluation.metrics import save_all_metrics
from src.features.engineering import engineer_features
from src.preprocessing.acn_loader import load_acn_sessions
from src.preprocessing.harmonize import build_unified_dataset
from src.preprocessing.urbanev_loader import load_urbanev_data, urbanev_to_long_format


def ensure_data() -> None:
    acn_dir = DATA_RAW / "acn"
    urbanev_dir = DATA_RAW / "urbanev"
    need_urbanev = not (urbanev_dir / "occupancy.csv").exists()
    need_acn = not list(acn_dir.glob("*_sessions.json")) if acn_dir.exists() else True
    if need_urbanev or need_acn:
        print("Data not found — running download...")
        from scripts.download_data import main as download_main
        download_main()


def _save_results_summary(
    acn_count: int,
    urbanev_count: int,
    unified_count: int,
    demand_metrics: dict,
    tariff_metrics: dict,
    monitoring_metrics: dict,
) -> None:
    summary = {
        "project": "OP'26 EV Charging Dynamic Tariff Optimization",
        "acn_sessions": acn_count,
        "urbanev_records": urbanev_count,
        "unified_slots": unified_count,
        "demand_prediction": demand_metrics,
        "tariff_pricing": tariff_metrics,
        "monitoring_learning": monitoring_metrics,
        "headline_results": {
            "r2_score": demand_metrics.get("r2"),
            "revenue_gain_pct": tariff_metrics.get("revenue_gain_pct"),
            "off_peak_uplift_pct": tariff_metrics.get("off_peak_uplift_pct"),
            "avg_wait_reduction_pct": monitoring_metrics.get("avg_wait_reduction_pct"),
            "pricing_efficiency_inr_per_kwh": monitoring_metrics.get("pricing_efficiency_score"),
        },
    }
    out = DATA_OUTPUTS / "results_summary.json"
    out.write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")


def main() -> None:
    print("=" * 60)
    print("OP'26 EV Charging Analytics Pipeline")
    print("=" * 60)

    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    DATA_OUTPUTS.mkdir(parents=True, exist_ok=True)
    MODELS_DIR.mkdir(parents=True, exist_ok=True)

    print("\n[1/7] Loading datasets...")
    ensure_data()

    acn_df = load_acn_sessions(output_csv=DATA_PROCESSED / "acn_sessions.csv")
    urbanev_raw = load_urbanev_data()
    urbanev_long = urbanev_to_long_format(urbanev_raw)
    urbanev_long.to_csv(DATA_PROCESSED / "urbanev_long.csv", index=False)

    print(f"  ACN sessions:    {len(acn_df):,}")
    print(f"  UrbanEV records: {len(urbanev_long):,}")

    print("\n[2/7] Harmonizing datasets...")
    unified = build_unified_dataset(acn_df, urbanev_long)
    unified.to_csv(DATA_PROCESSED / "unified_dataset.csv", index=False)
    print(f"  Unified slots:   {len(unified):,}")

    print("\n[3/7] Feature engineering...")
    features = engineer_features(unified)
    features.to_csv(DATA_PROCESSED / "features.csv", index=False)
    print(f"  Feature rows:    {len(features):,}")

    print("\n[4/7] Training Demand Prediction Agent...")
    demand_agent = DemandPredictionAgent()
    demand_metrics = demand_agent.train(features)
    demand_agent.train_load_model(features)
    demand_agent.save(MODELS_DIR / "demand_agent.joblib")

    if demand_agent.feature_importance is not None:
        demand_agent.feature_importance.to_csv(
            DATA_OUTPUTS / "feature_importance.csv", index=False
        )

    forecasts = demand_agent.predict(features)
    forecasts.to_csv(DATA_OUTPUTS / "demand_forecasts.csv", index=False)

    print(f"  RMSE: {demand_metrics['rmse']:.4f}")
    print(f"  MAE:  {demand_metrics['mae']:.4f}")
    print(f"  R²:   {demand_metrics['r2']:.4f}")

    print("\n[5/7] Running Tariff Pricing Agent...")
    tariff_agent = TariffPricingAgent()
    pricing_df = tariff_agent.apply_pricing(forecasts, features)
    tariff_metrics = tariff_agent.evaluate(pricing_df)
    pricing_df.to_csv(DATA_OUTPUTS / "pricing_decisions.csv", index=False)

    signal_dist = pricing_df["pricing_signal"].value_counts(normalize=True) * 100
    signal_dist.to_csv(DATA_OUTPUTS / "pricing_signal_distribution.csv")

    print(f"  Revenue Gain:     {tariff_metrics['revenue_gain_pct']:.2f}%")
    print(f"  Off-Peak Uplift:  {tariff_metrics['off_peak_uplift_pct']:.2f}%")
    print(f"  Post Utilization: {tariff_metrics['post_pricing_utilization_rate']:.4f}")

    print("\n[6/7] Running Monitoring & Learning Agent...")
    monitoring_agent = MonitoringLearningAgent()
    monitoring_history = monitoring_agent.run_feedback_loop(
        pricing_df, tariff_metrics, n_episodes=5
    )
    monitoring_history.to_csv(DATA_OUTPUTS / "monitoring_episodes.csv", index=False)

    print(f"  Avg Wait Reduction: {monitoring_agent.metrics['avg_wait_reduction_pct']:.2f}%")
    print(f"  Pricing Efficiency: {monitoring_agent.metrics['pricing_efficiency_score']:.2f} INR/kWh")
    print(f"  Efficiency Improve: {monitoring_agent.metrics['efficiency_improvement_pct']:.2f}%")

    print("\n[7/7] Generating outputs & presentation...")
    run_eda(features, pricing_df, monitoring_history, DATA_OUTPUTS)

    metrics_path = save_all_metrics(
        demand_metrics,
        tariff_metrics,
        monitoring_agent.metrics,
        DATA_OUTPUTS,
    )

    _save_results_summary(
        len(acn_df), len(urbanev_long), len(unified),
        demand_metrics, tariff_metrics, monitoring_agent.metrics,
    )

    summary = pd.DataFrame([
        {"stage": "ACN Sessions", "count": len(acn_df)},
        {"stage": "UrbanEV Records", "count": len(urbanev_long)},
        {"stage": "Unified Slots", "count": len(unified)},
        {"stage": "Feature Rows", "count": len(features)},
        {"stage": "Forecasts", "count": len(forecasts)},
        {"stage": "Pricing Decisions", "count": len(pricing_df)},
    ])
    summary.to_csv(DATA_OUTPUTS / "pipeline_summary.csv", index=False)

    print("Running robustness checks...")
    from scripts.robustness_checks import main as robustness_main
    robustness_main()

    print("Generating notebooks...")
    from scripts.generate_notebooks import main as nb_main
    nb_main()

    try:
        from scripts.create_presentation import create_presentation
        ppt_path = create_presentation()
    except ImportError:
        print("  python-pptx not installed — run: pip install python-pptx")
        ppt_path = None

    print("Packaging submission folder...")
    from scripts.prepare_submission import prepare
    sub_path = prepare()

    print("\n" + "=" * 60)
    print("Pipeline complete!")
    print(f"  Metrics:       {metrics_path}")
    print(f"  Presentation:  {ppt_path or 'N/A'}")
    print(f"  Submission:    {sub_path}")
    print(f"  Outputs:       {DATA_OUTPUTS}")
    print("=" * 60)


if __name__ == "__main__":
    main()
