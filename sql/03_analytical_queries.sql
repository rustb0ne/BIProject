-- Các câu query phân tích insight từ DWH

USE olist_dwh;

-- ================================================================
-- 1. EXECUTIVE KPIs
-- ================================================================

-- Tổng quan doanh thu & đơn hàng
SELECT
    COUNT(DISTINCT order_id)                   AS total_orders,
    COUNT(*)                                   AS total_order_items,
    ROUND(SUM(price), 2)                       AS total_product_revenue,
    ROUND(SUM(freight_value), 2)               AS total_freight_revenue,
    ROUND(SUM(total_revenue), 2)               AS total_revenue,
    ROUND(AVG(price), 2)                       AS avg_item_price,
    ROUND(SUM(price) / COUNT(DISTINCT order_id), 2) AS avg_order_value,
    ROUND(AVG(review_score), 2)                AS avg_review_score,
    COUNT(DISTINCT customer_key)               AS unique_customers
FROM fact_orders
WHERE order_status = 'delivered';


-- ================================================================
-- 2. TOP SẢN PHẨM BÁN CHẠY (theo doanh thu và số lượng)
-- ================================================================

-- Top 20 danh mục theo doanh thu
SELECT
    p.product_category_name_english            AS category,
    COUNT(*)                                   AS items_sold,
    COUNT(DISTINCT f.order_id)                 AS orders,
    ROUND(SUM(f.price), 2)                     AS total_revenue,
    ROUND(AVG(f.price), 2)                     AS avg_price,
    ROUND(AVG(f.review_score), 2)              AS avg_review_score
FROM fact_orders f
JOIN dim_product p ON f.product_key = p.product_key
WHERE f.order_status = 'delivered'
GROUP BY p.product_category_name_english
ORDER BY total_revenue DESC
LIMIT 20;

-- Top 20 danh mục theo số lượng bán
SELECT
    p.product_category_name_english            AS category,
    COUNT(*)                                   AS items_sold,
    ROUND(SUM(f.price), 2)                     AS total_revenue,
    ROUND(AVG(f.price), 2)                     AS avg_price
FROM fact_orders f
JOIN dim_product p ON f.product_key = p.product_key
WHERE f.order_status = 'delivered'
GROUP BY p.product_category_name_english
ORDER BY items_sold DESC
LIMIT 20;


-- ================================================================
-- 3. DOANH THU THEO THỜI GIAN
-- ================================================================

-- Doanh thu theo tháng
SELECT
    t.year,
    t.month,
    t.month_name,
    CONCAT(t.year, '-', LPAD(t.month, 2, '0')) AS year_month,
    COUNT(DISTINCT f.order_id)                  AS total_orders,
    COUNT(*)                                    AS total_items,
    ROUND(SUM(f.price), 2)                      AS product_revenue,
    ROUND(SUM(f.freight_value), 2)              AS freight_revenue,
    ROUND(SUM(f.total_revenue), 2)              AS total_revenue,
    ROUND(AVG(f.review_score), 2)               AS avg_review_score
FROM fact_orders f
JOIN dim_time t ON f.purchase_time_key = t.time_key
WHERE f.order_status IN ('delivered', 'shipped')
GROUP BY t.year, t.month, t.month_name
ORDER BY t.year, t.month;

-- Doanh thu theo quý
SELECT
    t.year,
    t.quarter,
    CONCAT(t.year, ' Q', t.quarter)            AS year_quarter,
    COUNT(DISTINCT f.order_id)                  AS total_orders,
    ROUND(SUM(f.price), 2)                      AS product_revenue,
    ROUND(SUM(f.total_revenue), 2)              AS total_revenue,
    ROUND(AVG(f.review_score), 2)               AS avg_review_score
FROM fact_orders f
JOIN dim_time t ON f.purchase_time_key = t.time_key
WHERE f.order_status IN ('delivered', 'shipped')
GROUP BY t.year, t.quarter
ORDER BY t.year, t.quarter;

-- Doanh thu theo ngày trong tuần (hành vi mua sắm)
SELECT
    t.day_of_week,
    t.day_name,
    COUNT(DISTINCT f.order_id)                  AS total_orders,
    ROUND(SUM(f.price), 2)                      AS total_revenue,
    ROUND(AVG(f.price), 2)                      AS avg_order_value
FROM fact_orders f
JOIN dim_time t ON f.purchase_time_key = t.time_key
WHERE f.order_status IN ('delivered', 'shipped')
GROUP BY t.day_of_week, t.day_name
ORDER BY t.day_of_week;


-- ================================================================
-- 4. PHÂN TÍCH THEO ĐỊA LÝ
-- ================================================================

