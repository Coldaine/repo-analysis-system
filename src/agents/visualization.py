"""
Visualization Agent
Enhanced visualization generation with Mermaid support and storage integration
"""

import logging
import json
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from src.storage.adapter import StorageAdapter
from src.models.model_manager import ModelManager

logger = logging.getLogger(__name__)

@dataclass
class VisualizationSpec:
    """Specification for a visualization"""
    type: str  # timeline, gantt, flowchart, sequence, xychart
    title: str
    description: str
    focus: str  # Primary insight this visualization conveys
    data_structure: Dict[str, Any]
    complexity: str = "medium"  # simple, medium, complex
    priority: int = 1  # 1=high, 2=medium, 3=low

@dataclass
class VisualizationResult:
    """Result of visualization generation"""
    type: str
    title: str
    filename: str
    mermaid_code: str
    metadata: Dict[str, Any]
    quality_score: float = 0.8
    approved: bool = False

class VisualizationAgent:
    """Enhanced visualization agent with model integration and storage"""
    
    def __init__(self, config: Dict, storage: StorageAdapter, model_manager: ModelManager):
        self.config = config
        self.storage = storage
        self.model_manager = model_manager
        
        viz_config = config.get('visualizations', {})
        self.limits = viz_config.get('limits', {})
        self.max_nodes = self.limits.get('max_nodes', 20)
        self.max_events = self.limits.get('max_events_per_timeline', 7)
        self.max_concurrent = self.limits.get('max_concurrent_tasks', 12)
        
        agent_config = config.get('agents', {}).get('visualization_agent', {})
        self.output_format = agent_config.get('output_format', 'mermaid')
        self.max_diagrams = agent_config.get('max_diagrams', 5)
        self.render_svg = agent_config.get('render_svg', True)
    
    def select_visualizations(self, insights_data: Dict) -> List[VisualizationSpec]:
        """Select optimal visualization types for given insights"""
        logger.info("Selecting optimal visualizations for insights")
        
        prompt = self._build_visualization_selection_prompt(insights_data)
        
        try:
            response = self.model_manager.call_model(
                'glm_4_6', prompt, 
                fallback_models=['minimax']
            )
            
            return self._parse_visualization_selection(response.content)
            
        except Exception as e:
            logger.error(f"Visualization selection failed: {e}")
            return self._generate_fallback_visualizations(insights_data)
    
    def generate_visualizations(self, analysis_run_id: int, insights_data: Dict, 
                           repository_data: Dict = None) -> List[VisualizationResult]:
        """Generate Mermaid visualizations from analysis results"""
        logger.info(f"Generating visualizations for analysis run {analysis_run_id}")
        
        # Select visualization types
        viz_specs = self.select_visualizations(insights_data)
        
        results = []
        for spec in viz_specs[:self.max_diagrams]:  # Limit number of diagrams
            try:
                result = self._generate_single_visualization(spec, insights_data, repository_data)
                if result:
                    # Store in database
                    if analysis_run_id:
                        self._store_visualization(analysis_run_id, result)
                    results.append(result)
                    
            except Exception as e:
                logger.error(f"Failed to generate {spec.type} visualization: {e}")
                continue
        
        return results
    
    def _store_visualization(self, analysis_run_id: int, result: VisualizationResult):
        """Store visualization in PostgreSQL"""
        try:
            with self.storage.get_session() as session:
                viz = self.storage.create_visualization(
                    run_id=analysis_run_id,
                    viz_type=result.type,
                    title=result.title,
                    description=result.metadata.get('description', ''),
                    mermaid_code=result.mermaid_code,
                    file_path=result.filename,
                    extra_metadata=result.metadata
                )
                logger.info(f"Stored visualization: {result.type} - {result.title}")
                return viz
                
        except Exception as e:
            logger.error(f"Failed to store visualization {result.type}: {e}")
    
    def _generate_single_visualization(self, spec: VisualizationSpec, insights_data: Dict, 
                                  repository_data: Dict = None) -> Optional[VisualizationResult]:
        """Generate a single visualization"""
        logger.info(f"Generating {spec.type} visualization: {spec.title}")
        
        prompt = self._build_generation_prompt(spec, insights_data, repository_data)
        
        try:
            response = self.model_manager.call_model(
                'glm_4_6', prompt,
                fallback_models=['minimax']
            )
            
            mermaid_code = self._extract_mermaid_code(response.content)
            if not mermaid_code:
                logger.warning(f"No Mermaid code generated for {spec.type}")
                return None
            
            # Generate filename
            timestamp = datetime.now().strftime('%Y%m%d')
            filename = f"{spec.type.replace('_', '-')}-{timestamp}.mmd"
            
            # Quality assessment
            quality_score = self._assess_quality(mermaid_code, spec)
            
            return VisualizationResult(
                type=spec.type,
                title=spec.title,
                filename=filename,
                mermaid_code=mermaid_code,
                metadata={
                    'description': spec.description,
                    'focus': spec.focus,
                    'complexity': spec.complexity,
                    'generated_at': datetime.now(timezone.utc).isoformat(),
                    'data_structure': spec.data_structure
                },
                quality_score=quality_score,
                approved=quality_score >= 0.7
            )
            
        except Exception as e:
            logger.error(f"Failed to generate {spec.type}: {e}")
            return None
    
    def _build_visualization_selection_prompt(self, insights_data: Dict) -> str:
        """Build prompt for visualization selection"""
        return f"""
        You are a Visualization Selection Agent. Given repository analysis insights, determine the optimal Mermaid visualization types and structure.

        Available Visualization Types:
        1. Timeline: Ideal for temporal data, PR lifecycles, commit history
        2. Gantt: Perfect for workflow scheduling, agent coordination, task dependencies
        3. Flowchart: Best for decision processes, pain point resolution, CI/CD flows
        4. Sequence: Optimal for agent interactions, API calls, system communications
        5. XY Chart: Good for metrics comparison, trend analysis, performance data

        Analysis Insights:
        {json.dumps(insights_data, indent=2)}

        Selection Criteria:
        - Number of entities involved
        - Need for dependency visualization
        - Audience technical level
        - Data complexity and volume

        For each insight, recommend the most effective visualization type.

        Return JSON format:
        {{
            "visualizations": [
                {{
                    "type": "timeline|gantt|flowchart|sequence|xychart",
                    "title": "Descriptive title",
                    "focus": "Primary insight this visualization conveys",
                    "data_structure": {{
                        "entities": ["list of key entities"],
                        "relationships": ["list of relationships"],
                        "metrics": ["key metrics to visualize"]
                    }},
                    "complexity": "simple|medium|complex",
                    "priority": 1-3
                }}
            ]
        }}

        Choose visualization types that most effectively communicate insights while maintaining clarity and conciseness.
        """
    
    def _parse_visualization_selection(self, response_content: str) -> List[VisualizationSpec]:
        """Parse visualization selection response"""
        try:
            data = json.loads(response_content)
            if 'visualizations' in data:
                specs = []
                for viz in data['visualizations']:
                    spec = VisualizationSpec(
                        type=viz.get('type', 'flowchart'),
                        title=viz.get('title', 'Analysis Visualization'),
                        description=viz.get('focus', ''),
                        focus=viz.get('focus', ''),
                        data_structure=viz.get('data_structure', {}),
                        complexity=viz.get('complexity', 'medium'),
                        priority=viz.get('priority', 2)
                    )
                    specs.append(spec)
                return specs
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse visualization selection: {e}")
        
        # Fallback visualizations
        return self._generate_fallback_specs()
    
    def _generate_fallback_specs(self) -> List[VisualizationSpec]:
        """Generate fallback visualization specifications"""
        return [
            VisualizationSpec(
                type="flowchart",
                title="Repository Analysis Flow",
                description="High-level analysis workflow",
                focus="Analysis process and pain point identification",
                data_structure={},
                complexity="medium",
                priority=1
            ),
            VisualizationSpec(
                type="timeline",
                title="Repository Timeline",
                description="Recent activity and changes",
                focus="Temporal patterns and activity trends",
                data_structure={},
                complexity="simple",
                priority=2
            )
        ]
    
    def _build_generation_prompt(self, spec: VisualizationSpec, insights_data: Dict, 
                            repository_data: Dict = None) -> str:
        """Build prompt for Mermaid code generation"""
        
        base_prompt = f"""
        You are a Mermaid Generation Agent. Convert visualization specifications into clean, effective Mermaid code following best practices.

        Visualization Specification:
        - Type: {spec.type}
        - Title: {spec.title}
        - Focus: {spec.focus}
        - Complexity: {spec.complexity}
        - Data Structure: {json.dumps(spec.data_structure, indent=2)}

        Code Standards:
        - Maximum {self.max_nodes} nodes for flowcharts
        - Clear section divisions for timelines
        - Descriptive node and edge labels
        - Consistent styling and theming

        Analysis Data:
        {json.dumps(insights_data, indent=2)}
        """
        
        if repository_data:
            base_prompt += f"""
        Repository Context:
        - Name: {repository_data.get('name', 'Unknown')}
        - Owner: {repository_data.get('owner', 'Unknown')}
        - Language: {repository_data.get('language', 'Unknown')}
        - Health Score: {repository_data.get('health_score', 'Unknown')}
            """
        
        # Add type-specific instructions
        if spec.type == "timeline":
            base_prompt += f"""
        
        Generate a timeline visualization showing:
        - Key events and milestones
        - PR lifecycle phases
        - Activity patterns over time
        - Maximum {self.max_events} events
        
        Use timeline syntax with clear date markers and event descriptions.
        """
        
        elif spec.type == "gantt":
            base_prompt += f"""
        
        Generate a Gantt chart showing:
        - Analysis workflow phases
        - Agent coordination and dependencies
        - Task durations and overlaps
        - Maximum {self.max_concurrent} concurrent tasks
        
        Use gantt syntax with sections, tasks, and dependencies.
        """
        
        elif spec.type == "flowchart":
            base_prompt += f"""
        
        Generate a flowchart showing:
        - Analysis decision points
        - Pain point resolution processes
        - CI/CD pipeline stages
        - Agent interactions
        
        Use flowchart TD syntax with clear decision points and process flows.
        """
        
        elif spec.type == "sequence":
            base_prompt += f"""
        
        Generate a sequence diagram showing:
        - Agent communication patterns
        - API call sequences
        - System interactions
        - Data flow between components
        
        Use sequenceDiagram syntax with clear participants and message flows.
        """
        
        elif spec.type == "xychart":
            base_prompt += f"""
        
        Generate an XY chart showing:
        - Performance metrics
        - Trend analysis
        - Comparative data
        - Key indicators over time
        
        Use xychart-beta syntax with clear axis labels and data series.
        """
        
        base_prompt += """
        
        Return only the Mermaid code block without explanations or markdown formatting.
        The code should be ready to save as a .mmd file.
        """
        
        return base_prompt
    
    def _extract_mermaid_code(self, response_content: str) -> Optional[str]:
        """Extract Mermaid code from model response"""
        # Look for Mermaid code blocks
        start_marker = "```mermaid"
        end_marker = "```"
        
        start_idx = response_content.find(start_marker)
        if start_idx == -1:
            # No code block found, check if entire response is code
            if any(line.strip().startswith(('graph', 'flowchart', 'sequenceDiagram', 'gantt', 'timeline', 'xychart-beta')) 
                for line in response_content.split('\n')):
                return response_content.strip()
            return None
        
        start_idx += len(start_marker)
        end_idx = response_content.find(end_marker, start_idx)
        
        if end_idx == -1:
            return None
        
        return response_content[start_idx:end_idx].strip()
    
    def _assess_quality(self, mermaid_code: str, spec: VisualizationSpec) -> float:
        """Assess quality of generated Mermaid code"""
        score = 0.8  # Base score
        
        # Check for basic syntax
        if not mermaid_code:
            return 0.0
        
        # Type-specific quality checks
        if spec.type == "flowchart":
            node_count = mermaid_code.count('-->') + mermaid_code.count('--->')
            if node_count > self.max_nodes:
                score -= 0.2
            if 'A[' in mermaid_code and 'B[' in mermaid_code:
                score += 0.1  # Has proper decision points
        
        elif spec.type == "timeline":
            if 'section' in mermaid_code:
                score += 0.1
            event_count = mermaid_code.count(':')
            if event_count > self.max_events:
                score -= 0.1
        
        # General quality checks
        if mermaid_code.count('\n') < 3:  # Too short
            score -= 0.2
        
        if 'style' in mermaid_code or 'classDef' in mermaid_code:
            score += 0.1  # Has styling
        
        return max(0.0, min(1.0, score))
    
    def get_supported_types(self) -> List[str]:
        """Get list of supported visualization types"""
        return ["timeline", "gantt", "flowchart", "sequence", "xychart"]
    
    def validate_spec(self, spec: VisualizationSpec) -> Dict[str, Any]:
        """Validate a visualization specification"""
        errors = []
        warnings = []
        
        if spec.type not in self.get_supported_types():
            errors.append(f"Unsupported visualization type: {spec.type}")
        
        if not spec.title:
            errors.append("Title is required")
        
        if spec.complexity not in ["simple", "medium", "complex"]:
            warnings.append(f"Unknown complexity level: {spec.complexity}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings
        }
    
    def generate_mock_visualization(self, viz_type: str, title: str = "Mock Visualization") -> VisualizationResult:
        """Generate a mock visualization for testing"""
        mock_codes = {
            "flowchart": """flowchart TD
    A[Start] --> B{Analyze Data}
    B --> C{Identify Issues}
    C --> D{Generate Solutions}
    D --> E[End]""",
            
            "timeline": """timeline
    title Repository Timeline
    section Analysis Phase
    Data Collection : 2024-01-01
    Analysis Complete : 2024-01-02
    section Implementation Phase
    Solution Design : 2024-01-03
    Implementation : 2024-01-10""",
            
            "gantt": """gantt
    title Analysis Workflow
    dateFormat  YYYY-MM-DD
    section Data Collection
    Gather Repository Data :a1, 2024-01-01, 1d
    section Analysis
    Analyze Pain Points :a2, after a1, 2d
    Generate Solutions :a3, after a2, 1d""",
            
            "sequence": """sequenceDiagram
    participant Agent
    participant Model
    participant Storage
    
    Agent->>Model: Request Analysis
    Model-->>Agent: Return Results
    Agent->>Storage: Store Data"""
        }
        
        mermaid_code = mock_codes.get(viz_type, mock_codes["flowchart"])
        
        return VisualizationResult(
            type=viz_type,
            title=title,
            filename=f"{viz_type}-mock.mmd",
            mermaid_code=mermaid_code,
            metadata={"mock": True, "generated_for": "testing"},
            quality_score=0.9,
            approved=True
        )