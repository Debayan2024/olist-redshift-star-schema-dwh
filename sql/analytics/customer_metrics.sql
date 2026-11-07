-- ============================================
-- Customer Analytics Report
-- Purpose: Customer behavior and retention metrics
-- ============================================

-- ============================================
-- Customer Cohort Analysis
-- ============================================

WITH customer_cohorts AS (
    SELECT
        dc.customer_id,
        DATE_TRUNC('month', dc.registration_date) as cohort_month,
        DATE_TRUNC('month', dd.date_actual) as order_month,
        EXTRACT(YEAR FROM AGE(dd.date_actual, dc.registration_date)) * 12 + 
        EXTRACT(MONTH FROM AGE(dd.date_actual, dc.registration_date)) as months_since_registration,
        SUM(fo.net_amount) as revenue
    FROM analytics.dim_customers dc
    INNER JOIN analytics.fact_orders fo ON dc.customer_key = fo.customer_key
    INNER JOIN analytics.dim_date dd ON fo.order_date_key = dd.date_key
    WHERE dc.is_current = TRUE
    GROUP BY dc.customer_id, dc.registration_date, dd.date_actual
)
SELECT
    TO_CHAR(cohort_month, 'YYYY-MM') as cohort,
    COUNT(DISTINCT CASE WHEN months_since_registration = 0 THEN customer_id END) as month_0,
    COUNT(DISTINCT CASE WHEN months_since_registration = 1 THEN customer_id END) as month_1,
    COUNT(DISTINCT CASE WHEN months_since_registration = 2 THEN customer_id END) as month_2,
    COUNT(DISTINCT CASE WHEN months_since_registration = 3 THEN customer_id END) as month_3,
    COUNT(DISTINCT CASE WHEN months_since_registration = 6 THEN customer_id END) as month_6,
    COUNT(DISTINCT CASE WHEN months_since_registration = 12 THEN customer_id END) as month_12,
    -- Retention rates
    ROUND(COUNT(DISTINCT CASE WHEN months_since_registration = 1 THEN customer_id END)::NUMERIC / 
          NULLIF(COUNT(DISTINCT CASE WHEN months_since_registration = 0 THEN customer_id END), 0) * 100, 2) as retention_month_1_pct,
    ROUND(COUNT(DISTINCT CASE WHEN months_since_registration = 3 THEN customer_id END)::NUMERIC / 
          NULLIF(COUNT(DISTINCT CASE WHEN months_since_registration = 0 THEN customer_id END), 0) * 100, 2) as retention_month_3_pct
FROM customer_cohorts
WHERE cohort_month >= CURRENT_DATE - INTERVAL '12 months'
GROUP BY cohort_month
ORDER BY cohort_month DESC;

-- ============================================
-- Customer Lifetime Value (CLV) Analysis
-- ============================================

SELECT
    dc.customer_segment,
    dc.customer_tier,
    dc.age_group,
    COUNT(DISTINCT dc.customer_key) as customer_count,
    ROUND(AVG(dc.total_lifetime_value), 0) as avg_ltv,
    ROUND(PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY dc.total_lifetime_value), 0) as median_ltv,
    ROUND(AVG(dc.total_lifetime_orders), 1) as avg_lifetime_orders,
    ROUND(AVG(dc.average_order_value), 0) as avg_order_value,
    ROUND(AVG(CASE WHEN dc.last_order_date IS NOT NULL 
        THEN EXTRACT(DAY FROM AGE(dc.last_order_date, dc.first_order_date)) 
        END), 0) as avg_customer_lifespan_days,
    ROUND(AVG(dc.days_since_last_order), 0) as avg_days_since_last_order,
    COUNT(CASE WHEN dc.days_since_last_order > 90 THEN 1 END) as at_risk_customers,
    COUNT(CASE WHEN dc.days_since_last_order > 180 THEN 1 END) as churned_customers
FROM analytics.dim_customers dc
WHERE dc.is_current = TRUE
    AND dc.total_lifetime_orders > 0
GROUP BY dc.customer_segment, dc.customer_tier, dc.age_group
ORDER BY avg_ltv DESC;

