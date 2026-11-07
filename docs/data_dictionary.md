## Data Dictionary

### Analytics Layer - Dimensional Model

#### dim_date
Date dimension for time-based analysis

| Column | Type | Description |
|--------|------|-------------|
| date_key | INTEGER | Primary key (YYYYMMDD format) |
| date_actual | DATE | Actual date |
| day_of_week | INTEGER | Day of week (0=Sunday, 6=Saturday) |
| day_name | VARCHAR(10) | Name of day |
| day_of_month | INTEGER | Day number in month |
| day_of_year | INTEGER | Day number in year |
| week_of_year | INTEGER | ISO week number |
| month_number | INTEGER | Month number (1-12) |
| month_name | VARCHAR(10) | Name of month |
| quarter | INTEGER | Quarter (1-4) |
| year | INTEGER | Year (YYYY) |
| is_weekend | BOOLEAN | Weekend flag |
| is_holiday | BOOLEAN | Holiday flag |
| fiscal_year | INTEGER | Fiscal year |
| fiscal_quarter | INTEGER | Fiscal quarter |

#### dim_customers
Customer dimension with demographics and metrics

| Column | Type | Description |
|--------|------|-------------|
| customer_key | SERIAL | Surrogate primary key |
| customer_id | VARCHAR(50) | Business key |
| email | VARCHAR(255) | Customer email |
| full_name | VARCHAR(255) | Full name |
| first_name | VARCHAR(100) | First name |
| last_name | VARCHAR(100) | Last name |
| date_of_birth | DATE | Birth date |
| age | INTEGER | Current age |
| age_group | VARCHAR(20) | Age group (18-24, 25-34, etc.) |
| gender | VARCHAR(10) | Gender (M/F/Other) |
| registration_date | TIMESTAMP | Registration timestamp |
| customer_segment | VARCHAR(50) | Customer segment (REGULAR, VIP, GOLD) |
| customer_tier | VARCHAR(20) | Tier based on LTV (Bronze, Silver, Gold, VIP) |
| city | VARCHAR(100) | City |
| province | VARCHAR(100) | Province |
| region | VARCHAR(50) | Region (North, South, Central) |
| total_lifetime_orders | INTEGER | Total orders placed |
| total_lifetime_value | DECIMAL(15,2) | Total spend (VND) |
| average_order_value | DECIMAL(15,2) | Average order value (VND) |
| first_order_date | DATE | Date of first order |
| last_order_date | DATE | Date of last order |
| days_since_last_order | INTEGER | Days since last purchase |
| is_active | BOOLEAN | Active customer flag |
| valid_from | TIMESTAMP | SCD Type 2: Valid from |
| valid_to | TIMESTAMP | SCD Type 2: Valid to (NULL for current) |
| is_current | BOOLEAN | SCD Type 2: Current version flag |

#### dim_products
Product dimension with catalog information

| Column | Type | Description |
|--------|------|-------------|
| product_key | SERIAL | Surrogate primary key |
| product_id | VARCHAR(50) | Business key |
| product_name | VARCHAR(255) | Product name |
| product_name_english | VARCHAR(255) | English product name |
| category | VARCHAR(100) | Product category |
| subcategory | VARCHAR(100) | Product subcategory |
| brand | VARCHAR(100) | Brand name |
| unit_price | DECIMAL(15,2) | Selling price (VND) |
| cost_price | DECIMAL(15,2) | Cost price (VND) |
| margin_percent | DECIMAL(5,2) | Profit margin percentage |
| price_tier | VARCHAR(20) | Price tier (Budget, Standard, Premium, Luxury) |
| supplier_id | VARCHAR(50) | Supplier identifier |
| supplier_name | VARCHAR(255) | Supplier name |
| is_active | BOOLEAN | Active product flag |
| product_launch_date | DATE | Launch date |
| valid_from | TIMESTAMP | SCD Type 2: Valid from |
| valid_to | TIMESTAMP | SCD Type 2: Valid to |
| is_current | BOOLEAN | SCD Type 2: Current version flag |

