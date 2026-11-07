# Setup Guide

Complete guide to setting up and running the E-commerce Data Pipeline & Analytics Platform.

## Prerequisites

### System Requirements
- **Operating System**: Linux, macOS, or Windows with WSL
- **RAM**: Minimum 8GB (16GB recommended)
- **Storage**: At least 10GB free space
- **Python**: Version 3.9 or higher
- **PostgreSQL**: Version 13 or higher

### Required Software
```bash
# Check versions
python --version  # Should be 3.9+
psql --version    # Should be 13+
pip --version
```

## Installation Steps

### 1. Clone or Download the Project
```bash
cd ~/projects
# If you have the project files
cd analytics_engineer_project
```

### 2. Create Python Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/Mac:
source venv/bin/activate

# On Windows:
venv\Scripts\activate
```

### 3. Install Python Dependencies
```bash
# Upgrade pip
pip install --upgrade pip

# Install project dependencies
pip install -r requirements.txt

# Verify installation
pip list
```

### 4. Setup PostgreSQL Databases

#### Create Databases
```bash
# Connect to PostgreSQL
psql -U postgres

# In PostgreSQL prompt:
CREATE DATABASE ecommerce_source;
CREATE DATABASE ecommerce_dwh;

# Create user (optional)
CREATE USER analytics_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE ecommerce_dwh TO analytics_user;

# Exit
\q
```

#### Create Database Schemas
```bash
# Create schemas in data warehouse
psql -U postgres -d ecommerce_dwh -f sql/schema/01_create_staging_tables.sql
psql -U postgres -d ecommerce_dwh -f sql/schema/02_create_core_tables.sql
psql -U postgres -d ecommerce_dwh -f sql/schema/03_create_dimensional_model.sql
```

Verify schema creation:
```bash
psql -U postgres -d ecommerce_dwh -c "\dn"  # List schemas
psql -U postgres -d ecommerce_dwh -c "\dt staging.*"  # List staging tables
psql -U postgres -d ecommerce_dwh -c "\dt core.*"     # List core tables
psql -U postgres -d ecommerce_dwh -c "\dt analytics.*" # List analytics tables
```

### 5. Configure Database Connections

Edit `config/database_config.yaml`:
```yaml
data_warehouse:
  host: localhost
  port: 5432
  database: ecommerce_dwh
  user: postgres  # or analytics_user
  password: your_password_here
```

**Security Best Practice**: Use environment variables:
```bash
# Add to ~/.bashrc or ~/.zshrc
export DB_HOST=localhost
export DB_USER=postgres
export DB_PASSWORD=your_password
```

### 6. Generate Sample Data
```bash
# Generate and load sample data
python data/data_generator.py
```

Expected output:
```
Generating 1,000 customers...
Generating 200 products...
Generating 5,000 orders...
Generating 10,000 user events...
Loading data to staging tables...
✓ All data loaded successfully!
```

Verify data loaded:
```bash
psql -U postgres -d ecommerce_dwh -c "SELECT COUNT(*) FROM staging.orders;"
psql -U postgres -d ecommerce_dwh -c "SELECT COUNT(*) FROM staging.customers;"
```

### 7. Run ETL Pipeline Manually

#### Extract Data
```bash
python src/etl/extract.py
```

#### Transform Data
```bash
python src/etl/transform.py
```

#### Load Dimensional Model
```bash
python src/etl/load.py
```

#### Run Data Quality Checks
```bash
python src/data_quality/validators.py
```

### 8. Setup Apache Airflow (Optional)

#### Initialize Airflow
```bash
# Set Airflow home
export AIRFLOW_HOME=$(pwd)/airflow

# Initialize Airflow database
airflow db init

# Create admin user
airflow users create \
    --username admin \
    --firstname Admin \
    --lastname User \
    --role Admin \
    --email admin@example.com \
    --password admin
