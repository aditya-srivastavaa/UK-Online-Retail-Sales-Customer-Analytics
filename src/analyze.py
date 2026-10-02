"""Clean UCI Online Retail II and build portfolio-ready outputs."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data" / "raw" / "online_retail_II.xlsx"
OUT = ROOT / "outputs"
DB_PATH = OUT / "retail_analysis.sqlite"


def load_source(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Source workbook not found: {path}\nRun: python src/download_data.py")
    sheets = pd.read_excel(path, sheet_name=None, engine="openpyxl")
    frames = [frame.assign(SourceSheet=sheet) for sheet, frame in sheets.items()]
    data = pd.concat(frames, ignore_index=True)
    expected = {"Invoice", "StockCode", "Description", "Quantity", "InvoiceDate", "Price", "Customer ID", "Country"}
    missing = expected.difference(data.columns)
    if missing:
        raise ValueError(f"Unexpected source workbook; missing columns: {sorted(missing)}")
    return data


def clean_and_aggregate(raw: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    df = raw.copy()
    original_rows = len(df)
    duplicate_mask = df.duplicated(subset=list(raw.columns.drop("SourceSheet")), keep="first")
    duplicates_removed = int(duplicate_mask.sum())
    df = df.loc[~duplicate_mask].copy()

    df["Invoice"] = df["Invoice"].astype("string").str.strip()
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"], errors="coerce")
    df["Quantity"] = pd.to_numeric(df["Quantity"], errors="coerce")
    df["Price"] = pd.to_numeric(df["Price"], errors="coerce")
    df["Customer ID"] = pd.to_numeric(df["Customer ID"], errors="coerce").astype("Int64")
    df["Country"] = df["Country"].astype("string").str.strip()
    df["Description"] = df["Description"].astype("string").str.strip()
    df["LineValue"] = df["Quantity"] * df["Price"]
    df["IsCancellation"] = df["Invoice"].str.upper().str.startswith("C", na=False)

    cancellation = df.loc[df["IsCancellation"]].copy()
    cancellation["CancellationValueGBP"] = cancellation["LineValue"].abs()
    cancellation["Month"] = cancellation["InvoiceDate"].dt.to_period("M").dt.to_timestamp()

    sales_candidate = df.loc[~df["IsCancellation"]].copy()
    invalid_sales = sales_candidate["InvoiceDate"].isna() | sales_candidate["Quantity"].isna() | sales_candidate["Price"].isna()
    nonpositive_quantity = sales_candidate["Quantity"].le(0).fillna(False)
    nonpositive_price = sales_candidate["Price"].le(0).fillna(False)
    valid = ~(invalid_sales | nonpositive_quantity | nonpositive_price)
    sales = sales_candidate.loc[valid].copy()
    sales["RevenueGBP"] = sales["Quantity"] * sales["Price"]
    sales["Month"] = sales["InvoiceDate"].dt.to_period("M").dt.to_timestamp()
    sales["CustomerID"] = sales["Customer ID"].astype("string")
    sales = sales.rename(columns={"Invoice": "InvoiceNo", "StockCode": "StockCode", "Description": "Description", "Quantity": "Quantity", "InvoiceDate": "InvoiceDate", "Price": "UnitPriceGBP", "Country": "Country"})

    monthly = sales.groupby("Month", as_index=False).agg(
        RecordedSalesGBP=("RevenueGBP", "sum"), Orders=("InvoiceNo", "nunique"), Units=("Quantity", "sum"),
        IdentifiedCustomers=("CustomerID", "nunique"), LineItems=("InvoiceNo", "size"),
    )
    monthly["AverageOrderValueGBP"] = monthly["RecordedSalesGBP"] / monthly["Orders"].replace(0, np.nan)

    product = sales.groupby(["StockCode", "Description"], dropna=False, as_index=False).agg(
        RecordedSalesGBP=("RevenueGBP", "sum"), Units=("Quantity", "sum"), Orders=("InvoiceNo", "nunique"),
    ).sort_values("RecordedSalesGBP", ascending=False).head(20)
    country = sales.groupby("Country", as_index=False).agg(
        RecordedSalesGBP=("RevenueGBP", "sum"), Orders=("InvoiceNo", "nunique"), Customers=("CustomerID", "nunique"),
    ).sort_values("RecordedSalesGBP", ascending=False)

    identified = sales.loc[sales["CustomerID"].notna()].copy()
    reference_date = identified["InvoiceDate"].max().normalize() + pd.Timedelta(days=1)
    rfm = identified.groupby("CustomerID", as_index=False).agg(
        LastPurchase=("InvoiceDate", "max"), Frequency=("InvoiceNo", "nunique"), MonetaryGBP=("RevenueGBP", "sum"),
    )
    rfm["RecencyDays"] = (reference_date - rfm["LastPurchase"].dt.normalize()).dt.days
    rfm["RScore"] = pd.qcut(rfm["RecencyDays"].rank(method="first"), 5, labels=[5, 4, 3, 2, 1]).astype(int)
    rfm["FScore"] = pd.qcut(rfm["Frequency"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["MScore"] = pd.qcut(rfm["MonetaryGBP"].rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    rfm["RFMScore"] = rfm[["RScore", "FScore", "MScore"]].sum(axis=1)
    conditions = [
        (rfm["RScore"] >= 4) & (rfm["FScore"] >= 4),
        rfm["FScore"] >= 4,
        rfm["RScore"] <= 2,
        rfm["RScore"] >= 4,
    ]
    rfm["Segment"] = np.select(conditions, ["Champions", "Loyal", "At Risk", "Recent"], default="Regular")
    rfm["LastPurchase"] = rfm["LastPurchase"].dt.strftime("%Y-%m-%d")
    rfm_summary = rfm.groupby("Segment", as_index=False).agg(
        Customers=("CustomerID", "nunique"), RecordedSalesGBP=("MonetaryGBP", "sum"), AverageRecencyDays=("RecencyDays", "mean"),
    ).sort_values("RecordedSalesGBP", ascending=False)

    cancel_monthly = cancellation.groupby("Month", as_index=False).agg(
        CancellationLines=("Invoice", "size"), CancellationInvoices=("Invoice", "nunique"), CancellationValueGBP=("CancellationValueGBP", "sum"),
    )
    report = {
        "source_rows": int(original_rows), "exact_duplicate_rows_removed": duplicates_removed,
        "sales_candidate_rows": int(len(sales_candidate)), "eligible_sales_rows": int(len(sales)),
        "cancellation_rows": int(len(cancellation)), "nonpositive_quantity_rows_excluded": int(nonpositive_quantity.sum()),
        "nonpositive_price_rows_excluded": int(nonpositive_price.sum()), "invalid_date_or_numeric_rows_excluded": int(invalid_sales.sum()),
        "eligible_recorded_sales_gbp": round(float(sales["RevenueGBP"].sum()), 2),
        "eligible_orders": int(sales["InvoiceNo"].nunique()), "identified_customers": int(rfm["CustomerID"].nunique()),
        "sales_rows_missing_customer_id": int(sales["CustomerID"].isna().sum()),
        "first_eligible_transaction": sales["InvoiceDate"].min().isoformat(), "last_eligible_transaction": sales["InvoiceDate"].max().isoformat(),
        "rfm_reference_date": reference_date.date().isoformat(),
    }
    return sales, rfm, {"report": report, "monthly": monthly, "product": product, "country": country, "rfm_summary": rfm_summary, "cancellations": cancel_monthly}


def build_dashboard(tables: dict[str, pd.DataFrame], report: dict, output: Path) -> None:
    monthly = tables["monthly"].sort_values("Month")
    country = tables["country"].nlargest(10, "RecordedSalesGBP").sort_values("RecordedSalesGBP")
    product = tables["product"].head(10).sort_values("RecordedSalesGBP")
    segments = tables["rfm_summary"].sort_values("Customers")
    cancels = tables["cancellations"].sort_values("Month")

    fig = make_subplots(rows=3, cols=2, subplot_titles=("Recorded sales by month (GBP)", "Top 10 countries by recorded sales (GBP)", "Top 10 products by recorded sales (GBP)", "Identified customers by RFM segment", "Cancellation line value by month (GBP)", "Average order value by month (GBP)"), vertical_spacing=0.14, horizontal_spacing=0.14)
    fig.add_trace(go.Scatter(x=monthly["Month"], y=monthly["RecordedSalesGBP"], mode="lines+markers", name="Recorded sales", line={"color": "#2563eb", "width": 3}, hovertemplate="%{x|%b %Y}<br>£%{y:,.0f}<extra></extra>"), row=1, col=1)
    fig.add_trace(go.Bar(x=country["RecordedSalesGBP"], y=country["Country"], orientation="h", name="Country sales", marker_color="#0f766e", hovertemplate="%{y}<br>£%{x:,.0f}<extra></extra>"), row=1, col=2)
    fig.add_trace(go.Bar(x=product["RecordedSalesGBP"], y=product["Description"].fillna("(description missing)"), orientation="h", name="Product sales", marker_color="#7c3aed", hovertemplate="%{y}<br>£%{x:,.0f}<extra></extra>"), row=2, col=1)
    fig.add_trace(go.Bar(x=segments["Customers"], y=segments["Segment"], orientation="h", name="Customers", marker_color="#d97706", customdata=np.column_stack([segments["RecordedSalesGBP"], segments["AverageRecencyDays"]]), hovertemplate="%{y}<br>Customers: %{x:,}<br>Sales: £%{customdata[0]:,.0f}<br>Avg recency: %{customdata[1]:.0f} days<extra></extra>"), row=2, col=2)
    fig.add_trace(go.Bar(x=cancels["Month"], y=cancels["CancellationValueGBP"], name="Cancellation line value", marker_color="#dc2626", hovertemplate="%{x|%b %Y}<br>£%{y:,.0f}<extra></extra>"), row=3, col=1)
    fig.add_trace(go.Scatter(x=monthly["Month"], y=monthly["AverageOrderValueGBP"], mode="lines+markers", name="Average order value", line={"color": "#0891b2", "width": 3}, hovertemplate="%{x|%b %Y}<br>£%{y:,.2f}<extra></extra>"), row=3, col=2)
    fig.update_xaxes(title_text="Month", row=1, col=1)
    fig.update_yaxes(title_text="Recorded sales (GBP)", row=1, col=1)
    fig.update_xaxes(title_text="Recorded sales (GBP)", row=1, col=2)
    fig.update_yaxes(title_text="Country", row=1, col=2)
    fig.update_xaxes(title_text="Recorded sales (GBP)", row=2, col=1)
    fig.update_yaxes(title_text="Product description", row=2, col=1)
    fig.update_xaxes(title_text="Identified customers", row=2, col=2)
    fig.update_yaxes(title_text="RFM segment", row=2, col=2)
    fig.update_xaxes(title_text="Month", row=3, col=1)
    fig.update_yaxes(title_text="Cancellation line value (GBP)", row=3, col=1)
    fig.update_xaxes(title_text="Month", row=3, col=2)
    fig.update_yaxes(title_text="Average order value (GBP)", row=3, col=2)
    fig.update_layout(height=1120, template="plotly_white", font={"family": "Arial, sans-serif", "color": "#1f2937"}, margin={"l": 45, "r": 30, "t": 80, "b": 50}, showlegend=False, title={"text": "Online Retail | Sales & Customer Overview", "x": 0.04, "xanchor": "left", "font": {"size": 24}})
    chart = fig.to_html(full_html=False, include_plotlyjs=True, config={"displaylogo": False, "responsive": True})

    total_sales = report["eligible_recorded_sales_gbp"]
    aov = total_sales / report["eligible_orders"] if report["eligible_orders"] else 0
    cancellation_invoices = int(tables["cancellations"]["CancellationInvoices"].sum())
    kpis = [("Recorded sales", f"£{total_sales:,.0f}"), ("Eligible orders", f"{report['eligible_orders']:,}"), ("Identified customers", f"{report['identified_customers']:,}"), ("Cancellation invoices", f"{cancellation_invoices:,}"), ("Average order value", f"£{aov:,.2f}")]
    cards = "\n".join(f'<div class="kpi"><div class="label">{label}</div><div class="value">{value}</div></div>' for label, value in kpis)
    date_range = f"{report['first_eligible_transaction'][:10]} to {report['last_eligible_transaction'][:10]}"
    html = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>Online Retail | Sales & Customer Overview</title>
<style>body{{margin:0;background:#f3f4f6;color:#111827;font-family:Arial,sans-serif}}main{{max-width:1440px;margin:0 auto;padding:36px 28px}}header{{margin-bottom:24px}}h1{{font-size:30px;margin:0 0 8px}}.sub{{color:#4b5563;font-size:14px;line-height:1.5}}.kpis{{display:grid;grid-template-columns:repeat(5,minmax(130px,1fr));gap:12px;margin:22px 0}}.kpi{{background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:17px}}.label{{font-size:12px;color:#6b7280;margin-bottom:8px}}.value{{font-size:23px;font-weight:700}}.chart{{background:#fff;border:1px solid #e5e7eb;border-radius:8px;padding:12px}}.note{{font-size:12px;color:#4b5563;line-height:1.6;margin:20px 2px}}@media(max-width:850px){{.kpis{{grid-template-columns:repeat(2,1fr)}}main{{padding:22px 12px}}}}</style></head>
<body><main><header><h1>Online Retail | Sales & Customer Overview</h1><div class="sub">Descriptive analysis of the UCI Online Retail II transaction history · {date_range} · GBP</div></header>
<section class="kpis">{cards}</section><section class="chart">{chart}</section>
<p class="note"><strong>How to read this:</strong> Recorded sales are eligible positive-quantity, positive-price lines on non-cancelled invoices. Cancellation activity is displayed separately. This dataset contains no cost data, so sales are not profit. RFM segments are relative, descriptive groups for identified customers only. Source: Chen (2012), UCI Online Retail II, CC BY 4.0.</p></main></body></html>'''
    output.write_text(html, encoding="utf-8")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    raw = load_source(SOURCE)
    sales, rfm, tables = clean_and_aggregate(raw)
    sales.to_csv(OUT / "clean_sales.csv", index=False, encoding="utf-8")
    rfm.to_csv(OUT / "customer_rfm.csv", index=False, encoding="utf-8")
    for name, table in tables.items():
        if name != "report":
            table.to_csv(OUT / f"{name}.csv", index=False, encoding="utf-8")
    (OUT / "quality_report.json").write_text(json.dumps(tables["report"], indent=2), encoding="utf-8")
    with sqlite3.connect(DB_PATH) as connection:
        sales.to_sql("fact_sales", connection, if_exists="replace", index=False, chunksize=20_000)
        rfm.to_sql("customer_rfm", connection, if_exists="replace", index=False, chunksize=20_000)
        tables["monthly"].to_sql("monthly_sales", connection, if_exists="replace", index=False)
        tables["cancellations"].to_sql("monthly_cancellations", connection, if_exists="replace", index=False)
    build_dashboard(tables, tables["report"], OUT / "dashboard.html")
    print(f"Analysis complete: {len(sales):,} eligible sales lines; £{tables['report']['eligible_recorded_sales_gbp']:,.2f} recorded sales; {tables['report']['eligible_orders']:,} orders.")
    print(f"Dashboard: {OUT / 'dashboard.html'}")


if __name__ == "__main__":
    main()
