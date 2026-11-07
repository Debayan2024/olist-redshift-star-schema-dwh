# E-commerce Data Pipeline & Analytics Platform

## Project Overview
This project demonstrates a complete end-to-end data engineering solution for an e-commerce platform, showcasing ETL pipelines, data warehousing, and analytics capabilities suitable for an Analytics Engineer role.

## Business Context
An e-commerce company needs to:
- Track customer orders, products, and user behavior
- Build a dimensional data warehouse for analytics
- Monitor data quality and pipeline health
- Generate daily business reports and insights
- Scale data processing for growing business needs

## Technical Architecture

### Data Sources (Simulated)
- **Transactional Database** (PostgreSQL): Orders, Products, Customers, Payments
- **Event Logs** (CSV/JSON): User clickstream, app events
- **External APIs**: Payment gateway, shipping providers

### Data Warehouse (PostgreSQL)
- **Staging Layer**: Raw data ingestion
- **Core Layer**: Cleaned and transformed data
- **Dimensional Model**: Star schema with fact and dimension tables
  - Fact: `fact_orders`, `fact_daily_sales`
  - Dimensions: `dim_customers`, `dim_products`, `dim_date`, `dim_locations`

### Tech Stack
- **Language**: Python
- **Database**: PostgreSQL
- **Orchestration**: Apache Airflow
- **Data Processing**: Pandas, SQLAlchemy
- **Data Quality**: Custom validation framework
- **Visualization**: SQL queries for BI tools

## Project Structure

```
analytics_engineer_project/
├── README.md
├── requirements.txt
├── config/
│   ├── database_config.yaml
│   └── pipeline_config.yaml
├── data/
│   ├── sample_data/
│   └── data_generator.py
├── sql/
│   ├── schema/
│   │   ├── 01_create_staging_tables.sql
│   │   ├── 02_create_core_tables.sql
│   │   └── 03_create_dimensional_model.sql
│   ├── transforms/
│   │   ├── staging_to_core.sql
│   │   └── core_to_dimensional.sql
│   └── analytics/
│       ├── daily_sales_report.sql
│       └── customer_metrics.sql
├── src/
│   ├── etl/
│   │   ├── __init__.py
│   │   ├── extract.py
│   │   ├── transform.py
│   │   └── load.py
│   ├── data_quality/
│   │   ├── __init__.py
│   │   ├── validators.py
│   │   └── monitors.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── db_connector.py
│   │   └── logger.py
│   └── orchestration/
│       ├── dags/
│       │   ├── daily_etl_pipeline.py
│       │   ├── data_quality_checks.py
│       │   └── dimensional_model_refresh.py
│       └── tasks/
├── tests/
│   ├── test_etl.py
│   └── test_data_quality.py
├── notebooks/
│   └── exploratory_analysis.ipynb
└── docs/
    ├── architecture.md
    ├── data_dictionary.md
    └── setup_guide.md
```

## Key Features

### 1. ETL Pipeline
- **Extract**: Pull data from multiple sources (databases, files, APIs)
- **Transform**: Data cleaning, validation, business logic application
- **Load**: Incremental and full load strategies into data warehouse

### 2. Data Warehouse Design
- Implemented star schema for optimal query performance
- SCD Type 2 for tracking historical changes
- Partitioning strategies for large fact tables
- Indexing for query optimization

### 3. Workflow Orchestration (Airflow)
- Scheduled DAGs for daily, hourly pipelines
- Dependency management between tasks
- Error handling and retry logic
- Email/Slack notifications on failures

### 4. Data Quality Framework
- Schema validation
- Data completeness checks
- Business rule validation
- Anomaly detection
- Data profiling and statistics

### 5. Monitoring & Logging
- Pipeline execution metrics
- Data quality dashboards
- Error tracking and alerting
- Performance monitoring

## Skills Demonstrated

✅ **ETL Development**: Complete extract, transform, load processes  
✅ **Python Proficiency**: Object-oriented design, pandas, SQLAlchemy  
✅ **SQL Mastery**: Complex queries, window functions, CTEs, optimization  
✅ **Data Warehousing**: Dimensional modeling, star schema, SCD  
✅ **Workflow Orchestration**: Apache Airflow DAGs, task dependencies  
✅ **Data Quality**: Validation frameworks, monitoring, alerting  
✅ **Database Management**: PostgreSQL, connection pooling, transactions  
✅ **Best Practices**: Code organization, documentation, testing  

## Quick Start

### Prerequisites
```bash
- Python 3.9+
- PostgreSQL 13+
- Apache Airflow 2.0+
```

### Installation
```bash
# Clone the repository
cd analytics_engineer_project

# Create Python virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up PostgreSQL data warehouse database
createdb ecommerce_dwh

# Run database schema creation
psql -d ecommerce_dwh -f sql/schema/01_create_staging_tables.sql
psql -d ecommerce_dwh -f sql/schema/02_create_core_tables.sql
psql -d ecommerce_dwh -f sql/schema/03_create_dimensional_model.sql

# Update database password in config/database_config.yaml
# Change 'your_password_here' to your actual postgres password

# Generate sample data (loads directly into staging tables)
python data/data_generator.py

# Optional: Initialize Airflow (for workflow orchestration)
export AIRFLOW_HOME=$(pwd)/airflow
airflow db init
airflow users create --username admin --password admin --firstname Admin --lastname User --role Admin --email admin@example.com

# Start Airflow (optional)
airflow webserver -p 8080 &
airflow scheduler &
```

### Running the Pipeline
```bash
# Run ETL manually (after generating sample data)
python src/etl/transform.py  # Transform staging → core
python src/etl/load.py        # Load core → analytics

# Run data quality checks
python src/data_quality/validators.py

# Run pipeline monitoring
python src/data_quality/monitors.py

# Or trigger complete Airflow DAG (if Airflow is set up)
airflow dags trigger daily_etl_pipeline
```

## Business Metrics & Reports

The pipeline generates key business metrics:
- Daily/Monthly GMV (Gross Merchandise Value)
- Customer Acquisition & Retention metrics
- Product Performance analysis
- Order Fulfillment metrics
- Payment Success rates
- Customer Lifetime Value (CLV)

## Future Enhancements
- [ ] Integration with Apache Spark for big data processing
- [ ] Real-time streaming with Kafka
- [ ] dbt for transformation layer
- [ ] CI/CD pipeline with GitHub Actions
- [ ] Docker containerization
- [ ] Kubernetes deployment
- [ ] Integration with BI tools (Tableau, Power BI, Metabase)

