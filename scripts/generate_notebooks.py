"""Generate submission Jupyter notebooks from pipeline modules."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
NB_DIR = ROOT / "notebooks"


def _cell(cell_type: str, source: str) -> dict:
    return {
        "cell_type": cell_type,
        "metadata": {},
        "source": [line + "\n" for line in source.split("\n")],
        **({"outputs": [], "execution_count": None} if cell_type == "code" else {}),
    }


def _write_nb(name: str, cells: list[dict]) -> None:
    nb = {
        "nbformat": 4,
        "nbformat_minor": 5,
        "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"}},
        "cells": cells,
    }
    path = NB_DIR / name
    path.write_text(json.dumps(nb, indent=1), encoding="utf-8")
    print(f"Created {path}")


def main() -> None:
    NB_DIR.mkdir(parents=True, exist_ok=True)

    _write_nb("01_data_preprocessing.ipynb", [
        _cell("markdown", "# OP'26 — Data Preprocessing\n\nLoad ACN-Data and UrbanEV, harmonize to unified hourly slots."),
        _cell("code", "import sys\nfrom pathlib import Path\nROOT = Path('..').resolve()\nsys.path.insert(0, str(ROOT))\n\nfrom src.preprocessing.acn_loader import load_acn_sessions\nfrom src.preprocessing.urbanev_loader import load_urbanev_data, urbanev_to_long_format\nfrom src.preprocessing.harmonize import build_unified_dataset\nfrom config import DATA_PROCESSED, DATA_RAW"),
        _cell("code", "acn_df = load_acn_sessions()\nurbanev_raw = load_urbanev_data()\nurbanev_long = urbanev_to_long_format(urbanev_raw)\nunified = build_unified_dataset(acn_df, urbanev_long)\n\nprint(f'ACN sessions: {len(acn_df):,}')\nprint(f'UrbanEV records: {len(urbanev_long):,}')\nprint(f'Unified slots: {len(unified):,}')\nunified.head()"),
        _cell("code", "unified.to_csv(DATA_PROCESSED / 'unified_dataset.csv', index=False)\nacn_df.to_csv(DATA_PROCESSED / 'acn_sessions.csv', index=False)"),
    ])

    _write_nb("02_eda.ipynb", [
        _cell("markdown", "# OP'26 — Exploratory Data Analysis\n\nTemporal demand patterns and pricing implications."),
        _cell("code", "import sys\nfrom pathlib import Path\nROOT = Path('..').resolve()\nsys.path.insert(0, str(ROOT))\n\nimport pandas as pd\nfrom src.features.engineering import engineer_features\nfrom src.evaluation.eda import run_eda\nfrom config import DATA_PROCESSED, DATA_OUTPUTS"),
        _cell("code", "unified = pd.read_csv(DATA_PROCESSED / 'unified_dataset.csv')\nfeatures = engineer_features(unified)\nfeatures.head()"),
        _cell("code", "paths = run_eda(features, output_dir=DATA_OUTPUTS)\nfor p in paths:\n    print(p)"),
        _cell("code", "features.groupby('hour')['charger_utilization_rate'].mean().plot(kind='bar', title='Utilization by Hour')"),
    ])

    _write_nb("03_demand_prediction_agent.ipynb", [
        _cell("markdown", "# OP'26 — Demand Prediction Agent\n\nForecast utilization, congestion probability, and expected load."),
        _cell("code", "import sys\nfrom pathlib import Path\nROOT = Path('..').resolve()\nsys.path.insert(0, str(ROOT))\n\nimport pandas as pd\nfrom src.features.engineering import engineer_features\nfrom src.agents.demand_prediction import DemandPredictionAgent\nfrom config import DATA_PROCESSED, DATA_OUTPUTS, MODELS_DIR"),
        _cell("code", "unified = pd.read_csv(DATA_PROCESSED / 'unified_dataset.csv')\nfeatures = engineer_features(unified)\n\nagent = DemandPredictionAgent()\nmetrics = agent.train(features)\nmetrics"),
        _cell("code", "forecasts = agent.predict(features)\nforecasts.to_csv(DATA_OUTPUTS / 'demand_forecasts.csv', index=False)\nforecasts.describe()"),
    ])

    _write_nb("04_tariff_pricing_agent.ipynb", [
        _cell("markdown", "# OP'26 — Tariff Pricing Agent\n\nDynamic tariffs: surge ≥80%, discount ≤30% vs ₹15/kWh baseline."),
        _cell("code", "import sys\nfrom pathlib import Path\nROOT = Path('..').resolve()\nsys.path.insert(0, str(ROOT))\n\nimport pandas as pd\nfrom src.agents.tariff_pricing import TariffPricingAgent\nfrom config import DATA_OUTPUTS"),
        _cell("code", "from config import DATA_PROCESSED\n\nforecasts = pd.read_csv(DATA_OUTPUTS / 'demand_forecasts.csv')\nfeatures = pd.read_csv(DATA_PROCESSED / 'features.csv')\n\nagent = TariffPricingAgent()\npricing = agent.apply_pricing(forecasts, features)\nmetrics = agent.evaluate(pricing)\nmetrics"),
        _cell("code", "pricing.to_csv(DATA_OUTPUTS / 'pricing_decisions.csv', index=False)\npricing['pricing_signal'].value_counts()"),
    ])

    _write_nb("05_monitoring_learning_agent.ipynb", [
        _cell("markdown", "# OP'26 — Monitoring & Learning Agent\n\nFeedback loop evaluating pricing decisions over episodes."),
        _cell("code", "import sys\nfrom pathlib import Path\nROOT = Path('..').resolve()\nsys.path.insert(0, str(ROOT))\n\nimport pandas as pd\nfrom src.agents.tariff_pricing import TariffPricingAgent\nfrom src.agents.monitoring_learning import MonitoringLearningAgent\nfrom config import DATA_OUTPUTS"),
        _cell("code", "pricing = pd.read_csv(DATA_OUTPUTS / 'pricing_decisions.csv')\nagent = TariffPricingAgent()\ntariff_metrics = agent.evaluate(pricing)\n\nmonitor = MonitoringLearningAgent()\nhistory = monitor.run_feedback_loop(pricing, tariff_metrics, n_episodes=5)\nhistory"),
        _cell("code", "history.to_csv(DATA_OUTPUTS / 'monitoring_episodes.csv', index=False)\nmonitor.metrics"),
    ])


if __name__ == "__main__":
    main()
