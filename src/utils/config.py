"""
Configuration Loader
Enhanced configuration loading with validation and environment variable expansion
"""

import os
import yaml
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class ConfigLoader:
    """Enhanced configuration loader with validation"""
    
    def __init__(self):
        pass
    
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """Load and validate configuration from file"""
        logger.info(f"Loading configuration from: {config_path}")
        
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            # Expand environment variables
            config = self._expand_env_vars(config)
            
            # Validate configuration
            self._validate_config(config)
            
            logger.info("Configuration loaded and validated successfully")
            return config
            
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML in configuration: {e}")
            raise
        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise
    
    def _expand_env_vars(self, config: Any) -> Any:
        """Recursively expand environment variables in configuration"""
        if isinstance(config, str):
            return os.path.expandvars(config)
        elif isinstance(config, dict):
            return {k: self._expand_env_vars(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._expand_env_vars(item) for item in config]
        else:
            return config
    
    def _validate_config(self, config: Dict[str, Any]) -> None:
        """Validate configuration structure and required fields"""
        errors = []
        warnings = []
        
        # Check required sections
        required_sections = ['database', 'api_keys', 'models', 'orchestration']
        for section in required_sections:
            if section not in config:
                errors.append(f"Missing required section: {section}")
        
        # Validate database configuration
        if 'database' in config:
            db_config = config['database']
            required_db_fields = ['type', 'host', 'port', 'name', 'user']
            for field in required_db_fields:
                if field not in db_config:
                    errors.append(f"Missing database field: {field}")
            
            if db_config.get('type') != 'postgresql':
                warnings.append("Only PostgreSQL is supported in this version")
        
        # Validate API keys
        if 'api_keys' in config:
            api_keys = config['api_keys']
            for key, value in api_keys.items():
                if not value or value.startswith('${'):
                    warnings.append(f"API key '{key}' may be missing or unset")
        
        # Validate models
        if 'models' in config:
            models = config['models']
            for model_name, model_config in models.items():
                if not model_config.get('model'):
                    warnings.append(f"Model '{model_name}' missing model field")
        
        if errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(f"  - {error}" for error in errors)
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        if warnings:
            warning_msg = "Configuration warnings:\n" + "\n".join(f"  - {warning}" for warning in warnings)
            logger.warning(warning_msg)
    
    def get_database_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Get database configuration with defaults"""
        db_config = config.get('database', {})
        
        return {
            'type': db_config.get('type', 'postgresql'),
            'host': db_config.get('host', os.getenv('DB_HOST', 'localhost')),
            'port': int(db_config.get('port', os.getenv('DB_PORT', '5432'))),
            'name': db_config.get('name', os.getenv('DB_NAME', 'repo_analysis')),
            'user': db_config.get('user', os.getenv('DB_USER', 'postgres')),
            'password': db_config.get('password', os.getenv('DB_PASSWORD', '')),
            'pool_size': int(db_config.get('pool_size', 10)),
            'max_overflow': int(db_config.get('max_overflow', 20)),
            'echo': db_config.get('echo', False)
        }
    
    def get_model_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Get model configuration"""
        return config.get('models', {})
    
    def get_api_keys(self, config: Dict[str, Any]) -> Dict[str, str]:
        """Get API keys with environment variable fallback"""
        api_keys = config.get('api_keys', {})
        
        # Check environment variables for missing keys
        env_keys = ['GITHUB_TOKEN', 'GLM_API_KEY', 'MINIMAX_API_KEY', 'GOOGLE_SEARCH_KEY']
        for env_key in env_keys:
            config_key = env_key.lower().replace('_key', '_api_key')
            if config_key not in api_keys and os.getenv(env_key):
                api_keys[config_key] = os.getenv(env_key)
        
        return api_keys