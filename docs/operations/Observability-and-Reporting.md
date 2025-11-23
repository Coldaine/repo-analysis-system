# Observability and Reporting

**Status**: Canonical
**Last Updated**: November 23, 2025

## 📊 Logging Strategy

We use a structured logging approach that captures both system events and agent reasoning.

### Log Levels
-   **DEBUG**: Detailed agent thought processes and raw API responses.
-   **INFO**: High-level workflow steps (e.g., "Forensics Agent started").
-   **WARNING**: Non-critical failures (e.g., "Rate limit hit, retrying").
-   **ERROR**: Critical failures stopping a workflow.

### Log Storage
-   **Console**: Real-time streaming of INFO/ERROR logs.
-   **File**: `logs/app.log` (rotating daily).
-   **Database**: `run_logs` table stores structured execution data.

### Structured Logging Standards
-   **Format**: JSON for all logs.
-   **Mandatory Fields**: `timestamp`, `level`, `correlation_id` (Run ID), `repository`, `event_type`.
-   **Context**: Every log entry must carry the `run_id` to trace execution across parallel agents.

## 📈 Metrics

We track the following metrics to ensure system health:

1.  **Success Rate**: Percentage of successful analysis runs.
2.  **Latency**: Time taken for each agent to complete its task.
3.  **Token Usage**: Input/output tokens per run (cost tracking).
4.  **Error Rate**: Frequency of specific error types.
5.  **Dormancy**: Time since last analysis per repository.

## 📝 Reporting

### Progressive Disclosure
Reports are generated in layers to serve different stakeholders:
1.  **Level 1 (Executive Summary)**: High-level findings, health score, critical alerts.
2.  **Level 2 (Visuals)**: Mermaid diagrams (Gantt, Flowchart) visualizing the analysis.
3.  **Level 3 (Detailed Analysis)**: Deep dive into specific findings (e.g., Forensics evidence, Complexity metrics).
4.  **Level 4 (Raw Data)**: Full JSON artifacts and raw model outputs for debugging.

### Templates
Standard templates (Status Report, Repo Init) are defined in `docs/Templates-and-Examples.md`. The Output Agent populates these templates dynamically.

### GitHub Integration
-   **Comments**: When enabled, the system posts a summary comment on the PR/Issue.
-   **Status Checks**: The system updates the commit status (pending/success/failure) based on the analysis result.
-   **Links**: Comments link to the detailed Level 3 report (if hosted) or provide collapsible sections.

## 📊 Dashboards (Future)
-   **Goal**: Consolidate metrics/health from PostgreSQL into a web-based dashboard.
-   **Data Source**: `run_logs` and `repo_metrics` tables in PostgreSQL.
-   **Visuals**: Re-use the Mermaid generation logic for real-time status charts.

## 🎨 Visualization Constraints
-   **Types**: Timeline, Gantt, Flowchart, Sequence, XYChart.
-   **Limits**: Max 20 nodes/events per visualization to ensure readability.
-   **Rendering**: Visuals are generated as Mermaid code blocks in Markdown reports.

## 🔗 Tracing & Metrics Integration
- Attach `correlation_id` to all spans/logs; propagate through tool calls and subgraphs.
- Configure tracing (LangSmith/OpenTelemetry) to capture node/tool spans with tags: repo, job ID, run type, recursion_limit breaches.
- Emit scores/evaluations on spans where applicable (e.g., report quality, visualization quality) for later analysis.
- Tag errors/failures with agent/node identifiers; record retries/backoff.

## 🛰️ Tracing & LangSmith (Examples)

We integrate distributed traces via OpenTelemetry and annotate spans with LangGraph metadata. Example instrumentation in Python:

```python
from opentelemetry import trace
from opentelemetry.trace import Span

tracer = trace.get_tracer(__name__)

def instrumented_node(state, runtime):
	with tracer.start_as_current_span("agent_node_execute") as span:
		span.set_attribute("repo", runtime.context.repository)
		span.set_attribute("thread_id", runtime.context.thread_id)
		span.set_attribute("agent", "forensics")
		# Execute node work
		result = do_work(state)
		# Attach a score if applicable
		span.set_attribute("score.feedback", 0.87)
		return result
```

LangSmith integration: ensure LangSmith SDK is configured to read OTel traces or use a LangSmith client to upload trace metadata and scores.

```python
# Attach a feedback score to a LangSmith trace (pseudo-code)
langsmith_client = LangSmithClient(api_key=LANGSMITH_API_KEY)
langsmith_client.tag_trace(trace_id, {"satisfaction": 0.9, "quality": "high"})
```