-- Doanh thu theo bang khách hàng
SELECT
    r.state_code,
    r.state_name,
    r.macro_region,
    COUNT(DISTINCT f.order_id)                  AS total_orders,
    COUNT(DISTINCT f.customer_key)              AS unique_customers,
    ROUND(SUM(f.price), 2)                      AS total_revenue,
    ROUND(AVG(f.price), 2)                      AS avg_order_value,
    ROUND(AVG(f.delivery_days), 1)              AS avg_delivery_days,
    ROUND(AVG(f.review_score), 2)               AS avg_review_score,
    ROUND(100.0 * SUM(CASE WHEN f.is_on_time THEN 1 ELSE 0 END)
          / COUNT(*), 1)                         AS pct_on_time
FROM fact_orders f
JOIN dim_region r ON f.customer_region_key = r.region_key
WHERE f.order_status = 'delivered'
GROUP BY r.state_code, r.state_name, r.macro_region
ORDER BY total_revenue DESC;

-- Doanh thu theo macro region
SELECT
    r.macro_region,
    COUNT(DISTINCT f.order_id)                  AS total_orders,
    ROUND(SUM(f.price), 2)                      AS total_revenue,
    ROUND(100.0 * SUM(f.price) / SUM(SUM(f.price)) OVER(), 1) AS pct_revenue
FROM fact_orders f
JOIN dim_region r ON f.customer_region_key = r.region_key
WHERE f.order_status = 'delivered'
GROUP BY r.macro_region
ORDER BY total_revenue DESC;


-- ================================================================
-- 5. HÀNH VI KHÁCH HÀNG (RFM ANALYSIS)
-- ================================================================

-- RFM base: tính R, F, M cho mỗi unique customer
WITH customer_rfm AS (
    SELECT
        c.customer_unique_id,
        MAX(t.full_date)                        AS last_purchase_date,
        DATEDIFF('2018-10-01', MAX(t.full_date)) AS recency_days,
        COUNT(DISTINCT f.order_id)              AS frequency,
        ROUND(SUM(f.price), 2)                  AS monetary
    FROM fact_orders f
    JOIN dim_customer c  ON f.customer_key = c.customer_key
    JOIN dim_time t      ON f.purchase_time_key = t.time_key
    WHERE f.order_status = 'delivered'
    GROUP BY c.customer_unique_id
),
rfm_scored AS (
    SELECT
        customer_unique_id,
        last_purchase_date,
        recency_days,
        frequency,
        monetary,
        NTILE(5) OVER (ORDER BY recency_days ASC)  AS r_score,   -- lower recency = better
        NTILE(5) OVER (ORDER BY frequency DESC)    AS f_score,
        NTILE(5) OVER (ORDER BY monetary DESC)     AS m_score
    FROM customer_rfm
)
SELECT
    customer_unique_id,
    last_purchase_date,
    recency_days,
    frequency,
    monetary,
    r_score, f_score, m_score,
    (r_score + f_score + m_score)               AS rfm_total,
    CASE
        WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
        WHEN r_score >= 3 AND f_score >= 3                  THEN 'Loyal Customers'
        WHEN r_score >= 4 AND f_score <= 2                  THEN 'Recent Customers'
        WHEN r_score <= 2 AND f_score >= 3                  THEN 'At Risk'
        WHEN r_score = 1  AND f_score = 1                   THEN 'Lost'
        ELSE 'Potential Loyalists'
    END                                         AS rfm_segment
FROM rfm_scored
ORDER BY rfm_total DESC;

-- RFM Segment Summary
WITH customer_rfm AS (
    SELECT
        c.customer_unique_id,
        DATEDIFF('2018-10-01', MAX(t.full_date)) AS recency_days,
        COUNT(DISTINCT f.order_id)              AS frequency,
        ROUND(SUM(f.price), 2)                  AS monetary
    FROM fact_orders f
    JOIN dim_customer c ON f.customer_key = c.customer_key
    JOIN dim_time t     ON f.purchase_time_key = t.time_key
    WHERE f.order_status = 'delivered'
    GROUP BY c.customer_unique_id
),
rfm_scored AS (
    SELECT *,
        NTILE(5) OVER (ORDER BY recency_days ASC) AS r_score,
        NTILE(5) OVER (ORDER BY frequency DESC)   AS f_score,
        NTILE(5) OVER (ORDER BY monetary DESC)    AS m_score
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
    rfm_segment,
    COUNT(*)                            AS customer_count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 1) AS pct_customers,
    ROUND(AVG(recency_days), 0)         AS avg_recency_days,
    ROUND(AVG(frequency), 1)            AS avg_frequency,
    ROUND(AVG(monetary), 2)             AS avg_monetary,
    ROUND(SUM(monetary), 2)             AS total_monetary
