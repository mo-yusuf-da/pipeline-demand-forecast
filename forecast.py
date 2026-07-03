"""
Pipeline Demand Forecast — 30/60-Day Moving Average
-----------------------------------------------------
Uses the cleaned Keystone Pipeline dataset (output/keystone_clean.csv,
produced by analyze.py) to project throughput for the next two months
using a simple moving-average method, and documents the assumptions,
method, and variance drivers behind the forecast.

This is intentionally a simple, transparent method — not a machine
learning model — chosen because it's defensible, explainable, and
appropriate for a short exploratory forecasting exercise.

Author: Mo Yusuf
"""

import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

CLEAN_DATA_PATH = Path("../pipeline-throughput-analysis/output/keystone_clean.csv")
# Fallback if run from inside the same project folder as the source data
LOCAL_FALLBACK = Path("keystone_clean.csv")

OUTPUT_DIR = Path("output")
FORECAST_CSV = OUTPUT_DIR / "forecast.csv"
FORECAST_CHART = OUTPUT_DIR / "forecast_chart.png"
FORECAST_NARRATIVE = OUTPUT_DIR / "forecast_narrative.txt"

FORECAST_WINDOW = 3       # months of trailing history used to build the forecast
FORECAST_HORIZON = 2      # months ahead to project (approx. 30/60 days)


def load_data() -> pd.DataFrame:
    path = CLEAN_DATA_PATH if CLEAN_DATA_PATH.exists() else LOCAL_FALLBACK
    if not path.exists():
        raise FileNotFoundError(
            "Could not find keystone_clean.csv. Copy it into this folder, "
            "or run this script from a location where "
            "../pipeline-throughput-analysis/output/keystone_clean.csv exists."
        )
    df = pd.read_csv(path, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)
    print(f"Loaded {len(df)} monthly records from {path}")
    return df


def build_forecast(df: pd.DataFrame) -> pd.DataFrame:
    """
    Moving-average forecast: project each future month as the average of
    the trailing FORECAST_WINDOW months of actual throughput. This is a
    naive but transparent method — each forecasted month uses only real,
    already-known actuals, with no extrapolated trend or seasonality.
    """
    history = df[["date", "throughput"]].copy()
    history["type"] = "actual"

    last_date = history["date"].max()
    trailing_avg = history["throughput"].tail(FORECAST_WINDOW).mean()

    future_rows = []
    for i in range(1, FORECAST_HORIZON + 1):
        future_date = last_date + pd.DateOffset(months=i)
        future_rows.append({"date": future_date, "throughput": trailing_avg, "type": "forecast"})

    forecast_df = pd.DataFrame(future_rows)
    combined = pd.concat([history, forecast_df], ignore_index=True)

    print(f"Trailing {FORECAST_WINDOW}-month average used as forecast basis: {trailing_avg:.2f}")
    print(f"Forecast months: {[r['date'].strftime('%Y-%m') for r in future_rows]}")

    return combined


def compute_variance_context(df: pd.DataFrame) -> dict:
    """Quantify recent volatility so the forecast narrative can honestly
    describe how much the actuals have varied, rather than implying
    false precision in the projection."""
    recent = df["throughput"].tail(12)
    return {
        "recent_12mo_mean": recent.mean(),
        "recent_12mo_std": recent.std(),
        "recent_12mo_min": recent.min(),
        "recent_12mo_max": recent.max(),
    }


def make_chart(combined: pd.DataFrame, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(11, 6))

    actual = combined[combined["type"] == "actual"]
    forecast = combined[combined["type"] == "forecast"]

    # Plot actuals
    ax.plot(actual["date"], actual["throughput"], label="Actual Throughput", linewidth=1.5)

    # Bridge the gap visually by including the last actual point in the forecast line
    bridge = pd.concat([actual.tail(1), forecast])
    ax.plot(bridge["date"], bridge["throughput"], label="Forecast (3-mo moving average)",
            linewidth=2.5, linestyle="--", marker="o")

    # Only show the last ~3 years for readability
    cutoff = combined["date"].max() - pd.DateOffset(years=3)
    ax.set_xlim(cutoff, combined["date"].max() + pd.DateOffset(months=1))

    ax.set_title("Keystone Pipeline — 30/60-Day Throughput Forecast")
    ax.set_xlabel("Date")
    ax.set_ylabel("Throughput")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    print(f"Chart saved to {out_path}")


def write_narrative(combined: pd.DataFrame, variance_ctx: dict, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    forecast = combined[combined["type"] == "forecast"]

    lines = []
    lines.append("PIPELINE DEMAND FORECAST — 30/60 DAY PROJECTION")
    lines.append("=" * 50)
    lines.append("")
    lines.append("METHOD")
    lines.append(f"Each forecasted month is projected as the trailing "
                  f"{FORECAST_WINDOW}-month average of actual throughput. "
                  f"This is a moving-average forecast — it assumes the near-term "
                  f"future will resemble the recent past, and does not model trend, "
                  f"seasonality, or known planned events.")
    lines.append("")
    lines.append("FORECAST")
    for _, row in forecast.iterrows():
        lines.append(f"  {row['date'].strftime('%B %Y')}: {row['throughput']:.2f}")
    lines.append("")
    lines.append("ASSUMPTIONS")
    lines.append("- Assumes no unplanned outages, apportionment events, or maintenance")
    lines.append("  windows beyond the pattern already reflected in the trailing average.")
    lines.append("- Assumes no material change in available capacity in the forecast window.")
    lines.append("- Does not account for seasonality; the dataset does not show a strong")
    lines.append("  consistent seasonal pattern, so none was modeled.")
    lines.append("")
    lines.append("RECENT VARIANCE CONTEXT (trailing 12 months of actuals)")
    lines.append(f"  Mean: {variance_ctx['recent_12mo_mean']:.2f}")
    lines.append(f"  Std deviation: {variance_ctx['recent_12mo_std']:.2f}")
    lines.append(f"  Range: {variance_ctx['recent_12mo_min']:.2f} to {variance_ctx['recent_12mo_max']:.2f}")
    lines.append("")
    lines.append("This range matters more than the single-point forecast above: the historical")
    lines.append("data shows the system can drop sharply (see Section 5.3 of the main analysis")
    lines.append("write-up) within a single month due to maintenance or apportionment events,")
    lines.append("recovering within 1-2 months. A single-point moving-average forecast will NOT")
    lines.append("predict when such an event occurs — it only reflects the recent steady-state.")
    lines.append("A realistic forecast range should widen by roughly one standard deviation")
    lines.append("in either direction to reflect this known volatility.")

    text = "\n".join(lines)
    out_path.write_text(text)
    print("\n" + text)


def main():
    df = load_data()
    combined = build_forecast(df)
    variance_ctx = compute_variance_context(df)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    combined.to_csv(FORECAST_CSV, index=False)
    print(f"Forecast data saved to {FORECAST_CSV}")

    make_chart(combined, FORECAST_CHART)
    write_narrative(combined, variance_ctx, FORECAST_NARRATIVE)


if __name__ == "__main__":
    main()