#### dim_locations
Geographic dimension

| Column | Type | Description |
|--------|------|-------------|
| location_key | SERIAL | Primary key |
| city | VARCHAR(100) | City name |
| province | VARCHAR(100) | Province name |
| region | VARCHAR(50) | Region (North, South, Central) |
| country | VARCHAR(50) | Country (default: Vietnam) |
| postal_code | VARCHAR(20) | Postal code |
| latitude | DECIMAL(10,7) | Latitude coordinate |
| longitude | DECIMAL(10,7) | Longitude coordinate |
| population | INTEGER | City population |
| economic_zone | VARCHAR(50) | Economic zone |

#### dim_payment_methods
Payment method dimension

| Column | Type | Description |
|--------|------|-------------|
| payment_method_key | SERIAL | Primary key |
| payment_method_id | VARCHAR(50) | Business key |
| payment_method_name | VARCHAR(100) | Display name |
| payment_type | VARCHAR(50) | Type (Card, E-Wallet, Bank Transfer, Cash) |
| provider | VARCHAR(100) | Payment provider |
| is_digital | BOOLEAN | Digital payment flag |
| transaction_fee_percent | DECIMAL(5,2) | Transaction fee percentage |
| is_active | BOOLEAN | Active method flag |

#### dim_order_status
Order status dimension

| Column | Type | Description |
|--------|------|-------------|
| order_status_key | SERIAL | Primary key |
| order_status_id | VARCHAR(50) | Business key |
| order_status_name | VARCHAR(100) | Display name |
| status_category | VARCHAR(50) | Category (In Progress, Completed, Cancelled) |
| is_completed | BOOLEAN | Completion flag |
| is_cancelled | BOOLEAN | Cancellation flag |
| display_order | INTEGER | Sort order for display |

#### fact_orders
Order transaction fact table

| Column | Type | Description |
|--------|------|-------------|
| order_fact_key | SERIAL | Primary key |
| order_id | VARCHAR(50) | Business key |
| order_date_key | INTEGER | FK to dim_date |
| payment_date_key | INTEGER | FK to dim_date |
| delivery_date_key | INTEGER | FK to dim_date |
| customer_key | INTEGER | FK to dim_customers |
| location_key | INTEGER | FK to dim_locations |
| payment_method_key | INTEGER | FK to dim_payment_methods |
| order_status_key | INTEGER | FK to dim_order_status |
| order_number | VARCHAR(50) | Order number |
| transaction_id | VARCHAR(100) | Transaction ID |
| order_quantity | INTEGER | Total items in order |
| gross_amount | DECIMAL(15,2) | Gross order amount (VND) |
| discount_amount | DECIMAL(15,2) | Total discounts (VND) |
| tax_amount | DECIMAL(15,2) | Tax amount (VND) |
| shipping_fee | DECIMAL(15,2) | Shipping fee (VND) |
| net_amount | DECIMAL(15,2) | Net order amount (VND) |
| payment_amount | DECIMAL(15,2) | Payment received (VND) |
| is_first_order | BOOLEAN | First order flag |
| is_returned | BOOLEAN | Return flag |
| is_cancelled | BOOLEAN | Cancellation flag |
| order_processing_hours | DECIMAL(10,2) | Processing time (hours) |
| payment_processing_seconds | INTEGER | Payment time (seconds) |

#### fact_order_items
Order line item fact table

| Column | Type | Description |
|--------|------|-------------|
| order_item_fact_key | SERIAL | Primary key |
| order_item_id | VARCHAR(50) | Business key |
| order_id | VARCHAR(50) | Parent order ID |
| order_date_key | INTEGER | FK to dim_date |
| customer_key | INTEGER | FK to dim_customers |
| product_key | INTEGER | FK to dim_products |
| quantity | INTEGER | Quantity ordered |
| unit_price | DECIMAL(15,2) | Unit price (VND) |
| unit_cost | DECIMAL(15,2) | Unit cost (VND) |
| discount_amount | DECIMAL(15,2) | Line discount (VND) |
| gross_revenue | DECIMAL(15,2) | Gross revenue (VND) |
| net_revenue | DECIMAL(15,2) | Net revenue (VND) |
| product_cost | DECIMAL(15,2) | Total cost (VND) |
| gross_profit | DECIMAL(15,2) | Gross profit (VND) |