FROM rfm_segmented
GROUP BY rfm_segment
ORDER BY total_monetary DESC;


-- ================================================================
-- 6. PHÂN TÍCH VẬN HÀNH & GIAO HÀNG
-- ================================================================

-- Thời gian giao hàng trung bình theo bang người bán
SELECT
    r.state_code                                AS seller_state,
    r.state_name,
    COUNT(*)                                    AS deliveries,
    ROUND(AVG(f.delivery_days), 1)              AS avg_delivery_days,
    ROUND(AVG(f.estimated_delivery_days), 1)    AS avg_estimated_days,
    ROUND(AVG(f.delay_days), 1)                 AS avg_delay_days,
    ROUND(100.0 * SUM(CASE WHEN f.is_on_time THEN 1 ELSE 0 END)
          / COUNT(*), 1)                         AS pct_on_time
FROM fact_orders f
JOIN dim_region r ON f.seller_region_key = r.region_key
WHERE f.order_status = 'delivered' AND f.delivery_days IS NOT NULL
GROUP BY r.state_code, r.state_name
ORDER BY avg_delivery_days;

-- Phân phối review score
SELECT
    review_score,
    COUNT(*)                                    AS count,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 1) AS pct
FROM fact_orders
WHERE review_score IS NOT NULL
GROUP BY review_score
ORDER BY review_score;

-- Phương thức thanh toán phổ biến
SELECT
    payment_type,
    COUNT(DISTINCT order_id)                    AS orders,
    ROUND(100.0 * COUNT(DISTINCT order_id)
          / SUM(COUNT(DISTINCT order_id)) OVER(), 1) AS pct_orders,
    ROUND(SUM(payment_value), 2)                AS total_payment,
    ROUND(AVG(payment_installments), 1)         AS avg_installments
FROM fact_orders
WHERE payment_type IS NOT NULL
GROUP BY payment_type
ORDER BY orders DESC;


-- ================================================================
-- 7. SELLER PERFORMANCE
-- ================================================================

SELECT
    s.seller_id,
    s.seller_state,
    COUNT(DISTINCT f.order_id)                  AS total_orders,
    COUNT(*)                                    AS items_sold,
    ROUND(SUM(f.price), 2)                      AS total_revenue,
    ROUND(AVG(f.price), 2)                      AS avg_item_price,
    ROUND(AVG(f.review_score), 2)               AS avg_review_score,
    ROUND(AVG(f.delivery_days), 1)              AS avg_delivery_days,
    ROUND(100.0 * SUM(CASE WHEN f.is_on_time THEN 1 ELSE 0 END)
          / COUNT(*), 1)                         AS pct_on_time
FROM fact_orders f
JOIN dim_seller s ON f.seller_key = s.seller_key
WHERE f.order_status = 'delivered'
GROUP BY s.seller_id, s.seller_state
HAVING total_orders >= 5
ORDER BY total_revenue DESC
LIMIT 50;


-- ================================================================
-- 8. COHORT ANALYSIS (Monthly cohorts by first purchase)
-- ================================================================

WITH first_purchase AS (
    SELECT
        c.customer_unique_id,
        MIN(t.full_date)                        AS cohort_date,
        DATE_FORMAT(MIN(t.full_date), '%Y-%m')  AS cohort_month
    FROM fact_orders f
    JOIN dim_customer c ON f.customer_key = c.customer_key
    JOIN dim_time t     ON f.purchase_time_key = t.time_key
    WHERE f.order_status = 'delivered'
    GROUP BY c.customer_unique_id
),
customer_activity AS (
    SELECT
        c.customer_unique_id,
        fp.cohort_month,
        DATE_FORMAT(t.full_date, '%Y-%m')       AS activity_month,
        PERIOD_DIFF(
            DATE_FORMAT(t.full_date, '%Y%m'),
            DATE_FORMAT(fp.cohort_date, '%Y%m')
        )                                       AS months_since_first
    FROM fact_orders f
    JOIN dim_customer c ON f.customer_key = c.customer_key
    JOIN dim_time t     ON f.purchase_time_key = t.time_key
    JOIN first_purchase fp ON c.customer_unique_id = fp.customer_unique_id
    WHERE f.order_status = 'delivered'
)
SELECT
    cohort_month,
    months_since_first,
    COUNT(DISTINCT customer_unique_id)          AS active_customers
FROM customer_activity
GROUP BY cohort_month, months_since_first
ORDER BY cohort_month, months_since_first;
