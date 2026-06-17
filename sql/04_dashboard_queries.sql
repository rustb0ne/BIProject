-- ============================================================
--  OLIST BI DASHBOARD -- QUERY COLLECTION
--  Demo-Ready | Catchy | Visual-Optimized
--  Dung cho Metabase (MySQL / olist_dwh)
-- ============================================================

USE olist_dwh;


-- ================================================================
-- 1. EXECUTIVE OVERVIEW DASHBOARD
-- ================================================================

-- ----------------------------------------------------------------
-- [EX-1] BIG NUMBER -- 5 KPI Headline Cards
-- -> Dung lam 5 so metric noi bat dau trang
-- ----------------------------------------------------------------
SELECT
    COUNT(DISTINCT f.order_id)                        AS total_orders,
    COUNT(DISTINCT c.customer_unique_id)              AS unique_customers,
    CONCAT('R$ ', FORMAT(SUM(f.price), 0))            AS gross_revenue,
    CONCAT(ROUND(AVG(f.review_score), 2), ' / 5')     AS avg_review_score,
    CONCAT(ROUND(100.0 * SUM(CASE WHEN f.is_on_time THEN 1 ELSE 0 END)
               / COUNT(*), 1), '%')                   AS on_time_rate
FROM fact_orders f
JOIN dim_customer c ON f.customer_key = c.customer_key
WHERE f.order_status = 'delivered';


-- ----------------------------------------------------------------
-- [EX-2] REVENUE TREND -- Monthly Line Chart
-- -> Line chart: x=ym (year_month), y=gross_revenue + total_orders
-- NOTE: Use subquery to avoid keyword clash (year/month/year_month)
-- ----------------------------------------------------------------
SELECT
    sub.ym                                            AS period,
    sub.total_orders,
    sub.gross_revenue,
    sub.freight_revenue,
    sub.total_revenue,
    sub.avg_review_score,
    ROUND(
        100.0 * (sub.gross_revenue - LAG(sub.gross_revenue) OVER (ORDER BY sub.yr, sub.mth))
              / NULLIF(LAG(sub.gross_revenue) OVER (ORDER BY sub.yr, sub.mth), 0),
        1
    )                                                 AS mom_growth_pct
FROM (
    SELECT
        t.year                                        AS yr,
        t.month                                       AS mth,
        CONCAT(t.year, '-', LPAD(t.month, 2, '0'))    AS ym,
        COUNT(DISTINCT f.order_id)                    AS total_orders,
        ROUND(SUM(f.price), 2)                        AS gross_revenue,
        ROUND(SUM(f.freight_value), 2)                AS freight_revenue,
        ROUND(SUM(f.total_revenue), 2)                AS total_revenue,
        ROUND(AVG(f.review_score), 2)                 AS avg_review_score
    FROM fact_orders f
    JOIN dim_time t ON f.purchase_time_key = t.time_key
    WHERE f.order_status IN ('delivered', 'shipped')
      AND t.full_date < '2018-09-01' -- Loại bỏ tháng 9 & 10 vì data chưa thu thập đủ 30 ngày
    GROUP BY t.year, t.month
) sub
ORDER BY sub.yr, sub.mth;


-- ----------------------------------------------------------------
-- [EX-3] QUARTERLY PERFORMANCE -- Bar+Line Combo
-- -> Bar: revenue per quarter | Line: avg review score
-- ----------------------------------------------------------------
SELECT
    CONCAT(t.year, ' Q', t.quarter)                   AS quarter_label,
    COUNT(DISTINCT f.order_id)                        AS total_orders,
    COUNT(DISTINCT f.customer_key)                    AS unique_customers,
    ROUND(SUM(f.price), 2)                            AS product_revenue,
    ROUND(SUM(f.freight_value), 2)                    AS freight_revenue,
    ROUND(SUM(f.total_revenue), 2)                    AS total_revenue,
    ROUND(AVG(f.review_score), 2)                     AS avg_review_score,
    ROUND(SUM(f.price) / COUNT(DISTINCT f.order_id), 2) AS avg_order_value
