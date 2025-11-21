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
        
        # API keys: reduce noise; do not warn globally here
        # Model-specific checks will occur at call time
        
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
        """Get API keys with environment variable fallback (explicit mapping)"""
        api_keys = dict(config.get('api_keys', {}))
        mapping = {
            'GITHUB_TOKEN': 'github_token',
            'GLM_API_KEY': 'glm_api_key',
            'MINIMAX_API_KEY': 'minimax_api_key',
            'OPENROUTER_API_KEY': 'openrouter_api_key',
            'GOOGLE_SEARCH_KEY': 'google_search_key',
        }
        for env_name, cfg_key in mapping.items():
            val = os.getenv(env_name)
            if val and not api_keys.get(cfg_key):
                api_keys[cfg_key] = val
        return api_keys