-- ============================================
-- RFM (Recency, Frequency, Monetary) Segmentation
-- ============================================

WITH rfm_calc AS (
    SELECT
        dc.customer_key,
        dc.customer_id,
        dc.full_name,
        dc.email,
        -- Recency: Days since last order
        COALESCE(dc.days_since_last_order, 999) as recency_days,
        -- Frequency: Number of orders
        dc.total_lifetime_orders as frequency,
        -- Monetary: Total spent
        dc.total_lifetime_value as monetary,
        -- Calculate RFM scores (1-5 scale)
        NTILE(5) OVER (ORDER BY COALESCE(dc.days_since_last_order, 999) DESC) as r_score,
        NTILE(5) OVER (ORDER BY dc.total_lifetime_orders ASC) as f_score,
        NTILE(5) OVER (ORDER BY dc.total_lifetime_value ASC) as m_score
    FROM analytics.dim_customers dc
    WHERE dc.is_current = TRUE
        AND dc.total_lifetime_orders > 0
)
SELECT
    customer_id,
    full_name,
    email,
    recency_days,
    frequency,
    ROUND(monetary, 0) as monetary,
    r_score,
    f_score,
    m_score,
    (r_score + f_score + m_score) as rfm_score,
    -- RFM Segmentation
    CASE
        WHEN r_score >= 4 AND f_score >= 4 AND m_score >= 4 THEN 'Champions'
        WHEN r_score >= 3 AND f_score >= 3 THEN 'Loyal Customers'
        WHEN r_score >= 4 AND f_score <= 2 THEN 'New Customers'
        WHEN r_score >= 3 AND m_score >= 4 THEN 'Big Spenders'
        WHEN r_score <= 2 AND f_score >= 3 THEN 'At Risk'
        WHEN r_score <= 2 AND f_score <= 2 THEN 'Lost'
        WHEN r_score = 3 THEN 'Need Attention'
        ELSE 'Others'
    END as customer_segment_rfm
FROM rfm_calc
ORDER BY rfm_score DESC, monetary DESC
LIMIT 100;

-- ============================================
-- Customer Acquisition Analysis
-- ============================================

SELECT
    dd.year,
    dd.month_name,
    dd.date_actual::DATE as date,
    COUNT(DISTINCT dc.customer_key) as new_customers,
    COUNT(DISTINCT CASE WHEN fo.is_first_order THEN fo.customer_key END) as first_time_buyers,
    ROUND(AVG(fo.net_amount), 0) as avg_first_order_value,
    COUNT(DISTINCT fo.order_id) as total_first_orders,
    ROUND(SUM(fo.net_amount), 0) as total_first_order_revenue
FROM analytics.dim_customers dc
LEFT JOIN analytics.fact_orders fo ON dc.customer_key = fo.customer_key AND fo.is_first_order = TRUE
LEFT JOIN analytics.dim_date dd ON DATE(dc.registration_date) = dd.date_actual
WHERE dd.date_actual >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY dd.year, dd.month_name, dd.date_actual
ORDER BY dd.date_actual DESC;

-- ============================================
-- Customer Repeat Purchase Behavior
-- ============================================

WITH customer_orders AS (
    SELECT
        dc.customer_key,
        dc.customer_id,
        dc.full_name,
        dc.registration_date,
        COUNT(fo.order_id) as total_orders,
        MIN(dd.date_actual) as first_order_date,
        MAX(dd.date_actual) as last_order_date,
        ROUND(AVG(fo.net_amount), 0) as avg_order_value,
        ROUND(SUM(fo.net_amount), 0) as total_spent,
        -- Calculate average days between orders
        CASE 
            WHEN COUNT(fo.order_id) > 1 
            THEN ROUND(EXTRACT(DAY FROM AGE(MAX(dd.date_actual), MIN(dd.date_actual)))::NUMERIC / 
                 NULLIF(COUNT(fo.order_id) - 1, 0), 1)
            ELSE NULL
        END as avg_days_between_orders
    FROM analytics.dim_customers dc
    LEFT JOIN analytics.fact_orders fo ON dc.customer_key = fo.customer_key
    LEFT JOIN analytics.dim_date dd ON fo.order_date_key = dd.date_key
    WHERE dc.is_current = TRUE
    GROUP BY dc.customer_key, dc.customer_id, dc.full_name, dc.registration_date
)
SELECT
    CASE 
        WHEN total_orders = 1 THEN '1 order'
        WHEN total_orders = 2 THEN '2 orders'
        WHEN total_orders BETWEEN 3 AND 5 THEN '3-5 orders'
        WHEN total_orders BETWEEN 6 AND 10 THEN '6-10 orders'
        WHEN total_orders > 10 THEN '10+ orders'
        ELSE 'No orders'
    END as order_frequency_bucket,
    COUNT(DISTINCT customer_key) as customer_count,
    ROUND(AVG(total_spent), 0) as avg_total_spent,
    ROUND(AVG(avg_order_value), 0) as avg_order_value,
    ROUND(AVG(avg_days_between_orders), 1) as avg_days_between_orders,
    ROUND(COUNT(DISTINCT customer_key) / SUM(COUNT(DISTINCT customer_key)) OVER () * 100, 2) as customer_pct