FROM fact_orders f
JOIN dim_time t ON f.purchase_time_key = t.time_key
WHERE f.order_status IN ('delivered', 'shipped')
GROUP BY t.year, t.quarter
ORDER BY t.year, t.quarter;


-- ----------------------------------------------------------------
-- [EX-4] REVENUE BY MACRO-REGION
-- -> Pie chart / Treemap: Contribution % per region
-- ----------------------------------------------------------------
SELECT
    r.macro_region,
    COUNT(DISTINCT f.order_id)                        AS total_orders,
    COUNT(DISTINCT f.customer_key)                    AS unique_customers,
    ROUND(SUM(f.price), 2)                            AS total_revenue,
    ROUND(100.0 * SUM(f.price) / SUM(SUM(f.price)) OVER(), 1) AS revenue_share_pct,
    ROUND(AVG(f.review_score), 2)                     AS avg_review_score,
    ROUND(AVG(f.delivery_days), 1)                    AS avg_delivery_days
FROM fact_orders f
JOIN dim_region r ON f.customer_region_key = r.region_key
WHERE f.order_status = 'delivered'
GROUP BY r.macro_region
ORDER BY total_revenue DESC;


-- ----------------------------------------------------------------
-- [EX-5] PAYMENT MIX -- Donut Chart
-- -> Ti le phuong thuc thanh toan + gia tri trung binh
-- ----------------------------------------------------------------
SELECT
    CASE payment_type
        WHEN 'credit_card' THEN 'Credit Card'
        WHEN 'boleto'      THEN 'Boleto'
        WHEN 'voucher'     THEN 'Voucher'
        WHEN 'debit_card'  THEN 'Debit Card'
        ELSE 'Other'
    END                                               AS payment_method,
    COUNT(DISTINCT order_id)                          AS order_count,
    ROUND(100.0 * COUNT(DISTINCT order_id)
          / SUM(COUNT(DISTINCT order_id)) OVER(), 1)  AS share_pct,
    ROUND(AVG(payment_value), 2)                      AS avg_payment_value,
    ROUND(AVG(payment_installments), 1)               AS avg_installments,
    ROUND(SUM(payment_value), 2)                      AS total_payment_volume
FROM fact_orders
WHERE payment_type IS NOT NULL
  AND payment_type != 'not_defined'
GROUP BY payment_type
ORDER BY order_count DESC;


-- ----------------------------------------------------------------
-- [EX-6] DAY-OF-WEEK SHOPPING PATTERN
-- -> Funnel / Bar: Ngay nao khach mua nhieu nhat
-- ----------------------------------------------------------------
SELECT
    t.day_of_week,
    t.day_name,
    CASE WHEN t.is_weekend THEN 'Weekend' ELSE 'Weekday' END AS day_type,
    COUNT(DISTINCT f.order_id)                        AS total_orders,
    ROUND(SUM(f.price), 2)                            AS total_revenue,
    ROUND(AVG(f.price), 2)                            AS avg_order_value,
    ROUND(100.0 * COUNT(DISTINCT f.order_id)
          / SUM(COUNT(DISTINCT f.order_id)) OVER(), 1) AS orders_share_pct
FROM fact_orders f
JOIN dim_time t ON f.purchase_time_key = t.time_key
WHERE f.order_status IN ('delivered', 'shipped')
GROUP BY t.day_of_week, t.day_name, t.is_weekend
ORDER BY t.day_of_week;


-- ================================================================
-- 2. CUSTOMER DASHBOARD
-- ================================================================

