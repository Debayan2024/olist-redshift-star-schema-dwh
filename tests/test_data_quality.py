"""
Unit tests for data quality framework
"""

import pytest
import sys
from pathlib import Path
import pandas as pd

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))


class TestDataValidation:
    """Tests for data validation rules"""
    
    def test_required_columns_present(self):
        """Test that required columns are present"""
        df = pd.DataFrame({
            'order_id': ['ORD001'],
            'customer_id': ['CUST001'],
            'total_amount': [100000]
        })
        
        required_columns = ['order_id', 'customer_id', 'total_amount']
        assert all(col in df.columns for col in required_columns)
    
    def test_no_negative_amounts(self):
        """Test that amounts are not negative"""
        df = pd.DataFrame({
            'order_id': ['ORD001', 'ORD002'],
            'total_amount': [100000, 250000]
        })
        
        assert all(df['total_amount'] >= 0), "All amounts must be non-negative"
    
    def test_no_negative_quantities(self):
        """Test that quantities are positive"""
        df = pd.DataFrame({
            'order_item_id': ['ITEM001', 'ITEM002'],
            'quantity': [1, 5]
        })
        
        assert all(df['quantity'] > 0), "Quantities must be positive"


class TestReferentialIntegrity:
    """Tests for referential integrity checks"""
    
    def test_order_items_have_valid_orders(self):
        """Test that all order items reference valid orders"""
        orders = pd.DataFrame({
            'order_id': ['ORD001', 'ORD002']
        })
        
        order_items = pd.DataFrame({
            'order_item_id': ['ITEM001', 'ITEM002'],
            'order_id': ['ORD001', 'ORD002']
        })
        
        # Check all order_items.order_id exist in orders
        valid = order_items['order_id'].isin(orders['order_id'])
        assert all(valid), "All order items must reference valid orders"
    
    def test_detect_orphaned_records(self):
        """Test detection of orphaned records"""
        orders = pd.DataFrame({
            'order_id': ['ORD001', 'ORD002']
        })
        
        order_items = pd.DataFrame({
            'order_item_id': ['ITEM001', 'ITEM002', 'ITEM003'],
            'order_id': ['ORD001', 'ORD002', 'ORD999']  # ORD999 doesn't exist
        })
        
        orphaned = ~order_items['order_id'].isin(orders['order_id'])
        orphaned_count = orphaned.sum()
        
        assert orphaned_count == 1, "Should detect 1 orphaned record"


class TestDataQualityMetrics:
    """Tests for data quality metric calculations"""
    
    def test_null_percentage_calculation(self):
        """Test null percentage calculation"""
        df = pd.DataFrame({
            'col1': [1, 2, None, None, 5]  # 2 nulls out of 5 = 40%
        })
        
        null_count = df['col1'].isnull().sum()
        total_count = len(df)
        null_percentage = (null_count / total_count) * 100
        
        assert null_count == 2
        assert null_percentage == 40.0
    
    def test_duplicate_percentage_calculation(self):
        """Test duplicate percentage calculation"""
        df = pd.DataFrame({
            'id': [1, 2, 2, 3, 3]  # 2 duplicates out of 5 = 40%
        })
        
        duplicate_count = df['id'].duplicated().sum()
        total_count = len(df)
        duplicate_percentage = (duplicate_count / total_count) * 100
        
        assert duplicate_count == 2
        assert duplicate_percentage == 40.0
    
    def test_completeness_rate(self):
        """Test data completeness rate"""
        df = pd.DataFrame({
            'col1': [1, 2, 3, None, 5]  # 80% complete
        })
        
        complete_count = df['col1'].notna().sum()
        total_count = len(df)
        completeness_rate = (complete_count / total_count) * 100
        
        assert completeness_rate == 80.0


class TestBusinessRules:
    """Tests for business rule validation"""
    
    def test_customer_age_requirement(self):
        """Test that customers meet minimum age requirement"""
        from datetime import date
        
        customers = pd.DataFrame({
            'customer_id': ['CUST001', 'CUST002'],
            'date_of_birth': [date(2000, 1, 1), date(2005, 1, 1)]
        })
        
        # Calculate age
        today = date(2024, 1, 1)
        customers['age'] = customers['date_of_birth'].apply(
            lambda x: today.year - x.year
        )
        
        min_age = 18
        valid_customers = customers[customers['age'] >= min_age]
        
        assert len(valid_customers) == 2  # Both are 18+
    
    def test_order_date_not_future(self):
        """Test that order dates are not in the future"""
        from datetime import datetime
        
        orders = pd.DataFrame({
            'order_id': ['ORD001', 'ORD002'],
            'order_date': [
                datetime(2024, 1, 1),
                datetime(2024, 1, 2)
            ]
        })
        
        today = datetime(2024, 1, 15)
        future_orders = orders[orders['order_date'] > today]
        
        assert len(future_orders) == 0, "No orders should be in the future"
    
    def test_revenue_equals_price_times_quantity(self):
        """Test revenue calculation logic"""
        order_items = pd.DataFrame({
            'quantity': [2, 3],
            'unit_price': [100, 200],
            'expected_revenue': [200, 600]
        })
        
        order_items['calculated_revenue'] = (
            order_items['quantity'] * order_items['unit_price']
        )
        
        assert all(
            order_items['calculated_revenue'] == order_items['expected_revenue']
        )


class TestAnomalyDetection:
    """Tests for anomaly detection logic"""
    
    def test_detect_outliers_std_dev(self):
        """Test outlier detection using standard deviation"""
        df = pd.DataFrame({
            'amount': [100, 110, 105, 108, 1000]  # 1000 is outlier
        })
        
        mean = df['amount'].mean()
        std = df['amount'].std()
        threshold = 3  # 3 standard deviations
        
        outliers = df[abs(df['amount'] - mean) > (threshold * std)]
        
        assert len(outliers) == 1
        assert outliers.iloc[0]['amount'] == 1000
    
    def test_detect_volume_anomaly(self):
        """Test volume anomaly detection"""
        # Daily order counts
        daily_counts = pd.DataFrame({
            'date': pd.date_range('2024-01-01', periods=7),
            'order_count': [100, 105, 98, 102, 99, 500, 101]  # Day 6 is anomaly
        })
        
        avg_count = daily_counts['order_count'].mean()
        
        # Define anomaly as > 2x average
        threshold = 2.0
        anomalies = daily_counts[daily_counts['order_count'] > (avg_count * threshold)]
        
        assert len(anomalies) == 1, "Should detect 1 volume anomaly"


class TestDataProfiling:
    """Tests for data profiling functions"""
    
    def test_column_statistics(self):
        """Test basic column statistics"""
        df = pd.DataFrame({
            'amount': [100, 200, 300, 400, 500]
        })
        
        stats = {
            'count': len(df),
            'mean': df['amount'].mean(),
            'min': df['amount'].min(),
            'max': df['amount'].max(),
            'std': df['amount'].std()
        }
        
        assert stats['count'] == 5
        assert stats['mean'] == 300.0
        assert stats['min'] == 100
        assert stats['max'] == 500
    
    def test_distinct_count(self):
        """Test distinct value counting"""
        df = pd.DataFrame({
            'category': ['A', 'B', 'A', 'C', 'B', 'A']
        })
        
        distinct_count = df['category'].nunique()
        value_counts = df['category'].value_counts()
        
        assert distinct_count == 3
        assert value_counts['A'] == 3
        assert value_counts['B'] == 2
        assert value_counts['C'] == 1


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, '-v'])

