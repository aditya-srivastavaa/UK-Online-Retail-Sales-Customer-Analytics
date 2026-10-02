# Learning guide

This project is meant to be explainable. Run it once, then follow the steps below and change small pieces of the code yourself.

## 1. Run the pipeline

```bash
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python src/download_data.py
python src/analyze.py
```

Open `outputs/dashboard.html`. The chart tooltips show the underlying values. The first run reads the 43 MB workbook and may take a few minutes.

## 2. Learn the Python flow

Open `src/analyze.py` in this order:

1. `load_source()` reads each Excel sheet and combines the two years.
2. `clean_and_aggregate()` flags cancellation invoices, checks valid sales lines, and builds monthly, product, country, and customer summaries.
3. `build_dashboard()` turns those summaries into Plotly charts.
4. `main()` exports tables and writes a local SQLite database.

Useful concepts to look up while reading: DataFrame, boolean filter, `groupby`, aggregation, `merge`/window functions, and a Python function. NumPy is used for assigning customer labels; pandas does most of the table work.

## 3. Practice SQL

Install a SQLite viewer (or use the Python standard library) and open `outputs/retail_analysis.sqlite`. Start with query 1 in `sql/analysis.sql`. Try changing the sort order or selecting a different month. Queries 1 and 6 use window functions; the others are introductory aggregation and grouping.

## 4. Explain one result

Pick one chart and answer:

- What is the unit and time period?
- Which rows were included?
- What does the chart show, in one sentence?
- What extra data would you need before recommending an action?

Use actual values from the generated dashboard and CSVs. The dataset is historical, so don't present its figures as current retail-market benchmarks.

## 5. Good next extensions

- Add a Power BI report by importing `outputs/monthly.csv`, `outputs/country.csv`, and `outputs/rfm_summary.csv`.
- Add year-over-year comparisons only for months present in both years.
- Ask how returns and cancellations are represented in an organization's accounting system before calculating net sales.
- Add a data dictionary and a short screenshot of the dashboard to your portfolio.