-- ----------------------------------------------------------------
-- [CUS-1] RFM SEGMENT LEADERBOARD
-- -> Scoreboard table: Phan khuc nao ngon nhat?
-- ----------------------------------------------------------------
WITH customer_rfm AS (
    SELECT
        c.customer_unique_id,
        DATEDIFF('2018-10-01', MAX(t.full_date))      AS recency_days,
        COUNT(DISTINCT f.order_id)                    AS frequency,
        ROUND(SUM(f.price), 2)                        AS monetary
    FROM fact_orders f
    JOIN dim_customer c ON f.customer_key = c.customer_key
    JOIN dim_time t     ON f.purchase_time_key = t.time_key
    WHERE f.order_status = 'delivered'
    GROUP BY c.customer_unique_id
),
rfm_scored AS (
    SELECT *,
        NTILE(5) OVER (ORDER BY recency_days DESC)    AS r_score,
        -- Frequency in Olist is 97% = 1. NTILE will randomly split ties. 
        -- We must use a deterministic CASE for f_score.
        CASE 
            WHEN frequency >= 3 THEN 5
            WHEN frequency = 2  THEN 4
            ELSE 1
        END                                           AS f_score,
        NTILE(5) OVER (ORDER BY monetary ASC)         AS m_score
    FROM customer_rfm
),
rfm_segmented AS (
    SELECT *,
        CASE
            WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
            WHEN r_score >= 3 AND f_score >= 3                  THEN 'Loyal Customers'
            WHEN r_score >= 4 AND f_score <= 2                  THEN 'Recent Customers'
            WHEN r_score <= 2 AND f_score >= 3                  THEN 'At Risk'
            WHEN r_score = 1  AND f_score = 1                   THEN 'Lost'
            ELSE 'Potential Loyalists'
        END AS rfm_segment
    FROM rfm_scored
)
SELECT
    rfm_segment                                       AS segment_label,
    COUNT(*)                                          AS customer_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 1) AS pct_of_customers,
    ROUND(AVG(recency_days), 0)                       AS avg_recency_days,
    ROUND(AVG(frequency), 2)                          AS avg_orders,
    ROUND(AVG(monetary), 2)                           AS avg_spend_per_customer,
    ROUND(SUM(monetary), 2)                           AS total_revenue_from_segment
FROM rfm_segmented
GROUP BY rfm_segment
ORDER BY total_revenue_from_segment DESC;


-- ----------------------------------------------------------------
-- [CUS-2] CUSTOMER GEO MAP -- State Revenue
-- -> Map chart (Brazil): Mau dam = doanh thu cao
-- ----------------------------------------------------------------
SELECT
    r.state_code,
    r.state_name,
    r.macro_region,
    COUNT(DISTINCT f.order_id)                        AS total_orders,
    COUNT(DISTINCT f.customer_key)                    AS unique_customers,
    ROUND(SUM(f.price), 2)                            AS total_revenue,
    ROUND(100.0 * SUM(f.price) / SUM(SUM(f.price)) OVER(), 1) AS revenue_share_pct,
    ROUND(AVG(f.price), 2)                            AS avg_order_value,
    ROUND(AVG(f.review_score), 2)                     AS avg_review_score,
    ROUND(AVG(f.delivery_days), 1)                    AS avg_delivery_days,
    ROUND(100.0 * SUM(CASE WHEN f.is_on_time THEN 1 ELSE 0 END)
          / COUNT(*), 1)                              AS on_time_pct
FROM fact_orders f
JOIN dim_region r ON f.customer_region_key = r.region_key
WHERE f.order_status = 'delivered'
GROUP BY r.state_code, r.state_name, r.macro_region
ORDER BY total_revenue DESC;


-- ----------------------------------------------------------------
-- [CUS-3] REPEAT vs ONE-TIME BUYERS
-- -> Gauge / Donut: Ti le khach mua lai
-- ----------------------------------------------------------------
WITH customer_order_count AS (
    SELECT
        c.customer_unique_id,
        COUNT(DISTINCT f.order_id)                    AS order_count,
        ROUND(SUM(f.price), 2)                        AS total_spend
    FROM fact_orders f
    JOIN dim_customer c ON f.customer_key = c.customer_key
    WHERE f.order_status = 'delivered'
    GROUP BY c.customer_unique_id
)
SELECT
    CASE
        WHEN order_count = 1 THEN '1. One-Time Buyer'
        WHEN order_count = 2 THEN '2. Bought Twice'
        WHEN order_count = 3 THEN '3. Bought 3x'
        ELSE '4. Loyal (4+ orders)'
    END                                               AS buyer_type,
    COUNT(*)                                          AS customer_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 1) AS pct_of_customers,
    ROUND(AVG(total_spend), 2)                        AS avg_lifetime_value,
    ROUND(SUM(total_spend), 2)                        AS total_revenue_contribution
