"""
LangGraph Orchestrator
Enhanced graph-based orchestration for repository analysis with LangGraph integration
"""

import os
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
from agents.complexity_agent import ComplexityAgent
from agents.security_agent import SecurityAgent
from agents.pr_review import PRReviewAgent
from utils.logging import get_logger, correlation_id, timer_decorator, correlation_context

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

    # Code quality analysis state
    complexity_results: Dict[str, Any] = field(default_factory=dict)
    security_results: Dict[str, Any] = field(default_factory=dict)

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
        self.complexity_agent = ComplexityAgent(storage=storage)
        self.security_agent = SecurityAgent(storage=storage)
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
            return None
        
        # Create the graph
        workflow = StateGraph(GraphState)
        
        # Add nodes
        workflow.add_node("initialize", self._initialize_analysis)
        workflow.add_node("sync_repositories", self._sync_repositories)
        workflow.add_node("detect_changes", self._detect_changes)
        workflow.add_node("collect_data", self._collect_repository_data)
        workflow.add_node("analyze_complexity", self._analyze_complexity)
        workflow.add_node("analyze_security", self._analyze_security)
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
        workflow.add_edge("collect_data", "analyze_complexity")
        workflow.add_edge("analyze_complexity", "analyze_security")
        workflow.add_edge("analyze_security", "analyze_repositories")
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
    
    async def run_analysis(self, repos: List[str], user_id: int = None, 
                        run_type: str = 'full') -> Dict[str, Any]:
        """Run the complete analysis workflow"""
        logger.info(f"Starting analysis for {len(repos)} repositories")
        
        # Graph must be available; run
        
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
            
            logger.info("Analysis completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    async def _run_fallback_orchestration(self, repos: List[str], user_id: int = None,
                                   run_type: str = 'full') -> Dict[str, Any]:
        """Fallback orchestration without LangGraph"""
        logger.info("Running fallback orchestration")

        try:
            # Step 1: Initialize
            state = GraphState(
                repos=repos,
                user_id=user_id,
                run_type=run_type,
                current_step="initialization"
            )

            # Step 2: Detect changes (simplified)
            state = await self._detect_changes(state)

            # Step 3: Collect data
            state = await self._collect_repository_data(state)

            # Step 4: Analyze repositories
            state = await self._analyze_repositories(state)

            # Step 5: Generate visualizations
            state = await self._generate_visualizations(state)

            # Step 6: Generate report
            state = await self._generate_report(state)

            # Step 7: Finalize
            state = await self._finalize_analysis(state)

            return {
                "status": "completed",
                "state": state,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        except Exception as e:
            logger.error(f"Fallback orchestration failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    async def _initialize_analysis(self, state: GraphState) -> GraphState:
        """Initialize the analysis workflow"""
        logger.info("Step: Initialize analysis")
        
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
            logger.info(f"Created analysis run: {run.id}")
            
        except Exception as e:
            state.errors.append(f"Failed to create analysis run: {e}")
        
        return state

    async def _sync_repositories(self, state: GraphState) -> GraphState:
        """Ensure local mirrors are synced for configured repositories"""
        logger.info("Step: Sync repositories")
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
            logger.info(f"Repositories synced: {sync_result.synced} (cloned {sync_result.cloned}, updated {sync_result.updated})")
        except Exception as e:
            state.errors.append(f"Repository sync failed: {e}")
            logger.error(f"Repository sync failed: {e}")
        
        return state
    
    async def _detect_changes(self, state: GraphState) -> GraphState:
        """Detect changes in repositories"""
        logger.info("Step: Detect changes")
        
        state.current_step = "detect_changes"
        state.changed_repos = []
        
        # For now, assume all repos need analysis
        # In a real implementation, this would check git status, webhooks, etc.
        state.changed_repos = state.repos.copy()
        
        logger.info(f"Detected changes in {len(state.changed_repos)} repositories")
        return state
    
    async def _collect_repository_data(self, state: GraphState) -> GraphState:
        """Collect repository data"""
        logger.info("Step: Collect repository data")
        
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
            
            logger.info(f"Collected data for {len(repo_data_list)} repositories")
            
        except Exception as e:
            state.errors.append(f"Data collection failed: {e}")

        return state

    async def _analyze_complexity(self, state: GraphState) -> GraphState:
        """Analyze code complexity for repositories"""
        logger.info("Step: Analyze complexity")

        state.current_step = "analyze_complexity"

        try:
            analysis_run_id = state.metrics.get('analysis_run_id')

            for repo_key, repo_result in state.per_repo_results.items():
                repo_data = repo_result['repository_data']

                # Check if repository has a local path for analysis
                # For now, we'll assume the repo needs to be cloned
                # In production, this would integrate with git clone
                repo_path = repo_data.path

                if repo_path and os.path.exists(repo_path):
                    # Analyze complexity
                    complexity_result = self.complexity_agent.analyze_repository(
                        repo_path=repo_path,
                        repo_name=repo_key,
                        analysis_run_id=analysis_run_id,
                    )

                    # Store results
                    state.complexity_results[repo_key] = complexity_result.to_dict()
                    repo_result['complexity_analysis'] = complexity_result.to_dict()

                    logger.info(
                        f"Complexity analysis for {repo_key}: "
                        f"{complexity_result.metrics.get('total_hotspots', 0)} hotspots found"
                    )
                else:
                    logger.warning(f"Repository path not found for {repo_key}, skipping complexity analysis")

        except Exception as e:
            logger.error(f"Complexity analysis failed: {e}")
            state.errors.append(f"Complexity analysis failed: {e}")

        return state

    async def _analyze_security(self, state: GraphState) -> GraphState:
        """Scan repositories for security vulnerabilities"""
        logger.info("Step: Analyze security")

        state.current_step = "analyze_security"

        try:
            analysis_run_id = state.metrics.get('analysis_run_id')

            for repo_key, repo_result in state.per_repo_results.items():
                repo_data = repo_result['repository_data']

                # Check if repository has a local path for analysis
                repo_path = repo_data.path

                if repo_path and os.path.exists(repo_path):
                    # Scan for vulnerabilities
                    security_result = self.security_agent.analyze_repository(
                        repo_path=repo_path,
                        repo_name=repo_key,
                        analysis_run_id=analysis_run_id,
                    )

                    # Store results
                    state.security_results[repo_key] = security_result.to_dict()
                    repo_result['security_analysis'] = security_result.to_dict()

                    logger.info(
                        f"Security scan for {repo_key}: "
                        f"{security_result.summary.get('total_vulnerabilities', 0)} vulnerabilities found "
                        f"({security_result.summary.get('critical', 0)} critical)"
                    )
                else:
                    logger.warning(f"Repository path not found for {repo_key}, skipping security scan")

        except Exception as e:
            logger.error(f"Security analysis failed: {e}")
            state.errors.append(f"Security analysis failed: {e}")

        return state

    async def _analyze_repositories(self, state: GraphState) -> GraphState:
        """Analyze repositories for pain points"""
        logger.info("Step: Analyze repositories")
        
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
                
                logger.info(f"Analyzed repository {repo_key}")

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
                    'analysis_results': repo_result['analysis_results']
                })
            
        except Exception as e:
            state.errors.append(f"Repository analysis failed: {e}")
        
        return state
    
    async def _generate_visualizations(self, state: GraphState) -> GraphState:
        """Generate visualizations for analysis results"""
        logger.info("Step: Generate visualizations")
        
        state.current_step = "generate_visualizations"
        
        try:
            analysis_run_id = state.metrics.get('analysis_run_id')
            
            for repo_key, repo_result in state.per_repo_results.items():
                analysis_results = repo_result.get('analysis_results', {})
                
                if not analysis_results:
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
                logger.info(f"Generated {len(viz_results)} visualizations for {repo_key}")

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
                            'approved': v.approved
                        } for v in viz_results
                    ]
                })
            
        except Exception as e:
            state.errors.append(f"Visualization generation failed: {e}")
        
        return state
    
    async def _generate_report(self, state: GraphState) -> GraphState:
        """Generate analysis report"""
        logger.info("Step: Generate report")
        
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
            logger.info(f"Generated analysis report: {report_path}")
            
        except Exception as e:
            state.errors.append(f"Report generation failed: {e}")
        
        return state

    async def _review_pull_requests(self, state: GraphState) -> GraphState:
        """Run programmatic PR reviews when enabled"""
        logger.info("Step: Review pull requests")
        state.current_step = "review_pull_requests"
        try:
            analysis_run_id = state.metrics.get('analysis_run_id')
            if not getattr(self.pr_agent, 'enabled', False):
                logger.info("PR review disabled; skipping")
                return state
            for repo_key, repo_result in state.per_repo_results.items():
                parts = repo_key.split('/')
                if len(parts) != 2:
                    continue
                owner, name = parts
                count = self.pr_agent.review_repo(owner, name, analysis_run_id)
                logger.info(f"Reviewed {count} open PRs for {repo_key}")
        except Exception as e:
            state.errors.append(f"PR review failed: {e}")
        return state
    
    async def _finalize_analysis(self, state: GraphState) -> GraphState:
        """Finalize the analysis workflow"""
        logger.info("Step: Finalize analysis")
        
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
                else:
                    self.storage.update_analysis_run_status(
                        analysis_run_id, 
                        'completed'
                    )
            
            # Clean up old reports
            self.output_agent.cleanup_old_reports()
            
            state.metrics['completed_at'] = datetime.now(timezone.utc).isoformat()
            logger.info("Analysis finalized successfully")
            
        except Exception as e:
            state.errors.append(f"Finalization failed: {e}")
        
        return state
    
    def get_graph_stats(self) -> Dict[str, Any]:
        """Get statistics about the graph configuration"""
        return {
            "langgraph_available": StateGraph is not None,
            "max_concurrent_runs": self.max_concurrent_runs,
            "timeout_seconds": self.timeout_seconds,
            "retry_attempts": self.retry_attempts,
            "supported_repos": self.data_agent.default_owner,
            "model_stats": self.model_manager.get_model_stats()
        }
    
    def health_check(self) -> Dict[str, Any]:
        """Perform health check on the orchestration system"""
        try:
            # Check storage health
            storage_health = self.storage.health_check()
            
            # Check model availability
            model_stats = self.model_manager.get_model_stats()
            
            # Check output configuration
            output_stats = self.output_agent.get_output_stats()
            
            return {
                "status": "healthy" if storage_health.get("status") == "healthy" else "degraded",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "components": {
                    "storage": storage_health,
                    "models": model_stats,
                    "output": output_stats,
                    "orchestration": self.get_graph_stats()
                }
            }
            
        except Exception as e:
            return {
                "status": "unhealthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }