"""Run robustness checks for appendix."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from config import DATA_OUTPUTS, DATA_PROCESSED, RANDOM_STATE
from src.features.engineering import engineer_features, get_feature_columns


def main() -> None:
    features = engineer_features(pd.read_csv(DATA_PROCESSED / "unified_dataset.csv"))
    cols = get_feature_columns()
    results = []

    # 1. Elasticity sensitivity
    from src.agents.tariff_pricing import TariffPricingAgent
    from src.agents.demand_prediction import DemandPredictionAgent

    demand = DemandPredictionAgent()
    demand.train(features)
    forecasts = demand.predict(features)

    for elasticity in [-0.2, -0.35, -0.5]:
        agent = TariffPricingAgent()
        pricing = agent.apply_pricing(forecasts, features)
        pricing["adjusted_kwh"] = pricing["kwh_delivered"] * np.clip(
            1 + elasticity * (pricing["dynamic_tariff"] / 15 - 1), 0.6, 1.4
        )
        pricing["dynamic_revenue"] = pricing["adjusted_kwh"] * pricing["dynamic_tariff"]
        baseline = pricing["kwh_delivered"].sum() * 15
        dynamic = pricing["dynamic_revenue"].sum()
        gain = (dynamic - baseline) / baseline * 100
        results.append({"check": "elasticity_sensitivity", "parameter": elasticity, "revenue_gain_pct": gain})

    # 2. Per-dataset performance
    for dataset in features["dataset"].unique():
        sub = features[features["dataset"] == dataset]
        split = int(len(sub) * 0.75)
        model = HistGradientBoostingRegressor(max_iter=200, random_state=RANDOM_STATE)
        model.fit(sub.iloc[:split][cols], sub.iloc[:split]["target_utilization"])
        preds = model.predict(sub.iloc[split:][cols])
        y = sub.iloc[split:]["target_utilization"]
        results.append({
            "check": "dataset_split",
            "parameter": dataset,
            "rmse": float(np.sqrt(mean_squared_error(y, preds))),
            "mae": float(mean_absolute_error(y, preds)),
            "r2": float(r2_score(y, preds)),
        })

    # 3. Alternative model comparison
    from sklearn.ensemble import GradientBoostingRegressor
    split_idx = int(len(features) * 0.75)
    X_train, X_test = features.iloc[:split_idx][cols], features.iloc[split_idx:][cols]
    y_train, y_test = features.iloc[:split_idx]["target_utilization"], features.iloc[split_idx:]["target_utilization"]

    for name, model in [
        ("HistGradientBoosting", HistGradientBoostingRegressor(max_iter=200, random_state=RANDOM_STATE)),
        ("GradientBoosting", GradientBoostingRegressor(n_estimators=100, random_state=RANDOM_STATE)),
    ]:
        model.fit(X_train, y_train)
        preds = model.predict(X_test)
        results.append({
            "check": "model_comparison",
            "parameter": name,
            "rmse": float(np.sqrt(mean_squared_error(y_test, preds))),
            "mae": float(mean_absolute_error(y_test, preds)),
            "r2": float(r2_score(y_test, preds)),
        })

    df = pd.DataFrame(results)
    DATA_OUTPUTS.mkdir(parents=True, exist_ok=True)
    out = DATA_OUTPUTS / "robustness_checks.csv"
    df.to_csv(out, index=False)
    print(f"Robustness checks saved: {out}")
    print(df.to_string(index=False))


if __name__ == "__main__":
    main()