FROM customer_order_count
GROUP BY
    CASE
        WHEN order_count = 1 THEN '1. One-Time Buyer'
        WHEN order_count = 2 THEN '2. Bought Twice'
        WHEN order_count = 3 THEN '3. Bought 3x'
        ELSE '4. Loyal (4+ orders)'
    END
ORDER BY customer_count DESC;


-- ----------------------------------------------------------------
-- [CUS-4] COHORT RETENTION -- Month 0 vs Month 1+
-- -> Heatmap table: Cohort theo thang dau tien mua
-- ----------------------------------------------------------------
WITH first_purchase AS (
    SELECT
        c.customer_unique_id,
        MIN(t.full_date)                              AS cohort_date,
        DATE_FORMAT(MIN(t.full_date), '%Y-%m')        AS cohort_month
    FROM fact_orders f
    JOIN dim_customer c ON f.customer_key = c.customer_key
    JOIN dim_time t     ON f.purchase_time_key = t.time_key
    WHERE f.order_status = 'delivered'
    GROUP BY c.customer_unique_id
),
cohort_size AS (
    SELECT cohort_month, COUNT(DISTINCT customer_unique_id) AS cohort_customers
    FROM first_purchase
    GROUP BY cohort_month
),
customer_activity AS (
    SELECT
        c.customer_unique_id,
        fp.cohort_month,
        PERIOD_DIFF(
            DATE_FORMAT(t.full_date, '%Y%m'),
            DATE_FORMAT(fp.cohort_date, '%Y%m')
        )                                             AS months_since_first
    FROM fact_orders f
    JOIN dim_customer c  ON f.customer_key = c.customer_key
    JOIN dim_time t      ON f.purchase_time_key = t.time_key
    JOIN first_purchase fp ON c.customer_unique_id = fp.customer_unique_id
    WHERE f.order_status = 'delivered'
)
SELECT
    ca.cohort_month,
    cs.cohort_customers                               AS cohort_size,
    ca.months_since_first                             AS month_number,
    COUNT(DISTINCT ca.customer_unique_id)             AS active_customers,
    ROUND(100.0 * COUNT(DISTINCT ca.customer_unique_id)
          / cs.cohort_customers, 1)                   AS retention_rate_pct
FROM customer_activity ca
JOIN cohort_size cs ON ca.cohort_month = cs.cohort_month
WHERE ca.months_since_first > 0
GROUP BY ca.cohort_month, cs.cohort_customers, ca.months_since_first
HAVING ca.cohort_month >= '2017-01'
ORDER BY ca.cohort_month, ca.months_since_first;


-- ----------------------------------------------------------------
-- [CUS-5] REVIEW SCORE DISTRIBUTION
-- -> Bar chart: Cam xuc khach hang (Bimodal pattern)
-- ----------------------------------------------------------------
SELECT
    review_score,
    CASE review_score
        WHEN 5 THEN '5 - Excellent'
        WHEN 4 THEN '4 - Good'
        WHEN 3 THEN '3 - Neutral'
        WHEN 2 THEN '2 - Poor'
        WHEN 1 THEN '1 - Terrible'
    END                                               AS score_label,
    COUNT(*)                                          AS review_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 1) AS pct_of_reviews
FROM fact_orders
WHERE review_score IS NOT NULL
  AND order_status = 'delivered'
GROUP BY review_score
ORDER BY review_score DESC;


-- ----------------------------------------------------------------
-- [CUS-6] TOP 10 CITIES BY CUSTOMER COUNT
-- -> Horizontal bar: Thanh pho nao dong khach nhat
-- ----------------------------------------------------------------
SELECT
    CONCAT(c.customer_city, ' - ', c.customer_state)  AS city_state,
    COUNT(DISTINCT c.customer_unique_id)              AS unique_customers,
    COUNT(DISTINCT f.order_id)                        AS total_orders,
    ROUND(SUM(f.price), 2)                            AS total_revenue,
    ROUND(AVG(f.review_score), 2)                     AS avg_review_score
FROM fact_orders f
JOIN dim_customer c ON f.customer_key = c.customer_key
WHERE f.order_status = 'delivered'
GROUP BY c.customer_city, c.customer_state
ORDER BY unique_customers DESC
LIMIT 10;


-- ================================================================
-- 3. PRODUCT DASHBOARD
-- ================================================================

-- ----------------------------------------------------------------
-- [PRD-1] TOP 15 CATEGORY LEADERBOARD
-- -> Horizontal bar: Revenue voi badge review score
-- ----------------------------------------------------------------
SELECT
    COALESCE(p.product_category_name_english, 'Unknown') AS category,
    COUNT(*)                                          AS items_sold,
    COUNT(DISTINCT f.order_id)                        AS unique_orders,
    COUNT(DISTINCT f.customer_key)                    AS unique_buyers,
    ROUND(SUM(f.price), 2)                            AS total_revenue,
    ROUND(100.0 * SUM(f.price) / SUM(SUM(f.price)) OVER(), 1) AS revenue_share_pct,
    ROUND(AVG(f.price), 2)                            AS avg_price,
    ROUND(AVG(f.review_score), 2)                     AS avg_review_score,
    ROUND(AVG(f.delivery_days), 1)                    AS avg_delivery_days
FROM fact_orders f
JOIN dim_product p ON f.product_key = p.product_key
WHERE f.order_status = 'delivered'
GROUP BY p.product_category_name_english
ORDER BY total_revenue DESC
LIMIT 15;


-- ----------------------------------------------------------------
-- [PRD-2] CATEGORY REVENUE TREND -- Over Time
-- -> Multi-line chart: Top 5 categories qua tung thang
-- ----------------------------------------------------------------
WITH top_categories AS (
    SELECT p.product_category_name_english AS category
    FROM fact_orders f
    JOIN dim_product p ON f.product_key = p.product_key
    WHERE f.order_status = 'delivered'
      AND p.product_category_name_english IS NOT NULL
    GROUP BY p.product_category_name_english
    ORDER BY SUM(f.price) DESC
    LIMIT 5
)
SELECT
    CONCAT(t.year, '-', LPAD(t.month, 2, '0'))        AS period,
    COALESCE(p.product_category_name_english, 'Other') AS category,
    COUNT(DISTINCT f.order_id)                        AS orders,
    ROUND(SUM(f.price), 2)                            AS revenue
FROM fact_orders f
JOIN dim_time t    ON f.purchase_time_key = t.time_key
JOIN dim_product p ON f.product_key = p.product_key
JOIN top_categories tc ON p.product_category_name_english = tc.category
WHERE f.order_status = 'delivered'
GROUP BY t.year, t.month, p.product_category_name_english
ORDER BY t.year, t.month, revenue DESC;


-- ----------------------------------------------------------------
-- [PRD-3] PREMIUM vs BUDGET -- Price Bucket Analysis
-- -> Stacked bar: So luong san pham moi phan khuc gia
-- ----------------------------------------------------------------
SELECT
    CASE
        WHEN f.price < 50    THEN '1. Budget (< R$50)'
        WHEN f.price < 150   THEN '2. Mid-Range (R$50-150)'
        WHEN f.price < 500   THEN '3. Premium (R$150-500)'
        ELSE '4. Luxury (R$500+)'
    END                                               AS price_segment,
    CASE
        WHEN f.price < 50    THEN 1
        WHEN f.price < 150   THEN 2
        WHEN f.price < 500   THEN 3
        ELSE 4
    END                                               AS segment_order,
    COUNT(*)                                          AS items_sold,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 1) AS pct_items,
    ROUND(SUM(f.price), 2)                            AS total_revenue,
    ROUND(100.0 * SUM(f.price) / SUM(SUM(f.price)) OVER(), 1) AS pct_revenue,
    ROUND(AVG(f.review_score), 2)                     AS avg_review_score,
    ROUND(AVG(f.delivery_days), 1)                    AS avg_delivery_days