```

#### Configure Airflow
```bash
# Copy DAGs to Airflow
mkdir -p $AIRFLOW_HOME/dags
cp src/orchestration/dags/*.py $AIRFLOW_HOME/dags/

# Update airflow.cfg
# Set: dags_folder = /path/to/analytics_engineer_project/src/orchestration/dags
```

#### Start Airflow
```bash
# Terminal 1: Start webserver
airflow webserver --port 8080

# Terminal 2: Start scheduler
airflow scheduler
```

Access Airflow UI: http://localhost:8080
- Username: admin
- Password: admin

#### Trigger DAG
```bash
# Via CLI
airflow dags trigger daily_etl_pipeline

# Or use the Airflow UI
```

## Directory Structure Created

After setup, your project should look like:
```
analytics_engineer_project/
├── venv/                    # Virtual environment
├── logs/                    # Log files (auto-created)
├── airflow/                 # Airflow home (if using Airflow)
├── config/
├── data/
├── docs/
├── sql/
├── src/
└── [other files]
```

## Verification Steps

### 1. Check Database Connection
```bash
python -c "from src.utils.db_connector import get_db_connector; db = get_db_connector(); print('Connection successful!')"
```

### 2. Verify Data in Each Layer
```sql
-- Check staging layer
SELECT 'staging' as layer, 
       'orders' as table_name, 
       COUNT(*) as row_count 
FROM staging.orders
UNION ALL
SELECT 'core', 'orders', COUNT(*) FROM core.orders
UNION ALL
SELECT 'analytics', 'fact_orders', COUNT(*) FROM analytics.fact_orders;
```

### 3. Run Sample Queries
```sql
-- Daily sales summary
SELECT 
    dd.date_actual,
    SUM(fds.total_orders) as orders,
    SUM(fds.total_net_revenue) as revenue
FROM analytics.fact_daily_sales fds
JOIN analytics.dim_date dd ON fds.date_key = dd.date_key
WHERE dd.date_actual >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY dd.date_actual
ORDER BY dd.date_actual;
```

## Common Issues & Solutions

### Issue 1: ModuleNotFoundError
**Error**: `ModuleNotFoundError: No module named 'src'`

**Solution**:
```bash
# Make sure you're in project root
cd analytics_engineer_project

# Add to PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

### Issue 2: Database Connection Failed
**Error**: `psycopg2.OperationalError: could not connect to server`

**Solution**:
1. Check PostgreSQL is running: `pg_isready`
2. Verify credentials in `config/database_config.yaml`
3. Check PostgreSQL allows local connections in `pg_hba.conf`

### Issue 3: Permission Denied on Tables
**Error**: `ERROR: permission denied for schema staging`

**Solution**:
```sql
-- Grant permissions
GRANT USAGE ON SCHEMA staging TO analytics_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA staging TO analytics_user;
GRANT USAGE ON SCHEMA core TO analytics_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA core TO analytics_user;
GRANT USAGE ON SCHEMA analytics TO analytics_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA analytics TO analytics_user;
```

### Issue 4: Airflow DAG Not Showing
**Solution**:
1. Check DAG file has no syntax errors: `python src/orchestration/dags/daily_etl_pipeline.py`
2. Verify `dags_folder` path in `airflow.cfg`
3. Refresh Airflow: Wait 30 seconds or restart scheduler

### Issue 5: Out of Memory
**Solution**:
- Reduce batch sizes in `config/pipeline_config.yaml`
- Process data in smaller chunks
- Increase system RAM or use cloud VM

## Testing the Pipeline

### Run Complete Pipeline
```bash
# Method 1: Manual execution
python src/etl/extract.py && \
python src/etl/transform.py && \
python src/etl/load.py && \
python src/data_quality/validators.py

# Method 2: Via Airflow
airflow dags trigger daily_etl_pipeline
```

### Monitor Execution
```bash
# Check logs
tail -f logs/etl_pipeline_$(date +%Y%m%d).log

# Or check Airflow UI
open http://localhost:8080
```

## Next Steps

### 1. Connect BI Tool
- **Metabase**: Free, open-source
- **Tableau**: Enterprise visualization
- **Power BI**: Microsoft's BI platform
- **Looker/Looker Studio**: Google's BI tools

Connection details:
- Host: localhost
- Port: 5432
- Database: ecommerce_dwh
- Schema: analytics
- User: postgres (or analytics_user)

### 2. Schedule Regular Runs
If not using Airflow, use cron:
```bash
crontab -e

# Add:
0 2 * * * cd /path/to/analytics_engineer_project && /path/to/venv/bin/python src/etl/extract.py
15 2 * * * cd /path/to/analytics_engineer_project && /path/to/venv/bin/python src/etl/transform.py
30 2 * * * cd /path/to/analytics_engineer_project && /path/to/venv/bin/python src/etl/load.py
```

### 3. Monitor and Maintain
- Check logs daily
- Monitor data quality reports
- Review pipeline performance
- Update as business needs evolve

## Production Deployment Considerations

### Security
- [ ] Use environment variables for credentials
- [ ] Enable SSL for database connections
- [ ] Implement role-based access control
- [ ] Set up VPN for remote access

### Performance
- [ ] Tune PostgreSQL configuration
- [ ] Add appropriate indexes
- [ ] Partition large tables
- [ ] Implement connection pooling

### Reliability
- [ ] Set up database backups
- [ ] Configure alerting (email/Slack)
- [ ] Document runbooks
- [ ] Test disaster recovery

### Monitoring
- [ ] Set up Grafana/Prometheus
- [ ] Track pipeline SLAs
- [ ] Monitor query performance
- [ ] Alert on failures

## Support & Resources

- **Documentation**: See `docs/` folder
- **Logs**: Check `logs/` directory
- **Issues**: Review error logs for troubleshooting
- **PostgreSQL Docs**: https://www.postgresql.org/docs/
- **Airflow Docs**: https://airflow.apache.org/docs/

## Maintenance Tasks

### Daily
- Monitor pipeline execution
- Check data quality reports
- Review error logs

### Weekly
- Review performance metrics
- Clean up old log files
- Verify data freshness

### Monthly
- Review and optimize slow queries
- Update documentation
- Backup configuration files
- Review and update data retention policies

---

**Congratulations!** Your analytics engineering pipeline is now set up and ready to use.

