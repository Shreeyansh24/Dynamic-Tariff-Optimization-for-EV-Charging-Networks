"""Project configuration for OP'26 EV Charging Analytics."""

from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA_RAW = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"
DATA_OUTPUTS = ROOT / "data" / "outputs"
MODELS_DIR = ROOT / "models"

BASELINE_TARIFF_INR = 15.0
ENERGY_COST_INR = 8.0

SURGE_UTILIZATION_THRESHOLD = 0.80
DISCOUNT_UTILIZATION_THRESHOLD = 0.30
SURGE_MULTIPLIER = 1.35
DISCOUNT_MULTIPLIER = 0.75
MIN_TARIFF_INR = 10.0
MAX_TARIFF_INR = 25.0

OFF_PEAK_HOURS = tuple(range(0, 6))

SHOULDER_HOURS = tuple(range(10, 23))
SHOULDER_UTILIZATION_THRESHOLD = 0.30
SHOULDER_MULTIPLIER = 1.28

IDLE_CAPACITY_SHIFT = 1.04

SURGE_ELASTICITY = -0.10
DISCOUNT_ELASTICITY = -0.48
SHOULDER_ELASTICITY = -0.08
STANDARD_ELASTICITY = -0.04

ACN_SITES = ["caltech", "jpl"]
ACN_API_BASE = "https://ev.caltech.edu/api/v1/sessions"

ST_EVCDP_BASE = (
    "https://raw.githubusercontent.com/IntelligentSystemsLab/ST-EVCDP/main/datasets"
)
ST_EVCDP_FILES = [
    "information.csv",
    "time.csv",
    "occupancy.csv",
    "volume.csv",
    "duration.csv",
    "price.csv",
]

TIME_SLOT_MINUTES = 60
TRAIN_RATIO = 0.75
RANDOM_STATE = 42

METRIC_STANDARDS = {
    "demand_r2_min": 0.70,
    "demand_rmse_max": 0.15,
    "demand_mae_max": 0.08,
    "revenue_gain_min_pct": 5.0,
    "off_peak_uplift_min_pct": 5.0,
    "wait_reduction_min_pct": 10.0,
    "customer_response_min": 0.02,
    "efficiency_improvement_min_pct": 1.0,
}