FROM fact_orders f
WHERE f.order_status = 'delivered'
GROUP BY price_segment, segment_order
ORDER BY segment_order;


-- ----------------------------------------------------------------
-- [PRD-4] QUALITY MATRIX -- Revenue vs Review Score
-- -> Scatter / Bubble chart: Category vua doanh thu cao vua review tot?
-- ----------------------------------------------------------------
SELECT
    COALESCE(p.product_category_name_english, 'Unknown') AS category,
    COUNT(*)                                          AS items_sold,
    ROUND(SUM(f.price), 2)                            AS total_revenue,
    ROUND(AVG(f.price), 2)                            AS avg_price,
    ROUND(AVG(f.review_score), 2)                     AS avg_review_score,
    ROUND(AVG(f.delivery_days), 1)                    AS avg_delivery_days,
    ROUND(100.0 * SUM(CASE WHEN f.is_on_time THEN 1 ELSE 0 END)
          / COUNT(*), 1)                              AS on_time_pct,
    -- Composite Quality Score = (review/5 * 60%) + (on_time/100 * 40%)
    ROUND(
        (AVG(f.review_score) / 5.0 * 60)
      + (SUM(CASE WHEN f.is_on_time THEN 1 ELSE 0 END) / COUNT(*) * 40),
        1
    )                                                 AS quality_score_100
FROM fact_orders f
JOIN dim_product p ON f.product_key = p.product_key
WHERE f.order_status = 'delivered'
GROUP BY p.product_category_name_english
HAVING items_sold >= 100
ORDER BY quality_score_100 DESC
LIMIT 20;


-- ----------------------------------------------------------------
-- [PRD-5] HOT CATEGORIES -- MoM Growth
-- -> Bar chart: Category nao dang tang truong manh nhat?
-- ----------------------------------------------------------------
WITH monthly_cat_revenue AS (
    SELECT
        CONCAT(t.year, '-', LPAD(t.month, 2, '0'))    AS period,
        t.year,
        t.month,
        COALESCE(p.product_category_name_english, 'Unknown') AS category,
        ROUND(SUM(f.price), 2)                        AS revenue
    FROM fact_orders f
    JOIN dim_time t    ON f.purchase_time_key = t.time_key
    JOIN dim_product p ON f.product_key = p.product_key
    WHERE f.order_status = 'delivered'
    GROUP BY t.year, t.month, p.product_category_name_english
),
with_lag AS (
    SELECT *,
        LAG(revenue) OVER (PARTITION BY category ORDER BY year, month) AS prev_month_revenue
    FROM monthly_cat_revenue
)
SELECT
    period,
    category,
    revenue                                           AS current_revenue,
    prev_month_revenue,
    ROUND(100.0 * (revenue - prev_month_revenue)
          / NULLIF(prev_month_revenue, 0), 1)         AS mom_growth_pct,
    CASE
        WHEN revenue > prev_month_revenue THEN 'Growing'
        WHEN revenue < prev_month_revenue THEN 'Declining'
        ELSE 'Stable'
    END                                               AS trend
FROM with_lag
WHERE period = '2018-08'
  AND prev_month_revenue IS NOT NULL
ORDER BY mom_growth_pct DESC
LIMIT 15;


-- ================================================================
-- 4. OPERATING DASHBOARD
-- ================================================================

-- ----------------------------------------------------------------
-- [OPS-1] DELIVERY KPI SCORECARD
-- -> 4 Big Number Cards: On-time rate, avg delay, etc.
-- ----------------------------------------------------------------
SELECT
    COUNT(*)                                          AS total_deliveries,
    ROUND(AVG(delivery_days), 1)                      AS avg_delivery_days,
    ROUND(AVG(estimated_delivery_days), 1)            AS avg_estimated_days,
    ROUND(AVG(CASE WHEN delay_days > 0 THEN delay_days END), 1) AS avg_delay_when_late,
    ROUND(AVG(CASE WHEN delay_days <= 0 THEN ABS(delay_days) END), 1) AS avg_early_days,
    SUM(CASE WHEN is_on_time THEN 1 ELSE 0 END)       AS on_time_count,
    SUM(CASE WHEN NOT is_on_time THEN 1 ELSE 0 END)   AS late_count,
    ROUND(100.0 * SUM(CASE WHEN is_on_time THEN 1 ELSE 0 END)
          / COUNT(*), 1)                              AS on_time_rate_pct,
    ROUND(100.0 * SUM(CASE WHEN NOT is_on_time THEN 1 ELSE 0 END)
          / COUNT(*), 1)                              AS late_rate_pct
