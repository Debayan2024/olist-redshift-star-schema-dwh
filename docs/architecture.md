# E-commerce Data Warehouse Architecture

## Overview
This document describes the architecture of the e-commerce data warehouse and ETL pipeline.

## Architecture Layers

### 1. Data Sources Layer
**Purpose**: Origin of raw business data

- **Transactional Database** (PostgreSQL)
  - Orders, Products, Customers, Payments
  - OLTP optimized for transactions
  - Real-time operational data

- **Event Streams** (CSV/JSON files)
  - User clickstream data
  - Application events
  - Log files

- **External APIs** (Future)
  - Payment gateway APIs
  - Shipping provider APIs
  - Marketing platform APIs

### 2. Staging Layer
**Purpose**: Raw data landing zone

- **Schema**: `staging`
- **Characteristics**:
  - Exact copy of source data
  - Minimal transformations
  - Includes load metadata (timestamp, source_system)
  - Acts as data lake for raw data
  
- **Tables**:
  - `staging.orders`
  - `staging.order_items`
  - `staging.customers`
  - `staging.products`
  - `staging.payments`
  - `staging.user_events`

**Load Strategy**: 
- Incremental loads based on `updated_at` timestamp
- Configurable lookback window (default: 7 days)
- Full refresh option available

### 3. Core Layer
**Purpose**: Cleaned and validated business data

- **Schema**: `core`
- **Characteristics**:
  - Data quality rules applied
  - Business logic implemented
  - SCD Type 2 for historical tracking
  - Referential integrity enforced
  
- **Transformations**:
  - Data cleansing (trim, uppercase, null handling)
  - Deduplication
  - Data type conversions
  - Calculated fields (e.g., is_first_order, age)
  - SCD Type 2 implementation for customers & products

- **Tables**:
  - `core.orders` - Order transactions
  - `core.order_items` - Order line items
  - `core.customers` - Customer master (SCD Type 2)
  - `core.products` - Product catalog (SCD Type 2)
  - `core.payments` - Payment transactions
  - `core.user_events` - Clickstream events

### 4. Analytics Layer (Dimensional Model)
**Purpose**: Optimized for reporting and analytics

- **Schema**: `analytics`
- **Model Type**: Star Schema
- **Characteristics**:
  - Denormalized for query performance
  - Pre-aggregated metrics
  - Business-friendly naming
  - Optimized indexes

#### Dimension Tables
1. **dim_date**
   - Date attributes (day, week, month, quarter, year)
   - Fiscal calendar
   - Holiday flags
   - Pre-populated for 5 years

2. **dim_customers**
   - Customer attributes and demographics
   - Segmentation (Regular, VIP, Gold, etc.)
   - Lifetime metrics (CLV, total orders, AOV)
   - SCD Type 2 for tracking changes
   - Geographic information

3. **dim_products**
   - Product catalog information
   - Category hierarchy
   - Pricing and cost information
   - Margin calculations
   - SCD Type 2 for price/attribute changes

4. **dim_locations**
   - Geographic information
   - City, province, region
   - Vietnam market focus

5. **dim_payment_methods**
   - Payment method attributes
   - Payment type categorization
   - Provider information

6. **dim_order_status**
   - Order status definitions
   - Status categories
   - Display order

#### Fact Tables
1. **fact_orders** (Transaction Grain)
   - One row per order
   - Foreign keys to dimensions
   - Order metrics (amounts, quantities)
   - Processing times
   - Flags (is_first_order, is_cancelled)

2. **fact_order_items** (Line Item Grain)
   - One row per order line item
   - Product-level detail
   - Revenue and profit calculations
   - Quantity and pricing

3. **fact_daily_sales** (Daily Aggregate Grain)
   - Pre-aggregated daily metrics
   - Sliceable by category, segment, location
   - Performance optimization for dashboards
   - Reduced query times for common reports

## Data Flow

```
┌─────────────┐
│   Sources   │
│  (OLTP DB)  │
└──────┬──────┘
       │
       │ Extract
       ▼
┌──────────────┐
│   Staging    │
│ (Raw Data)   │
└──────┬───────┘
       │
       │ Transform & Validate
       ▼
┌──────────────┐
│     Core     │
│ (Cleansed)   │
└──────┬───────┘
       │
       │ Dimensional Modeling
       ▼
┌──────────────┐
│  Analytics   │
│ (Star Schema)│
└──────┬───────┘
       │
       │ Query & Report
       ▼
┌──────────────┐
│  BI Tools    │
│  Dashboards  │
└──────────────┘
```

