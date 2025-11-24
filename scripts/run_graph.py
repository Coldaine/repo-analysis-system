#!/usr/bin/env python3
"""
Repository Analysis System - New CLI Entry Point
Replaces the prototype script with LangGraph orchestration
"""

import sys
import json
import argparse
import asyncio
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.repo_manager import RepoManager
from src.utils.config import ConfigLoader
from src.utils.logging import setup_logging

logger = logging.getLogger(__name__)

class GraphRunner:
    """Main runner for the repository analysis graph"""
    
    def __init__(self, config_path: str = "config/new_config.yaml"):
        self.config_path = Path(config_path)
        self.config = self._load_config()
        self.storage = None
        self.graph = None
        
    def _load_config(self) -> Dict[str, Any]:
        """Load and validate configuration"""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
        
        loader = ConfigLoader()
        config = loader.load_config(str(self.config_path))
        
        # Validate required sections
        required_sections = ['database', 'api_keys', 'models', 'orchestration']
        missing_sections = [section for section in required_sections if section not in config]
        
        if missing_sections:
            raise ValueError(f"Missing required configuration sections: {missing_sections}")
        
        return config
    
    async def initialize(self):
        """Initialize storage and graph components"""
        logger.info("Initializing repository analysis system")
        
        # Initialize storage adapter
        from src.storage.adapter import create_storage_adapter
        db_config = self.config.get('database', {})
        self.storage = create_storage_adapter(db_config)
        
        # Check storage health
        health = self.storage.health_check()
        if health.get('status') != 'healthy':
            logger.warning(f"Storage health check failed: {health}")
        
        # Initialize graph
        from src.orchestration.graph import RepositoryAnalysisGraph
        self.graph = RepositoryAnalysisGraph(self.config, self.storage)
        
        logger.info("System initialized successfully")
    
    async def run_analysis(self, repos: List[str] = None, user_id: int = None,
                        run_type: str = 'full') -> Dict[str, Any]:
        """Run repository analysis workflow"""
        logger.info(f"Starting analysis run (type: {run_type})")
        
        if not repos:
            # Get repos from config
            repos = self.config.get('repositories', {}).get('target_repos', [])
        
        try:
            # Run the analysis graph
            result = await self.graph.run_analysis(
                repos=repos,
                user_id=user_id,
                run_type=run_type
            )
            
            logger.info("Analysis completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": self._get_timestamp()
            }
    
    async def run_health_check(self) -> Dict[str, Any]:
        """Run system health check"""
        logger.info("Running system health check")
        
        try:
            if not self.graph:
                await self.initialize()
            
            health = self.graph.health_check()
            logger.info("Health check completed")
            return health
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": self._get_timestamp()
            }
    
    async def get_system_stats(self) -> Dict[str, Any]:
        """Get system statistics"""
        logger.info("Retrieving system statistics")
        
        try:
            if not self.graph:
                await self.initialize()
            
            stats = self.graph.get_graph_stats()
            logger.info("System statistics retrieved")
            return stats
            
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": self._get_timestamp()
            }
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime, timezone
        return datetime.now(timezone.utc).isoformat()

