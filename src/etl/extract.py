"""
Extract Module
Extracts data from source systems and loads into staging layer
"""

import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pandas as pd
import yaml

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.utils.db_connector import get_db_connector
from src.utils.logger import ETLLogger


class DataExtractor:
    """
    Extract data from various sources into staging layer
    """
    
    def __init__(self, config_path: str = "config/pipeline_config.yaml"):
        """Initialize data extractor"""
        self.logger = ETLLogger("DataExtractor")
        self.db = get_db_connector()
        self.config = self._load_config(config_path)
        
    def _load_config(self, config_path: str) -> Dict:
        """Load pipeline configuration"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def extract_incremental(self, table_name: str, 
                           incremental_column: str = 'updated_at',
                           lookback_days: int = 7) -> pd.DataFrame:
        """
        Extract data incrementally based on timestamp column
        
        Args:
            table_name: Source table name
            incremental_column: Column to use for incremental logic
            lookback_days: Number of days to look back
            
        Returns:
            pandas DataFrame with extracted data
        """
        self.logger.log_stage("EXTRACT", f"Extracting {table_name} (incremental)")
        
        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=lookback_days)
        
        # Build query
        query = f"""
            SELECT *
            FROM {table_name}
            WHERE {incremental_column} >= '{cutoff_date}'
            ORDER BY {incremental_column}
        """
        
        try:
            df = self.db.read_sql(query, db_name='source_db')
            self.logger.log_metric(f"{table_name}_rows_extracted", len(df))
            self.logger.log_stage("EXTRACT", f"Extracted {len(df)} rows from {table_name}")
            return df
        except Exception as e:
            self.logger.logger.error(f"Failed to extract {table_name}: {e}")
            raise
    
    def extract_full(self, table_name: str) -> pd.DataFrame:
        """
        Extract full table data
        
        Args:
            table_name: Source table name
            
        Returns:
            pandas DataFrame with extracted data
        """
        self.logger.log_stage("EXTRACT", f"Extracting {table_name} (full)")
        
        query = f"SELECT * FROM {table_name}"
        
        try:
            df = self.db.read_sql(query, db_name='source_db')
            self.logger.log_metric(f"{table_name}_rows_extracted", len(df))
            self.logger.log_stage("EXTRACT", f"Extracted {len(df)} rows from {table_name}")
            return df
        except Exception as e:
            self.logger.logger.error(f"Failed to extract {table_name}: {e}")
            raise
    
    def load_to_staging(self, df: pd.DataFrame, table_name: str,
                       truncate: bool = False):
        """
        Load extracted data to staging layer
        
        Args:
            df: DataFrame to load
            table_name: Staging table name
            truncate: Whether to truncate table before loading
        """
        self.logger.log_stage("LOAD_STAGING", f"Loading to staging.{table_name}")
        
        try:
            # Add load timestamp
            df['load_timestamp'] = datetime.now()
            df['source_system'] = 'source_db'
            
            # Truncate if requested
            if truncate:
                self.db.execute_query(
                    f"TRUNCATE TABLE staging.{table_name}",
                    db_name='data_warehouse'
                )
                self.logger.log_stage("LOAD_STAGING", f"Truncated staging.{table_name}")
            
            # Load data
            self.db.write_dataframe(
                df=df,
                table_name=table_name,
                schema='staging',
                if_exists='append',
                db_name='data_warehouse'
            )
            
            self.logger.log_metric(f"{table_name}_rows_loaded", len(df))
            self.logger.log_stage("LOAD_STAGING", 
                                f"Loaded {len(df)} rows to staging.{table_name}")
            
        except Exception as e:
            self.logger.logger.error(f"Failed to load to staging: {e}")
            raise
    
    def extract_and_load(self, table_name: str, strategy: str = 'incremental'):
        """
        Extract from source and load to staging in one operation
        
        Args:
            table_name: Table name
            strategy: 'incremental' or 'full'
        """
        config = self.config['etl']['extract']
        
        # Extract data
        if strategy == 'incremental':
            df = self.extract_incremental(
                table_name=table_name,
                incremental_column=config['incremental_column'],
                lookback_days=config['lookback_days']
            )
        else:
            df = self.extract_full(table_name)
        
        # Load to staging
        if not df.empty:
            self.load_to_staging(df, table_name)
        else:
            self.logger.log_stage("EXTRACT", f"No new data for {table_name}")
    
    def run_full_extraction(self):
        """Run extraction for all configured sources"""
        self.logger.start_pipeline()
        
        sources = self.config['etl']['extract']['sources']
        strategy = self.config['etl']['load']['strategy']
        
        total_rows = 0
        success_count = 0
        
        for source_table in sources:
            try:
                self.extract_and_load(source_table, strategy=strategy)
                success_count += 1
            except Exception as e:
                self.logger.logger.error(f"Failed to process {source_table}: {e}")
        
        self.logger.log_metric("tables_processed", success_count)
        self.logger.log_metric("tables_failed", len(sources) - success_count)
        
        status = "SUCCESS" if success_count == len(sources) else "PARTIAL_SUCCESS"
        self.logger.end_pipeline(status=status)


def main():
    """Main execution function"""
    print("=" * 80)
    print("EXTRACT: Starting data extraction process")
    print("=" * 80)
    
    extractor = DataExtractor()
    extractor.run_full_extraction()
    
    print("\n" + "=" * 80)
    print("EXTRACT: Data extraction completed")
    print("=" * 80)


if __name__ == "__main__":
    main()

