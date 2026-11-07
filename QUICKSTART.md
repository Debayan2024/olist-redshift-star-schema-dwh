# Quick Start Guide (5 Minutes)

This guide will get your Analytics Engineering project up and running in just 5 minutes!

## Prerequisites Check

Before starting, verify you have:

```bash
# Check Python version (need 3.9+)
python --version

# Check PostgreSQL (need 13+)
psql --version

# Check pip
pip --version
```

## Step-by-Step Setup

### 1. Create Virtual Environment (1 min)

```bash
cd analytics_engineer_project

# Create virtual environment
python -m venv venv

# Activate it
# On macOS/Linux:
source venv/bin/activate

# On Windows:
venv\Scripts\activate

# Your prompt should now show (venv)
```

### 2. Install Dependencies (1 min)

```bash
# Upgrade pip
pip install --upgrade pip

# Install all required packages
pip install -r requirements.txt

# Wait for installation to complete...
```

### 3. Create Database (30 seconds)

```bash
# Create the data warehouse database
createdb ecommerce_dwh

# Verify it was created
psql -l | grep ecommerce
```

### 4. Create Database Schemas (30 seconds)

```bash
# Create staging schema and tables
psql -d ecommerce_dwh -f sql/schema/01_create_staging_tables.sql

# Create core schema and tables
psql -d ecommerce_dwh -f sql/schema/02_create_core_tables.sql

# Create analytics schema and tables
psql -d ecommerce_dwh -f sql/schema/03_create_dimensional_model.sql

# Verify schemas were created
psql -d ecommerce_dwh -c "\dn"
```

Expected output:
```
   Name    |  Owner
-----------+----------
 analytics | postgres
 core      | postgres
 public    | postgres
 staging   | postgres
```

### 5. Update Database Password (30 seconds)

```bash
# Edit the config file
nano config/database_config.yaml
# or use your preferred editor: code, vim, etc.
```

Change this line:
```yaml
password: your_password_here
```

To your actual postgres password:
```yaml
password: postgres  # or whatever your postgres password is
```

Save and exit.

### 6. Generate Sample Data (1 min)

```bash
# Generate 1,000 customers, 200 products, 5,000 orders
python data/data_generator.py
```

Expected output:
```
================================================================================
E-COMMERCE DATA GENERATOR
================================================================================
Generating 1000 customers...
Generated 1000 customers
Generating 200 products...
Generated 200 products
Generating 5000 orders...
Generated 5000 orders and 12000+ order items
✓ Loaded customers
✓ Loaded products
✓ Loaded orders
✓ Loaded order items
✓ Loaded payments
✓ Loaded user events
```

### 7. Run ETL Pipeline (1 min)

```bash
# Transform data from staging to core
python src/etl/transform.py

# Load data into dimensional model
python src/etl/load.py

# Run data quality checks
python src/data_quality/validators.py
```

### 8. Verify Everything Works (30 seconds)

```bash
# Check data in each layer
psql -d ecommerce_dwh << EOF
-- Check staging
SELECT 'Staging Orders:' as layer, COUNT(*) as count FROM staging.orders
UNION ALL
-- Check core
SELECT 'Core Orders:', COUNT(*) FROM core.orders
UNION ALL
-- Check analytics
SELECT 'Analytics Fact Orders:', COUNT(*) FROM analytics.fact_orders;
EOF
```

Expected output (approximate):
```
         layer          | count
------------------------+-------
 Staging Orders:        |  5000
 Core Orders:           |  5000
 Analytics Fact Orders: |  5000
```

### 9. Run Your First Analytics Query! 🎉

```bash
psql -d ecommerce_dwh
```

Then run:
```sql
-- Daily sales summary
SELECT 
    dd.date_actual,
    SUM(fds.total_orders) as orders,
    ROUND(SUM(fds.total_net_revenue)) as revenue
FROM analytics.fact_daily_sales fds
JOIN analytics.dim_date dd ON fds.date_key = dd.date_key
WHERE dd.date_actual >= CURRENT_DATE - INTERVAL '7 days'
GROUP BY dd.date_actual
ORDER BY dd.date_actual DESC
LIMIT 10;
```

## Troubleshooting

