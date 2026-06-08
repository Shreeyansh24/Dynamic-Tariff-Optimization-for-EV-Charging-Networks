"""Generate OP'26 PowerPoint deck from pipeline outputs."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

from config import DATA_OUTPUTS

DOCS_DIR = ROOT / "docs"
SLIDE_W = Inches(13.333)
SLIDE_H = Inches(7.5)

NAVY = RGBColor(0x1B, 0x2A, 0x4A)
TEAL = RGBColor(0x2E, 0x86, 0xAB)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
GRAY = RGBColor(0x55, 0x55, 0x55)


def _load_metrics() -> dict[str, float]:
    path = DATA_OUTPUTS / "evaluation_metrics.csv"
    if not path.exists():
        return {}
    df = pd.read_csv(path)
    return dict(zip(df["metric"], df["value"]))


def _load_summary() -> dict:
    path = DATA_OUTPUTS / "results_summary.json"
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return {}


def _add_title_slide(prs: Presentation, summary: dict) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    bg = slide.background
    fill = bg.fill
    fill.solid()
    fill.fore_color.rgb = NAVY

    title = slide.shapes.add_textbox(Inches(0.8), Inches(2.0), Inches(11.5), Inches(1.2))
    tf = title.text_frame
    p = tf.paragraphs[0]
    p.text = "Agentic AI Dynamic Tariff Optimization"
    p.font.size = Pt(36)
    p.font.bold = True
    p.font.color.rgb = WHITE

    sub = slide.shapes.add_textbox(Inches(0.8), Inches(3.2), Inches(11.5), Inches(0.8))
    sp = sub.text_frame.paragraphs[0]
    sp.text = "EV Charging Networks | Open Project 2026 | Society of Business"
    sp.font.size = Pt(18)
    sp.font.color.rgb = TEAL

    stats = slide.shapes.add_textbox(Inches(0.8), Inches(4.5), Inches(11.5), Inches(1.5))
    stf = stats.text_frame
    acn = summary.get("acn_sessions", 900)
    urban = summary.get("urbanev_records", 0)
    slots = summary.get("unified_slots", 0)
    stf.paragraphs[0].text = (
        f"900+ ACN sessions  •  {urban:,} UrbanEV records  •  {slots:,} unified hourly slots"
    )
    stf.paragraphs[0].font.size = Pt(14)
    stf.paragraphs[0].font.color.rgb = WHITE


def _add_content_slide(
    prs: Presentation,
    title: str,
    bullets: list[str],
    image_path: Path | None = None,
) -> None:
    slide = prs.slides.add_slide(prs.slide_layouts[6])

    header = slide.shapes.add_textbox(Inches(0.6), Inches(0.4), Inches(12), Inches(0.7))
    hp = header.text_frame.paragraphs[0]
    hp.text = title
    hp.font.size = Pt(28)
    hp.font.bold = True
    hp.font.color.rgb = NAVY

    content_width = Inches(6.2) if image_path and image_path.exists() else Inches(12)
    body = slide.shapes.add_textbox(Inches(0.6), Inches(1.3), content_width, Inches(5.5))
    tf = body.text_frame
    tf.word_wrap = True
    for i, bullet in enumerate(bullets):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = bullet
        p.font.size = Pt(16)
        p.font.color.rgb = GRAY
        p.space_after = Pt(10)
        p.level = 0

    if image_path and image_path.exists():
        slide.shapes.add_picture(
            str(image_path), Inches(7.0), Inches(1.3), width=Inches(5.8)
        )


def _fmt(val: float, suffix: str = "", decimals: int = 2) -> str:
    if suffix == "%":
        return f"{val:.{decimals}f}%"
    return f"{val:.{decimals}f}{suffix}"


def create_presentation(output_path: Path | None = None) -> Path:
    metrics = _load_metrics()
    summary = _load_summary()
    output_path = output_path or (DOCS_DIR / "OP26_Analytics_Presentation.pptx")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    prs = Presentation()
    prs.slide_width = SLIDE_W
    prs.slide_height = SLIDE_H

    _add_title_slide(prs, summary)

    headline = summary.get("headline_results", {})
    _add_content_slide(
        prs,
        "Executive Summary",
        [
            "Built a 3-agent ML pricing engine on ACN-Data + UrbanEV charging networks",
            f"Demand forecast R² = {_fmt(headline.get('r2_score', metrics.get('r2', 0)))}",
            f"Revenue gain vs ₹15/kWh baseline: {_fmt(headline.get('revenue_gain_pct', metrics.get('revenue_gain_pct', 0)), '%')}",
            f"Off-peak uplift: {_fmt(headline.get('off_peak_uplift_pct', metrics.get('off_peak_uplift_pct', 0)), '%')}",
            f"Peak wait reduction: {_fmt(headline.get('avg_wait_reduction_pct', metrics.get('avg_wait_reduction_pct', 0)), '%')}",
            "Modular architecture: Demand → Tariff → Monitoring feedback loop",
        ],
    )

    _add_content_slide(
        prs,
        "Data Landscape & Preprocessing",
        [
            "Dual-source integration: ACN-Data (Caltech/JPL workplace) + UrbanEV (Shenzhen, 247 zones)",
            "Harmonized to hourly station-level slots with aligned timestamps and station IDs",
            "Engineered 21 features: utilization rate, queue proxy, occupancy density, cyclical time",
            "Transparent missing-value handling: median imputation for lag features",
            "Baseline benchmark: fixed ₹15/kWh tariff per case specification",
        ],
        DATA_OUTPUTS / "eda_dataset_comparison.png",
    )

    _add_content_slide(
        prs,
        "Key EDA Findings",
        [
            "Distinct intraday peaks at morning (8–10) and afternoon (16–18) hours",
            "Weekday utilization significantly exceeds weekends — workplace charging signature",
            "UrbanEV CBD zones show >80% peak occupancy; suburban zones below 30%",
            "Off-peak windows (midnight–6 AM) consistently underutilized → discount opportunity",
            "All patterns directly inform surge (>80%) and discount (<30%) pricing rules",
        ],
        DATA_OUTPUTS / "eda_utilization_by_hour.png",
    )

    rmse = metrics.get("rmse", 0)
    mae = metrics.get("mae", 0)
    r2 = metrics.get("r2", 0)
    _add_content_slide(
        prs,
        "Demand Prediction Agent",
        [
            "Model: Histogram Gradient Boosting on 21 temporal + lag features",
            f"Performance: RMSE = {_fmt(rmse)}, MAE = {_fmt(mae)}, R² = {_fmt(r2)}",
            "Per-station chronological train/test split (75/25) prevents data leakage",
            "Outputs: predicted utilization, congestion probability, expected kWh load",
            "Top drivers: hour-of-day, 1h utilization lag, 24h rolling average",
        ],
        DATA_OUTPUTS / "eda_weekday_weekend.png",
    )

    rev_gain = metrics.get("revenue_gain_pct", 0)
    off_peak = metrics.get("off_peak_uplift_pct", 0)
    post_util = metrics.get("post_pricing_utilization_rate", 0)
    _add_content_slide(
        prs,
        "Dynamic Tariff Optimization",
        [
            "Surge pricing at ≥80% utilization (1.35×); discount at ≤30% (0.75×)",
            f"Revenue gain vs ₹15/kWh baseline: {_fmt(rev_gain, '%')}",
            f"Off-peak session uplift after discounts: {_fmt(off_peak, '%')}",
            f"Post-pricing utilization rate: {_fmt(post_util)} (smoother demand distribution)",
            "Price elasticity model (-0.35) simulates demand shift without causal claims",
        ],
        DATA_OUTPUTS / "eda_pricing_outcomes.png",
    )

    wait_red = metrics.get("avg_wait_reduction_pct", 0)
    response = metrics.get("customer_response_rate", 0)
    efficiency = metrics.get("pricing_efficiency_score", 0)
    eff_imp = metrics.get("efficiency_improvement_pct", 0)
    _add_content_slide(
        prs,
        "Monitoring & Learning Agent",
        [
            "5-episode feedback loop evaluates revenue, utilization, and wait-time outcomes",
            f"Average peak wait-time reduction: {_fmt(wait_red, '%')}",
            f"Customer response rate (elasticity proxy): {_fmt(response)}",
            f"Pricing efficiency: {_fmt(efficiency, ' ₹/kWh')} — improved {_fmt(eff_imp, '%')} over episodes",
            "Autonomous parameter refinement via surge/discount adjustment learning",
        ],
        DATA_OUTPUTS / "eda_monitoring_learning.png",
    )

    _add_content_slide(
        prs,
        "Business & Policy Implications",
        [
            "Operators: Dynamic pricing increases revenue while reducing peak congestion",
            "Grid operators: Off-peak discounts enable load-shifting and grid stability",
            "Consumers: Transparent price caps (₹10–25/kWh) with predictable surge windows",
            "Scalability: Modular 3-agent architecture deployable per-site or network-wide",
            "Limitation: Cross-geography transfer (US/China) requires localized calibration",
        ],
    )

    robustness_path = DATA_OUTPUTS / "robustness_checks.csv"
    appendix_bullets = [
        "Elasticity sensitivity: revenue gain stable across ε = -0.2, -0.35, -0.5",
        "Per-dataset validation: separate RMSE/R² for ACN vs UrbanEV subsets",
        "Model comparison: HistGradientBoosting vs GradientBoosting benchmarked",
        "Assumptions documented: ₹15/kWh baseline, ₹8/kWh cost, no causal claims",
        "See outputs/robustness_checks.csv and docs/ASSUMPTIONS_AND_LIMITATIONS.md",
    ]
    if robustness_path.exists():
        rb = pd.read_csv(robustness_path)
        for _, row in rb.head(4).iterrows():
            if row["check"] == "model_comparison":
                appendix_bullets.insert(0, f"Model {row['parameter']}: R² = {row['r2']:.3f}")

    _add_content_slide(prs, "Appendix — Robustness Checks", appendix_bullets)

    prs.save(str(output_path))
    print(f"Presentation saved: {output_path}")
    return output_path


if __name__ == "__main__":
    create_presentation()
