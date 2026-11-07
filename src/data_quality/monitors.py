"""
Data Quality Monitors
Monitor pipeline health, performance, and anomalies
"""

import sys
from pathlib import Path
from typing import Dict, List
from datetime import datetime, timedelta
import pandas as pd
import yaml

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from src.utils.db_connector import get_db_connector
from src.utils.logger import ETLLogger


class PipelineMonitor:
    """
    Monitor data pipeline health and performance
    """
    
    def __init__(self, config_path: str = "config/pipeline_config.yaml"):
        """Initialize pipeline monitor"""
        self.logger = ETLLogger("PipelineMonitor")
        self.db = get_db_connector()
        self.config = self._load_config(config_path)
        
    def _load_config(self, config_path: str) -> Dict:
        """Load pipeline configuration"""
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def check_data_freshness(self, table_name: str, schema: str,
                            timestamp_column: str = 'dw_created_at',
                            max_age_hours: int = 24) -> Dict:
        """
        Check if data is fresh
        
        Args:
            table_name: Table name
            schema: Schema name
            timestamp_column: Column with timestamp
            max_age_hours: Maximum allowed age in hours
            
        Returns:
            Dict with check results
        """
        query = f"""
            SELECT 
                MAX({timestamp_column}) as latest_timestamp,
                COUNT(*) as total_rows,
                EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - MAX({timestamp_column})))/3600 as age_hours
            FROM {schema}.{table_name}
        """
        
        try:
            result = self.db.execute_query(query, db_name='data_warehouse', fetch=True)
            if result and result[0][0]:
                latest_ts, row_count, age_hours = result[0]
                
                is_fresh = age_hours <= max_age_hours
                
                return {
                    'table': f"{schema}.{table_name}",
                    'latest_timestamp': latest_ts,
                    'age_hours': round(age_hours, 2),
                    'max_age_hours': max_age_hours,
                    'is_fresh': is_fresh,
                    'total_rows': row_count
                }
            else:
                return {
                    'table': f"{schema}.{table_name}",
                    'is_fresh': False,
                    'error': 'No data found'
                }
                
        except Exception as e:
            return {
                'table': f"{schema}.{table_name}",
                'is_fresh': False,
                'error': str(e)
            }
    
    def check_data_volume_anomaly(self, table_name: str, schema: str,
                                  date_column: str = 'order_date',
                                  anomaly_threshold: float = 0.5) -> Dict:
        """
        Detect anomalies in data volume
        
        Args:
            table_name: Table name
            schema: Schema name
            date_column: Date column for grouping
            anomaly_threshold: Threshold for anomaly detection (0.5 = 50% deviation)
            
        Returns:
            Dict with anomaly check results
        """
        query = f"""
            WITH daily_counts AS (
                SELECT 
                    DATE({date_column}) as date,
                    COUNT(*) as row_count
                FROM {schema}.{table_name}
                WHERE {date_column} >= CURRENT_DATE - INTERVAL '7 days'
                GROUP BY DATE({date_column})
            ),
            stats AS (
                SELECT 
                    AVG(row_count) as avg_count,
                    STDDEV(row_count) as stddev_count
                FROM daily_counts
            )
            SELECT 
                dc.date,
                dc.row_count,
                s.avg_count,
                s.stddev_count,
                ABS(dc.row_count - s.avg_count) / NULLIF(s.avg_count, 0) as deviation_ratio
            FROM daily_counts dc
            CROSS JOIN stats s
            ORDER BY dc.date DESC
            LIMIT 1
        """
        
        try:
            result = self.db.execute_query(query, db_name='data_warehouse', fetch=True)
            if result and result[0]:
                date, count, avg, stddev, deviation = result[0]
                
                has_anomaly = deviation > anomaly_threshold if deviation else False
                
                return {
                    'table': f"{schema}.{table_name}",
                    'date': date,
                    'row_count': count,
                    'average': round(avg, 2) if avg else 0,
                    'deviation_ratio': round(deviation, 2) if deviation else 0,
                    'threshold': anomaly_threshold,
                    'has_anomaly': has_anomaly
                }
            else:
                return {
                    'table': f"{schema}.{table_name}",
                    'has_anomaly': False,
                    'error': 'Insufficient data for analysis'
                }
                
        except Exception as e:
            return {
                'table': f"{schema}.{table_name}",
                'has_anomaly': False,
                'error': str(e)
            }
    
    def get_table_statistics(self, table_name: str, schema: str) -> Dict:
        """
        Get comprehensive table statistics
        
        Args:
            table_name: Table name
            schema: Schema name
            
        Returns:
            Dict with table statistics
        """
        query = f"""
            SELECT 
                COUNT(*) as row_count,
                pg_size_pretty(pg_total_relation_size('{schema}.{table_name}')) as total_size,
                pg_size_pretty(pg_relation_size('{schema}.{table_name}')) as table_size,
                pg_size_pretty(pg_indexes_size('{schema}.{table_name}')) as indexes_size
        """
        
        try:
            result = self.db.execute_query(query, db_name='data_warehouse', fetch=True)
            if result:
                row_count, total_size, table_size, index_size = result[0]
                
                return {
                    'table': f"{schema}.{table_name}",
                    'row_count': row_count,
                    'total_size': total_size,
                    'table_size': table_size,
                    'indexes_size': index_size
                }
            else:
                return {'table': f"{schema}.{table_name}", 'error': 'No stats available'}
                
        except Exception as e:
            return {'table': f"{schema}.{table_name}", 'error': str(e)}
    
    def get_pipeline_health_report(self) -> Dict:
        """
        Generate comprehensive pipeline health report
        
        Returns:
            Dict with pipeline health metrics
        """
        self.logger.log_stage("MONITOR", "Generating pipeline health report")
        
        report = {
            'timestamp': datetime.now().isoformat(),
            'freshness_checks': [],
            'volume_anomalies': [],
            'table_statistics': [],
            'overall_health': 'HEALTHY'
        }
        
        # Tables to monitor
        tables_to_check = [
            ('staging', 'orders'),
            ('core', 'orders'),
            ('analytics', 'fact_orders')
        ]
        
        # Freshness checks
        for schema, table in tables_to_check:
            freshness = self.check_data_freshness(table, schema)
            report['freshness_checks'].append(freshness)
            
            if not freshness.get('is_fresh', False):
                report['overall_health'] = 'WARNING'
        
        # Volume anomaly detection
        for schema, table in [('core', 'orders')]:
            anomaly = self.check_data_volume_anomaly(table, schema)
            report['volume_anomalies'].append(anomaly)
            
            if anomaly.get('has_anomaly', False):
                report['overall_health'] = 'WARNING'
        
        # Table statistics
        for schema, table in tables_to_check:
            stats = self.get_table_statistics(table, schema)
            report['table_statistics'].append(stats)
        
        self.logger.log_metric("pipeline_health", report['overall_health'])
        
        return report
    
    def print_health_report(self, report: Dict):
        """Print formatted health report"""
        print("\n" + "=" * 80)
        print(f"PIPELINE HEALTH REPORT - {report['timestamp']}")
        print("=" * 80)
        
        print(f"\nOverall Health: {report['overall_health']}")
        
        print("\n--- Data Freshness ---")
        for check in report['freshness_checks']:
            status = "✓" if check.get('is_fresh') else "✗"
            table = check.get('table')
            age = check.get('age_hours', 'N/A')
            print(f"{status} {table}: {age} hours old")
        
        print("\n--- Volume Anomalies ---")
        for check in report['volume_anomalies']:
            status = "!" if check.get('has_anomaly') else "✓"
            table = check.get('table')
            deviation = check.get('deviation_ratio', 'N/A')
            print(f"{status} {table}: {deviation}x deviation")
        
        print("\n--- Table Statistics ---")
        for stats in report['table_statistics']:
            table = stats.get('table')
            rows = stats.get('row_count', 'N/A')
            size = stats.get('total_size', 'N/A')
            print(f"  {table}: {rows} rows, {size}")
        
        print("\n" + "=" * 80)


def main():
    """Main execution function"""
    print("=" * 80)
    print("MONITOR: Starting pipeline health monitoring")
    print("=" * 80)
    
    monitor = PipelineMonitor()
    report = monitor.get_pipeline_health_report()
    monitor.print_health_report(report)
    
    print("\nMONITOR: Health check completed")
    print("=" * 80)


if __name__ == "__main__":
    main()

