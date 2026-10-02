# Online Retail II: Sales, Product & Customer Analysis

An end-to-end business analysis of the UCI Online Retail II transaction history. The project answers a practical question: **what does this retailer's recorded sales history reveal about demand, product and country mix, cancellations, and repeat-customer value?** A reproducible Python pipeline cleans the source, creates documented sales and customer tables, answers follow-up questions in SQLite, and builds a self-contained interactive dashboard.

> **Headline findings:** eligible transaction value totals **£20.48m** across **40,077 invoices** from December 2009 to December 2011. The United Kingdom accounts for **85.0%** of that value. November 2011 is the strongest month in the available data (**£1.50m**). These are historical recorded sales figures, not profit or current market benchmarks.

## Business questions and findings

1. **How did demand change over time?** Monthly recorded sales peaked at **£1,503,866.78 in November 2011**, the highest month in the supplied period. The source ends on 9 December 2011, so December 2011 is partial and should not be compared directly with complete months.
2. **Which markets contribute most?** The United Kingdom generated **£17.41m (85.0%)** of recorded sales. The source's `Country` field is reported as customer country; it is not independently verified as delivery destination.
3. **Which products lead sales?** The 10 highest-selling product codes in the product summary contribute **£2.07m (10.1%)** of recorded sales. Product sales ranking says nothing about margin because unit costs are absent; service and postage codes also appear in the source.
4. **What do identified customers contribute?** The relative, quantile-based **Champions** segment contributes **£11.99m (69.0%)** of the **£17.37m** recorded sales from identified customers. The segment is a descriptive prioritization label, not a validated persona or prediction.
5. **What cancellation activity is recorded?** The source contains **19,104 lines** on **8,292 cancellation invoices**, with **£1.46m** in absolute line value. These are reported separately; they are not subtracted from sales because the data does not establish the business or accounting treatment of each cancellation.

All figures above are generated from the checked-in summary outputs by `src/analyze.py`. The complete monthly, country, product, customer-segment, and cancellation tables are in `outputs/`. Open [`outputs/dashboard.html`](outputs/dashboard.html) in a browser for the interactive views.

## Deliverables

- `src/download_data.py` downloads the original UCI workbook.
- `src/analyze.py` cleans and analyzes the two source sheets, exports tables and a quality report, writes a local SQLite database, and builds the dashboard.
- `sql/analysis.sql` contains seven follow-up queries, including monthly trend, product ranking, order-value distribution, customer segments, and product concentration.
- `outputs/quality_report.json` records row counts, exclusions, date coverage, and analysis totals.
- `LEARNING_GUIDE.md` explains how to run and walk through the analysis.

## Run it locally

Requires Python 3.10 or newer. From the project directory:

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python src/download_data.py
python src/analyze.py
```

The workbook is about 46 MB and is intentionally excluded from Git. The analysis writes derived CSVs, a SQLite database, a JSON quality report, and the self-contained HTML dashboard to `outputs/`. To run a SQL query, open `outputs/retail_analysis.sqlite` with SQLite or use the Python standard library and execute a statement from `sql/analysis.sql`.

## Data and method

**Source:** Chen (2012), [Online Retail II, UCI Machine Learning Repository](https://doi.org/10.24432/C5CG6D), licensed under [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). The source includes 1,067,371 transaction rows in two Excel sheets, covering 1 December 2009 through 9 December 2011.

The pipeline removes **34,335 exact duplicate rows** (comparing transaction fields across both sheets), then classifies invoices beginning with `C` as cancellation activity. Recorded sales include non-cancellation lines with valid dates, positive quantity, and positive unit price. Missing customer IDs remain in sales totals but are not included in customer-level RFM calculations. The report's invalid-value counts are diagnostic counts and may overlap; do not add them together as a unique excluded-row total.

**Metric definitions:**

- Recorded sales = quantity × unit price for eligible transaction lines. This is transaction value, not accounting revenue, net sales, or profit.
- Orders = distinct eligible invoice numbers. Cancellation invoice counts are calculated separately.
- Cancellation value = absolute quantity × unit-price line value for invoices whose number begins with `C`; it is not treated as a confirmed refund or loss.
- RFM uses each identified customer's last purchase date, distinct invoice count, and recorded sales. Quintile scores and segment names are relative to this dataset and period.

## Limitations and next steps

This is historical data from one UK-based non-store retailer. It contains no product costs, marketing spend, stock availability, or customer demographics, so it cannot support profit, campaign-effect, or causal claims. Discounting is not interpreted as causing sales or customer outcomes. A useful next step would be to join verified cost and inventory data, then compare margin and availability by product and period.

## Resume description

**Online Retail Sales & Customer Analytics | Python, pandas, SQL, Plotly**

- Built a reproducible Python pipeline to clean and analyze **1.07M source transaction rows**, documenting duplicate removal, eligibility rules, cancellation handling, and missing customer IDs.
- Used pandas and SQLite to analyze sales trends, country and product mix, cancellations, and customer purchase behavior; delivered an interactive dashboard with documented KPI definitions.
- Identified **£20.48m** in eligible recorded sales and found that the UK accounted for **85.0%**; described relative RFM segments without presenting them as predictive or causal findings.

Use these bullets only if you can explain the definitions and reproduce the results by running the project. Do not claim a profit increase, business impact, forecasting, or a deployed BI report.
