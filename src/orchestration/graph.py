"""
LangGraph Orchestrator
Enhanced graph-based orchestration for repository analysis with LangGraph integration
"""

import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from storage.adapter import StorageAdapter, AnalysisRun, Repository, User
from repo_manager import RepoManager, SyncResult
from agents.data_collection import DataCollectionAgent
from models.model_manager import ModelManager
from agents.visualization import VisualizationAgent
from agents.output import OutputAgent
from agents.pr_review import PRReviewAgent
from utils.logging import get_logger, correlation_id, timer_decorator

# Replace standard logging with enhanced structured logging
logger = get_logger(__name__)

@dataclass
class GraphState:
    """Global state for the analysis graph"""
    # Input configuration
    repos: List[str] = field(default_factory=list)
    user_id: Optional[int] = None
    run_type: str = 'full'
    
    # Processing state
    changed_repos: List[str] = field(default_factory=list)
    baselines: Dict[str, Any] = field(default_factory=dict)
    per_repo_results: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    
    # Output state
    visualizations: List[Dict[str, Any]] = field(default_factory=list)
    summary: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)
    
    # Error handling
    errors: List[str] = field(default_factory=list)
    current_step: str = "initialization"

class RepositoryAnalysisGraph:
    """LangGraph-based repository analysis orchestrator"""
    
    def __init__(self, config: Dict, storage: StorageAdapter):
        self.config = config
        self.storage = storage
        
        # Initialize components
        self.model_manager = ModelManager(config)
        self.data_agent = DataCollectionAgent(config, storage, self.model_manager)
        self.viz_agent = VisualizationAgent(config, storage, self.model_manager)
        self.output_agent = OutputAgent(config, storage, self.model_manager)
        self.pr_agent = PRReviewAgent(config, storage, self.model_manager, self.output_agent)
        
        # Graph configuration
        self.graph_config = config.get('orchestration', {}).get('langgraph', {})
        self.max_concurrent_runs = self.graph_config.get('max_concurrent_runs', 5)
        self.timeout_seconds = self.graph_config.get('timeout_seconds', 3600)
        self.retry_attempts = self.graph_config.get('retry_attempts', 3)
        
        # Initialize LangGraph
        self.graph = self._build_langgraph()
        
        # Initialize repo manager
        self.repo_manager = RepoManager(self.config)
    
    def _build_langgraph(self) -> Optional[StateGraph]:
        """Build the LangGraph workflow"""
        if not StateGraph:
            logger.warning("StateGraph not available, returning None", extra={
                'component': 'RepositoryAnalysisGraph',
                'function': '_build_langgraph'
            })
            return None
        
        # Create the graph
        workflow = StateGraph(GraphState)
        
        # Add nodes
        workflow.add_node("initialize", self._initialize_analysis)
        workflow.add_node("sync_repositories", self._sync_repositories)
        workflow.add_node("detect_changes", self._detect_changes)
        workflow.add_node("collect_data", self._collect_repository_data)
        workflow.add_node("analyze_repositories", self._analyze_repositories)
        workflow.add_node("generate_visualizations", self._generate_visualizations)
        workflow.add_node("review_pull_requests", self._review_pull_requests)
        workflow.add_node("generate_report", self._generate_report)
        workflow.add_node("finalize", self._finalize_analysis)
        
        # Add edges
        workflow.add_edge(START, "initialize")
        workflow.add_edge("initialize", "sync_repositories")
        workflow.add_edge("sync_repositories", "detect_changes")
        workflow.add_edge("detect_changes", "collect_data")
        workflow.add_edge("collect_data", "analyze_repositories")
        workflow.add_edge("analyze_repositories", "generate_visualizations")
        workflow.add_edge("generate_visualizations", "review_pull_requests")
        workflow.add_edge("generate_visualizations", "generate_report")
        workflow.add_edge("review_pull_requests", "generate_report")
        workflow.add_edge("generate_report", "finalize")
        workflow.add_edge("finalize", END)
        
        # Add conditional edges for error handling
        workflow.add_conditional_edges(
            "analyze_repositories",
            {
                "success": "generate_visualizations",
                "error": "finalize"
            }
        )
        
        # Add memory for persistence
        memory = MemorySaver()
        
        return workflow.compile(checkpointer=memory)
    
    @timer_decorator("analysis_workflow")
    async def run_analysis(self, repos: List[str], user_id: int = None, 
                        run_type: str = 'full') -> Dict[str, Any]:
        """Run the complete analysis workflow"""
        with correlation_id() as cid:
            logger.info(f"Starting analysis for {len(repos)} repositories", extra={
                'repos_count': len(repos),
                'user_id': user_id,
                'run_type': run_type,
                'correlation_id': cid,
                'component': 'RepositoryAnalysisGraph'
            })
            
            # Initialize state
            initial_state = GraphState(
                repos=repos,
                user_id=user_id,
                run_type=run_type,
                current_step="initialization"
            )
            
            try:
                # Run the graph
                config = {"recursion_limit": "none"}  # Prevent infinite recursion
                result = await self.graph.ainvoke(initial_state, config=config)
                
                logger.info("Analysis completed successfully", extra={
                    'repos_count': len(repos),
                    'correlation_id': cid,
                    'component': 'RepositoryAnalysisGraph',
                    'status': 'success'
                })
                return result
                
            except Exception as e:
                logger.error("Analysis failed", exc_info=True, extra={
                    'repos_count': len(repos),
                    'user_id': user_id,
                    'run_type': run_type,
                    'correlation_id': cid,
                    'component': 'RepositoryAnalysisGraph',
                    'status': 'failed'
                })
                return {
                    "status": "failed",
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "correlation_id": cid
                }
    
    @timer_decorator("initialize_analysis")
    async def _initialize_analysis(self, state: GraphState) -> GraphState:
        """Initialize the analysis workflow"""
        current_cid = correlation_context.get_correlation_id()
        logger.info("Step: Initialize analysis", extra={
            'step': 'initialization',
            'repos_count': len(state.repos),
            'user_id': state.user_id,
            'correlation_id': current_cid,
            'component': 'RepositoryAnalysisGraph'
        })
        
        state.current_step = "initialization"
        state.errors = []
        
        # Create analysis run in database
        try:
            run = self.storage.create_analysis_run(
                repo_id=None,  # Will be set per repo
                run_type=state.run_type,
                created_by=state.user_id
            )
            state.metrics['analysis_run_id'] = run.id if run else None
            logger.info(f"Created analysis run", extra={
                'analysis_run_id': run.id if run else None,
                'step': 'initialization',
                'correlation_id': current_cid,
                'component': 'RepositoryAnalysisGraph'
            })
            
        except Exception as e:
            state.errors.append(f"Failed to create analysis run: {e}")
            logger.error("Failed to create analysis run", exc_info=True, extra={
                'error': str(e),
                'step': 'initialization',
                'correlation_id': current_cid,
                'component': 'RepositoryAnalysisGraph'
            })
        
        return state

    @timer_decorator("sync_repositories")
    async def _sync_repositories(self, state: GraphState) -> GraphState:
        """Ensure local mirrors are synced for configured repositories"""
        current_cid = correlation_context.get_correlation_id()
        logger.info("Step: Sync repositories", extra={
            'step': 'sync_repositories',
            'repos_count': len(state.repos),
            'correlation_id': current_cid,
            'component': 'RepositoryAnalysisGraph'
        })
        
        state.current_step = "sync_repositories"
        
        try:
            sync_result: SyncResult = self.repo_manager.sync(state.repos)
            state.metrics['sync'] = {
                'synced': sync_result.synced,
                'cloned': sync_result.cloned,
                'updated': sync_result.updated,
                'failed': sync_result.failed,
                'details_path': sync_result.details_path
            }
            logger.info(f"Repositories synced successfully", extra={
                'synced': sync_result.synced,
                'cloned': sync_result.cloned,
                'updated': sync_result.updated,
                'failed': sync_result.failed,
                'step': 'sync_repositories',
                'correlation_id': current_cid,
                'component': 'RepositoryAnalysisGraph'
            })
        except Exception as e:
            state.errors.append(f"Repository sync failed: {e}")
            logger.error("Repository sync failed", exc_info=True, extra={
                'error': str(e),
                'step': 'sync_repositories',
                'correlation_id': current_cid,
                'component': 'RepositoryAnalysisGraph'
            })
        
        return state
    
    @timer_decorator("detect_changes")
    async def _detect_changes(self, state: GraphState) -> GraphState:
        """Detect changes in repositories"""
        current_cid = correlation_context.get_correlation_id()
        logger.info("Step: Detect changes", extra={
            'step': 'detect_changes',
            'repos_count': len(state.repos),
            'correlation_id': current_cid,
            'component': 'RepositoryAnalysisGraph'
        })
        
        state.current_step = "detect_changes"
        state.changed_repos = []
        
        # For now, assume all repos need analysis
        # In a real implementation, this would check git status, webhooks, etc.
        state.changed_repos = state.repos.copy()
        
        logger.info(f"Detected changes in repositories", extra={
            'changed_repos_count': len(state.changed_repos),
            'step': 'detect_changes',
            'correlation_id': current_cid,
            'component': 'RepositoryAnalysisGraph'
        })
        return state
    
    @timer_decorator("collect_repository_data")
    async def _collect_repository_data(self, state: GraphState) -> GraphState:
        """Collect repository data"""
        current_cid = correlation_context.get_correlation_id()
        logger.info("Step: Collect repository data", extra={
            'step': 'collect_data',
            'repos_count': len(state.repos),
            'correlation_id': current_cid,
            'component': 'RepositoryAnalysisGraph'
        })
        
        state.current_step = "collect_data"
        
        try:
            # Collect data for all repositories
            repo_data_list = self.data_agent.collect_repository_data(
                state.repos, 
                state.user_id
            )
            
            # Store repository data and create analysis runs per repo
            state.per_repo_results = {}
            for repo_data in repo_data_list:
                repo_key = f"{repo_data.owner}/{repo_data.name}"
                state.per_repo_results[repo_key] = {
                    'repository_data': repo_data,
                    'analysis_results': None,
                    'visualizations': None
                }
            
            logger.info(f"Collected data for repositories", extra={
                'repos_processed': len(repo_data_list),
                'step': 'collect_data',
                'correlation_id': current_cid,
                'component': 'RepositoryAnalysisGraph'
            })
            
        except Exception as e:
            state.errors.append(f"Data collection failed: {e}")
            logger.error("Data collection failed", exc_info=True, extra={
                'error': str(e),
                'step': 'collect_data',
                'correlation_id': current_cid,
                'component': 'RepositoryAnalysisGraph'
            })
        
        return state
    
    @timer_decorator("analyze_repositories")
    async def _analyze_repositories(self, state: GraphState) -> GraphState:
        """Analyze repositories for pain points"""
        current_cid = correlation_context.get_correlation_id()
        logger.info("Step: Analyze repositories", extra={
            'step': 'analyze_repositories',
            'repos_count': len(state.per_repo_results),
            'correlation_id': current_cid,
            'component': 'RepositoryAnalysisGraph'
        })
        
        state.current_step = "analyze_repositories"
        
        try:
            for repo_key, repo_result in state.per_repo_results.items():
                repo_data = repo_result['repository_data']
                
                # Analyze repository for pain points
                insights_data = {
                    'repository': {
                        'name': repo_data.name,
                        'owner': repo_data.owner,
                        'health_score': repo_data.health_score,
                        'open_prs': repo_data.open_prs,
                        'ci_status': repo_data.ci_status
                    }
                }
                
                analysis_response = self.model_manager.analyze_pain_points(
                    insights_data['repository'],
                    repo_data.open_prs
                )
                
                repo_result['analysis_results'] = {
                    'repository': repo_key,
                    'pain_points': analysis_response.metadata.get('pain_points', []) if analysis_response.metadata else [],
                    'confidence': analysis_response.confidence,
                    'model_used': analysis_response.model,
                    'solutions': []
                }
                
                logger.info(f"Analyzed repository for pain points", extra={
                    'repository': repo_key,
                    'pain_points_count': len(repo_result['analysis_results']['pain_points']),
                    'confidence': analysis_response.confidence,
                    'model': analysis_response.model,
                    'step': 'analyze_repositories',
                    'correlation_id': current_cid,
                    'component': 'RepositoryAnalysisGraph'
                })

                # Write per-agent log for analysis results
                lines = [
                    f"Agent: structure_architecture",
                    f"Repository: {repo_key}",
                    f"Timestamp: {datetime.now(timezone.utc).isoformat()}",
                    "",
                    f"Model: {repo_result['analysis_results']['model_used']} (confidence {repo_result['analysis_results']['confidence']:.2f})",
                    "",
                    "Identified Pain Points:",
                ]
                for p in repo_result['analysis_results']['pain_points']:
                    lines.append(f"- {p.get('type','unknown')} (severity {p.get('severity','?')}) - {p.get('description','')}")
                content = "\n".join(lines)
                self.output_agent.write_agent_log('structure_architecture', repo_key, content, json_payload={
                    'analysis_results': repo_result['analysis_results'],
                    'correlation_id': current_cid
                })
            
        except Exception as e:
            state.errors.append(f"Repository analysis failed: {e}")
            logger.error("Repository analysis failed", exc_info=True, extra={
                'error': str(e),
                'step': 'analyze_repositories',
                'correlation_id': current_cid,
                'component': 'RepositoryAnalysisGraph'
            })
        
        return state
    
    @timer_decorator("generate_visualizations")
    async def _generate_visualizations(self, state: GraphState) -> GraphState:
        """Generate visualizations for analysis results"""
        current_cid = correlation_context.get_correlation_id()
        logger.info("Step: Generate visualizations", extra={
            'step': 'generate_visualizations',
            'repos_count': len(state.per_repo_results),
            'correlation_id': current_cid,
            'component': 'RepositoryAnalysisGraph'
        })
        
        state.current_step = "generate_visualizations"
        
        try:
            analysis_run_id = state.metrics.get('analysis_run_id')
            
            for repo_key, repo_result in state.per_repo_results.items():
                analysis_results = repo_result.get('analysis_results', {})
                
                if not analysis_results:
                    logger.warning(f"No analysis results for repository, skipping visualization", extra={
                        'repository': repo_key,
                        'step': 'generate_visualizations',
                        'correlation_id': current_cid,
                        'component': 'RepositoryAnalysisGraph'
                    })
                    continue
                
                # Generate visualizations
                insights_data = {
                    'repository': analysis_results.get('repository', {}),
                    'pain_points': analysis_results.get('pain_points', [])
                }
                
                viz_results = self.viz_agent.generate_visualizations(
                    analysis_run_id,
                    insights_data,
                    analysis_results.get('repository')
                )
                
                repo_result['visualizations'] = viz_results
                logger.info(f"Generated visualizations for repository", extra={
                    'repository': repo_key,
                    'visualizations_count': len(viz_results),
                    'step': 'generate_visualizations',
                    'correlation_id': current_cid,
                    'component': 'RepositoryAnalysisGraph'
                })

                # Write per-agent log for visualization outputs
                lines = [
                    f"Agent: visualization",
                    f"Repository: {repo_key}",
                    f"Timestamp: {datetime.now(timezone.utc).isoformat()}",
                    "",
                    "Generated Visualizations:",
                ]
                for v in viz_results:
                    lines.append(f"- {v.type}: {v.title} -> {v.filename}")
                content = "\n".join(lines)
                self.output_agent.write_agent_log('visualization', repo_key, content, json_payload={
                    'visualizations': [
                        {
                            'type': v.type,
                            'title': v.title,
                            'filename': v.filename,
                            'quality_score': v.quality_score,
                            'approved': v.approved,
                            'correlation_id': current_cid
                        } for v in viz_results
                    ]
                })
            
        except Exception as e:
            state.errors.append(f"Visualization generation failed: {e}")
            logger.error("Visualization generation failed", exc_info=True, extra={
                'error': str(e),
                'step': 'generate_visualizations',
                'correlation_id': current_cid,
                'component': 'RepositoryAnalysisGraph'
            })
        
        return state
    
    @timer_decorator("generate_report")
    async def _generate_report(self, state: GraphState) -> GraphState:
        """Generate analysis report"""
        current_cid = correlation_context.get_correlation_id()
        logger.info("Step: Generate report", extra={
            'step': 'generate_report',
            'repos_count': len(state.per_repo_results),
            'correlation_id': current_cid,
            'component': 'RepositoryAnalysisGraph'
        })
        
        state.current_step = "generate_report"
        
        try:
            analysis_run_id = state.metrics.get('analysis_run_id')
            
            # Prepare data for report generation
            repositories = []
            analysis_results = []
            visualizations = []
            solutions = []
            
            for repo_key, repo_result in state.per_repo_results.items():
                repo_data = repo_result.get('repository_data', {})
                analysis = repo_result.get('analysis_results', {})
                vizs = repo_result.get('visualizations', [])
                
                repositories.append({
                    'name': repo_data.name,
                    'owner': repo_data.owner,
                    'health_score': repo_data.health_score,
                    'open_prs': repo_data.open_prs,
                    'ci_status': repo_data.ci_status
                })
                
                analysis_results.append(analysis)
                
                # Collect all visualizations
                for viz in vizs:
                    visualizations.append({
                        'type': viz.type,
                        'title': viz.title,
                        'filename': viz.filename,
                        'mermaid_code': viz.mermaid_code,
                        'description': viz.metadata.get('description', '')
                    })
                
                # Collect all solutions
                for pain_point in analysis.get('pain_points', []):
                    if pain_point.get('recommendations'):
                        solutions.extend(pain_point['recommendations'])
            
            # Generate report
            report_path = self.output_agent.generate_analysis_report(
                analysis_run_id,
                repositories,
                analysis_results,
                visualizations,
                solutions,
                state.metrics
            )
            
            state.summary['report_path'] = str(report_path)
            logger.info(f"Generated analysis report", extra={
                'report_path': str(report_path),
                'analysis_run_id': analysis_run_id,
                'step': 'generate_report',
                'correlation_id': current_cid,
                'component': 'RepositoryAnalysisGraph'
            })
            
        except Exception as e:
            state.errors.append(f"Report generation failed: {e}")
            logger.error("Report generation failed", exc_info=True, extra={
                'error': str(e),
                'step': 'generate_report',
                'correlation_id': current_cid,
                'component': 'RepositoryAnalysisGraph'
            })
        
        return state

    @timer_decorator("review_pull_requests")
    async def _review_pull_requests(self, state: GraphState) -> GraphState:
        """Run programmatic PR reviews when enabled"""
        current_cid = correlation_context.get_correlation_id()
        logger.info("Step: Review pull requests", extra={
            'step': 'review_pull_requests',
            'repos_count': len(state.per_repo_results),
            'correlation_id': current_cid,
            'component': 'RepositoryAnalysisGraph'
        })
        
        state.current_step = "review_pull_requests"
        
        try:
            analysis_run_id = state.metrics.get('analysis_run_id')
            if not getattr(self.pr_agent, 'enabled', False):
                logger.info("PR review disabled by configuration", extra={
                    'step': 'review_pull_requests',
                    'correlation_id': current_cid,
                    'component': 'RepositoryAnalysisGraph'
                })
                return state
            
            for repo_key, repo_result in state.per_repo_results.items():
                parts = repo_key.split('/')
                if len(parts) != 2:
                    logger.warning(f"Invalid repository format, skipping PR review", extra={
                        'repository': repo_key,
                        'step': 'review_pull_requests',
                        'correlation_id': current_cid,
                        'component': 'RepositoryAnalysisGraph'
                    })
                    continue
                
                owner, name = parts
                count = self.pr_agent.review_repo(owner, name, analysis_run_id)
                logger.info(f"Reviewed open PRs for repository", extra={
                    'repository': repo_key,
                    'prs_reviewed': count,
                    'step': 'review_pull_requests',
                    'correlation_id': current_cid,
                    'component': 'RepositoryAnalysisGraph'
                })
                
        except Exception as e:
            state.errors.append(f"PR review failed: {e}")
            logger.error("PR review failed", exc_info=True, extra={
                'error': str(e),
                'step': 'review_pull_requests',
                'correlation_id': current_cid,
                'component': 'RepositoryAnalysisGraph'
            })
        
        return state
    
    @timer_decorator("finalize_analysis")
    async def _finalize_analysis(self, state: GraphState) -> GraphState:
        """Finalize the analysis workflow"""
        current_cid = correlation_context.get_correlation_id()
        logger.info("Step: Finalize analysis", extra={
            'step': 'finalize',
            'repos_count': len(state.per_repo_results),
            'errors_count': len(state.errors),
            'correlation_id': current_cid,
            'component': 'RepositoryAnalysisGraph'
        })
        
        state.current_step = "finalize"
        
        try:
            analysis_run_id = state.metrics.get('analysis_run_id')
            
            # Update analysis run status
            if analysis_run_id:
                if state.errors:
                    self.storage.update_analysis_run_status(
                        analysis_run_id, 
                        'failed', 
                        f"Errors: {'; '.join(state.errors)}"
                    )
                    logger.error("Analysis run failed", extra={
                        'analysis_run_id': analysis_run_id,
                        'errors': state.errors,
                        'step': 'finalize',
                        'correlation_id': current_cid,
                        'component': 'RepositoryAnalysisGraph'
                    })
                else:
                    self.storage.update_analysis_run_status(
                        analysis_run_id, 
                        'completed'
                    )
                    logger.info("Analysis run completed successfully", extra={
                        'analysis_run_id': analysis_run_id,
                        'step': 'finalize',
                        'correlation_id': current_cid,
                        'component': 'RepositoryAnalysisGraph'
                    })
            
            # Clean up old reports
            self.output_agent.cleanup_old_reports()
            
            state.metrics['completed_at'] = datetime.now(timezone.utc).isoformat()
            logger.info("Analysis finalized successfully", extra={
                'analysis_run_id': analysis_run_id,
                'completed_at': state.metrics['completed_at'],
                'step': 'finalize',
                'correlation_id': current_cid,
                'component': 'RepositoryAnalysisGraph'
            })
            
        except Exception as e:
            state.errors.append(f"Finalization failed: {e}")
            logger.error("Finalization failed", exc_info=True, extra={
                'error': str(e),
                'step': 'finalize',
                'correlation_id': current_cid,
                'component': 'RepositoryAnalysisGraph'
            })
        
        return state
    
    def get_graph_stats(self) -> Dict[str, Any]:
        """Get statistics about the graph configuration"""
        current_cid = correlation_context.get_correlation_id()
        stats = {
            "langgraph_available": StateGraph is not None,
            "max_concurrent_runs": self.max_concurrent_runs,
            "timeout_seconds": self.timeout_seconds,
            "retry_attempts": self.retry_attempts,
            "supported_repos": self.data_agent.default_owner,
            "model_stats": self.model_manager.get_model_stats(),
            "correlation_id": current_cid
        }
        
        logger.debug("Graph stats retrieved", extra={
            'stats': stats,
            'correlation_id': current_cid,
            'component': 'RepositoryAnalysisGraph'
        })
        
        return stats
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on the orchestration system"""
        current_cid = correlation_context.get_correlation_id()
        
        try:
            # Check storage health
            storage_health = self.storage.health_check()
            
            # Check model availability
            model_stats = self.model_manager.get_model_stats()
            
            # Check output configuration
            output_stats = self.output_agent.get_output_stats()
            
            health_status = {
                "status": "healthy" if storage_health.get("status") == "healthy" else "degraded",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "correlation_id": current_cid,
                "components": {
                    "storage": storage_health,
                    "models": model_stats,
                    "output": output_stats,
                }
            }
            
            logger.info("Health check completed", extra={
                'health_status': health_status['status'],
                'correlation_id': current_cid,
                'component': 'RepositoryAnalysisGraph'
            })
            
            return health_status
            
        except Exception as e:
            logger.error("Health check failed", exc_info=True, extra={
                'error': str(e),
                'correlation_id': current_cid,
                'component': 'RepositoryAnalysisGraph'
            })
            
            return {
                "status": "unhealthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "correlation_id": current_cid,
                "error": str(e)
            }