#### fact_daily_sales
Daily aggregated sales metrics

| Column | Type | Description |
|--------|------|-------------|
| daily_sales_key | SERIAL | Primary key |
| date_key | INTEGER | FK to dim_date |
| product_category | VARCHAR(100) | Category filter |
| customer_segment | VARCHAR(50) | Segment filter |
| location_province | VARCHAR(100) | Province filter |
| total_orders | INTEGER | Order count |
| total_customers | INTEGER | Unique customer count |
| new_customers | INTEGER | New customer count |
| returning_customers | INTEGER | Returning customer count |
| total_items_sold | INTEGER | Total items sold |
| total_gross_revenue | DECIMAL(15,2) | Gross revenue (VND) |
| total_discounts | DECIMAL(15,2) | Total discounts (VND) |
| total_net_revenue | DECIMAL(15,2) | Net revenue (VND) |
| total_product_cost | DECIMAL(15,2) | Total cost (VND) |
| total_gross_profit | DECIMAL(15,2) | Gross profit (VND) |
| average_order_value | DECIMAL(15,2) | AOV (VND) |
| average_items_per_order | DECIMAL(10,2) | Items per order |
| cancelled_orders | INTEGER | Cancelled order count |
| returned_orders | INTEGER | Returned order count |

---

## Common Business Metrics

### Revenue Metrics
- **Gross Merchandise Value (GMV)**: Sum of gross_amount
- **Net Revenue**: GMV - discounts - returns
- **Average Order Value (AOV)**: Total revenue / number of orders

### Customer Metrics
- **Customer Lifetime Value (CLV)**: total_lifetime_value
- **Customer Acquisition**: Count of new customers (is_first_order = TRUE)
- **Customer Retention Rate**: returning_customers / (total_customers - new_customers)
- **Active Customers**: Customers with orders in last 90 days

### Product Metrics
- **Gross Profit**: net_revenue - product_cost
- **Gross Margin %**: (gross_profit / net_revenue) * 100
- **Product Velocity**: total_items_sold / days_in_period
- **Best Sellers**: Products by revenue or quantity

### Operational Metrics
- **Order Fulfillment Time**: Average order_processing_hours
- **Payment Success Rate**: Successful payments / total payments
- **Order Cancellation Rate**: Cancelled orders / total orders
- **Return Rate**: Returned orders / delivered orders

---

## Data Lineage

```
Source (OLTP) → Staging → Core → Analytics
```

### Example: Order Amount
1. **Source**: `orders.total_amount` (raw from OLTP)
2. **Staging**: `staging.orders.total_amount` (exact copy)
3. **Core**: `core.orders.total_amount` (validated, cleaned)
4. **Analytics**: `fact_orders.net_amount` (dimensional context added)

---

## Data Refresh Schedule

| Layer | Refresh Frequency | Method |
|-------|------------------|--------|
| Staging | Daily, 2:00 AM | Incremental (7-day window) |
| Core | Daily, 2:15 AM | Incremental + SCD Type 2 |
| Analytics (Dimensions) | Daily, 2:30 AM | Upsert |
| Analytics (Facts) | Daily, 2:45 AM | Append only |
| Daily Aggregates | Daily, 3:00 AM | Delete & reload (7 days) |

---

## Notes

- All amounts in **Vietnamese Dong (VND)**
- Timestamps in **UTC**
- SCD Type 2 tracks historical changes for customers and products
- Surrogate keys used for all dimensional tables
- Business keys preserved from source systems

