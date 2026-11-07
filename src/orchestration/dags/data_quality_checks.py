"""
Airflow DAG: Data Quality Monitoring
Standalone data quality checks and monitoring
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

from src.data_quality.validators import DataQualityValidator
from src.data_quality.monitors import PipelineMonitor


# Default arguments
default_args = {
    'owner': 'analytics_engineer',
    'depends_on_past': False,
    'email': ['your_email@example.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=3),
    'execution_timeout': timedelta(minutes=30),
}

# DAG definition
dag = DAG(
    'data_quality_monitoring',
    default_args=default_args,
    description='Data Quality Monitoring and Validation',
    schedule_interval='0 */4 * * *',  # Run every 4 hours
    start_date=days_ago(1),
    catchup=False,
    tags=['data-quality', 'monitoring'],
)


def run_data_quality_checks(**context):
    """Execute comprehensive data quality checks"""
    validator = DataQualityValidator()
    all_passed = validator.run_all_checks()
    
    # Push results to XCom
    context['task_instance'].xcom_push(key='all_checks_passed', value=all_passed)
    
    return {
        'status': 'PASSED' if all_passed else 'FAILED',
        'timestamp': datetime.now().isoformat()
    }


def generate_health_report(**context):
    """Generate pipeline health report"""
    monitor = PipelineMonitor()
    report = monitor.get_pipeline_health_report()
    
    # Store report in XCom
    context['task_instance'].xcom_push(key='health_report', value=report)
    
    return report['overall_health']


def check_data_freshness(**context):
    """Check if data is fresh across all layers"""
    monitor = PipelineMonitor()
    
    tables_to_check = [
        ('staging', 'orders', 24),
        ('core', 'orders', 24),
        ('analytics', 'fact_orders', 24)
    ]
    
    stale_tables = []
    
    for schema, table, max_age_hours in tables_to_check:
        result = monitor.check_data_freshness(table, schema, max_age_hours=max_age_hours)
        if not result.get('is_fresh', False):
            stale_tables.append(f"{schema}.{table}")
    
    if stale_tables:
        raise ValueError(f"Stale data detected in: {', '.join(stale_tables)}")
    
    return "All tables have fresh data"


def detect_volume_anomalies(**context):
    """Detect unusual volume patterns"""
    monitor = PipelineMonitor()
    
    result = monitor.check_data_volume_anomaly('orders', 'core')
    
    if result.get('has_anomaly', False):
        context['task_instance'].xcom_push(key='anomaly_detected', value=True)
        # Don't fail the pipeline, just log warning
        print(f"⚠️  Volume anomaly detected: {result}")
    
    return "Volume anomaly check completed"


def send_summary_notification(**context):
    """Send summary notification (mock implementation)"""
    # Get results from previous tasks
    ti = context['task_instance']
    health_status = ti.xcom_pull(task_ids='generate_health_report')
    checks_passed = ti.xcom_pull(task_ids='run_quality_checks', key='all_checks_passed')
    
    summary = f"""
    Data Quality Summary:
    - Health Status: {health_status}
    - Quality Checks: {'PASSED' if checks_passed else 'FAILED'}
    - Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    """
    
    print(summary)
    print("📧 Summary notification would be sent here (email/Slack)")
    
    return "Notification sent"


# Task definitions
task_start = BashOperator(
    task_id='start_monitoring',
    bash_command='echo "Starting Data Quality Monitoring - {{ ts }}"',
    dag=dag,
)

task_quality_checks = PythonOperator(
    task_id='run_quality_checks',
    python_callable=run_data_quality_checks,
    provide_context=True,
    dag=dag,
)

task_health_report = PythonOperator(
    task_id='generate_health_report',
    python_callable=generate_health_report,
    provide_context=True,
    dag=dag,
)

task_freshness = PythonOperator(
    task_id='check_data_freshness',
    python_callable=check_data_freshness,
    provide_context=True,
    dag=dag,
)

task_anomalies = PythonOperator(
    task_id='detect_volume_anomalies',
    python_callable=detect_volume_anomalies,
    provide_context=True,
    trigger_rule='all_done',  # Run even if previous tasks fail
    dag=dag,
)

task_notify = PythonOperator(
    task_id='send_summary_notification',
    python_callable=send_summary_notification,
    provide_context=True,
    trigger_rule='all_done',
    dag=dag,
)

task_end = BashOperator(
    task_id='end_monitoring',
    bash_command='echo "Data Quality Monitoring completed - {{ ts }}"',
    trigger_rule='all_done',
    dag=dag,
)

# Task dependencies (parallel execution where possible)
task_start >> [task_quality_checks, task_health_report, task_freshness] >> task_anomalies >> task_notify >> task_end


# Documentation
dag.doc_md = """
# Data Quality Monitoring Pipeline

## Overview
This DAG runs data quality checks and health monitoring independently from the main ETL pipeline.

## Schedule
- **Frequency**: Every 4 hours
- **Purpose**: Continuous monitoring of data quality

## Tasks
1. **run_quality_checks**: Execute comprehensive data validations
2. **generate_health_report**: Check pipeline health metrics
3. **check_data_freshness**: Verify data timeliness
4. **detect_volume_anomalies**: Identify unusual data volumes
5. **send_summary_notification**: Send alerts if issues detected

## Alerts
- Stale data (> 24 hours old)
- Failed data quality checks
- Volume anomalies detected
- Referential integrity violations

## Integration
Can run independently or alongside the main ETL pipeline for continuous monitoring.
"""

