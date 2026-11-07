"""
Airflow DAG: Daily ETL Pipeline
Orchestrates the complete ETL process from extraction to dimensional model load
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

from src.etl.extract import DataExtractor
from src.etl.transform import DataTransformer
from src.etl.load import DataLoader
from src.data_quality.validators import DataQualityValidator


# Default arguments
default_args = {
    'owner': 'analytics_engineer',
    'depends_on_past': False,
    'email': ['your_email@example.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=2),
}

# DAG definition
dag = DAG(
    'daily_etl_pipeline',
    default_args=default_args,
    description='Complete E-commerce ETL Pipeline - Extract, Transform, Load, and Validate',
    schedule_interval='0 2 * * *',  # Run daily at 2 AM
    start_date=days_ago(1),
    catchup=False,
    tags=['etl', 'daily', 'production'],
)


def extract_data(**context):
    """Extract data from source systems to staging"""
    extractor = DataExtractor()
    extractor.run_full_extraction()
    return "Extraction completed successfully"


def transform_data(**context):
    """Transform data from staging to core"""
    transformer = DataTransformer()
    transformer.run_full_transformation()
    return "Transformation completed successfully"


def load_dimensional_model(**context):
    """Load data into dimensional model"""
    loader = DataLoader()
    loader.run_full_load()
    return "Load completed successfully"


def validate_data_quality(**context):
    """Run data quality validations"""
    validator = DataQualityValidator()
    all_passed = validator.run_all_checks()
    
    if not all_passed:
        raise ValueError("Data quality checks failed")
    
    return "Data quality validation passed"


def cleanup_old_logs(**context):
    """Cleanup old log files"""
    import os
    import glob
    from datetime import datetime, timedelta
    
    log_dir = "logs"
    retention_days = 30
    cutoff_date = datetime.now() - timedelta(days=retention_days)
    
    deleted_count = 0
    for log_file in glob.glob(f"{log_dir}/*.log"):
        file_time = datetime.fromtimestamp(os.path.getmtime(log_file))
        if file_time < cutoff_date:
            os.remove(log_file)
            deleted_count += 1
    
    return f"Cleaned up {deleted_count} old log files"


# Task definitions
task_start = BashOperator(
    task_id='start_pipeline',
    bash_command='echo "Starting ETL Pipeline - {{ ds }}"',
    dag=dag,
)

task_extract = PythonOperator(
    task_id='extract_data',
    python_callable=extract_data,
    provide_context=True,
    dag=dag,
)

task_transform = PythonOperator(
    task_id='transform_data',
    python_callable=transform_data,
    provide_context=True,
    dag=dag,
)

task_load = PythonOperator(
    task_id='load_dimensional_model',
    python_callable=load_dimensional_model,
    provide_context=True,
    dag=dag,
)

task_validate = PythonOperator(
    task_id='validate_data_quality',
    python_callable=validate_data_quality,
    provide_context=True,
    dag=dag,
)

task_cleanup = PythonOperator(
    task_id='cleanup_old_logs',
    python_callable=cleanup_old_logs,
    provide_context=True,
    trigger_rule='all_done',  # Run even if previous tasks fail
    dag=dag,
)

task_end = BashOperator(
    task_id='end_pipeline',
    bash_command='echo "ETL Pipeline completed - {{ ds }}"',
    trigger_rule='all_done',
    dag=dag,
)

# Task dependencies
task_start >> task_extract >> task_transform >> task_load >> task_validate >> task_cleanup >> task_end


# Documentation
dag.doc_md = """
# Daily ETL Pipeline

## Overview
This DAG orchestrates the complete ETL process for the e-commerce data warehouse.

## Schedule
- **Frequency**: Daily
- **Time**: 2:00 AM
- **Timezone**: UTC

## Tasks
1. **extract_data**: Extract data from source systems to staging layer
2. **transform_data**: Transform and cleanse data, move to core layer
3. **load_dimensional_model**: Build dimensional model (star schema)
4. **validate_data_quality**: Run comprehensive data quality checks
5. **cleanup_old_logs**: Remove log files older than 30 days

## Dependencies
- PostgreSQL database must be accessible
- Source database must have fresh data
- Sufficient disk space for operations

## Monitoring
- Pipeline execution time: ~30-60 minutes
- Email alerts on failures
- Check logs in `logs/` directory

## Troubleshooting
- Check individual task logs in Airflow UI
- Review error logs in `logs/errors_*.log`
- Verify database connectivity
- Check data freshness in source systems
"""

