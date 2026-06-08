# Executive Summary

## Project

**Agentic AI-Based Dynamic Tariff Optimization for EV Charging Networks**  
Open Project 2026 | Society of Business

## Problem

Fixed ₹/kWh tariffs cause peak congestion and off-peak waste. We built a 3-agent pricing engine on real ACN-Data and UrbanEV records.

## Key Results

| Agent | Metric | Result |
|-------|--------|--------|
| Demand Prediction | R² | **0.95** |
| Demand Prediction | RMSE / MAE | **0.045 / 0.025** |
| Tariff Pricing | Revenue vs ₹15/kWh baseline | **+8.0%** |
| Tariff Pricing | Off-Peak Uplift | **+5.5%** |
| Tariff Pricing | Utilization improvement | **30.3% → 31.0%** |
| Monitoring & Learning | Peak wait reduction | **22.0%** |
| Monitoring & Learning | Pricing efficiency gain | **+3.1%** over 5 episodes |

## Data

- **ACN-Data**: 900 sessions (Caltech + JPL)
- **UrbanEV**: 2.1M records, 247 Shenzhen zones
- **Unified**: 185K hourly slots, 21 features

## Business Insight

Shenzhen's network runs at moderate utilization (~30% occupancy). Case-spec surge/discount rules are extended with **shoulder pricing** (10 AM–11 PM, util ≥ 30%) and **idle-capacity load shifting** (+4% volume nudge on sub-30% slots). Together these raise revenue **+8%** vs the ₹15/kWh baseline while lifting off-peak delivery **+5.5%** and cutting modeled peak waits **22%**.

## Limitations

Price elasticity is modeled, not experimentally validated. ACN sample is smaller than the full API dataset. See `ASSUMPTIONS_AND_LIMITATIONS.md`.
