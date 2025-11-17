#!/usr/bin/env python3
"""
Configuration Migration Utility
Migrates legacy config.yaml to new structure while maintaining compatibility
"""

import os
import sys
import yaml
import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

class ConfigMigrator:
    """Handles migration from legacy config.yaml to new structure"""
    
    def __init__(self, legacy_config_path: str = "config.yaml"):
        self.legacy_config_path = Path(legacy_config_path)
        self.new_config_path = Path("config/new_config.yaml")
        self.migration_log_path = Path("config/migration_log.json")
        
    def load_legacy_config(self) -> Dict[str, Any]:
        """Load the legacy configuration file"""
        if not self.legacy_config_path.exists():
            raise FileNotFoundError(f"Legacy config not found: {self.legacy_config_path}")
            
        with open(self.legacy_config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def transform_to_new_structure(self, legacy_config: Dict[str, Any]) -> Dict[str, Any]:
        """Transform legacy config to new structure"""
        new_config = {
            "version": "2.0",
            "migration": {
                "date": datetime.now().isoformat(),
                "source": "config.yaml v1.0",
                "migrated_by": "config/migration.py"
            },
            "database": {
                "type": "postgresql",
                "host": "${DB_HOST:localhost}",
                "port": "${DB_PORT:5432}",
                "name": "${DB_NAME:repo_analysis}",
                "user": "${DB_USER:postgres}",
                "password": "${DB_PASSWORD}",
                "pool_size": 10,
                "max_overflow": 20,
                "echo": False
            },
            "api_keys": legacy_config.get("api_keys", {}),
            "models": legacy_config.get("models", {}),
            "repositories": {
                **legacy_config.get("repositories", {}),
                "batch_size": 10,
                "concurrent_limit": 5
            },
            "orchestration": {
                "langgraph": {
                    "max_concurrent_runs": 5,
                    "timeout_seconds": 3600,
                    "retry_attempts": 3,
                    "retry_delay": 300
                },
                "scheduling": {
                    "default_type": "webhook",
                    "fallback_cron": "0 */6 * * *",
                    "timezone": "UTC",
                    "dormancy_audit_minutes": 30
                }
            },
            "agents": {
                **legacy_config.get("agents", {}),
                "data_collection": {
                    **legacy_config.get("agents", {}).get("data_collection", {}),
                    "batch_size": 10,
                    "timeout": 300
                },
                "pain_point_analyzer": {
                    **legacy_config.get("agents", {}).get("pain_point_analyzer", {}),
                    "primary_model": "glm_4_6",
                    "fallback_model": "minimax",
                    "confidence_threshold": 0.7
                },
                "search_agent": {
                    **legacy_config.get("agents", {}).get("search_agent", {}),
                    "search_provider": "duckduckgo",
                    "max_results": 10,
                    "timeout": 60
                },
                "visualization_agent": {
                    **legacy_config.get("agents", {}).get("visual_generator", {}),
                    "output_format": "mermaid",
                    "max_diagrams": 5,
                    "render_svg": True
                },
                "output_agent": {
                    **legacy_config.get("agents", {}).get("output_agent", {}),
                    "output_directory": "review_logging",
                    "file_prefix": "analysis-run",
                    "generate_markdown": True,
                    "generate_json": False
                }
            },
            "visualizations": legacy_config.get("visualizations", {}),
            "monitoring": {
                **legacy_config.get("monitoring", {}),
                "metrics_enabled": True,
                "health_check_interval": 60,
                "performance_tracking": True
            },
            "security": {
                **legacy_config.get("security", {}),
                "session_timeout": 3600,
                "rate_limiting": {
                    "enabled": True,
                    "requests_per_minute": 100
                }
            },
            "logging": {
                "level": legacy_config.get("error_handling", {}).get("log_level", "INFO"),
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "file": "logs/system.log",
                "max_size": "10MB",
                "backup_count": 5
            }
        }
        
        # Preserve any custom sections from legacy config
        for key, value in legacy_config.items():
            if key not in new_config and key not in ["api_keys", "models", "repositories", "agents", "visualizations", "monitoring", "security", "error_handling"]:
                new_config[key] = value
                
        return new_config
    
    def validate_new_config(self, config: Dict[str, Any]) -> bool:
        """Validate the new configuration structure"""
        required_sections = [
            "database", "api_keys", "models", "repositories", 
            "orchestration", "agents", "visualizations", "monitoring"
        ]
        
        missing_sections = [section for section in required_sections if section not in config]
        if missing_sections:
            print(f"❌ Missing required sections: {missing_sections}")
            return False
            
        # Validate database configuration
        db_config = config["database"]
        required_db_fields = ["type", "host", "port", "name", "user", "password"]
        missing_db_fields = [field for field in required_db_fields if field not in db_config]
        if missing_db_fields:
            print(f"❌ Missing database fields: {missing_db_fields}")
            return False
            
        print("✅ Configuration validation passed")
        return True
    
    def save_new_config(self, config: Dict[str, Any]) -> None:
        """Save the new configuration"""
        self.new_config_path.parent.mkdir(exist_ok=True)
        
        with open(self.new_config_path, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, indent=2)
        
        print(f"✅ New configuration saved to: {self.new_config_path}")
    
    def log_migration(self, legacy_config: Dict[str, Any], new_config: Dict[str, Any]) -> None:
        """Log the migration details"""
        migration_log = {
            "timestamp": datetime.now().isoformat(),
            "legacy_config_path": str(self.legacy_config_path),
            "new_config_path": str(self.new_config_path),
            "legacy_sections": list(legacy_config.keys()),
            "new_sections": list(new_config.keys()),
            "changes": {
                "added": [k for k in new_config.keys() if k not in legacy_config.keys()],
                "removed": [k for k in legacy_config.keys() if k not in new_config.keys()],
                "modified": [k for k in legacy_config.keys() if k in new_config.keys() and legacy_config[k] != new_config[k]]
            }
        }
        
        with open(self.migration_log_path, 'w') as f:
            json.dump(migration_log, f, indent=2)
        
        print(f"✅ Migration log saved to: {self.migration_log_path}")
    
    def backup_legacy_config(self) -> None:
        """Create a backup of the legacy configuration"""
        backup_path = Path(f"config/config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml")
        backup_path.parent.mkdir(exist_ok=True)
        
        import shutil
        shutil.copy2(self.legacy_config_path, backup_path)
        print(f"✅ Legacy config backed up to: {backup_path}")
    
    def migrate(self) -> bool:
        """Perform the complete migration"""
        try:
            print("🔄 Starting configuration migration...")
            
            # Load legacy configuration
            print("📖 Loading legacy configuration...")
            legacy_config = self.load_legacy_config()
            
            # Transform to new structure
            print("🔄 Transforming to new structure...")
            new_config = self.transform_to_new_structure(legacy_config)
            
            # Validate new configuration
            print("✅ Validating new configuration...")
            if not self.validate_new_config(new_config):
                return False
            
            # Backup legacy config
            print("💾 Backing up legacy configuration...")
            self.backup_legacy_config()
            
            # Save new configuration
            print("💾 Saving new configuration...")
            self.save_new_config(new_config)
            
            # Log migration
            print("📝 Logging migration details...")
            self.log_migration(legacy_config, new_config)
            
            print("✅ Migration completed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Migration failed: {str(e)}")
            return False
    
    def rollback(self) -> bool:
        """Rollback to legacy configuration"""
        try:
            if not self.legacy_config_path.exists():
                print("❌ No legacy configuration found for rollback")
                return False
                
            # Find the most recent backup
            backup_files = list(Path("config").glob("config_backup_*.yaml"))
            if not backup_files:
                print("❌ No backup files found for rollback")
                return False
                
            latest_backup = max(backup_files, key=lambda f: f.stat().st_mtime)
            
            # Restore backup
            import shutil
            shutil.copy2(latest_backup, self.legacy_config_path)
            
            print(f"✅ Rolled back to: {latest_backup}")
            return True
            
        except Exception as e:
            print(f"❌ Rollback failed: {str(e)}")
            return False


def main():
    """Main migration function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migrate configuration from legacy to new format")
    parser.add_argument("--config", default="config.yaml", help="Path to legacy config file")
    parser.add_argument("--rollback", action="store_true", help="Rollback to legacy configuration")
    
    args = parser.parse_args()
    
    migrator = ConfigMigrator(args.config)
    
    if args.rollback:
        success = migrator.rollback()
    else:
        success = migrator.migrate()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()