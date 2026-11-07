-- ============================================
-- Daily Sales Report
-- Purpose: Key daily metrics for business monitoring
-- ============================================

WITH daily_metrics AS (
    SELECT
        dd.date_actual,
        dd.day_name,
        dd.month_name,
        dd.year,
        SUM(fds.total_orders) as total_orders,
        SUM(fds.total_customers) as total_customers,
        SUM(fds.new_customers) as new_customers,
        SUM(fds.returning_customers) as returning_customers,
        SUM(fds.total_items_sold) as total_items_sold,
        SUM(fds.total_gross_revenue) as gross_revenue,
        SUM(fds.total_discounts) as total_discounts,
        SUM(fds.total_net_revenue) as net_revenue,
        SUM(fds.total_product_cost) as total_cost,
        SUM(fds.total_gross_profit) as gross_profit,
        AVG(fds.average_order_value) as avg_order_value,
        AVG(fds.average_items_per_order) as avg_items_per_order
    FROM analytics.fact_daily_sales fds
    INNER JOIN analytics.dim_date dd ON fds.date_key = dd.date_key
    WHERE dd.date_actual >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY dd.date_actual, dd.day_name, dd.month_name, dd.year
),
previous_period AS (
    SELECT
        dd.date_actual + INTERVAL '1 day' as compare_date,
        SUM(fds.total_orders) as prev_orders,
        SUM(fds.total_net_revenue) as prev_revenue
    FROM analytics.fact_daily_sales fds
    INNER JOIN analytics.dim_date dd ON fds.date_key = dd.date_key
    WHERE dd.date_actual >= CURRENT_DATE - INTERVAL '60 days'
        AND dd.date_actual < CURRENT_DATE - INTERVAL '30 days'
    GROUP BY dd.date_actual
)
SELECT
    dm.date_actual,
    dm.day_name,
    dm.total_orders,
    dm.total_customers,
    dm.new_customers,
    dm.returning_customers,
    ROUND(dm.returning_customers::NUMERIC / NULLIF(dm.total_customers, 0) * 100, 2) as returning_customer_pct,
    dm.total_items_sold,
    ROUND(dm.gross_revenue, 0) as gross_revenue,
    ROUND(dm.total_discounts, 0) as total_discounts,
    ROUND(dm.net_revenue, 0) as net_revenue,
    ROUND(dm.gross_profit, 0) as gross_profit,
    ROUND(dm.gross_profit / NULLIF(dm.net_revenue, 0) * 100, 2) as margin_percent,
    ROUND(dm.avg_order_value, 0) as avg_order_value,
    ROUND(dm.avg_items_per_order, 1) as avg_items_per_order,
    -- Comparison with previous period
    CASE 
        WHEN pp.prev_orders > 0 
        THEN ROUND((dm.total_orders - pp.prev_orders)::NUMERIC / pp.prev_orders * 100, 2)
        ELSE NULL
    END as order_growth_pct,
    CASE 
        WHEN pp.prev_revenue > 0 
        THEN ROUND((dm.net_revenue - pp.prev_revenue) / pp.prev_revenue * 100, 2)
        ELSE NULL
    END as revenue_growth_pct
FROM daily_metrics dm
LEFT JOIN previous_period pp ON dm.date_actual = pp.compare_date
ORDER BY dm.date_actual DESC;

-- ============================================
-- Sales by Category
-- ============================================

SELECT
    dp.category,
    COUNT(DISTINCT foi.order_id) as total_orders,
    SUM(foi.quantity) as units_sold,
    ROUND(SUM(foi.net_revenue), 0) as net_revenue,
    ROUND(SUM(foi.gross_profit), 0) as gross_profit,
    ROUND(AVG(foi.unit_price), 0) as avg_unit_price,
    ROUND(SUM(foi.net_revenue) / SUM(SUM(foi.net_revenue)) OVER () * 100, 2) as revenue_share_pct
FROM analytics.fact_order_items foi
INNER JOIN analytics.dim_products dp ON foi.product_key = dp.product_key
INNER JOIN analytics.dim_date dd ON foi.order_date_key = dd.date_key
WHERE dd.date_actual >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY dp.category
ORDER BY net_revenue DESC;

-- ============================================
-- Top Products by Revenue
-- ============================================

SELECT
    dp.product_name,
    dp.category,
    dp.brand,
    COUNT(DISTINCT foi.order_id) as times_ordered,
    SUM(foi.quantity) as units_sold,
    ROUND(SUM(foi.net_revenue), 0) as net_revenue,
    ROUND(SUM(foi.gross_profit), 0) as gross_profit,
    ROUND(AVG(foi.unit_price), 0) as avg_price
