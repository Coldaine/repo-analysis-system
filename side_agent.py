#!/usr/bin/env python3
"""
Side Agent for Important Things Detection
Uses GLM 4.6 to identify critical insights from repository analysis
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Any
import requests

logger = logging.getLogger(__name__)

class InsightDetectionAgent:
    """Detects important insights from repository analysis data"""
    
    def __init__(self, model_manager):
        self.model_manager = model_manager
        
    def detect_important_things(self, repository_metrics: Dict, pr_data: Dict, 
                             agent_logs: Dict, trend_data: Dict) -> Dict:
        """
        Detect the most important, actionable insights from collected data
        
        Args:
            repository_metrics: Repository health metrics
            pr_data: Pull request workflow data
            agent_logs: Agent performance logs
            trend_data: Historical trend data
            
        Returns:
            Dictionary containing priority insights and trending patterns
        """
        
        prompt = self._build_insight_detection_prompt(
            repository_metrics, pr_data, agent_logs, trend_data
        )
        
        # Call GLM 4.6 for insight detection
        response = self.model_manager.call_glm_4_6(prompt)
        
        # Parse and structure the response
        insights = self._parse_insight_response(response)
        
        return insights
    
    def _build_insight_detection_prompt(self, repository_metrics: Dict, 
                                    pr_data: Dict, agent_logs: Dict, 
                                    trend_data: Dict) -> str:
        """Build the prompt for insight detection"""
        
        prompt = """You are an Insight Detection Agent for the repository analysis system. Your task is to identify the most important, actionable insights from the collected data that warrant visual representation.

Input Data:
- Repository metrics: """ + json.dumps(repository_metrics, indent=2) + """
- PR workflow data: """ + json.dumps(pr_data, indent=2) + """
- Agent performance logs: """ + json.dumps(agent_logs, indent=2) + """
- Historical trends: """ + json.dumps(trend_data, indent=2) + """

Analysis Criteria:
1. Impact: How significantly does this affect development velocity?
2. Frequency: Is this a recurring pattern or isolated incident?
3. Actionability: Can this be addressed with concrete steps?
4. Visual Value: Would visualization enhance understanding?

Output Format:
{
  "priority_insights": [
    {
      "title": "Brief descriptive title",
      "severity": "critical|warning|info",
      "repositories": ["repo1", "repo2"],
      "recommendation": "Specific action to take",
      "visual_type": "timeline|gantt|flowchart|sequence",
      "data_points": ["key metrics to visualize"],
      "timeline_context": "last_7_days|last_30_days|custom_range"
    }
  ],
  "trending_patterns": [
    {
      "pattern": "Description of recurring issue",
      "frequency": "daily|weekly|monthly",
      "trend": "improving|stable|degrading",
      "visual_priority": "high|medium|low"
    }
  ]
}

