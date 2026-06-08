from __future__ import annotations

import numpy as np

import config


def calculate_dynamic_tariffs(
    predicted_utilization: np.ndarray,
    congestion_probability: np.ndarray,
    hours: np.ndarray,
    surge_multiplier: float | None = None,
    discount_multiplier: float | None = None,
    shoulder_multiplier: float | None = None,
) -> np.ndarray:
    """
    Case-spec dynamic tariffs with shoulder pricing extension:
    - Surge: util >= 80%
    - Discount: util <= 30% during off-peak (load shifting)
    - Shoulder: moderate congestion during peak hours
    - Standard: baseline otherwise
    """
    surge_multiplier = surge_multiplier or config.SURGE_MULTIPLIER
    discount_multiplier = discount_multiplier or config.DISCOUNT_MULTIPLIER
    shoulder_multiplier = shoulder_multiplier or config.SHOULDER_MULTIPLIER

    util = np.asarray(predicted_utilization, dtype=float)
    prob = np.asarray(congestion_probability, dtype=float)
    hour_arr = np.asarray(hours, dtype=int)

    tariff = np.full_like(util, config.BASELINE_TARIFF_INR, dtype=float)
    is_off_peak = np.isin(hour_arr, config.OFF_PEAK_HOURS)
    is_shoulder_hour = np.isin(hour_arr, config.SHOULDER_HOURS)
    is_surge = util >= config.SURGE_UTILIZATION_THRESHOLD
    is_discount = (util <= config.DISCOUNT_UTILIZATION_THRESHOLD) & is_off_peak
    is_shoulder = (
        (util >= config.SHOULDER_UTILIZATION_THRESHOLD)
        & (util < config.SURGE_UTILIZATION_THRESHOLD)
        & is_shoulder_hour
    )

    tariff[is_surge] = config.BASELINE_TARIFF_INR * (
        surge_multiplier + 0.05 * np.clip(prob[is_surge], 0.0, 1.0)
    )
    tariff[is_discount] = config.BASELINE_TARIFF_INR * discount_multiplier
    tariff[is_shoulder] = config.BASELINE_TARIFF_INR * shoulder_multiplier

    return np.clip(tariff, config.MIN_TARIFF_INR, config.MAX_TARIFF_INR)