FROM analytics.fact_order_items foi
INNER JOIN analytics.dim_products dp ON foi.product_key = dp.product_key
INNER JOIN analytics.dim_date dd ON foi.order_date_key = dd.date_key
WHERE dd.date_actual >= CURRENT_DATE - INTERVAL '30 days'
    AND dp.is_current = TRUE
GROUP BY dp.product_name, dp.category, dp.brand
ORDER BY net_revenue DESC
LIMIT 20;

-- ============================================
-- Sales by Region
-- ============================================

SELECT
    dl.region,
    dl.province,
    COUNT(DISTINCT fo.order_id) as total_orders,
    COUNT(DISTINCT fo.customer_key) as total_customers,
    ROUND(SUM(fo.net_amount), 0) as net_revenue,
    ROUND(AVG(fo.net_amount), 0) as avg_order_value,
    ROUND(SUM(fo.net_amount) / SUM(SUM(fo.net_amount)) OVER () * 100, 2) as revenue_share_pct
FROM analytics.fact_orders fo
INNER JOIN analytics.dim_locations dl ON fo.location_key = dl.location_key
INNER JOIN analytics.dim_date dd ON fo.order_date_key = dd.date_key
WHERE dd.date_actual >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY dl.region, dl.province
ORDER BY net_revenue DESC;

-- ============================================
-- Customer Segments Performance
-- ============================================

SELECT
    dc.customer_segment,
    dc.customer_tier,
    COUNT(DISTINCT dc.customer_key) as customer_count,
    COUNT(DISTINCT fo.order_id) as total_orders,
    ROUND(AVG(dc.total_lifetime_value), 0) as avg_ltv,
    ROUND(AVG(dc.average_order_value), 0) as avg_order_value,
    ROUND(AVG(dc.total_lifetime_orders), 1) as avg_orders_per_customer,
    ROUND(SUM(fo.net_amount), 0) as period_revenue
FROM analytics.dim_customers dc
LEFT JOIN analytics.fact_orders fo ON dc.customer_key = fo.customer_key
LEFT JOIN analytics.dim_date dd ON fo.order_date_key = dd.date_key
    AND dd.date_actual >= CURRENT_DATE - INTERVAL '30 days'
WHERE dc.is_current = TRUE
GROUP BY dc.customer_segment, dc.customer_tier
ORDER BY period_revenue DESC NULLS LAST;

-- ============================================
-- Payment Method Analysis
-- ============================================

SELECT
    dpm.payment_method_name,
    dpm.payment_type,
    COUNT(DISTINCT fo.order_id) as total_orders,
    ROUND(SUM(fo.payment_amount), 0) as total_amount,
    ROUND(AVG(fo.payment_amount), 0) as avg_transaction,
    ROUND(COUNT(fo.order_id) / SUM(COUNT(fo.order_id)) OVER () * 100, 2) as usage_pct,
    ROUND(SUM(fo.payment_amount) / SUM(SUM(fo.payment_amount)) OVER () * 100, 2) as amount_share_pct
FROM analytics.fact_orders fo
INNER JOIN analytics.dim_payment_methods dpm ON fo.payment_method_key = dpm.payment_method_key
INNER JOIN analytics.dim_date dd ON fo.order_date_key = dd.date_key
WHERE dd.date_actual >= CURRENT_DATE - INTERVAL '30 days'
    AND fo.payment_amount IS NOT NULL
GROUP BY dpm.payment_method_name, dpm.payment_type
ORDER BY total_amount DESC;

-- ============================================
-- Weekly Trend Analysis
-- ============================================

SELECT
    dd.year,
    dd.week_of_year,
    dd.month_name,
    MIN(dd.date_actual) as week_start_date,
    MAX(dd.date_actual) as week_end_date,
    COUNT(DISTINCT fo.order_id) as weekly_orders,
    COUNT(DISTINCT fo.customer_key) as weekly_customers,
    ROUND(SUM(fo.net_amount), 0) as weekly_revenue,
    ROUND(AVG(fo.net_amount), 0) as avg_order_value
FROM analytics.fact_orders fo
INNER JOIN analytics.dim_date dd ON fo.order_date_key = dd.date_key
WHERE dd.date_actual >= CURRENT_DATE - INTERVAL '90 days'
GROUP BY dd.year, dd.week_of_year, dd.month_name
ORDER BY dd.year DESC, dd.week_of_year DESC;

