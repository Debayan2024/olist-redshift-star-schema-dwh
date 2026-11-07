"""
Data Quality Validators
Comprehensive data validation checks
"""

import sys
from pathlib import Path
from typing import Dict, List, Tuple
from datetime import datetime
import pandas as pd
import yaml

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.utils.db_connector import get_db_connector
from src.utils.logger import ETLLogger


class DataQualityValidator:
    """
    Comprehensive data quality validation framework
    """
    
    def __init__(self, config_path: str = "config/pipeline_config.yaml"):
        """Initialize validator"""
        self.logger = ETLLogger("DataQualityValidator")
        self.db = get_db_connector()
        self.config = self._load_config(config_path)
        self.dq_config = self.config.get('data_quality', {})
        self.results = []
        
    def _load_config(self, config_path: str) -> Dict:
        """Load pipeline configuration"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def check_schema_validation(self, table_name: str, schema: str,
                                expected_columns: List[str]) -> Tuple[bool, str]:
        """
        Validate table schema
        
        Args:
            table_name: Table name
            schema: Schema name
            expected_columns: List of expected column names
            
        Returns:
            Tuple of (passed, details)
        """
        query = f"""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = '{schema}'
            AND table_name = '{table_name}'
            ORDER BY ordinal_position
        """
        
        try:
            result = self.db.execute_query(query, db_name='data_warehouse', fetch=True)
            actual_columns = [row[0] for row in result]
            
            missing = set(expected_columns) - set(actual_columns)
            extra = set(actual_columns) - set(expected_columns)
            
            if not missing and not extra:
                return True, "Schema matches expected structure"
            
            details = []
            if missing:
                details.append(f"Missing columns: {missing}")
            if extra:
                details.append(f"Extra columns: {extra}")
            
            return False, " | ".join(details)
            
        except Exception as e:
            return False, f"Schema check failed: {e}"
    
    def check_null_values(self, table_name: str, schema: str,
                         column_name: str) -> Tuple[bool, str]:
        """
        Check for null values in required columns
        
        Args:
            table_name: Table name
            schema: Schema name
            column_name: Column to check
            
        Returns:
            Tuple of (passed, details)
        """
        query = f"""
            SELECT 
                COUNT(*) as total_rows,
                COUNT({column_name}) as non_null_rows,
                COUNT(*) - COUNT({column_name}) as null_rows,
                ROUND(
                    (COUNT(*) - COUNT({column_name}))::NUMERIC / 
                    NULLIF(COUNT(*), 0) * 100, 
                    2
                ) as null_percentage
            FROM {schema}.{table_name}
        """
        
        try:
            result = self.db.execute_query(query, db_name='data_warehouse', fetch=True)
            if result:
                total, non_null, nulls, pct = result[0]
                threshold = self.dq_config.get('thresholds', {}).get('max_null_percentage', 5)
                
                passed = pct <= threshold
                details = f"{nulls} nulls ({pct}%), threshold: {threshold}%"
                return passed, details
            
            return False, "No data found"
            
        except Exception as e:
            return False, f"Null check failed: {e}"
    
    def check_uniqueness(self, table_name: str, schema: str,
                        column_name: str) -> Tuple[bool, str]:
        """
        Check uniqueness constraint
        
        Args:
            table_name: Table name
            schema: Schema name
            column_name: Column to check
            
        Returns:
            Tuple of (passed, details)
        """
        query = f"""
            SELECT 
                COUNT(*) as total_rows,
                COUNT(DISTINCT {column_name}) as unique_rows,
                COUNT(*) - COUNT(DISTINCT {column_name}) as duplicate_rows,
                ROUND(
                    (COUNT(*) - COUNT(DISTINCT {column_name}))::NUMERIC / 
                    NULLIF(COUNT(*), 0) * 100, 
                    2
                ) as duplicate_percentage
            FROM {schema}.{table_name}
        """
        
        try:
            result = self.db.execute_query(query, db_name='data_warehouse', fetch=True)
            if result:
                total, unique, duplicates, pct = result[0]
                threshold = self.dq_config.get('thresholds', {}).get('max_duplicate_percentage', 1)
                
                passed = pct <= threshold
                details = f"{duplicates} duplicates ({pct}%), threshold: {threshold}%"
                return passed, details
            
            return False, "No data found"
            
        except Exception as e:
            return False, f"Uniqueness check failed: {e}"
    
    def check_referential_integrity(self, child_table: str, child_column: str,
                                   parent_table: str, parent_column: str,
                                   child_schema: str = 'core',
                                   parent_schema: str = 'core') -> Tuple[bool, str]:
        """
        Check referential integrity between tables
        
        Args:
            child_table: Child table name
            child_column: Foreign key column
            parent_table: Parent table name
            parent_column: Primary key column
            child_schema: Child table schema
            parent_schema: Parent table schema
            
        Returns:
            Tuple of (passed, details)
        """
        query = f"""
            SELECT COUNT(*)
            FROM {child_schema}.{child_table} c
            LEFT JOIN {parent_schema}.{parent_table} p 
                ON c.{child_column} = p.{parent_column}
            WHERE c.{child_column} IS NOT NULL
            AND p.{parent_column} IS NULL
        """
        
        try:
            result = self.db.execute_query(query, db_name='data_warehouse', fetch=True)
            orphaned_rows = result[0][0] if result else 0
            
            passed = orphaned_rows == 0
            details = f"{orphaned_rows} orphaned records"
            return passed, details
            
        except Exception as e:
            return False, f"Referential integrity check failed: {e}"
    
    def check_value_range(self, table_name: str, schema: str, column_name: str,
                         min_value=None, max_value=None) -> Tuple[bool, str]:
        """
        Check if values are within expected range
        
        Args:
            table_name: Table name
            schema: Schema name
            column_name: Column to check
            min_value: Minimum allowed value
            max_value: Maximum allowed value
            
        Returns:
            Tuple of (passed, details)
        """
        conditions = []
        if min_value is not None:
            conditions.append(f"{column_name} < {min_value}")
        if max_value is not None:
            conditions.append(f"{column_name} > {max_value}")
        
        if not conditions:
            return True, "No range constraints specified"
        
        query = f"""
            SELECT COUNT(*)
            FROM {schema}.{table_name}
            WHERE {' OR '.join(conditions)}
        """
        
        try:
            result = self.db.execute_query(query, db_name='data_warehouse', fetch=True)
            out_of_range = result[0][0] if result else 0
            
            passed = out_of_range == 0
            details = f"{out_of_range} values out of range [{min_value}, {max_value}]"
            return passed, details
            
        except Exception as e:
            return False, f"Range check failed: {e}"
    
    def check_row_count(self, table_name: str, schema: str) -> Tuple[bool, str]:
        """
        Check if table has minimum required rows
        
        Args:
            table_name: Table name
            schema: Schema name
            
        Returns:
            Tuple of (passed, details)
        """
        try:
            count = self.db.get_table_row_count(table_name, schema)
            min_rows = self.dq_config.get('thresholds', {}).get('min_row_count', 100)
            
            passed = count >= min_rows
            details = f"{count} rows (minimum: {min_rows})"
            return passed, details
            
        except Exception as e:
            return False, f"Row count check failed: {e}"
    
    def run_all_checks(self):
        """Run comprehensive data quality checks"""
        self.logger.start_pipeline()
        
        checks_passed = 0
        checks_failed = 0
        
        # Core table checks
        core_checks = [
            ('core', 'orders', 'order_id', 'uniqueness'),
            ('core', 'orders', 'customer_id', 'not_null'),
            ('core', 'orders', 'total_amount', 'range', {'min_value': 0}),
            ('core', 'order_items', 'quantity', 'range', {'min_value': 1}),
            ('core', 'customers', 'email', 'uniqueness'),
            ('core', 'customers', 'customer_id', 'not_null'),
        ]
        
        # Referential integrity checks
        ref_checks = [
            ('order_items', 'order_id', 'orders', 'order_id', 'core', 'core'),
            ('order_items', 'product_id', 'products', 'product_id', 'core', 'core'),
            ('orders', 'customer_id', 'customers', 'customer_id', 'core', 'core'),
        ]
        
        # Execute checks
        for schema, table, column, check_type, *params in core_checks:
            check_name = f"{schema}.{table}.{column} - {check_type}"
            
            try:
                if check_type == 'uniqueness':
                    passed, details = self.check_uniqueness(table, schema, column)
                elif check_type == 'not_null':
                    passed, details = self.check_null_values(table, schema, column)
                elif check_type == 'range':
                    kwargs = params[0] if params else {}
                    passed, details = self.check_value_range(table, schema, column, **kwargs)
                else:
                    passed, details = False, "Unknown check type"
                
                self.logger.log_data_quality(check_name, passed, details)
                
                if passed:
                    checks_passed += 1
                else:
                    checks_failed += 1
                    
            except Exception as e:
                self.logger.logger.error(f"Check failed: {check_name} - {e}")
                checks_failed += 1
        
        # Referential integrity checks
        for child_table, child_col, parent_table, parent_col, child_schema, parent_schema in ref_checks:
            check_name = f"FK: {child_schema}.{child_table}.{child_col} -> {parent_schema}.{parent_table}.{parent_col}"
            
            try:
                passed, details = self.check_referential_integrity(
                    child_table, child_col, parent_table, parent_col, child_schema, parent_schema
                )
                
                self.logger.log_data_quality(check_name, passed, details)
                
                if passed:
                    checks_passed += 1
                else:
                    checks_failed += 1
                    
            except Exception as e:
                self.logger.logger.error(f"Check failed: {check_name} - {e}")
                checks_failed += 1
        
        # Log summary
        self.logger.log_metric("checks_passed", checks_passed)
        self.logger.log_metric("checks_failed", checks_failed)
        
        total_checks = checks_passed + checks_failed
        pass_rate = (checks_passed / total_checks * 100) if total_checks > 0 else 0
        self.logger.log_metric("pass_rate_percent", round(pass_rate, 2))
        
        status = "SUCCESS" if checks_failed == 0 else "COMPLETED_WITH_FAILURES"
        self.logger.end_pipeline(status=status)
        
        return checks_failed == 0


def main():
    """Main execution function"""
    print("=" * 80)
    print("DATA QUALITY: Running data quality validation")
    print("=" * 80)
    
    validator = DataQualityValidator()
    all_passed = validator.run_all_checks()
    
    print("\n" + "=" * 80)
    if all_passed:
        print("DATA QUALITY: All checks passed ✓")
    else:
        print("DATA QUALITY: Some checks failed - review logs")
    print("=" * 80)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    exit(main())

