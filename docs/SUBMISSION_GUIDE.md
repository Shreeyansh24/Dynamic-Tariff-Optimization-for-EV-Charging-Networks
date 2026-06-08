# OP'26 Submission Guide

Per the case specification, submit the following via the Google Form (once submitted, cannot be altered).

## Required Deliverables

### 1. Code / Notebooks

Upload the **`submission/`** folder (or zip it) containing:

| Item | Location |
|------|----------|
| 5 Jupyter notebooks | `submission/notebooks/` |
| Source code | `submission/src/` |
| Pipeline scripts | `submission/scripts/` |
| Requirements | `submission/requirements.txt` |

### 2. Output CSVs (scores & metrics)

| File | Description |
|------|-------------|
| `outputs/evaluation_metrics.csv` | All agent metrics (RMSE, MAE, R², revenue gain, etc.) |
| `outputs/demand_forecasts.csv` | Demand predictions |
| `outputs/pricing_decisions.csv` | Dynamic tariff decisions |
| `outputs/monitoring_episodes.csv` | Learning loop history |
| `outputs/robustness_checks.csv` | Appendix sensitivity analysis |
| `outputs/results_summary.json` | Headline results |

### 3. Presentation Deck

| File | Description |
|------|-------------|
| `docs/OP26_Analytics_Presentation.pptx` | Full deck |

**Slide structure (per case spec):**
- Cover page (not counted in 5–7)
- Executive summary (not counted)
- **6 content slides:** Data, EDA, Demand Agent, Tariff Agent, Monitoring Agent, Business Implications
- Appendix (not counted)
- Visualizations embedded in slides

### 4. Supporting Documents

| File | Purpose |
|------|---------|
| `docs/EXECUTIVE_SUMMARY.md` | One-page overview |
| `docs/APPENDIX.md` | Robustness checks |
| `docs/ASSUMPTIONS_AND_LIMITATIONS.md` | Transparency (required by case) |

### 5. Visualizations

| Folder | Contents |
|--------|----------|
| `submission/visualizations/` | 5 EDA/agent charts (PNG) |

---

## How to Package

```bash
python scripts/run_pipeline.py
python scripts/prepare_submission.py
```

```powershell
Compress-Archive -Path submission\* -DestinationPath OP26_Submission.zip -Force
```

---

## Final Results Summary

| Metric | Value |
|--------|-------|
| Demand Prediction R² | **0.95** |
| Demand Prediction RMSE | **0.045** |
| Demand Prediction MAE | **0.025** |
| Revenue Gain vs ₹15/kWh | **+8.0%** |
| Off-Peak Uplift | **+5.5%** |
| Peak Wait Reduction | **22.0%** |
| Pricing Efficiency | **16.6 INR/kWh** |

---

## Reproduce Everything

```bash
pip install -r requirements.txt
python scripts/download_data.py
python scripts/run_pipeline.py
python scripts/verify_submission.py
```
