"""
Logging Setup
Enhanced logging configuration for the new architecture
"""

import os
import logging
import sys
from pathlib import Path
from typing import Optional

def setup_logging(level: str | int = "INFO", log_file: Optional[str] = None, 
                 log_format: Optional[str] = None) -> None:
    """Setup enhanced logging configuration"""
    
    # Default log format
    if not log_format:
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Create logs directory if it doesn't exist
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        log_path = Path("logs/system.log")
        log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure root logger
    resolved_level = level
    if isinstance(level, str):
        resolved_level = getattr(logging, level.upper(), logging.INFO)
    elif isinstance(level, int):
        resolved_level = level
    else:
        resolved_level = logging.INFO
    logging.basicConfig(
        level=resolved_level,
        format=log_format,
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    # Set specific logger levels for different components
    loggers = {
        'src': logging.getLogger('src'),
        'storage': logging.getLogger('storage'),
        'orchestration': logging.getLogger('orchestration'),
        'agents': logging.getLogger('agents'),
        'models': logging.getLogger('models'),
        'utils': logging.getLogger('utils')
    }
    
    # Configure component-specific loggers
    for name, logger in loggers.items():
        logger.setLevel(resolved_level)
    
    # Add console colors for different levels
    if sys.stdout.isatty():
        from logging import StreamHandler, Formatter
        
        class ColoredFormatter(Formatter):
            """Colored log formatter for console output"""
            
            COLORS = {
                'DEBUG': '\033[36m',    # Cyan
                'INFO': '\033[32m',     # Green
                'WARNING': '\033[33m',  # Yellow
                'ERROR': '\033[31m',     # Red
                'CRITICAL': '\033[35m',  # Magenta
                'RESET': '\033[0m'      # Reset
            }
            
            def format(self, record):
                log_color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
                record.levelname = f"{log_color}{record.levelname}{self.COLORS['RESET']}"
                return super().format(record)
        
        # Apply colored formatter to console handler
        for handler in logging.root.handlers:
            if isinstance(handler, StreamHandler) and hasattr(handler, 'stream') and handler.stream.isatty():
                handler.setFormatter(ColoredFormatter(log_format))
    
    # Log initialization
    main_logger = logging.getLogger(__name__)
    main_logger.info(f"Logging initialized at level: {resolved_level}")
    if log_file:
        main_logger.info(f"Log file: {log_path}")