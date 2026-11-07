"""
Transform Module
Applies business logic and data transformations
Moves data from staging to core layer
"""

import sys
from pathlib import Path
from datetime import datetime
from typing import Dict
import yaml

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.utils.db_connector import get_db_connector
from src.utils.logger import ETLLogger


class DataTransformer:
    """
    Transform data from staging to core layer
    Applies data cleaning, validation, and business logic
    """
    
    def __init__(self, config_path: str = "config/pipeline_config.yaml"):
        """Initialize data transformer"""
        self.logger = ETLLogger("DataTransformer")
        self.db = get_db_connector()
        self.config = self._load_config(config_path)
        
    def _load_config(self, config_path: str) -> Dict:
        """Load pipeline configuration"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def transform_staging_to_core(self):
        """
        Execute staging to core transformation
        Runs SQL transformation logic
        """
        self.logger.log_stage("TRANSFORM", "Starting staging to core transformation")
        
        sql_file = "sql/transforms/staging_to_core.sql"
        
        try:
            # Check if file exists
            if not Path(sql_file).exists():
                self.logger.logger.warning(f"SQL file not found: {sql_file}")
                return
            
            # Execute transformation SQL
            self.db.execute_sql_file(sql_file, db_name='data_warehouse')
            
            # Log row counts
            core_tables = ['orders', 'order_items', 'customers', 'products', 'payments']
            for table in core_tables:
                try:
                    count = self.db.get_table_row_count(table, schema='core')
                    self.logger.log_metric(f"core_{table}_rows", count)
                except:
                    pass
            
            self.logger.log_stage("TRANSFORM", "Staging to core transformation completed")
            
        except Exception as e:
            self.logger.logger.error(f"Transformation failed: {e}")
            raise
    
    def update_customer_metrics(self):
        """Update customer aggregated metrics"""
        self.logger.log_stage("TRANSFORM", "Updating customer metrics")
        
        query = """
        UPDATE core.customers c
        SET 
            total_orders = COALESCE(order_stats.order_count, 0),
            total_spent = COALESCE(order_stats.total_spent, 0),
            last_order_date = order_stats.last_order_date,
            dw_updated_at = CURRENT_TIMESTAMP
        FROM (
            SELECT 
                customer_id,
                COUNT(*) as order_count,
                SUM(total_amount) as total_spent,
                MAX(order_date) as last_order_date
            FROM core.orders
            WHERE order_status NOT IN ('CANCELLED', 'REFUNDED')
            GROUP BY customer_id
        ) AS order_stats
        WHERE c.customer_id = order_stats.customer_id
        AND c.is_current = TRUE
        """
        
        try:
            self.db.execute_query(query, db_name='data_warehouse')
            self.logger.log_stage("TRANSFORM", "Customer metrics updated")
        except Exception as e:
            self.logger.logger.error(f"Failed to update customer metrics: {e}")
            raise
    
    def run_data_quality_checks(self):
        """Run basic data quality checks after transformation"""
        self.logger.log_stage("DATA_QUALITY", "Running transformation quality checks")
        
        checks = [
            {
                'name': 'Orphaned Order Items',
                'query': """
                    SELECT COUNT(*) 
                    FROM core.order_items oi
                    LEFT JOIN core.orders o ON oi.order_id = o.order_id
                    WHERE o.order_id IS NULL
                """
            },
            {
                'name': 'Negative Amounts',
                'query': """
                    SELECT COUNT(*) 
                    FROM core.orders 
                    WHERE total_amount < 0
                """
            },
            {
                'name': 'Invalid Quantities',
                'query': """
                    SELECT COUNT(*) 
                    FROM core.order_items 
                    WHERE quantity <= 0
                """
            }
        ]
        
        all_passed = True
        
        for check in checks:
            result = self.db.execute_query(
                check['query'],
                db_name='data_warehouse',
                fetch=True
            )
            count = result[0][0] if result else 0
            passed = count == 0
            all_passed = all_passed and passed
            
            self.logger.log_data_quality(
                check['name'],
                passed,
                f"Found {count} issues"
            )
        
        return all_passed
    
    def run_full_transformation(self):
        """Run complete transformation pipeline"""
        self.logger.start_pipeline()
        
        try:
            # Execute main transformation
            self.transform_staging_to_core()
            
            # Update aggregated metrics
            self.update_customer_metrics()
            
            # Run quality checks
            quality_passed = self.run_data_quality_checks()
            
            status = "SUCCESS" if quality_passed else "SUCCESS_WITH_WARNINGS"
            self.logger.end_pipeline(status=status)
            
        except Exception as e:
            self.logger.logger.error(f"Transformation pipeline failed: {e}")
            self.logger.end_pipeline(status="FAILED")
            raise


def main():
    """Main execution function"""
    print("=" * 80)
    print("TRANSFORM: Starting data transformation process")
    print("=" * 80)
    
    transformer = DataTransformer()
    transformer.run_full_transformation()
    
    print("\n" + "=" * 80)
    print("TRANSFORM: Data transformation completed")
    print("=" * 80)


if __name__ == "__main__":
    main()

