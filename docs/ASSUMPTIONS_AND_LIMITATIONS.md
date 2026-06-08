# Assumptions & Limitations

## Documented Assumptions

| Assumption | Value | Rationale |
|------------|-------|-----------|
| Baseline tariff | ₹15/kWh | Case specification benchmark |
| Energy procurement cost | ₹8/kWh | Industry estimate for operator margin analysis |
| Surge threshold | ≥80% utilization | Case specification |
| Discount threshold | ≤30% utilization | Case specification |
| Surge multiplier | 1.35× baseline | Case specification |
| Discount multiplier | 0.75× baseline | Case specification |
| Shoulder multiplier | 1.28× baseline | Extension for moderate congestion (10 AM–11 PM, util ≥ 30%) |
| Idle-capacity shift | +4% volume on util < 30% | Load-shifting nudge for underused slots |
| Price elasticity | Surge −0.10, discount −0.48, shoulder −0.08 | Literature-informed demand response model |
| Tariff bounds | ₹10–25/kWh | Consumer protection cap |
| Train/test split | 75/25 per station, chronological | Prevents temporal data leakage |
| Off-peak discount window | Hours 0–5 AM when util ≤ 30% | Case-spec deep off-peak discount |
| UrbanEV zone mapping | `grid` column (not `num`) | Corrects capacity denominator for utilization rate |

## Data Handling

- **ACN-Data**: API requires registration; static time-series mirror (tongxin-li/ACN-Data-Static) used as fallback for 900 sessions
- **UrbanEV**: Downloaded from ST-EVCDP GitHub repository; 5-minute intervals aggregated to hourly slots
- **Missing values**: Lag features imputed with column medians; sessions without timestamps dropped
- **Timezone**: All timestamps normalized to UTC-naive for cross-dataset alignment

## Limitations (No Causal Claims)

1. **Elasticity is modeled, not observed** — demand shifts from tariff changes are simulated, not A/B tested
2. **Queue length is a proxy** — derived from utilization exceeding 80%, not measured wait times
3. **Geographic heterogeneity** — ACN (US workplace) and UrbanEV (China urban) have different usage patterns; unified analysis uses normalized utilization metrics
4. **Currency normalization** — all pricing in ₹ per case spec; UrbanEV original prices in Yuan not directly used
5. **Monitoring loop** — episode improvements reflect parameter refinement on simulated outcomes, not live deployment

## What We Do NOT Claim

- That dynamic pricing *causes* specific revenue increases in production
- That our elasticity estimate is universally applicable
- That cross-dataset model transfer works without retraining