async def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Repository Analysis System - LangGraph Orchestration",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    # Configuration options
    parser.add_argument(
        "--config", "-c",
        default="config/new_config.yaml",
        help="Path to configuration file"
    )
    
    # Action options
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Analysis command
    analyze_parser = subparsers.add_parser(
        'analyze', 
        help='Run repository analysis'
    )
    analyze_parser.add_argument(
        '--repos', '-r',
        nargs='*',
        help='Repository names to analyze (overrides config)'
    )
    analyze_parser.add_argument(
        '--user-id', '-u',
        type=int,
        help='User ID for analysis'
    )
    analyze_parser.add_argument(
        '--run-type',
        choices=['full', 'incremental', 'webhook'],
        default='full',
        help='Type of analysis run'
    )
    analyze_parser.add_argument(
        '--enable-pr-review',
        action='store_true',
        help='Enable PR review for this run'
    )
    analyze_parser.add_argument(
        '--recursion-limit',
        type=int,
        help='Recursion limit to pass into LangGraph (default: 25)'
    )
    analyze_parser.add_argument(
        '--checkpointer',
        choices=['memory', 'postgres'],
        help='Which checkpointer to use for the graph (memory|postgres)'
    )
    
    # Health check command
    health_parser = subparsers.add_parser(
        'health',
        help='Run system health check'
    )
    
    # Stats command
    stats_parser = subparsers.add_parser(
        'stats',
        help='Get system statistics'
    )

    # Sync command
    sync_parser = subparsers.add_parser(
        'sync',
        help='Sync configured repositories locally'
    )
    sync_parser.add_argument(
        '--repos', '-r', nargs='*', help='Repositories to sync (default: config target_repos)'
    )
    
    # Migration command
    migrate_parser = subparsers.add_parser(
        'migrate',
        help='Migrate configuration from legacy format'
    )
    migrate_parser.add_argument(
        '--legacy-config',
        default='config.yaml',
        help='Path to legacy configuration file'
    )
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = 'INFO'
    if hasattr(args, 'verbose') and args.verbose:
        log_level = 'DEBUG'
    
    setup_logging(level=log_level)
    
    try:
        # Initialize runner
        runner = GraphRunner(getattr(args, 'config', 'config/new_config.yaml'))
        
        if args.command == 'analyze':
            # Run analysis
            repos = getattr(args, 'repos', None)
            user_id = getattr(args, 'user_id', None)
            run_type = getattr(args, 'run_type', 'full')
            enable_pr = getattr(args, 'enable_pr_review', False)
            
            recursion_limit = getattr(args, 'recursion_limit', None)
            if recursion_limit is not None:
                runner.config.setdefault('orchestration', {}).setdefault('langgraph', {})['recursion_limit'] = recursion_limit

            checkpointer = getattr(args, 'checkpointer', None)
            if checkpointer:
                runner.config.setdefault('orchestration', {}).setdefault('langgraph', {})['checkpointer'] = checkpointer
            if enable_pr:
                runner.config.setdefault('agents', {}).setdefault('pr_review', {})['enabled'] = True

            result = await runner.run_analysis(
                repos=repos,
                user_id=user_id,
                run_type=run_type
            )
            
            # Output result
            if args.verbose:
                print(json.dumps(result, indent=2))
            else:
                if result.get('status') == 'completed':
                    print("✅ Analysis completed successfully")
                    if 'state' in result and 'summary' in result['state']:
                        print(f"📊 Report: {result['state']['summary'].get('report_path', 'N/A')}")
                else:
                    print("❌ Analysis failed")
                    print(f"Error: {result.get('error', 'Unknown error')}")
        
        elif args.command == 'health':
            # Health check
            result = await runner.run_health_check()
            
            if args.verbose:
                print(json.dumps(result, indent=2))
            else:
                status = result.get('status', 'unknown')
                if status == 'healthy':
                    print("✅ System is healthy")
                else:
                    print("❌ System health issues detected")
                    if args.verbose:
                        print(f"Status: {status}")
                        if 'error' in result:
                            print(f"Error: {result['error']}")
        
        elif args.command == 'stats':
            # System statistics
            result = await runner.get_system_stats()
            
            if args.verbose:
                print(json.dumps(result, indent=2))
            else:
                print("📊 System Statistics:")
                if 'components' in result:
                    for component, stats in result['components'].items():
                        print(f"  {component.title()}: {stats.get('status', 'unknown')}")
                        if args.verbose and 'stats' in stats:
                            for key, value in stats['stats'].items():
                                print(f"    {key}: {value}")
        
        elif args.command == 'sync':
            # Sync repositories locally
            cfg_path = getattr(args, 'config', 'config/new_config.yaml')
            cfg = ConfigLoader().load_config(cfg_path)
            repos = getattr(args, 'repos', None) or cfg.get('repositories', {}).get('target_repos', [])
            manager = RepoManager(cfg)
            result = manager.sync(repos)
            print(json.dumps({
                'synced': result.synced,
                'cloned': result.cloned,
                'updated': result.updated,
                'failed': result.failed,
                'details_path': result.details_path
            }, indent=2))
        elif args.command == 'migrate':
            # Configuration migration
            from config.migration import ConfigMigrator
            
            legacy_config = getattr(args, 'legacy_config', 'config.yaml')
            migrator = ConfigMigrator(legacy_config)
            
            if migrator.migrate():
                print("✅ Configuration migrated successfully")
                print(f"📄 New config: config/new_config.yaml")
                print(f"💾 Backup: config/config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml")
            else:
                print("❌ Configuration migration failed")
        
        else:
            parser.print_help()
            return 1
        
        return 0
    
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        return 130
    except Exception as e:
        logger.error(f"CLI execution failed: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))