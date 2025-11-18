# Repository Analysis System - Enhancements

## New Features Added

This document describes the recent enhancements made to the repository analysis system.

### 1. Code Complexity Analysis

**Location**: `src/analysis/complexity_analyzer.py`

Comprehensive code quality metrics analysis including:

- **Cyclomatic Complexity**: Measures code complexity using McCabe's metric
- **Cognitive Complexity**: Estimates how difficult code is to understand
- **Nesting Depth**: Tracks maximum nesting level of control structures
- **Maintainability Index**: Composite metric for code maintainability (0-100 scale)
- **Complexity Hotspots**: Automatically identifies functions with complexity > 10

**Features**:
- Analyzes individual functions and classes
- Generates complexity distribution histograms
- Identifies top complexity hotspots
- Calculates per-file maintainability index
- Provides actionable refactoring recommendations

**Documentation**: See [`docs/COMPLEXITY_ANALYSIS.md`](docs/COMPLEXITY_ANALYSIS.md)

### 2. Dependency Vulnerability Scanning

**Location**: `src/security/vulnerability_scanner.py`

Multi-language dependency vulnerability scanning:

**Supported Languages**:
- Python (requirements.txt, pyproject.toml)
- JavaScript/Node.js (package.json)
- Rust (Cargo.toml)

**Features**:
- Queries OSV (Open Source Vulnerabilities) database
- Detects CVE IDs and GitHub Security Advisories (GHSA)
- Classifies vulnerabilities by severity (CRITICAL, HIGH, MEDIUM, LOW)
- Generates fix recommendations with version upgrades
- Provides CVSS scores and reference links

**Documentation**: See [`docs/VULNERABILITY_SCANNING.md`](docs/VULNERABILITY_SCANNING.md)

### 3. LangGraph Integration

**Location**: `src/agents/complexity_agent.py`, `src/agents/security_agent.py`

New agents integrated into the LangGraph workflow:

- **ComplexityAgent**: Performs complexity analysis and stores results as pain points
- **SecurityAgent**: Scans for vulnerabilities and stores as pain points

**Workflow Updates** (`src/orchestration/graph.py`):
- Added `analyze_complexity` node
- Added `analyze_security` node
- Extended `GraphState` with complexity and security results
- Integrated results into analysis reports

### 4. Test Coverage

**Location**: `tests/`

Comprehensive test suites:

- **Unit Tests** (`test_complexity_analyzer.py`): 15+ test cases for complexity analysis
- **Integration Tests** (`test_vulnerability_scanner.py`): 15+ test cases for vulnerability scanning

Test coverage includes:
- Simple and complex function analysis
- Nesting depth calculation
- Maintainability index computation
- Hotspot identification
- Multi-language dependency parsing
- OSV API integration
- Severity classification
- Fix recommendation generation

## Installation

### Dependencies

New dependencies added to `requirements.txt`:

```
radon>=6.0.1          # Code complexity analysis
packaging>=23.0       # Version parsing
tomli>=2.0.1          # TOML parsing (Python < 3.11)
```

### Installation Steps

```bash
# Install new dependencies
pip install -r requirements.txt

# Run tests
python -m pytest tests/test_complexity_analyzer.py
python -m pytest tests/test_vulnerability_scanner.py
```

## Usage

### Standalone Usage

#### Complexity Analysis

```python
from src.analysis.complexity_analyzer import ComplexityAnalyzer

analyzer = ComplexityAnalyzer(hotspot_threshold=10)
report = analyzer.analyze_repository("/path/to/repo")

print(f"Total hotspots: {report.metrics.total_hotspots}")
print(f"Average complexity: {report.metrics.average_complexity}")
```

#### Vulnerability Scanning

```python
from src.security.vulnerability_scanner import VulnerabilityScanner

scanner = VulnerabilityScanner()
report = scanner.scan_repository("/path/to/repo")

print(f"Total vulnerabilities: {report.summary['total_vulnerabilities']}")
print(f"Critical: {report.summary['critical']}")
```

### Integrated Workflow

The new features are automatically included when running the full analysis:

```bash
python scripts/run_graph.py analyze --repos "owner/repo" --user-id 1
```

Results are:
- Stored in PostgreSQL database
- Included in analysis reports
- Used to generate recommendations

## Output Format

### Complexity Results

Results are stored as pain points with:
- **Type**: `complexity_hotspot`
- **Severity**: Based on complexity level (1-5)
- **Metadata**: Complexity metrics, line numbers, function names
- **Recommendations**: Refactoring suggestions

### Vulnerability Results

Results are stored as pain points with:
- **Type**: `security_vulnerability`
- **Severity**: Based on CVSS score
- **Metadata**: CVE ID, affected package, versions, CVSS score
- **Recommendations**: Upgrade instructions

## API Reference

### ComplexityAnalyzer

```python
class ComplexityAnalyzer:
    def __init__(self, hotspot_threshold: int = 10)
    def analyze_file(self, file_path: str) -> FileComplexity
    def analyze_repository(self, repo_path: str) -> ComplexityReport
```

### VulnerabilityScanner

```python
class VulnerabilityScanner:
    def __init__(self)
    def scan_repository(self, repo_path: str) -> VulnerabilityReport
```

### ComplexityAgent

```python
class ComplexityAgent:
    def __init__(self, storage: StorageAdapter = None, hotspot_threshold: int = 10)
    def analyze_repository(self, repo_path: str, repo_name: str,
                          analysis_run_id: int = None) -> ComplexityAnalysisResult
```

### SecurityAgent

```python
class SecurityAgent:
    def __init__(self, storage: StorageAdapter = None)
    def analyze_repository(self, repo_path: str, repo_name: str,
                          analysis_run_id: int = None) -> SecurityAnalysisResult
```

## Configuration

No additional configuration required. The agents use:
- Default hotspot threshold: 10
- OSV API endpoint: https://api.osv.dev/v1/query
- Automatic severity classification

## Best Practices

### Complexity Analysis

1. Target hotspots with complexity > 20 first
2. Maintain average complexity < 10
3. Keep maintainability index > 65
4. Monitor trends over time

### Vulnerability Scanning

1. Run scans on every commit or PR
2. Address CRITICAL and HIGH severity issues immediately
3. Subscribe to security advisories
4. Keep dependencies regularly updated
5. Use lock files for reproducibility

## Troubleshooting

### Complexity Analysis Issues

- **No results**: Ensure repository contains Python files
- **Import errors**: Install `radon` package
- **Performance**: Large repositories may take several minutes

### Vulnerability Scanning Issues

- **No vulnerabilities found**: Check dependency file formats
- **Rate limiting**: OSV API has rate limits (100 req/min)
- **Network errors**: Ensure internet connectivity for OSV queries

## Future Enhancements

Potential future improvements:

1. **Additional Languages**: Go, Java, Ruby support
2. **Historical Tracking**: Track complexity trends over time
3. **Custom Rules**: Configurable complexity thresholds
4. **SARIF Output**: Support for SARIF format
5. **Local Vulnerability DB**: Cache OSV data locally
6. **Auto-remediation**: Automatic PR creation for fixes

## Contributing

When contributing to these features:

1. Add tests for new functionality
2. Update documentation
3. Follow existing code patterns
4. Ensure backward compatibility

## License

Same as main project license.
