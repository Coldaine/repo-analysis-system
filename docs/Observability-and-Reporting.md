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

## 📈 Metrics

We track the following metrics to ensure system health:

1.  **Success Rate**: Percentage of successful analysis runs.
2.  **Latency**: Time taken for each agent to complete its task.
3.  **Token Usage**: Input/output tokens per run (cost tracking).
4.  **Error Rate**: Frequency of specific error types.

## 📝 Reporting

- Progressive disclosure: Level 1 (exec summary), Level 2 (visuals), Level 3 (detailed analysis), Level 4 (raw data).
- Report templates (status, repo init) live in Templates-and-Examples; Output agent populates them.
- GitHub comments/status checks (when enabled) should link to Levels 1–3; avoid dumping raw model text inline.

## 📊 Dashboards (Future)
- Consolidate metrics/health from PostgreSQL into a dashboard.
- Visual design ideas live in `archive/visual-design-history/`; current visuals are Mermaid assets tied to reports.
