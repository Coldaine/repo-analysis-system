# Code Complexity Analysis

## Overview

The repo-analysis-system now includes comprehensive code complexity analysis capabilities to help identify maintainability issues and complexity hotspots in your codebase.

## Features

### Complexity Metrics

The system calculates the following metrics for each Python file:

1. **Cyclomatic Complexity** (McCabe)
   - Measures the number of linearly independent paths through code
   - Ranges: A (1-5), B (6-10), C (11-20), D (21-30), E (31-40), F (41+)

2. **Cognitive Complexity**
   - Estimates how difficult code is to understand
   - Takes nesting depth into account
   - Higher values indicate harder-to-understand code

3. **Nesting Depth**
   - Maximum depth of nested control structures
   - Deep nesting (>3) often indicates code that's hard to maintain

4. **Maintainability Index**
   - Composite metric combining volume, complexity, and lines of code
   - Range: 0-100 (higher is better)
   - Ranks: A (high), B (medium), C (low)

### Complexity Hotspots

Functions with cyclomatic complexity > 10 are automatically flagged as "hotspots" requiring refactoring attention.

## Usage

### Standalone Analysis

```python
from src.analysis.complexity_analyzer import ComplexityAnalyzer

# Initialize analyzer
analyzer = ComplexityAnalyzer(hotspot_threshold=10)

# Analyze a single file
file_result = analyzer.analyze_file("path/to/file.py")
print(f"Maintainability Index: {file_result.maintainability_index}")
print(f"Hotspots: {file_result.hotspot_count}")

# Analyze entire repository
report = analyzer.analyze_repository("path/to/repo")

# Access metrics
print(f"Total files: {report.metrics.total_files}")
print(f"Total hotspots: {report.metrics.total_hotspots}")
print(f"Average complexity: {report.metrics.average_complexity}")

# Get complexity distribution
print(report.metrics.complexity_distribution)
# Output: {'A (1-5)': 45, 'B (6-10)': 12, 'C (11-20)': 3, ...}

# Get top hotspots
for file_path, func in report.hotspots[:10]:
    print(f"{func.name} in {file_path}: complexity={func.complexity}")
```

### Integrated with LangGraph Workflow

Complexity analysis runs automatically as part of the repository analysis workflow:

```bash
python scripts/run_graph.py analyze --repos "owner/repo" --user-id 1
```

The complexity results are:
- Stored in the database as pain points with type "complexity_hotspot"
- Included in the analysis report
- Used to generate refactoring recommendations

## Output Format

### ComplexityReport Structure

```json
{
  "metrics": {
    "total_files": 50,
    "total_functions": 250,
    "total_hotspots": 15,
    "average_maintainability_index": 72.5,
    "average_complexity": 4.2,
    "max_complexity": 45,
    "complexity_distribution": {
      "A (1-5)": 180,
      "B (6-10)": 50,
      "C (11-20)": 15,
      "D (21-30)": 3,
      "E (31-40)": 1,
      "F (41+)": 1
    }
  },
  "files": [
    {
      "file_path": "src/module.py",
      "maintainability_index": 65.3,
      "maintainability_rank": "B",
      "lines_of_code": 150,
      "average_complexity": 6.5,
      "max_complexity": 18,
      "hotspot_count": 2,
      "functions": [
        {
          "name": "complex_function",
          "line_number": 42,
          "cyclomatic_complexity": 18,
          "cognitive_complexity": 24,
          "nesting_depth": 4,
          "rank": "C",
          "is_hotspot": true
        }
      ]
    }
  ],
  "hotspots": [
    {
      "file": "src/module.py",
      "function": {
        "name": "complex_function",
        "line_number": 42,
        "cyclomatic_complexity": 18,
        "rank": "C"
      }
    }
  ]
}
```

## Recommendations

The system automatically generates refactoring recommendations based on complexity:

- **Complexity > 20**: Extract logical units into smaller functions
- **Nesting depth > 3**: Use early returns or guard clauses
- **Complexity > 10**: Add unit tests before refactoring

## Best Practices

1. **Target Hotspots First**: Focus refactoring efforts on functions with complexity > 20
2. **Maintain Good Scores**: Aim for average complexity < 10 and maintainability index > 65
3. **Monitor Trends**: Track complexity metrics over time to prevent degradation
4. **Use Distribution**: Check that most functions fall in categories A or B

## Integration with CI/CD

You can fail builds based on complexity thresholds:

```python
report = analyzer.analyze_repository(".")

if report.metrics.total_hotspots > 10:
    print("Too many complexity hotspots!")
    exit(1)

if report.metrics.average_complexity > 15:
    print("Average complexity too high!")
    exit(1)
```

## Limitations

- Currently supports Python only
- Cognitive complexity is estimated (not exact SonarQube formula)
- Requires `radon` library to be installed

## References

- [Cyclomatic Complexity](https://en.wikipedia.org/wiki/Cyclomatic_complexity)
- [Cognitive Complexity](https://www.sonarsource.com/docs/CognitiveComplexity.pdf)
- [Maintainability Index](https://docs.microsoft.com/en-us/visualstudio/code-quality/code-metrics-values)
