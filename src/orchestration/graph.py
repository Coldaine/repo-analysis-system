"""
LangGraph Orchestrator
Enhanced graph-based orchestration for repository analysis with LangGraph integration
"""

import os
import logging
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, TypedDict
from urllib.parse import quote_plus

from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

# Optional Postgres checkpointer; may not be available in development environments
try:
    from langgraph.checkpoint.postgres import PostgresSaver
except Exception:
    PostgresSaver = None

from src.storage.adapter import StorageAdapter
from src.repo_manager import RepoManager, SyncResult
from src.agents.data_collection import DataCollectionAgent
from src.models.model_manager import ModelManager
from src.agents.visualization import VisualizationAgent
from src.agents.output import OutputAgent
from src.agents.complexity_agent import ComplexityAgent
from src.agents.security_agent import SecurityAgent
from src.agents.pr_review import PRReviewAgent
from src.utils.logging import get_logger, correlation_context

# Replace standard logging with enhanced structured logging
logger = get_logger(__name__)

class GraphState(TypedDict, total=False):
    """Global state passed between LangGraph nodes."""

    # Input configuration
    repos: List[str]
    user_id: Optional[int]
    run_type: str

    # Processing state
    changed_repos: List[str]
    baselines: Dict[str, Any]
    per_repo_results: Dict[str, Dict[str, Any]]

    # Code quality analysis state
    complexity_results: Dict[str, Any]
    security_results: Dict[str, Any]

    # Output state
    visualizations: List[Dict[str, Any]]
    summary: Dict[str, Any]
    metrics: Dict[str, Any]

    # Error handling and orchestration metadata
    errors: List[str]
    current_step: str

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
        workflow.add_edge("generate_visualizations", "review_pull_requests")
        workflow.add_edge("generate_visualizations", "generate_report")
        workflow.add_edge("review_pull_requests", "generate_report")
        workflow.add_edge("generate_report", "finalize")
        workflow.add_edge("finalize", END)
        
        # Add conditional edges for error handling
        workflow.add_conditional_edges(
            "analyze_repositories",
            self._analysis_routing_condition,
            {
                "success": "generate_visualizations",
                "error": "finalize"
            }
        )
        
        checkpointer = self._build_checkpointer()

        return workflow.compile(checkpointer=checkpointer)

    @staticmethod
    def _analysis_routing_condition(state: GraphState) -> str:
        """Route to finalize if any errors were recorded during repo analysis."""
        errors = state.get("errors") or []
        return "error" if errors else "success"

    def _build_checkpointer(self):
        """Select the configured LangGraph checkpointer."""
        checkpointer_name = self.graph_config.get('checkpointer', 'memory')
        checkpointer_name = (checkpointer_name or 'memory').lower()

        if checkpointer_name == 'postgres' and PostgresSaver is not None:
            conn_string = self._postgres_connection_url()
            if conn_string:
                try:
                    return PostgresSaver.from_conn_string(conn_string)
                except Exception as exc:
                    logger.warning(
                        "Postgres checkpointer unavailable (%s); falling back to MemorySaver",
                        exc,
                    )
            else:
                logger.warning("Postgres checkpointer requested but database config missing; using MemorySaver")

        return MemorySaver()

    def _postgres_connection_url(self) -> Optional[str]:
        """Build a psycopg-compatible connection string from config."""
        db_cfg = self.config.get('database', {}) or {}
        host = db_cfg.get('host') or os.getenv('POSTGRES_HOST')
        name = db_cfg.get('name') or os.getenv('POSTGRES_DB')
        user = db_cfg.get('user') or os.getenv('POSTGRES_USER')
        password = db_cfg.get('password') or os.getenv('POSTGRES_PASSWORD') or ''
        port = db_cfg.get('port') or os.getenv('POSTGRES_PORT', 5432)

        if not (host and name and user):
            return None

        auth = quote_plus(str(user))
        if password:
            auth = f"{auth}:{quote_plus(str(password))}"

        return f"postgresql://{auth}@{host}:{port}/{name}"

    def _build_run_config(
        self,
        recursion_limit: int,
        run_id: str,
        user_id: Optional[int],
        run_type: str,
    ) -> Dict[str, Any]:
        """Construct the config payload passed into LangGraph Runtime."""

        metadata = {
            "run_id": run_id,
            "run_type": run_type,
        }
        if user_id is not None:
            metadata["user_id"] = user_id

        configurable = {
            "run_type": run_type,
        }
        if user_id is not None:
            configurable["user_id"] = user_id

        config: Dict[str, Any] = {
            "recursion_limit": recursion_limit,
            "metadata": metadata,
            "configurable": configurable,
        }

        tags = self.graph_config.get('tags')
        if tags:
            config["tags"] = tags

        return config
    
    async def run_analysis(self, repos: List[str], user_id: int = None, 
                        run_type: str = 'full') -> Dict[str, Any]:
        """Run the complete analysis workflow"""
        logger.info(f"Starting analysis for {len(repos)} repositories")
        
        # Graph must be available; run
        
        # Initialize state
        initial_state: GraphState = {
            "repos": repos,
            "user_id": user_id,
            "run_type": run_type,
            "current_step": "initialization",
            "changed_repos": [],
            "baselines": {},
            "per_repo_results": {},
            "complexity_results": {},
            "security_results": {},
            "visualizations": [],
            "summary": {},
            "metrics": {},
            "errors": [],
        }
        
        try:
            recursion_limit = self.graph_config.get('recursion_limit', 25)
            with correlation_context() as run_id:
                config = self._build_run_config(
                    recursion_limit=recursion_limit,
                    run_id=run_id,
                    user_id=user_id,
                    run_type=run_type,
                )

                result = await self.graph.ainvoke(initial_state, config=config)

            logger.info("Analysis completed successfully")
            return {
                "status": "completed",
                "state": result,
                "run_id": run_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

    async def _initialize_analysis(self, state: GraphState) -> GraphState:
        """Initialize the analysis workflow"""
        logger.info("Step: Initialize analysis")
        errors: List[str] = []
        metrics = dict(state.get("metrics", {}))

        try:
            run = self.storage.create_analysis_run(
                repo_id=None,
                run_type=state.get("run_type", "full"),
                created_by=state.get("user_id"),
            )
            metrics["analysis_run_id"] = getattr(run, "id", None)
            if run:
                logger.info("Created analysis run: %s", run.id)
        except Exception as e:
            errors.append(f"Failed to create analysis run: {e}")

        return {
            "current_step": "initialization",
            "errors": errors,
            "metrics": metrics,
        }

    async def _sync_repositories(self, state: GraphState) -> GraphState:
        """Ensure local mirrors are synced for configured repositories"""
        logger.info("Step: Sync repositories")
        errors = list(state.get("errors", []))
        metrics = dict(state.get("metrics", {}))

        try:
            sync_result: SyncResult = self.repo_manager.sync(state.get("repos", []))
            metrics['sync'] = {
                'synced': sync_result.synced,
                'cloned': sync_result.cloned,
                'updated': sync_result.updated,
                'failed': sync_result.failed,
                'details_path': sync_result.details_path
            }
            logger.info(f"Repositories synced: {sync_result.synced} (cloned {sync_result.cloned}, updated {sync_result.updated})")
        except Exception as e:
            errors.append(f"Repository sync failed: {e}")
            logger.error(f"Repository sync failed: {e}")
        
        return {
            "current_step": "sync_repositories",
            "metrics": metrics,
            "errors": errors,
        }
    
    async def _detect_changes(self, state: GraphState) -> GraphState:
        """Detect changes in repositories"""
        logger.info("Step: Detect changes")
        
        repos = state.get("repos", [])
        changed_repos = list(repos)
        logger.info("Detected changes in %d repositories", len(changed_repos))

        return {
            "current_step": "detect_changes",
            "changed_repos": changed_repos,
        }
    
    async def _collect_repository_data(self, state: GraphState) -> GraphState:
        """Collect repository data"""
        logger.info("Step: Collect repository data")

        errors = list(state.get("errors", []))
        per_repo_results: Dict[str, Dict[str, Any]] = {}

        try:
            repo_data_list = self.data_agent.collect_repository_data(
                state.get("repos", []),
                state.get("user_id"),
            )

            for repo_data in repo_data_list:
                repo_key = f"{repo_data.owner}/{repo_data.name}"
                per_repo_results[repo_key] = {
                    'repository_data': repo_data,
                    'analysis_results': None,
                    'visualizations': None,
                }

            logger.info("Collected data for %d repositories", len(repo_data_list))

        except Exception as e:
            errors.append(f"Data collection failed: {e}")

        return {
            "current_step": "collect_data",
            "per_repo_results": per_repo_results,
            "errors": errors,
        }

    async def _analyze_complexity(self, state: GraphState) -> GraphState:
        """Analyze code complexity for repositories"""
        logger.info("Step: Analyze complexity")

        errors = list(state.get("errors", []))
        metrics = state.get("metrics", {})
        analysis_run_id = metrics.get('analysis_run_id')
        per_repo_results = {
            key: value.copy() if isinstance(value, dict) else value
            for key, value in state.get("per_repo_results", {}).items()
        }
        complexity_results = dict(state.get("complexity_results", {}))

        try:
            for repo_key, repo_result in per_repo_results.items():
                repo_data = repo_result.get('repository_data')
                repo_path = getattr(repo_data, 'path', None)

                if repo_path and os.path.exists(repo_path):
                    complexity_result = self.complexity_agent.analyze_repository(
                        repo_path=repo_path,
                        repo_name=repo_key,
                        analysis_run_id=analysis_run_id,
                    )
                    serialized = complexity_result.to_dict()
                    complexity_results[repo_key] = serialized
                    repo_result['complexity_analysis'] = serialized
                    logger.info(
                        "Complexity analysis for %s: %s hotspots found",
                        repo_key,
                        complexity_result.metrics.get('total_hotspots', 0),
                    )
                else:
                    logger.warning("Repository path not found for %s, skipping complexity analysis", repo_key)

        except Exception as e:
            logger.error("Complexity analysis failed: %s", e)
            errors.append(f"Complexity analysis failed: {e}")

        return {
            "current_step": "analyze_complexity",
            "per_repo_results": per_repo_results,
            "complexity_results": complexity_results,
            "errors": errors,
        }

    async def _analyze_security(self, state: GraphState) -> GraphState:
        """Scan repositories for security vulnerabilities"""
        logger.info("Step: Analyze security")

        errors = list(state.get("errors", []))
        metrics = state.get("metrics", {})
        analysis_run_id = metrics.get('analysis_run_id')
        per_repo_results = {
            key: value.copy() if isinstance(value, dict) else value
            for key, value in state.get("per_repo_results", {}).items()
        }
        security_results = dict(state.get("security_results", {}))

        try:
            for repo_key, repo_result in per_repo_results.items():
                repo_data = repo_result.get('repository_data')
                repo_path = getattr(repo_data, 'path', None)

                if repo_path and os.path.exists(repo_path):
                    security_result = self.security_agent.analyze_repository(
                        repo_path=repo_path,
                        repo_name=repo_key,
                        analysis_run_id=analysis_run_id,
                    )
                    serialized = security_result.to_dict()
                    security_results[repo_key] = serialized
                    repo_result['security_analysis'] = serialized
                    logger.info(
                        "Security scan for %s: %s vulnerabilities found (%s critical)",
                        repo_key,
                        security_result.summary.get('total_vulnerabilities', 0),
                        security_result.summary.get('critical', 0),
                    )
                else:
                    logger.warning("Repository path not found for %s, skipping security scan", repo_key)

        except Exception as e:
            logger.error("Security analysis failed: %s", e)
            errors.append(f"Security analysis failed: {e}")

        return {
            "current_step": "analyze_security",
            "per_repo_results": per_repo_results,
            "security_results": security_results,
            "errors": errors,
        }

    async def _analyze_repositories(self, state: GraphState) -> GraphState:
        """Analyze repositories for pain points"""
        logger.info("Step: Analyze repositories")
        errors = list(state.get("errors", []))
        per_repo_results = {
            key: value.copy() if isinstance(value, dict) else value
            for key, value in state.get("per_repo_results", {}).items()
        }

        try:
            for repo_key, repo_result in per_repo_results.items():
                repo_data = repo_result.get('repository_data')
                if not repo_data:
                    continue

                insights_data = {
                    'repository': {
                        'name': repo_data.name,
                        'owner': repo_data.owner,
                        'health_score': repo_data.health_score,
                        'open_prs': repo_data.open_prs,
                        'ci_status': repo_data.ci_status,
                    }
                }

                analysis_response = self.model_manager.analyze_pain_points(
                    insights_data['repository'],
                    repo_data.open_prs,
                )

                repo_result['analysis_results'] = {
                    'repository': repo_key,
                    'pain_points': analysis_response.metadata.get('pain_points', []) if analysis_response.metadata else [],
                    'confidence': analysis_response.confidence,
                    'model_used': analysis_response.model,
                    'solutions': [],
                }

                logger.info("Analyzed repository %s", repo_key)

                lines = [
                    "Agent: structure_architecture",
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
                self.output_agent.write_agent_log(
                    'structure_architecture',
                    repo_key,
                    content,
                    json_payload={'analysis_results': repo_result['analysis_results']},
                )

        except Exception as e:
            errors.append(f"Repository analysis failed: {e}")

        return {
            "current_step": "analyze_repositories",
            "per_repo_results": per_repo_results,
            "errors": errors,
        }
    
    async def _generate_visualizations(self, state: GraphState) -> GraphState:
        """Generate visualizations for analysis results"""
        logger.info("Step: Generate visualizations")

        errors = list(state.get("errors", []))
        metrics = state.get("metrics", {})
        analysis_run_id = metrics.get('analysis_run_id')
        per_repo_results = {
            key: value.copy() if isinstance(value, dict) else value
            for key, value in state.get("per_repo_results", {}).items()
        }

        try:
            for repo_key, repo_result in per_repo_results.items():
                analysis_results = repo_result.get('analysis_results', {})
                if not analysis_results:
                    continue

                insights_data = {
                    'repository': analysis_results.get('repository', {}),
                    'pain_points': analysis_results.get('pain_points', []),
                }

                viz_results = self.viz_agent.generate_visualizations(
                    analysis_run_id,
                    insights_data,
                    analysis_results.get('repository'),
                )

                repo_result['visualizations'] = viz_results
                logger.info("Generated %d visualizations for %s", len(viz_results), repo_key)

                lines = [
                    "Agent: visualization",
                    f"Repository: {repo_key}",
                    f"Timestamp: {datetime.now(timezone.utc).isoformat()}",
                    "",
                    "Generated Visualizations:",
                ]
                for v in viz_results:
                    lines.append(f"- {v.type}: {v.title} -> {v.filename}")
                content = "\n".join(lines)
                self.output_agent.write_agent_log(
                    'visualization',
                    repo_key,
                    content,
                    json_payload={
                        'visualizations': [
                            {
                                'type': v.type,
                                'title': v.title,
                                'filename': v.filename,
                                'quality_score': v.quality_score,
                                'approved': v.approved,
                            }
                            for v in viz_results
                        ]
                    },
                )

        except Exception as e:
            errors.append(f"Visualization generation failed: {e}")

        return {
            "current_step": "generate_visualizations",
            "per_repo_results": per_repo_results,
            "errors": errors,
        }
    
    async def _generate_report(self, state: GraphState) -> GraphState:
        """Generate analysis report"""
        logger.info("Step: Generate report")

        errors = list(state.get("errors", []))
        summary = dict(state.get("summary", {}))
        metrics = state.get("metrics", {})

        try:
            analysis_run_id = metrics.get('analysis_run_id')

            repositories = []
            analysis_results = []
            visualizations = []
            solutions = []

            for repo_key, repo_result in state.get("per_repo_results", {}).items():
                repo_data = repo_result.get('repository_data', {})
                analysis = repo_result.get('analysis_results', {})
                vizs = repo_result.get('visualizations', [])

                repositories.append({
                    'name': repo_data.name,
                    'owner': repo_data.owner,
                    'health_score': repo_data.health_score,
                    'open_prs': repo_data.open_prs,
                    'ci_status': repo_data.ci_status,
                })

                analysis_results.append(analysis)

                for viz in vizs:
                    visualizations.append({
                        'type': viz.type,
                        'title': viz.title,
                        'filename': viz.filename,
                        'mermaid_code': viz.mermaid_code,
                        'description': viz.metadata.get('description', ''),
                    })

                for pain_point in analysis.get('pain_points', []):
                    if pain_point.get('recommendations'):
                        solutions.extend(pain_point['recommendations'])

            report_path = self.output_agent.generate_analysis_report(
                analysis_run_id,
                repositories,
                analysis_results,
                visualizations,
                solutions,
                metrics,
            )

            summary['report_path'] = str(report_path)
            logger.info("Generated analysis report: %s", report_path)

        except Exception as e:
            errors.append(f"Report generation failed: {e}")

        return {
            "current_step": "generate_report",
            "summary": summary,
            "errors": errors,
        }

    async def _review_pull_requests(self, state: GraphState) -> GraphState:
        """Run programmatic PR reviews when enabled"""
        logger.info("Step: Review pull requests")
        errors = list(state.get("errors", []))
        metrics = state.get("metrics", {})

        try:
            analysis_run_id = metrics.get('analysis_run_id')
            if not getattr(self.pr_agent, 'enabled', False):
                logger.info("PR review disabled; skipping")
            else:
                for repo_key in state.get("per_repo_results", {}).keys():
                    parts = repo_key.split('/')
                    if len(parts) != 2:
                        continue
                    owner, name = parts
                    count = self.pr_agent.review_repo(owner, name, analysis_run_id)
                    logger.info("Reviewed %d open PRs for %s", count, repo_key)
        except Exception as e:
            errors.append(f"PR review failed: {e}")

        return {
            "current_step": "review_pull_requests",
            "errors": errors,
        }
    
    async def _finalize_analysis(self, state: GraphState) -> GraphState:
        """Finalize the analysis workflow"""
        logger.info("Step: Finalize analysis")

        errors = list(state.get("errors", []))
        metrics = dict(state.get("metrics", {}))

        try:
            analysis_run_id = metrics.get('analysis_run_id')

            if analysis_run_id:
                if errors:
                    self.storage.update_analysis_run_status(
                        analysis_run_id,
                        'failed',
                        f"Errors: {'; '.join(errors)}",
                    )
                else:
                    self.storage.update_analysis_run_status(
                        analysis_run_id,
                        'completed',
                    )

            self.output_agent.cleanup_old_reports()
            metrics['completed_at'] = datetime.now(timezone.utc).isoformat()
            logger.info("Analysis finalized successfully")

        except Exception as e:
            errors.append(f"Finalization failed: {e}")

        return {
            "current_step": "finalize",
            "errors": errors,
            "metrics": metrics,
        }
    
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