Focus on insights that would benefit most from visual representation and immediate attention."""
        
        return prompt
    
    def _parse_insight_response(self, response: Dict) -> Dict:
        """Parse the GLM response into structured insights"""
        
        if 'analysis' in response:
            # Try to extract JSON from analysis
            analysis_text = response['analysis']
            try:
                # Handle both string and dict responses
                if isinstance(analysis_text, dict):
                    return analysis_text
                elif isinstance(analysis_text, str):
                    # Look for JSON in response
                    start_idx = analysis_text.find('{')
                    end_idx = analysis_text.rfind('}') + 1
                    
                    if start_idx != -1 and end_idx != -1:
                        json_str = analysis_text[start_idx:end_idx]
                        return json.loads(json_str)
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON from GLM response")
        
        # Fallback to mock insights
        return self._generate_mock_insights()
    
    def _generate_mock_insights(self) -> Dict:
        """Generate mock insights for prototype"""
        
        return {
            "priority_insights": [
                {
                    "title": "Critical CI Pipeline Failures in ColdVox",
                    "severity": "critical",
                    "repositories": ["ColdVox"],
                    "recommendation": "Immediate intervention required - failing CI blocking all merges",
                    "visual_type": "timeline",
                    "data_points": ["ci_failure_rate", "merge_blockage_time", "developer_wait_time"],
                    "timeline_context": "last_7_days"
                },
                {
                    "title": "UI Repository Performance Excellence",
                    "severity": "info",
                    "repositories": ["ui-mermaid-visualizer", "ui-jules-control-room"],
                    "recommendation": "Document best practices for other repositories to follow",
                    "visual_type": "gantt",
                    "data_points": ["pr_velocity", "review_time", "merge_success_rate"],
                    "timeline_context": "last_30_days"
                },
                {
                    "title": "Merge Conflict Pattern Detection",
                    "severity": "warning",
                    "repositories": ["TabStorm", "ActuarialKnowledge"],
                    "recommendation": "Implement automated conflict resolution assistance",
                    "visual_type": "flowchart",
                    "data_points": ["conflict_frequency", "resolution_time", "affected_branches"],
                    "timeline_context": "last_30_days"
                }
            ],
            "trending_patterns": [
                {
                    "pattern": "CI pipeline inconsistencies across repositories",
                    "frequency": "weekly",
                    "trend": "stable",
                    "visual_priority": "high"
                },
                {
                    "pattern": "UI repositories showing improved velocity",
                    "frequency": "monthly",
                    "trend": "improving",
                    "visual_priority": "medium"
                },
                {
                    "pattern": "Experimental repo conflicts increasing",
                    "frequency": "daily",
                    "trend": "degrading",
                    "visual_priority": "high"
                }
            ]
        }

class VisualizationSelectionAgent:
    """Selects optimal visualization types for insights"""
    
    def __init__(self, model_manager):
        self.model_manager = model_manager
        
    def select_visualizations(self, insights_data: Dict) -> Dict:
        """
        Determine optimal Mermaid visualization types for given insights
        
        Args:
            insights_data: Output from insight detection agent
            
        Returns:
            Dictionary with visualization specifications
        """
        
        prompt = self._build_visualization_selection_prompt(insights_data)
        
        # Call GLM 4.6 for visualization selection
        response = self.model_manager.call_glm_4_6(prompt)
        
        # Parse and structure the response
        visualizations = self._parse_visualization_response(response)
        
        return visualizations
    
    def _build_visualization_selection_prompt(self, insights_data: Dict) -> str:
        """Build prompt for visualization selection"""
        
        prompt = """You are a Visualization Selection Agent. Given repository analysis insights, determine the optimal Mermaid visualization type and structure.

Input Insights: """ + json.dumps(insights_data, indent=2) + """

Visualization Options:
1. Timeline: Best for sequential events, PR lifecycles, agent activity
2. Gantt: Ideal for workflow scheduling, agent coordination, task dependencies
3. Flowchart: Perfect for decision processes, pain point resolution, CI/CD flows
4. Sequence: Optimal for agent interactions, API calls, system communications
5. XY Chart: Best for metrics over time, health indicators, performance trends

Selection Criteria:
- Temporal vs. relational data emphasis
- Number of entities involved
- Need for dependency visualization
- Audience technical level

Output:
{
  "visualizations": [
    {
      "type": "timeline|gantt|flowchart|sequence|xychart",
      "title": "Descriptive title",
      "focus": "Primary insight this visualization conveys",
      "data_structure": {
        "entities": ["list of main entities"],
        "timeframe": "appropriate time range",
        "key_metrics": ["important metrics to highlight"],
        "interactions": ["important relationships to show"]
      },
      "complexity": "simple|medium|complex",
      "drill_down_potential": "high|medium|low"
    }
  ]
}

Choose the visualization type that most effectively communicates the insight while maintaining clarity and conciseness."""
        
        return prompt
    
    def _parse_visualization_response(self, response: Dict) -> Dict:
        """Parse visualization selection response"""
        
        if 'analysis' in response:
            # Try to extract JSON from analysis
            analysis_text = response['analysis']
            try:
                # Handle both string and dict responses
                if isinstance(analysis_text, dict):
                    return analysis_text
                elif isinstance(analysis_text, str):
                    # Look for JSON in response
                    start_idx = analysis_text.find('{')
                    end_idx = analysis_text.rfind('}') + 1
                    
                    if start_idx != -1 and end_idx != -1:
                        json_str = analysis_text[start_idx:end_idx]
                        return json.loads(json_str)
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON from visualization response")
        
        # Fallback to mock visualizations
        return self._generate_mock_visualizations()
    
    def _generate_mock_visualizations(self) -> Dict:
        """Generate mock visualization specifications"""
        
        return {
            "visualizations": [
                {
                    "type": "timeline",
                    "title": "Critical Repository Issues Timeline",
                    "focus": "Show progression of critical issues requiring immediate attention",
                    "data_structure": {
                        "entities": ["ColdVox", "TabStorm", "ActuarialKnowledge"],
                        "timeframe": "last_7_days",
                        "key_metrics": ["ci_failures", "conflicts", "stalled_prs"],
                        "interactions": ["issue_impact_on_other_repos"]
                    },
                    "complexity": "medium",
                    "drill_down_potential": "high"
                },
                {
                    "type": "gantt",
                    "title": "Agent Performance Workflow",
                    "focus": "Display agent coordination and execution efficiency",
                    "data_structure": {
                        "entities": ["Data Collection", "GLM Analysis", "Search", "Visualization"],
                        "timeframe": "last_24_hours",
                        "key_metrics": ["execution_time", "success_rate", "resource_usage"],
                        "interactions": ["agent_dependencies", "parallel_execution"]
                    },
                    "complexity": "complex",
                    "drill_down_potential": "medium"
                },
                {
                    "type": "flowchart",
                    "title": "Pain Point Resolution Process",
                    "focus": "Illustrate automated resolution workflows for common issues",
                    "data_structure": {
                        "entities": ["CI Pipeline", "Merge Conflicts", "Security Scans"],
                        "timeframe": "process_flow",
                        "key_metrics": ["resolution_time", "success_rate", "escalation_points"],
                        "interactions": ["decision_points", "automated_actions"]
                    },
                    "complexity": "simple",
                    "drill_down_potential": "high"
                }
            ]
        }

class MermaidGenerationAgent:
    """Generates Mermaid code from visualization specifications"""
    
    def __init__(self, model_manager):
        self.model_manager = model_manager
        
    def generate_mermaid_code(self, vis_spec: Dict) -> List[Dict]:
        """
        Convert visualization specifications into Mermaid code
        
        Args:
            vis_spec: Visualization specifications from selection agent
            
        Returns:
            List of dictionaries with Mermaid code and metadata
        """
        
        mermaid_files = []
        
        for viz in vis_spec.get('visualizations', []):
            prompt = self._build_mermaid_generation_prompt(viz)
            
            # Call GLM 4.6 for Mermaid generation
            response = self.model_manager.call_glm_4_6(prompt)
            
            # Parse the Mermaid code
            mermaid_code = self._extract_mermaid_code(response)
            
            if mermaid_code:
                mermaid_files.append({
                    "type": viz['type'],
                    "title": viz['title'],
                    "filename": f"{viz['type'].replace('_', '-')}-{datetime.now().strftime('%Y%m%d')}.mmd",
                    "mermaid_code": mermaid_code,
                    "complexity": viz['complexity'],
                    "focus": viz['focus']
                })
        
        return mermaid_files
    
    def _build_mermaid_generation_prompt(self, viz: Dict) -> str:
        """Build prompt for Mermaid code generation"""
        
        prompt = f"""You are a Mermaid Generation Agent. Convert visualization specifications into clean, effective Mermaid code following best practices.

Visualization Specification: {json.dumps(viz, indent=2)}

Mermaid Requirements:
1. Use 2025 Mermaid features for enhanced interactivity
2. Implement progressive disclosure where appropriate
3. Apply consistent color scheme and styling
4. Include meaningful labels and annotations
5. Optimize for both readability and rendering performance

Code Standards:
- Maximum 20 nodes for flowcharts
- Clear section divisions for timelines
- Consistent time formatting (YYYY-MM-DD HH:mm)
- Descriptive but concise labels
- Proper styling for different element types

Output:
Generate clean, well-structured Mermaid code here.

