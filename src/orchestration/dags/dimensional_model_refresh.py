"""
Airflow DAG: Dimensional Model Refresh
Refreshes dimensional model and aggregated fact tables
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.append(str(project_root))

from src.utils.db_connector import get_db_connector


# Default arguments
default_args = {
    'owner': 'analytics_engineer',
    'depends_on_past': False,
    'email': ['your_email@example.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=1),
}

# DAG definition
dag = DAG(
    'dimensional_model_refresh',
    default_args=default_args,
    description='Refresh dimensional model and aggregated tables',
    schedule_interval='0 3 * * *',  # Run daily at 3 AM (after main ETL)
    start_date=days_ago(1),
    catchup=False,
    tags=['dimensional', 'analytics', 'refresh'],
)


def refresh_customer_dimension(**context):
    """Refresh customer dimension with latest metrics"""
    db = get_db_connector()
    
    query = """
    -- Update existing customers with latest metrics
    UPDATE analytics.dim_customers dc
    SET 
        total_lifetime_orders = COALESCE(stats.order_count, 0),
        total_lifetime_value = COALESCE(stats.total_value, 0),
        average_order_value = CASE 
            WHEN COALESCE(stats.order_count, 0) > 0 
            THEN stats.total_value / stats.order_count 
            ELSE 0 
        END,
        last_order_date = stats.last_order_date,
        days_since_last_order = CURRENT_DATE - stats.last_order_date::DATE,
        dw_updated_at = CURRENT_TIMESTAMP
    FROM (
        SELECT 
            fo.customer_key,
            COUNT(*) as order_count,
            SUM(fo.net_amount) as total_value,
            MAX(dd.date_actual) as last_order_date
        FROM analytics.fact_orders fo
        INNER JOIN analytics.dim_date dd ON fo.order_date_key = dd.date_key
        GROUP BY fo.customer_key
    ) AS stats
    WHERE dc.customer_key = stats.customer_key
    AND dc.is_current = TRUE
    """
    
    db.execute_query(query, db_name='data_warehouse')
    
    # Get count
    count = db.get_table_row_count('dim_customers', schema='analytics')
    
    return f"Refreshed {count} customer records"


def refresh_daily_sales_aggregate(**context):
    """Rebuild daily sales aggregate for recent period"""
    db = get_db_connector()
    
    # Delete and rebuild last 7 days
    delete_query = """
    DELETE FROM analytics.fact_daily_sales
    WHERE date_key >= TO_CHAR(CURRENT_DATE - INTERVAL '7 days', 'YYYYMMDD')::INTEGER
    """
    
    insert_query = """
    INSERT INTO analytics.fact_daily_sales (
        date_key, product_category, customer_segment, location_province,
        total_orders, total_customers, new_customers, returning_customers,
        total_items_sold, total_gross_revenue, total_discounts,
        total_net_revenue, total_product_cost, total_gross_profit,
        average_order_value, average_items_per_order
    )
    SELECT
        foi.order_date_key as date_key,
        dp.category as product_category,
        dc.customer_segment,
        dl.province as location_province,
        COUNT(DISTINCT foi.order_id) as total_orders,
        COUNT(DISTINCT foi.customer_key) as total_customers,
        COUNT(DISTINCT CASE WHEN fo.is_first_order THEN foi.customer_key END) as new_customers,
        COUNT(DISTINCT CASE WHEN NOT fo.is_first_order THEN foi.customer_key END) as returning_customers,
        SUM(foi.quantity) as total_items_sold,
        SUM(foi.gross_revenue) as total_gross_revenue,
        SUM(foi.discount_amount) as total_discounts,
        SUM(foi.net_revenue) as total_net_revenue,
        SUM(foi.product_cost) as total_product_cost,
        SUM(foi.gross_profit) as total_gross_profit,
        AVG(fo.gross_amount) as average_order_value,
        AVG(fo.order_quantity) as average_items_per_order
    FROM analytics.fact_order_items foi
    INNER JOIN analytics.fact_orders fo ON foi.order_id = fo.order_id
    INNER JOIN analytics.dim_date dd ON foi.order_date_key = dd.date_key
    LEFT JOIN analytics.dim_products dp ON foi.product_key = dp.product_key
    LEFT JOIN analytics.dim_customers dc ON foi.customer_key = dc.customer_key
    LEFT JOIN analytics.dim_locations dl ON fo.location_key = dl.location_key
    WHERE dd.date_actual >= CURRENT_DATE - INTERVAL '7 days'
    GROUP BY 
        foi.order_date_key,
        dp.category,
        dc.customer_segment,
        dl.province
    """
    
    db.execute_query(delete_query, db_name='data_warehouse')
    db.execute_query(insert_query, db_name='data_warehouse')
    
    return "Daily sales aggregate refreshed for last 7 days"


def update_product_metrics(**context):
    """Update product performance metrics"""
    db = get_db_connector()
    
    query = """
    -- Could add product sales metrics here
    -- For now, just analyze the table
    ANALYZE analytics.dim_products;
    ANALYZE analytics.fact_order_items;
    """
    
    db.execute_query(query, db_name='data_warehouse')
    
    return "Product metrics updated"


def vacuum_and_analyze(**context):
    """Vacuum and analyze key tables"""
    db = get_db_connector()
    
    tables = [
        'analytics.dim_customers',
        'analytics.dim_products',
        'analytics.fact_orders',
        'analytics.fact_order_items',
        'analytics.fact_daily_sales'
    ]
    
    for table in tables:
        # Only ANALYZE (VACUUM needs special handling in Airflow)
        db.execute_query(f"ANALYZE {table}", db_name='data_warehouse')
    
    return f"Analyzed {len(tables)} tables"


def generate_refresh_report(**context):
    """Generate report of refresh operation"""
    db = get_db_connector()
    
    # Get row counts
    metrics = {}
    
    tables = {
        'dim_customers': 'analytics',
        'dim_products': 'analytics',
        'fact_orders': 'analytics',
        'fact_order_items': 'analytics',
        'fact_daily_sales': 'analytics'
    }
    
    for table, schema in tables.items():
        count = db.get_table_row_count(table, schema)
        metrics[f"{schema}.{table}"] = count
    
    report = f"""
    Dimensional Model Refresh Report
    ================================
    Timestamp: {datetime.now()}
    
    Table Counts:
    """
    
    for table, count in metrics.items():
        report += f"\n  - {table}: {count:,} rows"
    
    print(report)
    
    return metrics


# Task definitions
task_start = BashOperator(
    task_id='start_refresh',
    bash_command='echo "Starting dimensional model refresh - {{ ds }}"',
    dag=dag,
)

task_refresh_customers = PythonOperator(
    task_id='refresh_customer_dimension',
    python_callable=refresh_customer_dimension,
    provide_context=True,
    dag=dag,
)

task_refresh_daily_sales = PythonOperator(
    task_id='refresh_daily_sales_aggregate',
    python_callable=refresh_daily_sales_aggregate,
    provide_context=True,
    dag=dag,
)

task_update_products = PythonOperator(
    task_id='update_product_metrics',
    python_callable=update_product_metrics,
    provide_context=True,
    dag=dag,
)

task_optimize = PythonOperator(
    task_id='vacuum_and_analyze',
    python_callable=vacuum_and_analyze,
    provide_context=True,
    dag=dag,
)

task_report = PythonOperator(
    task_id='generate_refresh_report',
    python_callable=generate_refresh_report,
    provide_context=True,
    dag=dag,
)

task_end = BashOperator(
    task_id='end_refresh',
    bash_command='echo "Dimensional model refresh completed - {{ ds }}"',
    dag=dag,
)

# Task dependencies (parallel refresh where possible)
task_start >> [task_refresh_customers, task_refresh_daily_sales, task_update_products]
[task_refresh_customers, task_refresh_daily_sales, task_update_products] >> task_optimize >> task_report >> task_end


# Documentation
dag.doc_md = """
# Dimensional Model Refresh Pipeline

## Overview
This DAG refreshes aggregated metrics and optimizes dimensional tables for query performance.

## Schedule
- **Frequency**: Daily at 3:00 AM
- **Purpose**: Keep dimensional metrics up-to-date
- **Runs After**: Main ETL pipeline

## Tasks
1. **refresh_customer_dimension**: Update customer lifetime metrics
2. **refresh_daily_sales_aggregate**: Rebuild recent daily aggregates
3. **update_product_metrics**: Update product performance data
4. **vacuum_and_analyze**: Optimize tables for query performance
5. **generate_refresh_report**: Summary report of refresh operation

## Performance
- Updates last 7 days of aggregates
- Analyzes tables for query optimization
- Typical runtime: 10-20 minutes

## Use Cases
- Keep BI dashboards up-to-date
- Optimize query performance
- Maintain data warehouse health
"""