FROM customer_orders
GROUP BY order_frequency_bucket
ORDER BY 
    CASE order_frequency_bucket
        WHEN 'No orders' THEN 0
        WHEN '1 order' THEN 1
        WHEN '2 orders' THEN 2
        WHEN '3-5 orders' THEN 3
        WHEN '6-10 orders' THEN 4
        WHEN '10+ orders' THEN 5
    END;

-- ============================================
-- Customer Churn Risk Analysis
-- ============================================

SELECT
    dc.customer_segment,
    CASE 
        WHEN dc.days_since_last_order IS NULL THEN 'Never Ordered'
        WHEN dc.days_since_last_order <= 30 THEN 'Active (0-30 days)'
        WHEN dc.days_since_last_order <= 60 THEN 'Recent (31-60 days)'
        WHEN dc.days_since_last_order <= 90 THEN 'Cooling (61-90 days)'
        WHEN dc.days_since_last_order <= 180 THEN 'At Risk (91-180 days)'
        ELSE 'Churned (180+ days)'
    END as activity_status,
    COUNT(DISTINCT dc.customer_key) as customer_count,
    ROUND(AVG(dc.total_lifetime_value), 0) as avg_ltv,
    ROUND(AVG(dc.total_lifetime_orders), 1) as avg_orders,
    ROUND(SUM(dc.total_lifetime_value), 0) as total_value_at_risk,
    ROUND(COUNT(DISTINCT dc.customer_key) / SUM(COUNT(DISTINCT dc.customer_key)) OVER () * 100, 2) as customer_pct
FROM analytics.dim_customers dc
WHERE dc.is_current = TRUE
GROUP BY dc.customer_segment, activity_status
ORDER BY 
    dc.customer_segment,
    CASE activity_status
        WHEN 'Never Ordered' THEN 1
        WHEN 'Active (0-30 days)' THEN 2
        WHEN 'Recent (31-60 days)' THEN 3
        WHEN 'Cooling (61-90 days)' THEN 4
        WHEN 'At Risk (91-180 days)' THEN 5
        WHEN 'Churned (180+ days)' THEN 6
    END;

-- ============================================
-- Top Customers by Value
-- ============================================

SELECT
    dc.customer_id,
    dc.full_name,
    dc.email,
    dc.customer_segment,
    dc.customer_tier,
    dc.registration_date::DATE as registration_date,
    dc.total_lifetime_orders,
    ROUND(dc.total_lifetime_value, 0) as lifetime_value,
    ROUND(dc.average_order_value, 0) as avg_order_value,
    dc.last_order_date::DATE as last_order_date,
    dc.days_since_last_order,
    CASE 
        WHEN dc.days_since_last_order <= 30 THEN 'Active'
        WHEN dc.days_since_last_order <= 90 THEN 'Recent'
        WHEN dc.days_since_last_order <= 180 THEN 'At Risk'
        ELSE 'Churned'
    END as status
FROM analytics.dim_customers dc
WHERE dc.is_current = TRUE
    AND dc.total_lifetime_orders > 0
ORDER BY dc.total_lifetime_value DESC
LIMIT 50;

