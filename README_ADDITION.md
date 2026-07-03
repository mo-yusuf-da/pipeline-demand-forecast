## Demand Forecast Exercise

A short 30/60-day throughput forecast using a moving-average method, built on the same cleaned dataset as the main analysis.

**Method:** each forecasted month is projected as the trailing 3-month average of actual throughput — a simple, transparent method chosen deliberately over a more complex model, since the goal was a defensible forecast I can fully explain, not a black box.

**Files:**
- `forecast.py` — forecast script
- `output/forecast.csv` — actuals + forecast combined
- `output/forecast_chart.png` — visual forecast
- `output/forecast_narrative.txt` — method, assumptions, and variance context

Run it:
```bash
pip install pandas matplotlib
python forecast.py
```

Requires `keystone_clean.csv` from the main pipeline-throughput-analysis project (the script looks for it at `../pipeline-throughput-analysis/output/keystone_clean.csv` by default — or copy it into this folder directly).
