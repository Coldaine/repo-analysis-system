"""
Output Agent
Enhanced output generation with multiple format support and storage integration
"""

import os
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

from src.storage.adapter import StorageAdapter, AnalysisRun
from src.models.model_manager import ModelManager

logger = logging.getLogger(__name__)

@dataclass
class OutputConfig:
    """Configuration for output generation"""
    output_directory: str
    file_prefix: str
    generate_markdown: bool = True
    generate_mermaid: bool = True
    generate_json: bool = False
    compress_outputs: bool = False

@dataclass
class ReportData:
    """Data structure for analysis report"""
    timestamp: datetime
    repositories: List[Dict[str, Any]]
    analysis_results: List[Dict[str, Any]]
    visualizations: List[Dict[str, Any]]
    solutions: List[Dict[str, Any]]
    workflow_stats: Dict[str, Any]

class OutputAgent:
    """Enhanced output agent with multiple format support"""
    
    def __init__(self, config: Dict, storage: StorageAdapter, model_manager: ModelManager):
        self.config = config
        self.storage = storage
        self.model_manager = model_manager
        
        output_config = config.get('agents', {}).get('output_agent', {})
        self.output_config = OutputConfig(
            output_directory=output_config.get('output_directory', 'review_logging'),
            file_prefix=output_config.get('file_prefix', 'analysis-run'),
            generate_markdown=output_config.get('generate_markdown', True),
            generate_mermaid=output_config.get('generate_mermaid', True),
            generate_json=output_config.get('generate_json', False),
            compress_outputs=output_config.get('compress_outputs', False)
        )
        
        # Ensure output directories exist
        self.output_dir = Path(self.output_config.output_directory)
        self.viz_dir = self.output_dir / "visualizations"
        self.reports_dir = self.output_dir / "summaries"
        self.agent_logs_root = self.output_dir
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.viz_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        
    def write_agent_log(self, agent_name: str, repo_name: str, content: str, 
                        timestamp: Optional[datetime] = None, json_payload: Dict[str, Any] = None) -> str:
        """Write per-agent, per-run log files under review_logging/<agent>/<YYYY-MM-DD>/"""
        ts = timestamp or datetime.now(timezone.utc)
        date_dir = ts.strftime('%Y-%m-%d')
        stamp = ts.strftime('%Y%m%d_%H%M%S')
        safe_repo = repo_name.replace('/', '__')
        agent_dir = self.agent_logs_root / agent_name / date_dir
        agent_dir.mkdir(parents=True, exist_ok=True)
        md_path = agent_dir / f"{stamp}__{safe_repo}.md"
        with open(md_path, 'w', encoding='utf-8') as f:
            f.write(content)
        if json_payload is not None:
            json_path = agent_dir / f"{stamp}__{safe_repo}.json"
            with open(json_path, 'w', encoding='utf-8') as jf:
                json.dump(json_payload, jf, indent=2)
        logger.info(f"Wrote agent log: {md_path}")
        return str(md_path)
    
    def generate_analysis_report(
        self,
        analysis_run_id: int,
        repositories: List[Dict[str, Any]],
        analysis_results: List[Dict[str, Any]],
        visualizations: List[Dict[str, Any]],
        solutions: List[Dict[str, Any]],
        workflow_stats: Dict[str, Any]
    ) -> str:
        """Generate comprehensive analysis report"""
        logger.info(f"Generating analysis report for run {analysis_run_id}")
        
        timestamp = datetime.now(timezone.utc)
        
        # Build report data
        report_data = ReportData(
            timestamp=timestamp,
            repositories=repositories,
            analysis_results=analysis_results,
            visualizations=visualizations,
            solutions=solutions,
            workflow_stats=workflow_stats
        )
        
        # Generate different formats
        outputs = {}
        
        if self.output_config.generate_markdown:
            outputs['markdown'] = self._generate_markdown_report(report_data, analysis_run_id)
        
        if self.output_config.generate_mermaid:
            outputs['mermaid_files'] = self._save_visualizations(visualizations, analysis_run_id)
        
        if self.output_config.generate_json:
            outputs['json'] = self._generate_json_report(report_data, analysis_run_id)
        
        # Save main report
        report_path = self._save_main_report(report_data, analysis_run_id, outputs)
        
        # Store in database
        self._store_report_metadata(analysis_run_id, report_data, outputs)
        
        return str(report_path)
    
    def _generate_markdown_report(self, data: ReportData, analysis_run_id: int) -> str:
        """Generate markdown format report"""
        timestamp_str = data.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')
        
        # Executive Summary
        report = f"""# Repository Analysis Report
        
**Generated**: {timestamp_str}  
**Analysis Run ID**: {analysis_run_id}

## Executive Summary

This automated analysis examined {len(data.repositories)} repositories and identified {len(data.analysis_results)} areas requiring attention. The system used agentic workflows with GLM 4.6 for semantic analysis and generated {len(data.visualizations)} visualizations.

### Key Metrics
- **Repositories Analyzed**: {len(data.repositories)}
- **Pain Points Identified**: {sum(len(result.get('pain_points', [])) for result in data.analysis_results)}
- **Recommendations Generated**: {len(data.solutions)}
- **Visualizations Created**: {len(data.visualizations)}
- **Analysis Duration**: {data.workflow_stats.get('duration_seconds', 'N/A')} seconds

"""
        
        # Repository Details
        for i, repo in enumerate(data.repositories, 1):
            repo_name = repo.get('name', 'Unknown')
            health_score = repo.get('health_score', 0)
            open_prs = repo.get('open_prs', 0)
            ci_status = repo.get('ci_status', {}).get('conclusion', 'Unknown')
            
            report += f"""
## Repository {i}: {repo_name}

**Health Score**: {health_score:.2f}/1.0  
**Open Pull Requests**: {open_prs}  
**CI Status**: {ci_status}

"""
        
        # Analysis Results
        for i, result in enumerate(data.analysis_results, 1):
            repo_name = result.get('repository', 'Unknown')
            pain_points = result.get('pain_points', [])
            confidence = result.get('confidence', 0)
            model_used = result.get('model_used', 'Unknown')
            
            report += f"""
## Analysis {i}: {repo_name}

**Model Used**: {model_used}  
**Confidence**: {confidence:.2f}

### Identified Pain Points

"""
            
            for j, pain_point in enumerate(pain_points, 1):
                ptype = pain_point.get('type', 'Unknown')
                severity = pain_point.get('severity', 0)
                description = pain_point.get('description', 'No description')
                
                report += f"""
#### {j}. {ptype} (Severity: {severity}/5)
{description}

"""
        
        # Visualizations
        if data.visualizations:
            report += f"""
## Generated Visualizations

"""
            
            for viz in data.visualizations:
                viz_type = viz.get('type', 'Unknown')
                viz_title = viz.get('title', 'Untitled')
                viz_description = viz.get('description', '')
                
                report += f"""
### {viz_type}: {viz_title}
{viz_description}

![{viz.get('filename', viz_type)}](visualizations/{viz.get('filename', viz_type + '.mmd')})

"""
        
        # Recommendations
        if data.solutions:
            report += f"""
## Recommendations

"""
            
            for i, solution in enumerate(data.solutions, 1):
                text = solution.get('text', 'No recommendation')
                priority = solution.get('priority', 'medium')
                effort = solution.get('effort', 'Unknown')
                
                report += f"""
### {i}. {priority.upper()} Priority
{text}

**Estimated Effort**: {effort}

"""
        
        # Technical Details
        report += f"""
## Technical Details

### System Performance
{json.dumps(data.workflow_stats, indent=2)}

### Analysis Configuration
- **Models Available**: {', '.join(self.model_manager.get_available_models())}
- **Default Model**: {self.model_manager.default_model}
- **Visualization Limits**: Max {self.output_config.max_diagrams or 5} diagrams
- **Output Formats**: Markdown{', Mermaid' if self.output_config.generate_mermaid else ''}{', JSON' if self.output_config.generate_json else ''}

---
*Report generated by Repository Analysis System v2.0*
"""
        
        return report
    
    def _generate_json_report(self, data: ReportData, analysis_run_id: int) -> str:
        """Generate JSON format report"""
        json_data = {
            "metadata": {
                "generated_at": data.timestamp.isoformat(),
                "analysis_run_id": analysis_run_id,
                "version": "2.0",
                "format": "json"
            },
            "summary": {
                "repositories_analyzed": len(data.repositories),
                "pain_points_identified": sum(len(result.get('pain_points', [])) for result in data.analysis_results),
                "recommendations_generated": len(data.solutions),
                "visualizations_created": len(data.visualizations)
            },
            "repositories": data.repositories,
            "analysis_results": data.analysis_results,
            "visualizations": data.visualizations,
            "solutions": data.solutions,
            "workflow_stats": data.workflow_stats
        }
        
        return json.dumps(json_data, indent=2)
    
    def _save_visualizations(self, visualizations: List[Dict[str, Any]], analysis_run_id: int) -> List[str]:
        """Save visualization files and return list of paths"""
        saved_files = []
        
        for viz in visualizations:
            filename = viz.get('filename', f"viz-{len(saved_files)}.mmd")
            mermaid_code = viz.get('mermaid_code', '')
            
            if mermaid_code:
                viz_path = self.viz_dir / filename
                with open(viz_path, 'w', encoding='utf-8') as f:
                    f.write(mermaid_code)
                
                saved_files.append(str(viz_path))
                logger.info(f"Saved visualization: {filename}")
        
        return saved_files
    
    def _save_main_report(self, data: ReportData, analysis_run_id: int, outputs: Dict[str, str]) -> Path:
        """Save the main report file"""
        timestamp = data.timestamp.strftime('%Y%m%d_%H%M%S')
        filename = f"{self.output_config.file_prefix}-{timestamp}.md"
        report_path = self.reports_dir / filename
        
        # Generate markdown content
        markdown_content = outputs.get('markdown', '')
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        logger.info(f"Saved main report: {filename}")
        return report_path
    
    def _store_report_metadata(self, analysis_run_id: int, data: ReportData, outputs: Dict[str, str]):
        """Store report metadata in database"""
        try:
            with self.storage.get_session() as session:
                # Update analysis run with completion data
                run = session.query(AnalysisRun).filter(AnalysisRun.id == analysis_run_id).first()
                if run:
                    run.completed_at = data.timestamp
                    run.metrics = {
                        'repositories_count': len(data.repositories),
                        'pain_points_count': sum(len(result.get('pain_points', [])) for result in data.analysis_results),
                        'visualizations_count': len(data.visualizations),
                        'solutions_count': len(data.solutions),
                        'workflow_stats': data.workflow_stats
                    }
                    session.commit()
                
                logger.info(f"Stored report metadata for analysis run {analysis_run_id}")
                
        except Exception as e:
            logger.error(f"Failed to store report metadata: {e}")
    
    def generate_summary_report(self, analysis_runs: List[Dict[str, Any]]) -> str:
        """Generate summary report for multiple analysis runs"""
        logger.info("Generating summary report for multiple runs")
        
        total_repos = len(set().union(*[run.get('repositories', []) for run in analysis_runs]))
        total_pain_points = sum(len(run.get('pain_points', [])) for run in analysis_runs)
        total_visualizations = sum(len(run.get('visualizations', [])) for run in analysis_runs)
        
        summary = f"""# Analysis Summary Report

**Generated**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}

## Overview
- **Total Analysis Runs**: {len(analysis_runs)}
- **Unique Repositories**: {total_repos}
- **Total Pain Points**: {total_pain_points}
- **Total Visualizations**: {total_visualizations}

## Recent Analysis Runs

"""
        
        for i, run in enumerate(analysis_runs[-5:], 1):  # Show last 5 runs
            run_id = run.get('id', 'Unknown')
            timestamp = run.get('timestamp', 'Unknown')
            repo_count = len(run.get('repositories', []))
            
            summary += f"""
### Run {i}: ID {run_id}
- **Timestamp**: {timestamp}
- **Repositories**: {repo_count}
"""
        
        summary += f"""
---
*Summary generated by Repository Analysis System v2.0*
"""
        
        return summary
    
    def get_output_stats(self) -> Dict[str, Any]:
        """Get statistics about output generation"""
        return {
            "output_directory": str(self.output_dir),
            "visualization_directory": str(self.viz_dir),
            "report_directory": str(self.reports_dir),
            "config": {
                "generate_markdown": self.output_config.generate_markdown,
                "generate_mermaid": self.output_config.generate_mermaid,
                "generate_json": self.output_config.generate_json,
                "compress_outputs": self.output_config.compress_outputs
            }
        }
    
    def cleanup_old_reports(self, days_to_keep: int = 30) -> int:
        """Clean up old report files"""
        logger.info(f"Cleaning up reports older than {days_to_keep} days")
        
        from datetime import timedelta
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_to_keep)
        cleaned_count = 0
        
        try:
            for report_file in self.reports_dir.glob(f"{self.output_config.file_prefix}-*.md"):
                report_mtime = datetime.fromtimestamp(report_file.stat().st_mtime, tz=timezone.utc)
                if report_mtime < cutoff_date:
                    report_file.unlink()
                    cleaned_count += 1
            
            for viz_file in self.viz_dir.glob("*.mmd"):
                viz_mtime = datetime.fromtimestamp(viz_file.stat().st_mtime, tz=timezone.utc)
                if viz_mtime < cutoff_date:
                    viz_file.unlink()
                    cleaned_count += 1
            
            logger.info(f"Cleaned up {cleaned_count} old files")
            
        except Exception as e:
            logger.error(f"Cleanup failed: {e}")
        
        return cleaned_count