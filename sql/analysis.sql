-- Run these queries in SQLite after `python src/analyze.py` creates outputs/retail_analysis.sqlite.

-- 1. Monthly sales trend and month-over-month change.
WITH monthly AS (
    SELECT strftime('%Y-%m', Month) AS sales_month,
           SUM(RevenueGBP) AS recorded_sales_gbp,
           COUNT(DISTINCT InvoiceNo) AS orders
    FROM fact_sales
    GROUP BY strftime('%Y-%m', Month)
)
SELECT sales_month, ROUND(recorded_sales_gbp, 2) AS recorded_sales_gbp, orders,
       ROUND(100.0 * (recorded_sales_gbp - LAG(recorded_sales_gbp) OVER (ORDER BY sales_month))
             / NULLIF(LAG(recorded_sales_gbp) OVER (ORDER BY sales_month), 0), 1) AS sales_mom_pct
FROM monthly
ORDER BY sales_month;

-- 2. Highest-selling products (descriptive sales value, not margin).
SELECT StockCode, Description, ROUND(SUM(RevenueGBP), 2) AS recorded_sales_gbp,
       SUM(Quantity) AS units, COUNT(DISTINCT InvoiceNo) AS orders
FROM fact_sales
GROUP BY StockCode, Description
ORDER BY recorded_sales_gbp DESC
LIMIT 15;

-- 3. Country mix. The source describes the customer's country, not necessarily shipment destination.
SELECT Country, ROUND(SUM(RevenueGBP), 2) AS recorded_sales_gbp,
       COUNT(DISTINCT InvoiceNo) AS orders,
       COUNT(DISTINCT CustomerID) AS identified_customers
FROM fact_sales
GROUP BY Country
ORDER BY recorded_sales_gbp DESC;

-- 4. Order value distribution by month.
WITH order_totals AS (
    SELECT strftime('%Y-%m', Month) AS sales_month, InvoiceNo,
           SUM(RevenueGBP) AS order_value_gbp
    FROM fact_sales
    GROUP BY strftime('%Y-%m', Month), InvoiceNo
)
SELECT sales_month, COUNT(*) AS orders,
       ROUND(AVG(order_value_gbp), 2) AS average_order_value_gbp,
       ROUND(MIN(order_value_gbp), 2) AS smallest_order_gbp,
       ROUND(MAX(order_value_gbp), 2) AS largest_order_gbp
FROM order_totals
GROUP BY sales_month
ORDER BY sales_month;

-- 5. Customer segments from the documented, quantile-based RFM analysis.
SELECT Segment, COUNT(*) AS customers,
       ROUND(SUM(MonetaryGBP), 2) AS recorded_sales_gbp,
       ROUND(AVG(RecencyDays), 1) AS average_recency_days
FROM customer_rfm
GROUP BY Segment
ORDER BY recorded_sales_gbp DESC;

-- 6. Product concentration: share of eligible recorded sales from top 20 products.
WITH product_sales AS (
    SELECT StockCode, SUM(RevenueGBP) AS sales_gbp
    FROM fact_sales
    GROUP BY StockCode
), ranked AS (
    SELECT sales_gbp, DENSE_RANK() OVER (ORDER BY sales_gbp DESC) AS sales_rank
    FROM product_sales
)
SELECT ROUND(100.0 * SUM(CASE WHEN sales_rank <= 20 THEN sales_gbp ELSE 0 END)
             / NULLIF(SUM(sales_gbp), 0), 2) AS top_20_product_sales_share_pct
FROM ranked;

-- 7. Cancellation activity is reported separately from eligible sales.
SELECT strftime('%Y-%m', Month) AS cancellation_month,
       SUM(CancellationLines) AS cancellation_lines,
       SUM(CancellationInvoices) AS cancellation_invoices,
       ROUND(SUM(CancellationValueGBP), 2) AS cancellation_line_value_gbp
FROM monthly_cancellations
GROUP BY strftime('%Y-%m', Month)
ORDER BY cancellation_month;
