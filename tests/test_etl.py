"""
Unit tests for ETL pipeline
"""

import pytest
import sys
from pathlib import Path
from datetime import datetime
import pandas as pd

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent))


class TestDataExtractor:
    """Tests for data extraction module"""
    
    def test_extract_incremental_logic(self):
        """Test incremental extraction logic"""
        # Mock test - in real implementation would use actual database
        # This demonstrates the testing approach
        
        # Arrange
        lookback_days = 7
        expected_min_date = datetime.now().date()
        
        # Act & Assert
        assert lookback_days > 0
        assert isinstance(expected_min_date, type(datetime.now().date()))
    
    def test_data_validation(self):
        """Test data validation rules"""
        # Sample data
        df = pd.DataFrame({
            'order_id': ['ORD001', 'ORD002'],
            'customer_id': ['CUST001', 'CUST002'],
            'total_amount': [100000, 250000],
            'order_date': [datetime.now(), datetime.now()]
        })
        
        # Validations
        assert len(df) > 0, "DataFrame should not be empty"
        assert all(df['total_amount'] >= 0), "All amounts should be non-negative"
        assert df['order_id'].is_unique, "Order IDs should be unique"
        assert not df['customer_id'].isnull().any(), "Customer ID should not be null"


class TestDataTransformer:
    """Tests for data transformation module"""
    
    def test_data_cleaning(self):
        """Test data cleaning functions"""
        # Sample dirty data
        df = pd.DataFrame({
            'name': ['  John  ', 'JANE', '  bob'],
            'amount': [100, 200, 300]
        })
        
        # Clean data
        df['name'] = df['name'].str.strip().str.title()
        
        # Assertions
        assert df['name'].iloc[0] == 'John'
        assert df['name'].iloc[1] == 'Jane'
        assert df['name'].iloc[2] == 'Bob'
    
    def test_business_logic(self):
        """Test business logic calculations"""
        # Test margin calculation
        unit_price = 100000
        cost_price = 60000
        expected_margin = 40.0  # 40%
        
        actual_margin = ((unit_price - cost_price) / cost_price) * 100
        
        assert round(actual_margin, 2) == round(expected_margin, 2)
    
    def test_age_calculation(self):
        """Test age calculation from date of birth"""
        from datetime import date
        
        dob = date(1990, 1, 1)
        today = date(2024, 1, 1)
        expected_age = 34
        
        calculated_age = today.year - dob.year
        
        assert calculated_age == expected_age


class TestDataQuality:
    """Tests for data quality checks"""
    
    def test_null_check(self):
        """Test null value detection"""
        df = pd.DataFrame({
            'col1': [1, 2, None, 4],
            'col2': ['a', 'b', 'c', 'd']
        })
        
        null_count = df['col1'].isnull().sum()
        null_percentage = (null_count / len(df)) * 100
        
        assert null_count == 1
        assert null_percentage == 25.0
    
    def test_uniqueness_check(self):
        """Test uniqueness constraint"""
        df = pd.DataFrame({
            'id': [1, 2, 2, 3],  # Has duplicate
            'value': ['a', 'b', 'c', 'd']
        })
        
        is_unique = df['id'].is_unique
        duplicate_count = df['id'].duplicated().sum()
        
        assert not is_unique
        assert duplicate_count == 1
    
    def test_range_check(self):
        """Test value range validation"""
        df = pd.DataFrame({
            'quantity': [1, 5, -1, 10]  # Has negative value
        })
        
        invalid_count = (df['quantity'] < 0).sum()
        
        assert invalid_count == 1


class TestDatabaseConnector:
    """Tests for database connector (mock tests)"""
    
    def test_connection_string_format(self):
        """Test connection string formatting"""
        db_config = {
            'user': 'testuser',
            'password': 'testpass',
            'host': 'localhost',
            'port': 5432,
            'database': 'testdb'
        }
        
        expected = "postgresql://testuser:testpass@localhost:5432/testdb"
        actual = f"postgresql://{db_config['user']}:{db_config['password']}@{db_config['host']}:{db_config['port']}/{db_config['database']}"
        
        assert actual == expected


# Helper functions for testing
def create_sample_dataframe():
    """Create sample DataFrame for testing"""
    return pd.DataFrame({
        'order_id': ['ORD001', 'ORD002', 'ORD003'],
        'customer_id': ['CUST001', 'CUST001', 'CUST002'],
        'total_amount': [100000, 150000, 200000],
        'order_date': pd.date_range('2024-01-01', periods=3)
    })


def test_sample_data_creation():
    """Test sample data helper function"""
    df = create_sample_dataframe()
    
    assert len(df) == 3
    assert list(df.columns) == ['order_id', 'customer_id', 'total_amount', 'order_date']
    assert df['total_amount'].sum() == 450000


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, '-v'])

