# Agentic AI Dynamic Tariff Optimization for EV Charging

Open Project 2026 | Society of Business

A three-agent ML pipeline that forecasts charging demand, applies dynamic per-kWh tariffs, and iteratively improves pricing through a monitoring feedback loop. Built on ACN-Data (US workplace sessions) and UrbanEV (Shenzhen charging network).

## Results

| Agent | Metric | Result |
|-------|--------|--------|
| Demand Prediction | R² | **0.95** |
| Demand Prediction | RMSE / MAE | **0.045 / 0.025** |
| Tariff Pricing | Revenue vs ₹15/kWh baseline | **+8.0%** |
| Tariff Pricing | Off-peak uplift | **+5.5%** |
| Monitoring & Learning | Peak wait reduction | **22.0%** |

**Data:** 900 ACN sessions + 2.1M UrbanEV records → 185K hourly slots

## Quick Start

```bash
pip install -r requirements.txt
python scripts/download_data.py
python scripts/run_pipeline.py
python scripts/verify_submission.py
```

## Project Structure

```
├── config.py              # Paths, pricing parameters, evaluation thresholds
├── scripts/
│   ├── run_pipeline.py    # End-to-end orchestrator
│   ├── download_data.py   # Fetch ACN + UrbanEV datasets
│   ├── robustness_checks.py
│   ├── generate_notebooks.py
│   ├── create_presentation.py
│   ├── prepare_submission.py
│   └── verify_submission.py
├── src/
│   ├── preprocessing/     # ACN + UrbanEV loaders, dataset harmonization
│   ├── features/          # Temporal and lag feature engineering
│   ├── agents/            # Demand, tariff, and monitoring agents
│   └── evaluation/        # EDA plots and metric export
├── notebooks/             # 5 Jupyter notebooks (pipeline stages)
├── data/                  # Raw, processed, and output artifacts
├── docs/                  # Executive summary, appendix, submission guide
└── models/                # Saved demand prediction model
```

## Architecture

```
Download → Preprocess → Feature Engineering
  → Demand Prediction → Tariff Pricing → Monitoring & Learning (5 episodes)
  → EDA → Metrics → Notebooks → Presentation → Submission package
```

## Documentation

- [Executive Summary](docs/EXECUTIVE_SUMMARY.md)
- [Assumptions & Limitations](docs/ASSUMPTIONS_AND_LIMITATIONS.md)
- [Appendix (Robustness)](docs/APPENDIX.md)
- [Submission Guide](docs/SUBMISSION_GUIDE.md)

## Key Implementation Note

UrbanEV occupancy columns map to traffic-zone `grid` IDs (not `information.num`). Correcting this mapping fixed inflated utilization (~96% → ~30%).
