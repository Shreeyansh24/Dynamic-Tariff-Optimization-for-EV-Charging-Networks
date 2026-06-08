# OP'26 Presentation Outline

## Slide 1: Data Landscape & Preprocessing
- Two datasets: ACN-Data (900 US workplace sessions) + UrbanEV (247 Shenzhen zones, 5-min intervals)
- Harmonized to hourly station-level slots aligned by timestamp and station ID
- 21 engineered features: utilization rate, temporal encodings, lags, rolling stats
- **Assumption**: ₹15/kWh baseline; ₹8/kWh energy cost

## Slide 2: Key EDA Findings
- Intraday peaks in morning and afternoon utilization
- Weekday utilization higher than weekends (workplace pattern in ACN)
- UrbanEV shows spatial heterogeneity across Shenzhen zones
- Off-peak windows (0–6 AM) below 30% utilization → discount opportunity

## Slide 3: Demand Prediction Agent
- Model: Histogram Gradient Boosting on 21 temporal + lag features
- Metrics: RMSE 0.045, MAE 0.025, R² 0.95 on held-out 25% time-series split
- Outputs: predicted utilization, congestion probability, expected load

## Slide 4: Dynamic Tariff Optimization
- Surge (util ≥ 80%) → 1.35×; discount (util ≤ 30%) → 0.75×; shoulder pricing extension
- Price elasticity model simulates demand shift by signal type
- **+8.0%** revenue vs ₹15/kWh baseline; **+5.5%** off-peak uplift

## Slide 5: Monitoring & Learning Agent
- 5-episode feedback loop tracking wait reduction, response rate, pricing efficiency
- **22%** peak wait reduction; **+3.1%** pricing efficiency improvement over episodes

## Slide 6: Business & Policy Implications
- Dynamic pricing improves revenue and utilization vs flat tariffs
- Off-peak discounts shift load away from peak hours
- Surge caps (max ₹25/kWh) protect consumers
- Elasticity estimates are modeled, not experimentally validated

## Appendix
- Robustness checks (elasticity sensitivity)
- Cross-dataset limitations (US vs China)
- Full metric tables and EDA charts
