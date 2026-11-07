"""
Database Connection Manager
Handles PostgreSQL connections with connection pooling
"""

import os
import yaml
import psycopg2
from psycopg2 import pool
from sqlalchemy import create_engine
from contextlib import contextmanager
from typing import Dict, Optional, Generator
import pandas as pd
from .logger import setup_logger


class DatabaseConnector:
    """
    Database connection manager with connection pooling
    Supports both psycopg2 and SQLAlchemy connections
    """
    
    def __init__(self, config_path: str = "config/database_config.yaml"):
        """
        Initialize database connector
        
        Args:
            config_path: Path to database configuration file
        """
        self.logger = setup_logger(__name__)
        self.config = self._load_config(config_path)
        self.connection_pools: Dict[str, pool.ThreadedConnectionPool] = {}
        self.engines: Dict[str, create_engine] = {}
        
    def _load_config(self, config_path: str) -> Dict:
        """Load database configuration from YAML file"""
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            
            # Override with environment variables if available
            for db_name in ['source_db', 'data_warehouse']:
                if db_name in config:
                    config[db_name]['host'] = os.getenv('DB_HOST', config[db_name]['host'])
                    config[db_name]['user'] = os.getenv('DB_USER', config[db_name]['user'])
                    config[db_name]['password'] = os.getenv('DB_PASSWORD', config[db_name]['password'])
            
            return config
        except Exception as e:
            self.logger.error(f"Failed to load config: {e}")
            raise
    
    def _get_connection_string(self, db_config: Dict) -> str:
        """Build PostgreSQL connection string"""
        return (
            f"postgresql://{db_config['user']}:{db_config['password']}"
            f"@{db_config['host']}:{db_config['port']}/{db_config['database']}"
        )
    
    def get_connection_pool(self, db_name: str = 'data_warehouse') -> pool.ThreadedConnectionPool:
        """
        Get or create connection pool for specified database
        
        Args:
            db_name: Database name ('source_db' or 'data_warehouse')
        
        Returns:
            ThreadedConnectionPool instance
        """
        if db_name not in self.connection_pools:
            db_config = self.config[db_name]
            pool_config = self.config.get('connection_pool', {})
            
            try:
                self.connection_pools[db_name] = pool.ThreadedConnectionPool(
                    minconn=pool_config.get('min_connections', 2),
                    maxconn=pool_config.get('max_connections', 10),
                    host=db_config['host'],
                    port=db_config['port'],
                    database=db_config['database'],
                    user=db_config['user'],
                    password=db_config['password']
                )
                self.logger.info(f"Connection pool created for {db_name}")
            except Exception as e:
                self.logger.error(f"Failed to create connection pool: {e}")
                raise
        
        return self.connection_pools[db_name]
    
    @contextmanager
    def get_connection(self, db_name: str = 'data_warehouse') -> Generator:
        """
        Context manager for database connections
        
        Args:
            db_name: Database name
            
        Yields:
            Database connection
        """
        conn_pool = self.get_connection_pool(db_name)
        conn = conn_pool.getconn()
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            self.logger.error(f"Database error: {e}")
            raise
        finally:
            conn_pool.putconn(conn)
    
    def get_engine(self, db_name: str = 'data_warehouse'):
        """
        Get SQLAlchemy engine for specified database
        
        Args:
            db_name: Database name
            
        Returns:
            SQLAlchemy engine
        """
        if db_name not in self.engines:
            db_config = self.config[db_name]
            connection_string = self._get_connection_string(db_config)
            
            try:
                self.engines[db_name] = create_engine(
                    connection_string,
                    pool_size=10,
                    max_overflow=20,
                    pool_pre_ping=True
                )
                self.logger.info(f"SQLAlchemy engine created for {db_name}")
            except Exception as e:
                self.logger.error(f"Failed to create engine: {e}")
                raise
        
        return self.engines[db_name]
    
    def execute_query(self, query: str, params: Optional[tuple] = None, 
                     db_name: str = 'data_warehouse', fetch: bool = False):
        """
        Execute SQL query
        
        Args:
            query: SQL query string
            params: Query parameters
            db_name: Database name
            fetch: Whether to fetch results
            
        Returns:
            Query results if fetch=True, else None
        """
        with self.get_connection(db_name) as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, params)
                if fetch:
                    return cursor.fetchall()
                return None
    
    def execute_sql_file(self, file_path: str, db_name: str = 'data_warehouse'):
        """
        Execute SQL from file
        
        Args:
            file_path: Path to SQL file
            db_name: Database name
        """
        self.logger.info(f"Executing SQL file: {file_path}")
        
        with open(file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        with self.get_connection(db_name) as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql_content)
        
        self.logger.info(f"Successfully executed {file_path}")
    
    def read_sql(self, query: str, db_name: str = 'data_warehouse') -> pd.DataFrame:
        """
        Read SQL query into pandas DataFrame
        
        Args:
            query: SQL query
            db_name: Database name
            
        Returns:
            pandas DataFrame
        """
        engine = self.get_engine(db_name)
        return pd.read_sql(query, engine)
    
    def write_dataframe(self, df: pd.DataFrame, table_name: str, 
                       schema: str = 'staging', if_exists: str = 'append',
                       db_name: str = 'data_warehouse', chunk_size: int = 10000):
        """
        Write pandas DataFrame to database
        
        Args:
            df: pandas DataFrame
            table_name: Target table name
            schema: Database schema
            if_exists: What to do if table exists ('fail', 'replace', 'append')
            db_name: Database name
            chunk_size: Number of rows per batch
        """
        engine = self.get_engine(db_name)
        
        self.logger.info(f"Writing {len(df)} rows to {schema}.{table_name}")
        
        df.to_sql(
            name=table_name,
            con=engine,
            schema=schema,
            if_exists=if_exists,
            index=False,
            chunksize=chunk_size,
            method='multi'
        )
        
        self.logger.info(f"Successfully wrote data to {schema}.{table_name}")
    
    def get_table_row_count(self, table_name: str, schema: str = 'staging',
                           db_name: str = 'data_warehouse') -> int:
        """
        Get row count for a table
        
        Args:
            table_name: Table name
            schema: Schema name
            db_name: Database name
            
        Returns:
            Row count
        """
        query = f"SELECT COUNT(*) FROM {schema}.{table_name}"
        result = self.execute_query(query, db_name=db_name, fetch=True)
        return result[0][0] if result else 0
    
    def close_all(self):
        """Close all connection pools and engines"""
        for pool_name, conn_pool in self.connection_pools.items():
            conn_pool.closeall()
            self.logger.info(f"Closed connection pool: {pool_name}")
        
        for engine_name, engine in self.engines.items():
            engine.dispose()
            self.logger.info(f"Disposed engine: {engine_name}")


# Singleton instance
_db_connector = None

def get_db_connector() -> DatabaseConnector:
    """Get singleton database connector instance"""
    global _db_connector
    if _db_connector is None:
        _db_connector = DatabaseConnector()
    return _db_connector