## ETL Pipeline Flow

### Daily Pipeline (2:00 AM UTC)
1. **Extract** (15-20 min)
   - Pull incremental data from sources
   - Load to staging tables
   - Log extraction metrics

2. **Transform** (20-30 min)
   - Clean and validate data
   - Apply business rules
   - Load to core tables
   - Update SCD Type 2 records

3. **Load** (15-20 min)
   - Build dimensional model
   - Update fact tables
   - Refresh aggregates
   - Optimize tables (ANALYZE)

4. **Validate** (5-10 min)
   - Data quality checks
   - Referential integrity validation
   - Business rule validation
   - Generate quality report

**Total Runtime**: ~60-80 minutes

## Data Quality Framework

### Validation Layers
1. **Schema Validation**
   - Column existence and types
   - Required fields present

2. **Data Quality Checks**
   - Null value thresholds
   - Uniqueness constraints
   - Value range validation
   - Referential integrity

3. **Business Rules**
   - Order amounts ≥ 0
   - Order quantities > 0
   - Dates in valid ranges
   - Customer age ≥ 18

4. **Anomaly Detection**
   - Volume anomalies
   - Data freshness
   - Pattern detection

### Monitoring
- Data freshness checks (every 4 hours)
- Pipeline health monitoring
- Performance metrics tracking
- Automated alerting

## Technology Stack

### Core Technologies
- **Database**: PostgreSQL 13+
- **Language**: Python 3.9+
- **Orchestration**: Apache Airflow 2.6+
- **Libraries**: pandas, SQLAlchemy, psycopg2

### Data Processing
- **Batch Processing**: pandas DataFrames
- **SQL Transforms**: Complex SQL in dedicated files
- **Connection Pooling**: psycopg2 ThreadedConnectionPool

### Optional Extensions
- **Big Data**: Apache Spark (for scale)
- **Streaming**: Apache Kafka (for real-time)
- **Transformation**: dbt (SQL-based transforms)
- **BI Tools**: Tableau, Power BI, Metabase

## Scalability Considerations

### Current Capacity
- Handles millions of rows per table
- 60-80 minute daily pipeline runtime
- Single database instance

### Future Scaling Options
1. **Horizontal Partitioning**
   - Partition fact tables by date
   - Improve query performance
   - Easier maintenance

2. **Columnar Storage**
   - Consider PostgreSQL with cstore_fdw
   - Or migrate to columnar DB (Redshift, BigQuery)

3. **Distributed Processing**
   - Apache Spark for transformations
   - Parallel processing capabilities

4. **Caching Layer**
   - Redis for frequently accessed aggregates
   - Reduce database load

5. **Read Replicas**
   - Separate analytics workload
   - Dedicated reporting database

## Security & Compliance

### Data Security
- Connection credentials in environment variables
- Database user access controls
- Encrypted connections (SSL)

### Data Privacy
- PII handling procedures
- Data retention policies
- Anonymization options available

### Audit Trail
- All transformations logged
- Data lineage tracking
- Pipeline execution history

## Performance Optimization

### Indexing Strategy
- Primary keys on all tables
- Foreign keys indexed
- Query-specific indexes on analytics layer
- Composite indexes for common joins

### Query Optimization
- Pre-aggregated metrics in fact_daily_sales
- Denormalized dimensions
- ANALYZE run after loads
- Query plan review

### Storage Optimization
- Appropriate data types
- Compression where applicable
- Regular VACUUM operations
- Partition old data

## Disaster Recovery

### Backup Strategy
- Daily database backups
- Transaction log backups
- Backup retention: 30 days

### Recovery Procedures
- Point-in-time recovery capability
- Documented restoration process
- Regular backup testing

## Monitoring & Alerting

### Metrics Tracked
- Pipeline execution time
- Data volume trends
- Quality check pass rates
- Query performance

### Alerts
- Pipeline failures
- Data quality issues
- Data freshness problems
- Performance degradation

### Dashboards
- Pipeline health dashboard
- Data quality metrics
- Business KPI dashboard

