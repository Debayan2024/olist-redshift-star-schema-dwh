"""
Load Module
Loads transformed data into dimensional model (analytics layer)
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


class DataLoader:
    """
    Load data from core layer to analytical dimensional model
    """
    
    def __init__(self, config_path: str = "config/pipeline_config.yaml"):
        """Initialize data loader"""
        self.logger = ETLLogger("DataLoader")
        self.db = get_db_connector()
        self.config = self._load_config(config_path)
        
    def _load_config(self, config_path: str) -> Dict:
        """Load pipeline configuration"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def load_dimensional_model(self):
        """
        Execute core to dimensional transformation
        Builds star schema
        """
        self.logger.log_stage("LOAD", "Loading dimensional model")
        
        sql_file = "sql/transforms/core_to_dimensional.sql"
        
        try:
            # Check if file exists
            if not Path(sql_file).exists():
                self.logger.logger.warning(f"SQL file not found: {sql_file}")
                return
            
            # Execute dimensional model SQL
            self.db.execute_sql_file(sql_file, db_name='data_warehouse')
            
            self.logger.log_stage("LOAD", "Dimensional model loaded successfully")
            
        except Exception as e:
            self.logger.logger.error(f"Failed to load dimensional model: {e}")
            raise
    
    def log_dimensional_metrics(self):
        """Log row counts for dimensional tables"""
        self.logger.log_stage("METRICS", "Collecting dimensional model metrics")
        
        # Dimension tables
        dimensions = ['dim_date', 'dim_customers', 'dim_products', 
                     'dim_locations', 'dim_payment_methods', 'dim_order_status']
        
        # Fact tables
        facts = ['fact_orders', 'fact_order_items', 'fact_daily_sales']
        
        # Log dimension counts
        for dim in dimensions:
            try:
                count = self.db.get_table_row_count(dim, schema='analytics')
                self.logger.log_metric(f"{dim}_rows", count)
            except Exception as e:
                self.logger.logger.warning(f"Could not get count for {dim}: {e}")
        
        # Log fact counts
        for fact in facts:
            try:
                count = self.db.get_table_row_count(fact, schema='analytics')
                self.logger.log_metric(f"{fact}_rows", count)
            except Exception as e:
                self.logger.logger.warning(f"Could not get count for {fact}: {e}")
    
    def validate_dimensional_model(self):
        """Validate dimensional model integrity"""
        self.logger.log_stage("VALIDATION", "Validating dimensional model")
        
        checks = [
            {
                'name': 'Orders without customers',
                'query': """
                    SELECT COUNT(*) 
                    FROM analytics.fact_orders fo
                    WHERE fo.customer_key IS NULL
                """
            },
            {
                'name': 'Order items without products',
                'query': """
                    SELECT COUNT(*) 
                    FROM analytics.fact_order_items foi
                    WHERE foi.product_key IS NULL
                """
            },
            {
                'name': 'Orders without dates',
                'query': """
                    SELECT COUNT(*) 
                    FROM analytics.fact_orders fo
                    LEFT JOIN analytics.dim_date dd ON fo.order_date_key = dd.date_key
                    WHERE dd.date_key IS NULL
                """
            },
            {
                'name': 'Fact-Dimension consistency',
                'query': """
                    SELECT COUNT(*) 
                    FROM analytics.fact_orders fo
                    LEFT JOIN analytics.dim_customers dc 
                        ON fo.customer_key = dc.customer_key
                    WHERE fo.customer_key IS NOT NULL 
                    AND dc.customer_key IS NULL
                """
            }
        ]
        
        all_passed = True
        
        for check in checks:
            try:
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
            except Exception as e:
                self.logger.logger.error(f"Validation check failed: {check['name']} - {e}")
                all_passed = False
        
        return all_passed
    
    def optimize_tables(self):
        """Run VACUUM and ANALYZE on dimensional tables"""
        if not self.config['performance'].get('vacuum_after_load', True):
            return
        
        self.logger.log_stage("OPTIMIZE", "Optimizing dimensional tables")
        
        tables = [
            'analytics.dim_customers',
            'analytics.dim_products',
            'analytics.fact_orders',
            'analytics.fact_order_items',
            'analytics.fact_daily_sales'
        ]
        
        for table in tables:
            try:
                # ANALYZE for statistics
                if self.config['performance'].get('analyze_after_load', True):
                    self.db.execute_query(f"ANALYZE {table}", db_name='data_warehouse')
                    self.logger.log_stage("OPTIMIZE", f"Analyzed {table}")
            except Exception as e:
                self.logger.logger.warning(f"Could not optimize {table}: {e}")
    
    def run_full_load(self):
        """Run complete load pipeline"""
        self.logger.start_pipeline()
        
        try:
            # Load dimensional model
            self.load_dimensional_model()
            
            # Collect metrics
            self.log_dimensional_metrics()
            
            # Validate data
            validation_passed = self.validate_dimensional_model()
            
            # Optimize tables
            self.optimize_tables()
            
            status = "SUCCESS" if validation_passed else "SUCCESS_WITH_WARNINGS"
            self.logger.end_pipeline(status=status)
            
        except Exception as e:
            self.logger.logger.error(f"Load pipeline failed: {e}")
            self.logger.end_pipeline(status="FAILED")
            raise


def main():
    """Main execution function"""
    print("=" * 80)
    print("LOAD: Starting dimensional model load process")
    print("=" * 80)
    
    loader = DataLoader()
    loader.run_full_load()
    
    print("\n" + "=" * 80)
    print("LOAD: Dimensional model load completed")
    print("=" * 80)


if __name__ == "__main__":
    main()