FROM fact_orders
WHERE order_status = 'delivered'
  AND delivery_days IS NOT NULL;


-- ----------------------------------------------------------------
-- [OPS-2] DELIVERY PERFORMANCE BY SELLER STATE
-- -> Map / Ranked table: Bang nao giao hang dung han nhat?
-- ----------------------------------------------------------------
SELECT
    r.state_code                                      AS seller_state,
    r.state_name,
    r.macro_region,
    COUNT(*)                                          AS total_deliveries,
    ROUND(AVG(f.delivery_days), 1)                    AS avg_delivery_days,
    ROUND(AVG(f.estimated_delivery_days), 1)          AS avg_estimated_days,
    ROUND(AVG(f.delay_days), 1)                       AS avg_delay_days,
    ROUND(100.0 * SUM(CASE WHEN f.is_on_time THEN 1 ELSE 0 END)
          / COUNT(*), 1)                              AS on_time_pct,
    ROUND(AVG(f.review_score), 2)                     AS avg_review_score,
    -- SLA Rating
    CASE
        WHEN ROUND(100.0 * SUM(CASE WHEN f.is_on_time THEN 1 ELSE 0 END) / COUNT(*), 1) >= 90
            THEN 'Excellent'
        WHEN ROUND(100.0 * SUM(CASE WHEN f.is_on_time THEN 1 ELSE 0 END) / COUNT(*), 1) >= 75
            THEN 'Good'
        ELSE 'Needs Improvement'
    END                                               AS sla_rating
FROM fact_orders f
JOIN dim_region r ON f.seller_region_key = r.region_key
WHERE f.order_status = 'delivered'
  AND f.delivery_days IS NOT NULL
GROUP BY r.state_code, r.state_name, r.macro_region
ORDER BY on_time_pct DESC;


-- ----------------------------------------------------------------
-- [OPS-3] LATE DELIVERY -> REVIEW IMPACT
-- -> Bar+Line combo: Tre bao nhieu ngay thi review tut nhu the nao?
-- ----------------------------------------------------------------
SELECT
    CASE
        WHEN delay_days <= -7  THEN '1. Very Early (7+ days early)'
        WHEN delay_days <= -1  THEN '2. Early (1-7 days early)'
        WHEN delay_days = 0    THEN '3. Exactly On Time'
        WHEN delay_days <= 3   THEN '4. Slightly Late (1-3 days)'
        WHEN delay_days <= 7   THEN '5. Late (4-7 days)'
        ELSE '6. Very Late (7+ days)'
    END                                               AS delivery_status,
    CASE
        WHEN delay_days <= -7  THEN 1
        WHEN delay_days <= -1  THEN 2
        WHEN delay_days = 0    THEN 3
        WHEN delay_days <= 3   THEN 4
        WHEN delay_days <= 7   THEN 5
        ELSE 6
    END                                               AS sort_order,
    COUNT(*)                                          AS order_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 1) AS pct_of_orders,
    ROUND(AVG(review_score), 2)                       AS avg_review_score,
    ROUND(MIN(review_score), 0)                       AS min_review,
    ROUND(MAX(review_score), 0)                       AS max_review
FROM fact_orders
WHERE order_status = 'delivered'
  AND delay_days IS NOT NULL
  AND review_score IS NOT NULL
GROUP BY delivery_status, sort_order
ORDER BY sort_order;


