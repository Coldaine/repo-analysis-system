"""
Configuration Validation
Enhanced validation utilities for system configuration
"""

import re
from typing import Dict, Any, List, Optional

def validate_config(config: Dict[str, Any]) -> Dict[str, Any]:
    """Validate system configuration and return validation results"""
    errors = []
    warnings = []
    
    # Validate database configuration
    db_validation = validate_database_config(config.get('database', {}))
    errors.extend(db_validation['errors'])
    warnings.extend(db_validation['warnings'])
    
    # Validate API keys
    api_validation = validate_api_keys(config.get('api_keys', {}))
    errors.extend(api_validation['errors'])
    warnings.extend(api_validation['warnings'])
    
    # Validate models
    model_validation = validate_models(config.get('models', {}))
    errors.extend(model_validation['errors'])
    warnings.extend(model_validation['warnings'])
    
    # Validate orchestration
    orch_validation = validate_orchestration(config.get('orchestration', {}))
    errors.extend(orch_validation['errors'])
    warnings.extend(orch_validation['warnings'])
    
    return {
        'valid': len(errors) == 0,
        'errors': errors,
        'warnings': warnings
    }

def validate_database_config(db_config: Dict[str, Any]) -> Dict[str, Any]:
    """Validate database configuration"""
    errors = []
    warnings = []
    
    required_fields = ['type', 'host', 'port', 'name', 'user']
    for field in required_fields:
        if field not in db_config:
            errors.append(f"Database missing required field: {field}")
    
    if db_config.get('type') != 'postgresql':
        warnings.append("Only PostgreSQL is supported in this version")
    
    # Validate port
    port = db_config.get('port')
    if port and (not isinstance(port, int) or port < 1 or port > 65535):
        errors.append(f"Invalid port number: {port}")
    
    # Validate pool size
    pool_size = db_config.get('pool_size')
    if pool_size and (not isinstance(pool_size, int) or pool_size < 1 or pool_size > 100):
        warnings.append(f"Pool size should be between 1-100, got: {pool_size}")
    
    return {
        'errors': errors,
        'warnings': warnings
    }

def validate_api_keys(api_keys: Dict[str, str]) -> Dict[str, Any]:
    """Validate API keys configuration"""
    errors = []
    warnings = []
    
    # Check for required keys
    required_patterns = ['github', 'glm']
    for pattern in required_patterns:
        if not any(key.startswith(pattern) for key in api_keys.keys()):
            warnings.append(f"Missing API key pattern: {pattern}_*")
    
    # Validate key formats
    for key, value in api_keys.items():
        if value and not value.startswith('${') and len(value) < 10:
            warnings.append(f"API key '{key}' appears to be missing or too short")
    
    return {
        'errors': errors,
        'warnings': warnings
    }

def validate_models(models: Dict[str, Any]) -> Dict[str, Any]:
    """Validate model configuration"""
    errors = []
    warnings = []
    
    for model_name, model_config in models.items():
        if not isinstance(model_config, dict):
            errors.append(f"Model '{model_name}' configuration must be a dictionary")
            continue
        
        # Check required fields
        if 'model' not in model_config:
            errors.append(f"Model '{model_name}' missing required 'model' field")
        
        # Validate temperature
        temp = model_config.get('temperature')
        if temp is not None and (not isinstance(temp, (int, float)) or temp < 0 or temp > 2):
            warnings.append(f"Model '{model_name}' temperature should be 0-2, got: {temp}")
        
        # Validate max_tokens
        max_tokens = model_config.get('max_tokens')
        if max_tokens and (not isinstance(max_tokens, int) or max_tokens < 1 or max_tokens > 32000):
            warnings.append(f"Model '{model_name}' max_tokens should be 1-32000, got: {max_tokens}")
    
    return {
        'errors': errors,
        'warnings': warnings
    }

def validate_orchestration(orch_config: Dict[str, Any]) -> Dict[str, Any]:
    """Validate orchestration configuration"""
    errors = []
    warnings = []
    
    # Validate concurrent runs
    max_concurrent = orch_config.get('max_concurrent_runs')
    if max_concurrent and (not isinstance(max_concurrent, int) or max_concurrent < 1 or max_concurrent > 20):
        warnings.append(f"max_concurrent_runs should be 1-20, got: {max_concurrent}")
    
    # Validate timeout
    timeout = orch_config.get('timeout_seconds')
    if timeout and (not isinstance(timeout, (int, float)) or timeout < 60 or timeout > 7200):
        warnings.append(f"timeout_seconds should be 60-7200, got: {timeout}")
    
    # Validate retry attempts
    retry_attempts = orch_config.get('retry_attempts')
    if retry_attempts and (not isinstance(retry_attempts, int) or retry_attempts < 1 or retry_attempts > 10):
        warnings.append(f"retry_attempts should be 1-10, got: {retry_attempts}")
    
    return {
        'errors': errors,
        'warnings': warnings
    }

def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_url(url: str) -> bool:
    """Validate URL format"""
    pattern = r'^https?://(?:[-\w.]*)+(?:\.[a-zA-Z]{2,})$'
    return re.match(pattern, url) is not None

def validate_repository_name(name: str) -> bool:
    """Validate repository name format"""
    if not name or len(name) < 1 or len(name) > 100:
        return False
    
    # Check for invalid characters
    invalid_chars = ['<', '>', '|', '&', ';', ':', '"', '\\', '/', '?', '*']
    if any(char in name for char in invalid_chars):
        return False
    
    return True

def validate_github_token(token: str) -> bool:
    """Validate GitHub token format"""
    if not token:
        return False
    
    # GitHub tokens start with specific patterns
    valid_patterns = ['ghp_', 'gho_', 'ghu_', 'ghs_', 'github_pat_']
    return any(token.startswith(pattern) for pattern in valid_patterns) and len(token) >= 10