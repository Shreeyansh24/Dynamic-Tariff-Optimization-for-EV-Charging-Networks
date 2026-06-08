# Appendix — Robustness Checks & Additional Analysis

## 1. Elasticity Sensitivity

| Elasticity (ε) | Revenue Gain % |
|----------------|----------------|
| −0.20 (low sensitivity) | **+5.7%** |
| −0.35 (moderate) | **+4.1%** |
| −0.50 (high sensitivity) | **+2.6%** |

Revenue gain remains positive across all tested elasticity values.

## 2. Per-Dataset Validation

| Dataset | RMSE | MAE | R² |
|---------|------|-----|-----|
| UrbanEV | 0.038 | 0.023 | **0.95** |
| ACN | 0.143 | 0.071 | 0.30 |

UrbanEV dominates sample size; ACN subset is smaller (900 sessions) with different utilization patterns.

## 3. Model Comparison

| Model | RMSE | MAE | R² |
|-------|------|-----|-----|
| **HistGradientBoosting** (selected) | 0.054 | 0.028 | **0.95** |
| GradientBoosting (benchmark) | 0.060 | 0.032 | 0.94 |

Both models perform comparably; HistGradientBoosting selected for speed on 185K+ rows.

## 4. Monitoring Learning Trajectory

| Episode | Revenue Gain % | Pricing Efficiency (INR/kWh) |
|---------|----------------|------------------------------|
| 1 | 8.0% | 16.10 |
| 5 | 11.1% | 16.61 |

Efficiency improves **+3.1%** over 5 learning episodes via surge/shoulder parameter refinement.

## 5. Additional Outputs

- `outputs/robustness_checks.csv` — full sensitivity tables
- `outputs/pricing_signal_distribution.csv` — surge / shoulder / discount / standard mix
- `outputs/feature_importance.csv` — top demand model drivers
- `visualizations/` — EDA and agent performance charts
