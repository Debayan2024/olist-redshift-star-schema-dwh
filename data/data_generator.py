"""
Sample Data Generator
Generates realistic e-commerce data for testing and demonstration
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
import random
import pandas as pd
from faker import Faker
import uuid

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))

from src.utils.db_connector import get_db_connector
from src.utils.logger import setup_logger

# Initialize Faker
fake = Faker(['vi_VN', 'en_US'])  # Vietnamese and English locales
logger = setup_logger(__name__)


class EcommerceDataGenerator:
    """
    Generate realistic e-commerce sample data
    """
    
    def __init__(self, num_customers=1000, num_products=200, num_orders=5000):
        """
        Initialize data generator
        
        Args:
            num_customers: Number of customers to generate
            num_products: Number of products to generate
            num_orders: Number of orders to generate
        """
        self.num_customers = num_customers
        self.num_products = num_products
        self.num_orders = num_orders
        self.db = get_db_connector()
        
        # Data containers
        self.customers = []
        self.products = []
        self.orders = []
        self.order_items = []
        self.payments = []
        self.user_events = []
        
    def generate_customers(self):
        """Generate customer data"""
        logger.info(f"Generating {self.num_customers} customers...")
        
        segments = ['REGULAR', 'VIP', 'GOLD', 'NEW']
        genders = ['M', 'F', 'Other']
        
        for i in range(self.num_customers):
            customer = {
                'customer_id': f'CUST{str(i+1).zfill(6)}',
                'email': fake.email(),
                'phone': fake.phone_number()[:20],
                'first_name': fake.first_name(),
                'last_name': fake.last_name(),
                'date_of_birth': fake.date_of_birth(minimum_age=18, maximum_age=70),
                'gender': random.choice(genders),
                'registration_date': fake.date_time_between(start_date='-2y', end_date='now'),
                'customer_segment': random.choice(segments),
                'created_at': datetime.now(),
                'updated_at': datetime.now()
            }
            self.customers.append(customer)
        
        logger.info(f"Generated {len(self.customers)} customers")
        
    def generate_products(self):
        """Generate product catalog"""
        logger.info(f"Generating {self.num_products} products...")
        
        categories = [
            ('Electronics', ['Smartphones', 'Laptops', 'Tablets', 'Accessories']),
            ('Fashion', ['Clothing', 'Shoes', 'Bags', 'Watches']),
            ('Home & Living', ['Furniture', 'Decor', 'Kitchen', 'Bedding']),
            ('Beauty', ['Skincare', 'Makeup', 'Fragrance', 'Hair Care']),
            ('Sports', ['Fitness', 'Outdoor', 'Sports Gear', 'Activewear'])
        ]
        
        brands = ['Samsung', 'Apple', 'Nike', 'Adidas', 'LG', 'Sony', 'Zara', 'H&M', 'IKEA', 'Loreal']
        
        for i in range(self.num_products):
            category, subcategories = random.choice(categories)
            subcategory = random.choice(subcategories)
            
            unit_price = round(random.uniform(50000, 5000000), -3)  # VND
            cost_price = round(unit_price * random.uniform(0.4, 0.7), -3)
            
            product = {
                'product_id': f'PROD{str(i+1).zfill(6)}',
                'product_name': f'{fake.word().title()} {subcategory} {fake.color_name()}',
                'category': category,
                'subcategory': subcategory,
                'brand': random.choice(brands),
                'unit_price': unit_price,
                'cost_price': cost_price,
                'stock_quantity': random.randint(0, 1000),
                'supplier_id': f'SUP{random.randint(1, 50):03d}',
                'is_active': random.choice([True, True, True, False]),  # 75% active
                'created_at': fake.date_time_between(start_date='-1y', end_date='now'),
                'updated_at': datetime.now()
            }
            self.products.append(product)
        
        logger.info(f"Generated {len(self.products)} products")
        
    def generate_orders(self):
        """Generate orders and order items"""
        logger.info(f"Generating {self.num_orders} orders...")
        
        statuses = ['PENDING', 'CONFIRMED', 'PROCESSING', 'SHIPPED', 'DELIVERED', 'CANCELLED']
        status_weights = [5, 10, 15, 20, 45, 5]  # Weighted distribution
        
        payment_methods = ['Credit Card', 'Debit Card', 'MoMo', 'ZaloPay', 'VNPay', 'Bank Transfer', 'COD']
        
        vietnamese_cities = [
            ('Hồ Chí Minh', 'Hồ Chí Minh'),
            ('Hà Nội', 'Hà Nội'),
            ('Đà Nẵng', 'Đà Nẵng'),
            ('Hải Phòng', 'Hải Phòng'),
            ('Biên Hòa', 'Đồng Nai'),
            ('Nha Trang', 'Khánh Hòa'),
            ('Cần Thơ', 'Cần Thơ'),
            ('Vũng Tàu', 'Bà Rịa - Vũng Tàu')
        ]
        
        for i in range(self.num_orders):
            customer = random.choice(self.customers)
            order_date = fake.date_time_between(start_date='-6m', end_date='now')
            city, province = random.choice(vietnamese_cities)
            
            # Generate order items
            num_items = random.randint(1, 5)
            order_items = random.sample(self.products, min(num_items, len(self.products)))
            
            total_amount = 0
            order_id = f'ORD{str(i+1).zfill(8)}'
            
            for j, product in enumerate(order_items):
                quantity = random.randint(1, 3)
                unit_price = product['unit_price']
                discount_pct = random.choice([0, 0, 0, 5, 10, 15, 20])  # Mostly no discount
                discount_amount = round(unit_price * quantity * discount_pct / 100, -3)
                subtotal = unit_price * quantity
                
                order_item = {
                    'order_item_id': f'{order_id}_ITEM{j+1}',
                    'order_id': order_id,
                    'product_id': product['product_id'],
                    'product_name': product['product_name'],
                    'quantity': quantity,
                    'unit_price': unit_price,
                    'discount_amount': discount_amount,
                    'subtotal': subtotal,
                    'created_at': order_date
                }
                self.order_items.append(order_item)
                total_amount += subtotal
            
            # Adjust for discounts
            total_discount = sum(item['discount_amount'] for item in self.order_items if item['order_id'] == order_id)
            total_amount -= total_discount
            
            order = {
                'order_id': order_id,
                'customer_id': customer['customer_id'],
                'order_date': order_date,
                'order_status': random.choices(statuses, weights=status_weights)[0],
                'total_amount': total_amount,
                'payment_method': random.choice(payment_methods),
                'shipping_address': fake.address()[:200],
                'city': city,
                'province': province,
                'postal_code': fake.postcode()[:10],
                'created_at': order_date,
                'updated_at': order_date + timedelta(hours=random.randint(1, 48))
            }
            self.orders.append(order)
            
            # Generate payment record
            if order['order_status'] not in ['PENDING', 'CANCELLED']:
                payment_date = order_date + timedelta(minutes=random.randint(5, 120))
                payment_status = 'SUCCESS' if order['order_status'] != 'CANCELLED' else 'FAILED'
                
                payment = {
                    'payment_id': f'PAY{str(i+1).zfill(8)}',
                    'order_id': order_id,
                    'payment_date': payment_date,
                    'payment_method': order['payment_method'],
                    'payment_status': payment_status,
                    'amount': total_amount,
                    'transaction_id': str(uuid.uuid4()),
                    'gateway_response': '{"status": "success"}' if payment_status == 'SUCCESS' else '{"status": "failed"}',
                    'created_at': payment_date
                }
                self.payments.append(payment)
        
        logger.info(f"Generated {len(self.orders)} orders and {len(self.order_items)} order items")
        logger.info(f"Generated {len(self.payments)} payments")
        
    def generate_user_events(self, num_events=10000):
        """Generate user clickstream events"""
        logger.info(f"Generating {num_events} user events...")
        
        event_types = ['page_view', 'product_view', 'add_to_cart', 'remove_from_cart', 
                      'checkout_start', 'checkout_complete', 'search']
        
        pages = ['/home', '/products', '/cart', '/checkout', '/account', '/search', '/category/electronics']
        devices = ['mobile', 'desktop', 'tablet']
        browsers = ['Chrome', 'Safari', 'Firefox', 'Edge']
        
        for i in range(num_events):
            customer = random.choice(self.customers)
            event_timestamp = fake.date_time_between(start_date='-6m', end_date='now')
            
            event = {
                'event_id': str(uuid.uuid4()),
                'user_id': customer['customer_id'],
                'session_id': str(uuid.uuid4()),
                'event_type': random.choice(event_types),
                'event_timestamp': event_timestamp,
                'page_url': f"https://example.com{random.choice(pages)}",
                'referrer_url': 'https://google.com' if random.random() > 0.7 else None,
                'device_type': random.choice(devices),
                'browser': random.choice(browsers),
                'ip_address': fake.ipv4(),
                'event_properties': '{"property": "value"}'
            }
            self.user_events.append(event)
        
        logger.info(f"Generated {len(self.user_events)} user events")
        
    def load_to_staging(self):
        """Load generated data to staging tables"""
        logger.info("Loading data to staging tables...")
        
        # Convert to DataFrames
        df_customers = pd.DataFrame(self.customers)
        df_products = pd.DataFrame(self.products)
        df_orders = pd.DataFrame(self.orders)
        df_order_items = pd.DataFrame(self.order_items)
        df_payments = pd.DataFrame(self.payments)
        df_events = pd.DataFrame(self.user_events)
        
        # Load to staging
        self.db.write_dataframe(df_customers, 'customers', schema='staging', if_exists='append')
        logger.info("✓ Loaded customers")
        
        self.db.write_dataframe(df_products, 'products', schema='staging', if_exists='append')
        logger.info("✓ Loaded products")
        
        self.db.write_dataframe(df_orders, 'orders', schema='staging', if_exists='append')
        logger.info("✓ Loaded orders")
        
        self.db.write_dataframe(df_order_items, 'order_items', schema='staging', if_exists='append')
        logger.info("✓ Loaded order items")
        
        self.db.write_dataframe(df_payments, 'payments', schema='staging', if_exists='append')
        logger.info("✓ Loaded payments")
        
        self.db.write_dataframe(df_events, 'user_events', schema='staging', if_exists='append')
        logger.info("✓ Loaded user events")
        
        logger.info("All data loaded successfully!")
        
    def generate_all(self):
        """Generate all sample data"""
        logger.info("=" * 80)
        logger.info("Starting data generation...")
        logger.info("=" * 80)
        
        self.generate_customers()
        self.generate_products()
        self.generate_orders()
        self.generate_user_events()
        self.load_to_staging()
        
        logger.info("=" * 80)
        logger.info("Data generation completed successfully!")
        logger.info("=" * 80)
        
        # Print summary
        summary = f"""
        Data Generation Summary:
        - Customers: {len(self.customers):,}
        - Products: {len(self.products):,}
        - Orders: {len(self.orders):,}
        - Order Items: {len(self.order_items):,}
        - Payments: {len(self.payments):,}
        - User Events: {len(self.user_events):,}
        """
        print(summary)


def main():
    """Main execution"""
    print("\n" + "=" * 80)
    print("E-COMMERCE DATA GENERATOR")
    print("=" * 80)
    
    # Generate data
    generator = EcommerceDataGenerator(
        num_customers=1000,
        num_products=200,
        num_orders=5000
    )
    
    generator.generate_all()
    
    print("\n" + "=" * 80)
    print("Data has been loaded to staging tables")
    print("Next steps:")
    print("  1. Run transformation: python src/etl/transform.py")
    print("  2. Load dimensional model: python src/etl/load.py")
    print("  3. Or trigger Airflow DAG: airflow dags trigger daily_etl_pipeline")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()

