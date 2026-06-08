"""Demand Prediction Agent — forecasts utilization and congestion."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

from config import RANDOM_STATE, TRAIN_RATIO
from src.features.engineering import get_feature_columns


@dataclass
class DemandForecast:
    timestamp: pd.Timestamp
    station_id: str
    predicted_utilization: float
    congestion_probability: float
    expected_load_kwh: float


class DemandPredictionAgent:
    """ML agent that predicts charging demand and station utilization."""

    def __init__(self) -> None:
        self.model = HistGradientBoostingRegressor(
            max_iter=300,
            max_depth=8,
            learning_rate=0.06,
            min_samples_leaf=20,
            l2_regularization=0.1,
            random_state=RANDOM_STATE,
        )
        self.load_model: HistGradientBoostingRegressor | None = None
        self.feature_cols = get_feature_columns()
        self.metrics: dict[str, float] = {}
        self.feature_importance: pd.DataFrame | None = None

    def _time_series_split(self, df: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        train_parts, test_parts = [], []
        for _, group in df.groupby("station_id"):
            split_idx = max(int(len(group) * TRAIN_RATIO), 1)
            train_parts.append(group.iloc[:split_idx])
            test_parts.append(group.iloc[split_idx:])
        return pd.concat(train_parts), pd.concat(test_parts)

    def train(self, feature_df: pd.DataFrame) -> dict[str, float]:
        train_df, test_df = self._time_series_split(feature_df)

        X_train = train_df[self.feature_cols]
        y_train = train_df["target_utilization"]
        X_test = test_df[self.feature_cols]
        y_test = test_df["target_utilization"]

        self.model.fit(X_train, y_train)
        preds = np.clip(self.model.predict(X_test), 0, 1)

        self.metrics = {
            "rmse": float(np.sqrt(mean_squared_error(y_test, preds))),
            "mae": float(mean_absolute_error(y_test, preds)),
            "r2": float(r2_score(y_test, preds)),
            "train_rows": float(len(train_df)),
            "test_rows": float(len(test_df)),
        }
        return self.metrics

    def predict(self, feature_df: pd.DataFrame) -> pd.DataFrame:
        X = feature_df[self.feature_cols]
        util_pred = np.clip(self.model.predict(X), 0, 1)
        congestion_prob = 1 / (1 + np.exp(-12 * (util_pred - 0.8)))

        if self.load_model is not None:
            expected_load = np.clip(self.load_model.predict(X), 0, None)
        else:
            median_kwh = feature_df["kwh_delivered"].median() or 1.0
            expected_load = util_pred * median_kwh * 1.5

        return pd.DataFrame(
            {
                "timestamp": feature_df["timestamp"].values,
                "station_id": feature_df["station_id"].values,
                "predicted_utilization": util_pred,
                "congestion_probability": congestion_prob,
                "expected_load_kwh": expected_load,
            }
        )

    def train_load_model(self, feature_df: pd.DataFrame) -> None:
        train_df, _ = self._time_series_split(feature_df)
        self.load_model = HistGradientBoostingRegressor(
            max_iter=200, max_depth=6, learning_rate=0.08, random_state=RANDOM_STATE
        )
        self.load_model.fit(train_df[self.feature_cols], train_df["kwh_delivered"])

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {
                "model": self.model,
                "load_model": self.load_model,
                "metrics": self.metrics,
                "feature_importance": self.feature_importance,
            },
            path,
        )

    def load(self, path: Path) -> None:
        bundle = joblib.load(path)
        self.model = bundle["model"]
        self.load_model = bundle.get("load_model")
        self.metrics = bundle.get("metrics", {})
        self.feature_importance = bundle.get("feature_importance")
