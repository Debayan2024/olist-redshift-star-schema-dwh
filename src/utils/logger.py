"""
Logging Configuration
Centralized logging setup for the project
"""

import os
import logging
from datetime import datetime
from pathlib import Path


def setup_logger(name: str, log_level: str = None) -> logging.Logger:
    """
    Setup and configure logger
    
    Args:
        name: Logger name (usually __name__)
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        
    Returns:
        Configured logger instance
    """
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Get log level from environment or parameter
    level = log_level or os.getenv('LOG_LEVEL', 'INFO')
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, level.upper()))
    
    # Prevent duplicate handlers
    if logger.handlers:
        return logger
    
    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(simple_formatter)
    logger.addHandler(console_handler)
    
    # File handler - daily rotating
    today = datetime.now().strftime('%Y%m%d')
    file_handler = logging.FileHandler(
        log_dir / f'etl_pipeline_{today}.log',
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(detailed_formatter)
    logger.addHandler(file_handler)
    
    # Error file handler
    error_handler = logging.FileHandler(
        log_dir / f'errors_{today}.log',
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(detailed_formatter)
    logger.addHandler(error_handler)
    
    return logger


class ETLLogger:
    """
    Enhanced logger for ETL pipelines with metrics tracking
    """
    
    def __init__(self, pipeline_name: str):
        self.pipeline_name = pipeline_name
        self.logger = setup_logger(pipeline_name)
        self.start_time = None
        self.metrics = {}
        
    def start_pipeline(self):
        """Log pipeline start"""
        self.start_time = datetime.now()
        self.logger.info(f"=" * 80)
        self.logger.info(f"Starting pipeline: {self.pipeline_name}")
        self.logger.info(f"Start time: {self.start_time}")
        self.logger.info(f"=" * 80)
        
    def end_pipeline(self, status: str = "SUCCESS"):
        """Log pipeline end with duration"""
        end_time = datetime.now()
        duration = (end_time - self.start_time).total_seconds()
        
        self.logger.info(f"=" * 80)
        self.logger.info(f"Pipeline: {self.pipeline_name} - Status: {status}")
        self.logger.info(f"End time: {end_time}")
        self.logger.info(f"Duration: {duration:.2f} seconds")
        
        if self.metrics:
            self.logger.info(f"Metrics: {self.metrics}")
        
        self.logger.info(f"=" * 80)
        
    def log_stage(self, stage_name: str, message: str):
        """Log ETL stage"""
        self.logger.info(f"[{stage_name}] {message}")
        
    def log_metric(self, metric_name: str, value):
        """Track and log metric"""
        self.metrics[metric_name] = value
        self.logger.info(f"Metric - {metric_name}: {value}")
        
    def log_data_quality(self, check_name: str, passed: bool, details: str = ""):
        """Log data quality check result"""
        status = "PASSED" if passed else "FAILED"
        level = logging.INFO if passed else logging.WARNING
        self.logger.log(level, f"[DATA QUALITY] {check_name}: {status} - {details}")

