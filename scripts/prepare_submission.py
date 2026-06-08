"""Package all OP'26 deliverables into submission folder."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SUBMISSION = ROOT / "submission"

INCLUDE_DIRS = ["src", "notebooks"]
INCLUDE_FILES = ["config.py", "requirements.txt", "README.md"]

OUTPUT_CSVS = [
    "evaluation_metrics.csv",
    "results_summary.json",
    "demand_forecasts.csv",
    "pricing_decisions.csv",
    "monitoring_episodes.csv",
    "pipeline_summary.csv",
    "pricing_signal_distribution.csv",
    "feature_importance.csv",
    "robustness_checks.csv",
]

OUTPUT_PNGS = [
    "eda_utilization_by_hour.png",
    "eda_weekday_weekend.png",
    "eda_dataset_comparison.png",
    "eda_pricing_outcomes.png",
    "eda_monitoring_learning.png",
]

PIPELINE_SCRIPTS = [
    "run_pipeline.py",
    "download_data.py",
    "robustness_checks.py",
    "generate_notebooks.py",
    "create_presentation.py",
]

DOCS = [
    "OP26_Analytics_Presentation.pptx",
    "EXECUTIVE_SUMMARY.md",
    "APPENDIX.md",
    "ASSUMPTIONS_AND_LIMITATIONS.md",
    "SUBMISSION_GUIDE.md",
]


def prepare() -> Path:
    if SUBMISSION.exists():
        shutil.rmtree(SUBMISSION)
    SUBMISSION.mkdir()

    for d in INCLUDE_DIRS:
        src = ROOT / d
        if src.exists():
            shutil.copytree(src, SUBMISSION / d)

    scripts_dir = SUBMISSION / "scripts"
    scripts_dir.mkdir()
    for fname in PIPELINE_SCRIPTS:
        src = ROOT / "scripts" / fname
        if src.exists():
            shutil.copy2(src, scripts_dir / fname)

    for f in INCLUDE_FILES:
        src = ROOT / f
        if src.exists():
            shutil.copy2(src, SUBMISSION / f)

    out_dir = SUBMISSION / "outputs"
    out_dir.mkdir()
    data_out = ROOT / "data" / "outputs"
    for fname in OUTPUT_CSVS:
        src = data_out / fname
        if src.exists():
            shutil.copy2(src, out_dir / fname)

    viz_dir = SUBMISSION / "visualizations"
    viz_dir.mkdir()
    for fname in OUTPUT_PNGS:
        src = data_out / fname
        if src.exists():
            shutil.copy2(src, viz_dir / fname)

    docs_dir = SUBMISSION / "docs"
    docs_dir.mkdir()
    for fname in DOCS:
        src = ROOT / "docs" / fname
        if src.exists():
            shutil.copy2(src, docs_dir / fname)

    readme = SUBMISSION / "SUBMISSION_README.md"
    readme.write_text(
        "# OP'26 Submission Package\n\n"
        "## Contents\n\n"
        "| Folder / File | Description |\n"
        "|---|---|\n"
        "| `notebooks/` | 5 Jupyter notebooks (preprocessing → agents) |\n"
        "| `src/` | Reproducible Python source code |\n"
        "| `scripts/run_pipeline.py` | One-command end-to-end pipeline |\n"
        "| `outputs/` | All metric CSVs and results JSON |\n"
        "| `visualizations/` | EDA and agent performance charts |\n"
        "| `docs/OP26_Analytics_Presentation.pptx` | 7-slide deck + cover + exec summary + appendix |\n"
        "| `docs/EXECUTIVE_SUMMARY.md` | One-page project summary |\n"
        "| `docs/APPENDIX.md` | Robustness checks |\n"
        "| `docs/ASSUMPTIONS_AND_LIMITATIONS.md` | Transparency document |\n\n"
        "## How to Reproduce\n\n"
        "```bash\npip install -r requirements.txt\npython scripts/run_pipeline.py\n```\n",
        encoding="utf-8",
    )

    print(f"Submission package ready: {SUBMISSION}")
    return SUBMISSION


if __name__ == "__main__":
    prepare()