-- ----------------------------------------------------------------
-- [OPS-4] TOP SELLER PERFORMANCE TABLE
-- -> Sortable table: Ai la seller ngon nhat?
-- ----------------------------------------------------------------
SELECT
    s.seller_id,
    s.seller_city,
    s.seller_state,
    COUNT(DISTINCT f.order_id)                        AS total_orders,
    COUNT(*)                                          AS items_sold,
    ROUND(SUM(f.price), 2)                            AS total_revenue,
    ROUND(AVG(f.price), 2)                            AS avg_item_price,
    ROUND(AVG(f.review_score), 2)                     AS avg_review_score,
    ROUND(AVG(f.delivery_days), 1)                    AS avg_delivery_days,
    ROUND(100.0 * SUM(CASE WHEN f.is_on_time THEN 1 ELSE 0 END)
          / COUNT(*), 1)                              AS on_time_pct,
    CASE
        WHEN AVG(f.review_score) >= 4.5
         AND ROUND(100.0 * SUM(CASE WHEN f.is_on_time THEN 1 ELSE 0 END) / COUNT(*), 1) >= 90
            THEN 'Top Performer'
        WHEN AVG(f.review_score) >= 4.0
         AND ROUND(100.0 * SUM(CASE WHEN f.is_on_time THEN 1 ELSE 0 END) / COUNT(*), 1) >= 75
            THEN 'Good Seller'
        WHEN AVG(f.review_score) < 3.5
            THEN 'Needs Review'
        ELSE 'Average'
    END                                               AS seller_tier
FROM fact_orders f
JOIN dim_seller s ON f.seller_key = s.seller_key
WHERE f.order_status = 'delivered'
GROUP BY s.seller_id, s.seller_city, s.seller_state
HAVING total_orders >= 10
ORDER BY total_revenue DESC
LIMIT 50;


-- ----------------------------------------------------------------
-- [OPS-5] DELIVERY DAYS DISTRIBUTION
-- -> Histogram: Phan phoi thoi gian giao hang
-- ----------------------------------------------------------------
SELECT
    CASE
        WHEN delivery_days <= 3   THEN '1. Express (1-3 days)'
        WHEN delivery_days <= 7   THEN '2. Fast (4-7 days)'
        WHEN delivery_days <= 14  THEN '3. Standard (8-14 days)'
        WHEN delivery_days <= 21  THEN '4. Slow (15-21 days)'
        WHEN delivery_days <= 30  THEN '5. Very Slow (22-30 days)'
        ELSE '6. Critical (31+ days)'
    END                                               AS delivery_bucket,
    COUNT(*)                                          AS order_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 1) AS pct_of_orders,
    ROUND(AVG(review_score), 2)                       AS avg_review_score,
    ROUND(AVG(delay_days), 1)                         AS avg_delay_days
FROM fact_orders
WHERE order_status = 'delivered'
  AND delivery_days IS NOT NULL
  AND delivery_days > 0
GROUP BY delivery_bucket
ORDER BY delivery_bucket;


-- ----------------------------------------------------------------
-- [OPS-6] MONTHLY ON-TIME TREND
-- -> Line chart: SLA trend theo thoi gian
-- ----------------------------------------------------------------
SELECT
    CONCAT(t.year, '-', LPAD(t.month, 2, '0'))        AS period,
    COUNT(*)                                          AS total_deliveries,
    SUM(CASE WHEN f.is_on_time THEN 1 ELSE 0 END)     AS on_time_count,
    SUM(CASE WHEN NOT f.is_on_time THEN 1 ELSE 0 END) AS late_count,
    ROUND(100.0 * SUM(CASE WHEN f.is_on_time THEN 1 ELSE 0 END)
          / COUNT(*), 1)                              AS on_time_rate_pct,
    ROUND(AVG(f.delivery_days), 1)                    AS avg_delivery_days,
    ROUND(AVG(f.delay_days), 1)                       AS avg_delay_days,
    ROUND(AVG(f.review_score), 2)                     AS avg_review_score
FROM fact_orders f
JOIN dim_time t ON f.purchase_time_key = t.time_key
WHERE f.order_status = 'delivered'
  AND f.delivery_days IS NOT NULL
GROUP BY t.year, t.month
ORDER BY t.year, t.month;
