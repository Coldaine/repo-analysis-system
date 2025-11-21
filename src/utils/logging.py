"""
Enhanced Logging System for Repository Analysis System
Provides structured logging with correlation IDs, async support, security sanitization,
and performance metrics using Loguru framework.
"""

import os
import sys
import time
import uuid
import json
import asyncio
import logging
import threading
import re
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from contextlib import contextmanager
from functools import wraps
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

try:
    from loguru import logger as loguru_logger
    LOGURU_AVAILABLE = True
except ImportError:
    LOGURU_AVAILABLE = False
    import logging

# Security-sensitive patterns to sanitize
SENSITIVE_PATTERNS = [
    r'(?i)(api[_-]?key|apikey)\s*[:=]\s*["\']?([a-zA-Z0-9_-]{20,})["\']?',
    r'(?i)(token|access[_-]?token)\s*[:=]\s*["\']?([a-zA-Z0-9_-]{20,})["\']?',
    r'(?i)(password|pwd)\s*[:=]\s*["\']?([^"\']+)["\']?',
    r'(?i)(secret|private[_-]?key)\s*[:=]\s*["\']?([a-zA-Z0-9_-]{20,})["\']?',
    r'(?i)(github[_-]?token)\s*[:=]\s*["\']?([a-zA-Z0-9_-]{20,})["\']?',
    r'(?i)(glm[_-]?api[_-]?key)\s*[:=]\s*["\']?([a-zA-Z0-9_-]{20,})["\']?',
    r'(?i)(minimax[_-]?api[_-]?key)\s*[:=]\s*["\']?([a-zA-Z0-9_-]{20,})["\']?',
]

class CorrelationContext:
    """Manages correlation IDs for request tracing"""
    
    def __init__(self):
        self._local = threading.local()
    
    def get_correlation_id(self) -> str:
        """Get current correlation ID or generate new one"""
        if hasattr(self._local, 'correlation_id'):
            return self._local.correlation_id
        correlation_id = str(uuid.uuid4())
        self._local.correlation_id = correlation_id
        return correlation_id
    
    def set_correlation_id(self, correlation_id: str):
        """Set correlation ID for current context"""
        self._local.correlation_id = correlation_id
    
    def clear(self):
        """Clear current correlation context"""
        if hasattr(self._local, 'correlation_id'):
            delattr(self._local, 'correlation_id')