### Error: "createdb: command not found"

**Solution**: PostgreSQL is not in your PATH
```bash
# On macOS with Homebrew:
brew install postgresql

# On Ubuntu/Debian:
sudo apt-get install postgresql postgresql-contrib

# On Windows: Add PostgreSQL bin directory to PATH
```

### Error: "psql: FATAL: database does not exist"

**Solution**: Database not created yet
```bash
createdb ecommerce_dwh
```

### Error: "ModuleNotFoundError: No module named 'src'"

**Solution**: Run from project root
```bash
cd analytics_engineer_project
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
python src/etl/transform.py
```

### Error: "could not connect to server"

**Solution**: PostgreSQL not running
```bash
# Check if running
pg_isready

# Start PostgreSQL
# On macOS:
brew services start postgresql

# On Ubuntu:
sudo service postgresql start

# On Windows:
# Start from Services or pgAdmin
```

### Error: "permission denied for schema"

**Solution**: Grant permissions
```bash
psql -d ecommerce_dwh -c "GRANT ALL ON SCHEMA staging TO postgres;"
psql -d ecommerce_dwh -c "GRANT ALL ON SCHEMA core TO postgres;"
psql -d ecommerce_dwh -c "GRANT ALL ON SCHEMA analytics TO postgres;"
```

## What's Next?

### View Your Data
```bash
# Connect to database
psql -d ecommerce_dwh

# Explore tables
\dt staging.*
\dt core.*
\dt analytics.*

# View sample data
SELECT * FROM analytics.dim_customers LIMIT 5;
SELECT * FROM analytics.fact_orders LIMIT 5;
```

### Run Monitoring
```bash
python src/data_quality/monitors.py
```

### Setup Airflow (Optional)
```bash
export AIRFLOW_HOME=$(pwd)/airflow
airflow db init
airflow users create --username admin --password admin --role Admin --email admin@example.com

# Copy DAGs
mkdir -p $AIRFLOW_HOME/dags
cp src/orchestration/dags/*.py $AIRFLOW_HOME/dags/

# Start Airflow
airflow webserver -p 8080 &
airflow scheduler &

# Access: http://localhost:8080
```

### Try More Queries

```sql
-- Top 10 customers by revenue
SELECT 
    full_name,
    total_lifetime_value,
    total_lifetime_orders
FROM analytics.dim_customers
WHERE is_current = TRUE
ORDER BY total_lifetime_value DESC
LIMIT 10;

-- Product categories by revenue
SELECT 
    dp.category,
    COUNT(DISTINCT foi.order_id) as orders,
    SUM(foi.net_revenue) as revenue
FROM analytics.fact_order_items foi
JOIN analytics.dim_products dp ON foi.product_key = dp.product_key
GROUP BY dp.category
ORDER BY revenue DESC;

-- Daily order trends
SELECT 
    dd.date_actual,
    COUNT(DISTINCT fo.order_id) as orders,
    COUNT(DISTINCT fo.customer_key) as customers,
    ROUND(AVG(fo.net_amount)) as avg_order_value
FROM analytics.fact_orders fo
JOIN analytics.dim_date dd ON fo.order_date_key = dd.date_key
WHERE dd.date_actual >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY dd.date_actual
ORDER BY dd.date_actual;
```

## Success! 🎉

You now have a fully functional analytics engineering pipeline with:
- ✅ 3-layer data warehouse (staging, core, analytics)
- ✅ 5,000+ orders with realistic data
- ✅ Dimensional model with star schema
- ✅ ETL pipeline processing
- ✅ Data quality checks

**Ready for your portfolio and interviews!**

---

## Files Created

After setup, you should have:
```
analytics_engineer_project/
├── venv/                    # Virtual environment
├── logs/                    # ETL logs (auto-created)
│   ├── etl_pipeline_*.log
│   └── errors_*.log
└── [all other project files]
```

## Cleanup (if needed)

To start fresh:
```bash
# Drop database
dropdb ecommerce_dwh

# Remove virtual environment
deactivate
rm -rf venv

# Remove logs
rm -rf logs

# Then start over from Step 1
```

---

**Need help?** Check the full documentation in `docs/` or `README.md`