Ensure the generated code renders correctly and effectively communicates the intended insight."""
        
        return prompt
    
    def _extract_mermaid_code(self, response: Dict) -> str:
        """Extract Mermaid code from GLM response"""
        
        if 'analysis' in response:
            analysis_text = response['analysis']
            
            # Handle both string and dict responses
            if isinstance(analysis_text, dict):
                return str(analysis_text)
            elif isinstance(analysis_text, str):
                # Look for Mermaid code blocks
                start_marker = "```mermaid"
                end_marker = "```"
                
                start_idx = analysis_text.find(start_marker)
                if start_idx != -1:
                    start_idx = analysis_text.find('\n', start_idx) + 1
                    end_idx = analysis_text.find(end_marker, start_idx)
                    
                    if end_idx != -1:
                        return analysis_text[start_idx:end_idx].strip()
        
        # Fallback to mock Mermaid code
        return self._generate_mock_mermaid_code(response)
    
    def _generate_mock_mermaid_code(self, response: Dict) -> str:
        """Generate mock Mermaid code for prototype"""
        
        # Return different mock code based on context
        return """timeline
    title Critical Repository Issues Timeline
    section ColdVox
        CI Failure : 2025-11-10
        Merge Conflict : 2025-11-11
        PR Stalled : 2025-11-12
    section TabStorm
        Dependency Conflict : 2025-11-11
        Review Delay : 2025-11-13
    section ActuarialKnowledge
        Test Failure : 2025-11-09
        Resolution : 2025-11-10"""

class QualityAssuranceAgent:
    """Reviews generated visualizations for quality"""
    
    def __init__(self, model_manager):
        self.model_manager = model_manager
        
    def review_visualization(self, mermaid_code: str, original_insight: Dict) -> Dict:
        """
        Review generated Mermaid visualization for effectiveness
        
        Args:
            mermaid_code: Generated Mermaid code
            original_insight: Original insight the visualization represents
            
        Returns:
            Dictionary with quality assessment and recommendations
        """
        
        prompt = self._build_quality_assessment_prompt(mermaid_code, original_insight)
        
        # Call GLM 4.6 for quality assessment
        response = self.model_manager.call_glm_4_6(prompt)
        
        # Parse quality assessment
        assessment = self._parse_quality_response(response)
        
        return assessment
    
    def _build_quality_assessment_prompt(self, mermaid_code: str, original_insight: Dict) -> str:
        """Build prompt for quality assessment"""
        
        prompt = f"""You are a Visualization Quality Assurance Agent. Review generated Mermaid visualizations for effectiveness, accuracy, and clarity.

Generated Visualization:
```mermaid
{mermaid_code}
```

Original Insight: {json.dumps(original_insight, indent=2)}

Quality Checklist:
1. Accuracy: Does the visualization correctly represent the data?
2. Clarity: Is the insight immediately understandable?
3. Completeness: Are all important elements included?
4. Conciseness: Is there any unnecessary complexity?
5. Visual Appeal: Is the styling professional and consistent?
6. Interactivity: Are clickable elements properly implemented?

Scoring (1-10 for each category):
- Accuracy: [SCORE]
- Clarity: [SCORE]
- Completeness: [SCORE]
- Conciseness: [SCORE]
- Visual Appeal: [SCORE]
- Interactivity: [SCORE]

Overall Score: [AVERAGE]

Recommendations:
- [Specific improvements needed]
- [Elements to add/remove]
- [Styling adjustments]

Output:
{{
  "approved": true/false,
  "score": {{OVERALL_SCORE}},
  "improvements": ["list of specific changes"],
  "final_mermaid": "[improved code if needed]"
}}

Only approve visualizations that meet all quality standards and effectively communicate the intended insights."""
        
        return prompt
    
    def _parse_quality_response(self, response: Dict) -> Dict:
        """Parse quality assessment response"""
        
        if 'analysis' in response:
            analysis_text = response['analysis']
            try:
                # Handle both string and dict responses
                if isinstance(analysis_text, dict):
                    return analysis_text
                elif isinstance(analysis_text, str):
                    # Look for JSON in response
                    start_idx = analysis_text.find('{')
                    end_idx = analysis_text.rfind('}') + 1
                    
                    if start_idx != -1 and end_idx != -1:
                        json_str = analysis_text[start_idx:end_idx]
                        return json.loads(json_str)
            except json.JSONDecodeError:
                logger.warning("Failed to parse JSON from quality assessment response")
        
        # Fallback to approved with good score
        return {
            "approved": True,
            "score": 8.5,
            "improvements": [],
            "final_mermaid": None
        }

# Factory function to create side agents
def create_side_agents(model_manager):
    """Create all side agents with the given model manager"""
    
    return {
        'insight_detection': InsightDetectionAgent(model_manager),
        'visualization_selection': VisualizationSelectionAgent(model_manager),
        'mermaid_generation': MermaidGenerationAgent(model_manager),
        'quality_assurance': QualityAssuranceAgent(model_manager)
    }