class SecuritySanitizer:
    """Sanitizes sensitive data from log messages"""
    
    def __init__(self):
        self.patterns = [re.compile(pattern) for pattern in SENSITIVE_PATTERNS]
    
    def sanitize(self, message: str) -> str:
        """Remove sensitive information from log message"""
        sanitized = message
        for pattern in self.patterns:
            sanitized = pattern.sub(r'\1="[REDACTED]"', sanitized)
        return sanitized
    
    def sanitize_dict(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize sensitive data in dictionary"""
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, dict):
                sanitized[key] = self.sanitize_dict(value)
            elif isinstance(key, str) and any(sensitive in key.lower() for sensitive in 
                                           ['api_key', 'apikey', 'token', 'password', 'secret']):
                sanitized[key] = '[REDACTED]'
            else:
                sanitized[key] = value
        return sanitized

class PerformanceMetrics:
    """Tracks performance metrics for logging"""
    
    def __init__(self):
        self.metrics = {}
        self.start_times = {}
    
    @contextmanager
    def timer(self, operation: str, correlation_id: str = None):
        """Context manager for timing operations"""
        start_time = time.time()
        timer_id = f"{operation}_{correlation_id or 'default'}"
        self.start_times[timer_id] = start_time
        
        try:
            yield
        finally:
            duration = time.time() - start_time
            if operation not in self.metrics:
                self.metrics[operation] = []
            self.metrics[operation].append({
                'duration': duration,
                'timestamp': datetime.utcnow().isoformat(),
                'correlation_id': correlation_id
            })
            
            # Log performance metrics
            if duration > 1.0:  # Log slow operations (>1 second)
                logger.warning(
                    f"Slow operation detected",
                    extra={
                        'operation': operation,
                        'duration': duration,
                        'correlation_id': correlation_id,
                        'performance_category': 'slow_operation'
                    }
                )

class AsyncLogHandler:
    """Async logging handler to prevent blocking"""
    
    def __init__(self, max_workers: int = 4):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.queue = asyncio.Queue()
        self.running = False
    
    async def start(self):
        """Start the async logging handler"""
        self.running = True
        asyncio.create_task(self._process_logs())
    
    async def stop(self):
        """Stop the async logging handler"""
        self.running = False
        await self.queue.put(None)  # Sentinel to stop processing
        self.executor.shutdown(wait=True)
    
    async def _process_logs(self):
        """Process logs from the queue"""
        while self.running:
            try:
                log_entry = await self.queue.get()
                if log_entry is None:  # Sentinel value
                    break
                
                # Process log entry in thread pool
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(self.executor, self._write_log, log_entry)
                
            except Exception as e:
                # Fallback to standard logging if async fails
                logging.error(f"Async log processing failed: {e}")
    
    def _write_log(self, log_entry: Dict[str, Any]):
        """Write log entry (placeholder for actual implementation)"""
        # This would be implemented based on specific logging requirements
        pass
    
    async def log_async(self, log_data: Dict[str, Any]):
        """Queue a log entry for async processing"""
        if self.running:
            await self.queue.put(log_data)

# Global instances
correlation_context = CorrelationContext()
security_sanitizer = SecuritySanitizer()
performance_metrics = PerformanceMetrics()
async_handler = AsyncLogHandler()

class StructuredLogger:
    """Enhanced structured logger with correlation IDs and security features"""
    
    def __init__(self, name: str, level: str = "INFO"):
        self.name = name
        self.level = level
        self.correlation_id = None
        
        if LOGURU_AVAILABLE:
            self.logger = loguru_logger.bind(component=name)
            self._setup_loguru()
        else:
            self.logger = logging.getLogger(name)
            self._setup_standard_logging()
    
    def _setup_loguru(self):
        """Configure Loguru for structured logging"""
        # Remove default handler
        loguru_logger.remove()
        
        # Console handler with JSON formatting for production
        loguru_logger.add(
            sys.stdout,
            format=self._json_formatter,
            level=self.level,
            serialize=True,
            backtrace=True,
            diagnose=True
        )
        
        # File handler with rotation
        log_dir = Path("logs")
        log_dir.mkdir(exist_ok=True)
        
        loguru_logger.add(
            log_dir / "system.json",
            format=self._json_formatter,
            level=self.level,
            rotation="10 MB",
            retention="30 days",
            serialize=True,
            backtrace=True,
            diagnose=True
        )
    
    def _setup_standard_logging(self):
        """Fallback to standard logging if Loguru not available"""
        handler = logging.StreamHandler(sys.stdout)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        self.logger.addHandler(handler)
        self.logger.setLevel(getattr(logging, self.level.upper()))
    
    def _json_formatter(self, record):
        """Custom JSON formatter for structured logs"""
        log_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record['level'].name if LOGURU_AVAILABLE else record.levelname,
            'message': security_sanitizer.sanitize(record['message'] if LOGURU_AVAILABLE else record.getMessage()),
            'component': self.name,
            'correlation_id': self.correlation_id or correlation_context.get_correlation_id(),
            'module': record['name'] if LOGURU_AVAILABLE else record.name,
            'function': record['function'] if LOGURU_AVAILABLE else record.funcName,
            'line': record['line'] if LOGURU_AVAILABLE else record.lineno
        }
        
        # Add extra fields
        if LOGURU_AVAILABLE and 'extra' in record:
            log_entry.update(security_sanitizer.sanitize_dict(record['extra']))
        elif hasattr(record, 'extra'):
            log_entry.update(security_sanitizer.sanitize_dict(record.extra))
        
        return json.dumps(log_entry)
    
    def bind(self, **kwargs):
        """Bind additional context to logger"""
        if LOGURU_AVAILABLE:
            self.logger = self.logger.bind(**kwargs)
        self.correlation_id = kwargs.get('correlation_id')
        return self
    
    def debug(self, message: str, **kwargs):
        """Log debug message"""
        self._log('debug', message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message"""
        self._log('info', message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message"""
        self._log('warning', message, **kwargs)
    
    def error(self, message: str, exc_info=None, **kwargs):
        """Log error message"""
        self._log('error', message, exc_info=exc_info, **kwargs)
    
    def critical(self, message: str, exc_info=None, **kwargs):
        """Log critical message"""
        self._log('critical', message, exc_info=exc_info, **kwargs)
    
    def _log(self, level: str, message: str, exc_info=None, **kwargs):
        """Internal logging method"""
        # Sanitize message
        clean_message = security_sanitizer.sanitize(message)
        
        # Add correlation ID if not present
        if 'correlation_id' not in kwargs:
            kwargs['correlation_id'] = correlation_context.get_correlation_id()
        
        # Add performance metrics if timing data available
        if 'duration' in kwargs:
            kwargs['performance_category'] = 'operation_timing'
        
        if LOGURU_AVAILABLE:
            log_method = getattr(self.logger, level)
            if exc_info:
                log_method(clean_message, exc_info=exc_info, **kwargs)
            else:
                log_method(clean_message, **kwargs)
        else:
            log_method = getattr(self.logger, level)
            if exc_info:
                log_method(clean_message, exc_info=exc_info)
            else:
                log_method(clean_message)

def get_logger(name: str, level: str = "INFO") -> StructuredLogger:
    """Get a structured logger instance"""
    return StructuredLogger(name, level)

@contextmanager
def correlation_id(cid: str = None):
    """Context manager for correlation ID"""
    old_cid = correlation_context.get_correlation_id()
    new_cid = cid or str(uuid.uuid4())
    correlation_context.set_correlation_id(new_cid)
    
    try:
        yield new_cid
    finally:
        correlation_context.set_correlation_id(old_cid)

def timer_decorator(operation: str):
    """Decorator for timing function execution"""
    def decorator(func: Callable) -> Callable:
        if asyncio.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                correlation_id = correlation_context.get_correlation_id()
                with performance_metrics.timer(operation, correlation_id):
                    logger = get_logger(func.__module__)
                    logger.info(f"Starting {operation}", extra={
                        'operation': operation,
                        'function': func.__name__,
                        'correlation_id': correlation_id
                    })
                    try:
                        result = await func(*args, **kwargs)
                        logger.info(f"Completed {operation}", extra={
                            'operation': operation,
                            'function': func.__name__,
                            'correlation_id': correlation_id,
                            'status': 'success'
                        })
                        return result
                    except Exception as e:
                        logger.error(f"Failed {operation}", exc_info=True, extra={
                            'operation': operation,
                            'function': func.__name__,
                            'correlation_id': correlation_id,
                            'status': 'failed'
                        })
                        raise
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                correlation_id = correlation_context.get_correlation_id()
                with performance_metrics.timer(operation, correlation_id):
                    logger = get_logger(func.__module__)
                    logger.info(f"Starting {operation}", extra={
                        'operation': operation,
                        'function': func.__name__,
                        'correlation_id': correlation_id
                    })
                    try:
                        result = func(*args, **kwargs)
                        logger.info(f"Completed {operation}", extra={
                            'operation': operation,
                            'function': func.__name__,
                            'correlation_id': correlation_id,
                            'status': 'success'
                        })
                        return result
                    except Exception as e:
                        logger.error(f"Failed {operation}", exc_info=True, extra={
                            'operation': operation,
                            'function': func.__name__,
                            'correlation_id': correlation_id,
                            'status': 'failed'
                        })
                        raise
            return sync_wrapper
    return decorator

def setup_logging(level: str = "INFO", log_file: Optional[str] = None, 
                enable_async: bool = True, enable_metrics: bool = True) -> None:
    """
    Setup enhanced logging configuration
    
    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional custom log file path
        enable_async: Enable async logging handlers
        enable_metrics: Enable performance metrics collection
    """
    global async_handler
    
    # Create logs directory
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
    else:
        log_path = Path("logs/system.log")
        log_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Configure global logging level
    if LOGURU_AVAILABLE:
        loguru_logger.level(level)
    else:
        logging.basicConfig(level=getattr(logging, level.upper()))
    
    # Start async handler if enabled
    if enable_async:
        asyncio.create_task(async_handler.start())
    
    # Initialize performance metrics
    if enable_metrics:
        logger = get_logger("logging_setup")
        logger.info("Enhanced logging system initialized", extra={
            'log_level': level,
            'log_file': str(log_path),
            'async_enabled': enable_async,
            'metrics_enabled': enable_metrics,
            'loguru_available': LOGURU_AVAILABLE
        })

# Create module logger
logger = get_logger(__name__)

# Export public API
__all__ = [
    'get_logger',
    'correlation_id',
    'timer_decorator',
    'setup_logging',
    'StructuredLogger',
    'correlation_context',
    'security_sanitizer',
    'performance_metrics',
    'AsyncLogHandler',
    'SecuritySanitizer',
    'PerformanceMetrics',
    'CorrelationContext'
]