-- ============================================
-- Dimensional Layer: Star Schema for Analytics
-- Purpose: Optimized dimensional model for BI and reporting
-- ============================================

-- Drop existing analytics schema if exists
DROP SCHEMA IF EXISTS analytics CASCADE;
CREATE SCHEMA analytics;

-- ============================================
-- DIMENSION TABLES
-- ============================================

-- Dimension: Date
CREATE TABLE analytics.dim_date (
    date_key INTEGER PRIMARY KEY,
    date_actual DATE UNIQUE NOT NULL,
    day_of_week INTEGER,
    day_name VARCHAR(10),
    day_of_month INTEGER,
    day_of_year INTEGER,
    week_of_year INTEGER,
    month_number INTEGER,
    month_name VARCHAR(10),
    quarter INTEGER,
    year INTEGER,
    is_weekend BOOLEAN,
    is_holiday BOOLEAN,
    fiscal_year INTEGER,
    fiscal_quarter INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Dimension: Customers
CREATE TABLE analytics.dim_customers (
    customer_key SERIAL PRIMARY KEY,
    customer_id VARCHAR(50) NOT NULL,
    email VARCHAR(255),
    full_name VARCHAR(255),
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    date_of_birth DATE,
    age INTEGER,
    age_group VARCHAR(20),
    gender VARCHAR(10),
    registration_date TIMESTAMP,
    customer_segment VARCHAR(50),
    customer_tier VARCHAR(20),
    city VARCHAR(100),
    province VARCHAR(100),
    region VARCHAR(50),
    total_lifetime_orders INTEGER,
    total_lifetime_value DECIMAL(15,2),
    average_order_value DECIMAL(15,2),
    first_order_date DATE,
    last_order_date DATE,
    days_since_last_order INTEGER,
    is_active BOOLEAN,
    valid_from TIMESTAMP NOT NULL,
    valid_to TIMESTAMP,
    is_current BOOLEAN DEFAULT TRUE,
    dw_created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    dw_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Dimension: Products
CREATE TABLE analytics.dim_products (
    product_key SERIAL PRIMARY KEY,
    product_id VARCHAR(50) NOT NULL,
    product_name VARCHAR(255) NOT NULL,
    product_name_english VARCHAR(255),
    category VARCHAR(100),
    subcategory VARCHAR(100),
    brand VARCHAR(100),
    unit_price DECIMAL(15,2),
    cost_price DECIMAL(15,2),
    margin_percent DECIMAL(5,2),
    price_tier VARCHAR(20),
    supplier_id VARCHAR(50),
    supplier_name VARCHAR(255),
    is_active BOOLEAN,
    product_launch_date DATE,
    valid_from TIMESTAMP NOT NULL,
    valid_to TIMESTAMP,
    is_current BOOLEAN DEFAULT TRUE,
    dw_created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    dw_updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Dimension: Locations
CREATE TABLE analytics.dim_locations (
    location_key SERIAL PRIMARY KEY,
    city VARCHAR(100),
    province VARCHAR(100),
    region VARCHAR(50),
    country VARCHAR(50) DEFAULT 'Vietnam',
    postal_code VARCHAR(20),
    latitude DECIMAL(10,7),
    longitude DECIMAL(10,7),
    population INTEGER,
    economic_zone VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Dimension: Payment Methods
CREATE TABLE analytics.dim_payment_methods (
    payment_method_key SERIAL PRIMARY KEY,
    payment_method_id VARCHAR(50) UNIQUE NOT NULL,
    payment_method_name VARCHAR(100),
    payment_type VARCHAR(50),
    provider VARCHAR(100),
    is_digital BOOLEAN,
    transaction_fee_percent DECIMAL(5,2),
    is_active BOOLEAN,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Dimension: Order Status
CREATE TABLE analytics.dim_order_status (
    order_status_key SERIAL PRIMARY KEY,
    order_status_id VARCHAR(50) UNIQUE NOT NULL,
    order_status_name VARCHAR(100),
    status_category VARCHAR(50),
    is_completed BOOLEAN,
    is_cancelled BOOLEAN,
    display_order INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- FACT TABLES
-- ============================================

-- Fact: Orders (Transaction Grain)
CREATE TABLE analytics.fact_orders (
    order_fact_key SERIAL PRIMARY KEY,
    order_id VARCHAR(50) NOT NULL,
    
    -- Date Keys
    order_date_key INTEGER NOT NULL,
    payment_date_key INTEGER,
    delivery_date_key INTEGER,
    
    -- Dimension Keys
    customer_key INTEGER NOT NULL,
    location_key INTEGER,
    payment_method_key INTEGER,
    order_status_key INTEGER,
    
    -- Degenerate Dimensions
    order_number VARCHAR(50),
    transaction_id VARCHAR(100),
    
    -- Metrics (Measures)
    order_quantity INTEGER,
    gross_amount DECIMAL(15,2),
    discount_amount DECIMAL(15,2),
    tax_amount DECIMAL(15,2),
    shipping_fee DECIMAL(15,2),
    net_amount DECIMAL(15,2),
    payment_amount DECIMAL(15,2),
    
    -- Order Flags
    is_first_order BOOLEAN,
    is_returned BOOLEAN,
    is_cancelled BOOLEAN,
    
    -- Processing Metrics
    order_processing_hours DECIMAL(10,2),
    payment_processing_seconds INTEGER,
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign Keys
    FOREIGN KEY (order_date_key) REFERENCES analytics.dim_date(date_key),
    FOREIGN KEY (customer_key) REFERENCES analytics.dim_customers(customer_key),
    FOREIGN KEY (payment_method_key) REFERENCES analytics.dim_payment_methods(payment_method_key),
    FOREIGN KEY (order_status_key) REFERENCES analytics.dim_order_status(order_status_key)
);

-- Fact: Order Items (Order Line Item Grain)
CREATE TABLE analytics.fact_order_items (
    order_item_fact_key SERIAL PRIMARY KEY,
    order_item_id VARCHAR(50) NOT NULL,
    order_id VARCHAR(50) NOT NULL,
    
    -- Date Keys
    order_date_key INTEGER NOT NULL,
    
    -- Dimension Keys
    customer_key INTEGER NOT NULL,
    product_key INTEGER NOT NULL,
    
    -- Metrics
    quantity INTEGER NOT NULL,
    unit_price DECIMAL(15,2) NOT NULL,
    unit_cost DECIMAL(15,2),
    discount_amount DECIMAL(15,2),
    gross_revenue DECIMAL(15,2),
    net_revenue DECIMAL(15,2),
    product_cost DECIMAL(15,2),
    gross_profit DECIMAL(15,2),
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign Keys
    FOREIGN KEY (order_date_key) REFERENCES analytics.dim_date(date_key),
    FOREIGN KEY (customer_key) REFERENCES analytics.dim_customers(customer_key),
    FOREIGN KEY (product_key) REFERENCES analytics.dim_products(product_key),
    
    -- Constraints
    CONSTRAINT check_quantity CHECK (quantity > 0),
    CONSTRAINT check_prices CHECK (unit_price >= 0 AND unit_cost >= 0)
);

-- Fact: Daily Sales Aggregate (Daily Grain)
CREATE TABLE analytics.fact_daily_sales (
    daily_sales_key SERIAL PRIMARY KEY,
    date_key INTEGER NOT NULL,
    
    -- Optional Dimensions for slicing
    product_category VARCHAR(100),
    customer_segment VARCHAR(50),
    location_province VARCHAR(100),
    
    -- Aggregated Metrics
    total_orders INTEGER DEFAULT 0,
    total_customers INTEGER DEFAULT 0,
    new_customers INTEGER DEFAULT 0,
    returning_customers INTEGER DEFAULT 0,
    
    total_items_sold INTEGER DEFAULT 0,
    total_gross_revenue DECIMAL(15,2) DEFAULT 0,
    total_discounts DECIMAL(15,2) DEFAULT 0,
    total_net_revenue DECIMAL(15,2) DEFAULT 0,
    total_product_cost DECIMAL(15,2) DEFAULT 0,
    total_gross_profit DECIMAL(15,2) DEFAULT 0,
    
    average_order_value DECIMAL(15,2),
    average_items_per_order DECIMAL(10,2),
    
    cancelled_orders INTEGER DEFAULT 0,
    returned_orders INTEGER DEFAULT 0,
    
    -- Audit
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Foreign Keys
    FOREIGN KEY (date_key) REFERENCES analytics.dim_date(date_key),
    
    -- Unique constraint for daily grain
    UNIQUE(date_key, product_category, customer_segment, location_province)
);

-- ============================================
-- INDEXES FOR QUERY PERFORMANCE
-- ============================================

-- Dimension Indexes
CREATE INDEX idx_dim_date_actual ON analytics.dim_date(date_actual);
CREATE INDEX idx_dim_date_year_month ON analytics.dim_date(year, month_number);
CREATE INDEX idx_dim_customers_current ON analytics.dim_customers(customer_id, is_current);
CREATE INDEX idx_dim_customers_segment ON analytics.dim_customers(customer_segment);
CREATE INDEX idx_dim_products_current ON analytics.dim_products(product_id, is_current);
CREATE INDEX idx_dim_products_category ON analytics.dim_products(category, subcategory);

-- Fact Table Indexes
CREATE INDEX idx_fact_orders_date ON analytics.fact_orders(order_date_key);
CREATE INDEX idx_fact_orders_customer ON analytics.fact_orders(customer_key);
CREATE INDEX idx_fact_orders_status ON analytics.fact_orders(order_status_key);
CREATE INDEX idx_fact_orders_composite ON analytics.fact_orders(order_date_key, customer_key, order_status_key);

CREATE INDEX idx_fact_order_items_date ON analytics.fact_order_items(order_date_key);
CREATE INDEX idx_fact_order_items_product ON analytics.fact_order_items(product_key);
CREATE INDEX idx_fact_order_items_customer ON analytics.fact_order_items(customer_key);
CREATE INDEX idx_fact_order_items_order ON analytics.fact_order_items(order_id);

CREATE INDEX idx_fact_daily_sales_date ON analytics.fact_daily_sales(date_key);
CREATE INDEX idx_fact_daily_sales_category ON analytics.fact_daily_sales(product_category);
CREATE INDEX idx_fact_daily_sales_segment ON analytics.fact_daily_sales(customer_segment);

-- ============================================
-- COMMENTS AND DOCUMENTATION
-- ============================================

COMMENT ON SCHEMA analytics IS 'Dimensional model (star schema) optimized for analytics and BI';
COMMENT ON TABLE analytics.dim_date IS 'Date dimension with calendar and fiscal attributes';
COMMENT ON TABLE analytics.dim_customers IS 'Customer dimension with SCD Type 2';
COMMENT ON TABLE analytics.dim_products IS 'Product dimension with SCD Type 2';
COMMENT ON TABLE analytics.fact_orders IS 'Order fact table at transaction grain';
COMMENT ON TABLE analytics.fact_order_items IS 'Order items fact table at line item grain';
COMMENT ON TABLE analytics.fact_daily_sales IS 'Aggregated daily sales metrics';

