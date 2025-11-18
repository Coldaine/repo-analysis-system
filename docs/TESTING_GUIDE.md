# Testing Guide

Comprehensive guide for running tests in the Repository Analysis System.

---

## Quick Start

```bash
# Install test dependencies
make install-dev

# Run all tests (excluding live tests)
make test

# Run with coverage
make coverage

# Run specific test category
make test-unit
make test-integration
make test-e2e
```

---

## Test Organization

### Directory Structure

```
tests/
├── __init__.py
├── conftest.py                    # Shared fixtures and configuration
├── test_github_sync.py           # GitHub Sync Service tests
├── test_baseline_initializer.py  # Baseline Initialization tests
├── test_preprocessing_engine.py  # Pre-Processing Engine tests
├── test_end_to_end.py           # End-to-end workflow tests
└── test_live_api.py             # Live API integration tests
```

### Test Markers

Tests are organized using pytest markers:

- `@pytest.mark.unit`: Fast unit tests, no external dependencies
- `@pytest.mark.integration`: Integration tests with database/file system
- `@pytest.mark.e2e`: End-to-end workflow tests
- `@pytest.mark.live`: Tests requiring live GitHub API access
- `@pytest.mark.slow`: Slow-running tests (>5 seconds)
- `@pytest.mark.stress`: Stress and performance tests

---

## Running Tests

### Using Make Commands

```bash
# Run unit tests (fastest)
make test-unit

# Run integration tests
make test-integration

# Run end-to-end tests
make test-e2e

# Run live API tests (requires GITHUB_TOKEN)
make test-live

# Run all non-live tests
make test

# Run everything including live tests
make test-all

# Generate coverage report
make coverage
```

### Using Pytest Directly

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_github_sync.py

# Run specific test class
pytest tests/test_github_sync.py::TestGitHubSyncService

# Run specific test method
pytest tests/test_github_sync.py::TestGitHubSyncService::test_initialization

# Run tests by marker
pytest tests/ -m "unit"
pytest tests/ -m "integration and not live"
pytest tests/ -m "e2e"

# Verbose output
pytest tests/ -v

# Stop on first failure
pytest tests/ -x

# Run last failed tests
pytest tests/ --lf

# Show print statements
pytest tests/ -s
```

### Using the Test Runner Script

```bash
# Make script executable
chmod +x scripts/run_tests.sh

# Run with different modes
./scripts/run_tests.sh --mode unit
./scripts/run_tests.sh --mode integration
./scripts/run_tests.sh --mode e2e
./scripts/run_tests.sh --mode live
./scripts/run_tests.sh --mode all
./scripts/run_tests.sh --mode full  # Includes live tests

# With coverage
./scripts/run_tests.sh --mode all --coverage

# Verbose output
./scripts/run_tests.sh --mode all --verbose
```

---

## Environment Setup

### Required Environment Variables

```bash
# For live tests
export GITHUB_TOKEN="ghp_your_token_here"
export TEST_GITHUB_OWNER="your-username"

# For integration tests with database
export TEST_DB_HOST="localhost"
export TEST_DB_PORT="5432"
export TEST_DB_NAME="repo_analysis_test"
export TEST_DB_USER="postgres"
export TEST_DB_PASSWORD="your_password"

# Optional
export PRIMARY_AUTHOR="your-username"
```

### Database Setup for Integration Tests

```bash
# Create test database
createdb repo_analysis_test

# Initialize schema
psql -d repo_analysis_test -f src/storage/schema.sql

# Using make
make db-setup
```

---

## Test Categories

### 1. Unit Tests

**Purpose:** Test individual components in isolation

**Characteristics:**
- Fast execution (<1s per test)
- No external dependencies
- Use mocks for external services
- High code coverage

**Example:**
```python
@pytest.mark.unit
def test_parse_repository_data(test_config, mock_github_response):
    """Test parsing GitHub API repository data"""
    service = GitHubSyncService(test_config)
    repo_data = mock_github_response['repository']

    repo_info = service._parse_repository_data(repo_data)

    assert repo_info.name == 'test-repo'
    assert repo_info.owner == 'test-owner'
```

### 2. Integration Tests

**Purpose:** Test component interaction with real dependencies

**Characteristics:**
- Use real database (PostgreSQL)
- Use real file system
- May use mocked GitHub API
- Moderate execution time (1-10s)

**Example:**
```python
@pytest.mark.integration
def test_initialize_repository_baseline(test_config, temp_repo_dir):
    """Test full baseline initialization"""
    initializer = BaselineInitializer(test_config)

    baseline = initializer.initialize_repository_baseline(
        temp_repo_dir, 'test-repo', 'test-owner'
    )

    assert baseline.hash
    assert len(baseline.goals) >= 4
```

### 3. End-to-End Tests

**Purpose:** Test complete workflows from start to finish

**Characteristics:**
- Test multiple components together
- Real or mocked external services
- Validate complete user workflows
- Longer execution time (10-60s)

**Example:**
```python
@pytest.mark.e2e
def test_complete_single_repo_workflow(test_config, temp_repo_dir):
    """Test complete workflow for a single repository"""
    sync_service = GitHubSyncService(test_config)
    baseline_service = BaselineInitializer(test_config)
    preproc_engine = PreProcessingEngine(test_config)

    # Clone repository
    # Initialize baseline
    # Pre-process data
    # Verify results
```

### 4. Live API Tests

**Purpose:** Verify integration with real GitHub API

**Characteristics:**
- Require GITHUB_TOKEN
- Hit real GitHub API endpoints
- Network dependent
- May be slow (10-120s)
- Rate limit aware

**Example:**
```python
@pytest.mark.live
@pytest.mark.skipif(not os.getenv('GITHUB_TOKEN'),
                   reason="Requires GITHUB_TOKEN")
def test_discover_repositories_live(test_config):
    """Test discovering repositories from real GitHub account"""
    service = GitHubSyncService(test_config)
    repos = service.discover_repositories(owner)

    assert len(repos) > 0
```

---

## Test Fixtures

### Common Fixtures (conftest.py)

#### `test_config`
Provides test configuration with all necessary settings.

```python
def test_something(test_config):
    service = MyService(test_config)
    # ... test code
```

#### `temp_repo_dir`
Creates a temporary directory for test repositories.

```python
def test_with_repo(temp_repo_dir):
    (temp_repo_dir / 'README.md').write_text('# Test')
    # ... test code
```

#### `mock_github_response`
Provides mock GitHub API response data.

```python
def test_parsing(mock_github_response):
    repo_data = mock_github_response['repository']
    pr_data = mock_github_response['pull_request']
    # ... test code
```

---

## Coverage

### Generating Coverage Reports

```bash
# Terminal report
pytest tests/ --cov=src --cov-report=term-missing

# HTML report
pytest tests/ --cov=src --cov-report=html

# Both
make coverage
```

### Viewing HTML Coverage

```bash
# Generate and open
make coverage
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Coverage Goals

- Overall: >80%
- Critical paths: >95%
- New code: 100%

---

## CI/CD Integration

Tests run automatically on:
- Push to `main`, `develop`, `claude/**` branches
- Pull requests to `main`, `develop`

### GitHub Actions Workflow

```yaml
jobs:
  test-unit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run unit tests
        run: pytest tests/ -m "unit"

  test-integration:
    services:
      postgres:
        image: postgres:15
    steps:
      - uses: actions/checkout@v4
      - name: Run integration tests
        run: pytest tests/ -m "integration and not live"
```

---

## Writing New Tests

### Test Structure

```python
import pytest
from pathlib import Path

from module import ServiceClass


class TestServiceClass:
    """Test suite for ServiceClass"""

    def test_initialization(self, test_config):
        """Test service initialization"""
        service = ServiceClass(test_config)
        assert service.config == test_config

    def test_specific_feature(self, test_config):
        """Test specific feature with descriptive name"""
        service = ServiceClass(test_config)
        result = service.do_something()
        assert result.success is True

    @pytest.mark.integration
    def test_with_database(self, test_config):
        """Integration test with database"""
        service = ServiceClass(test_config)
        # Test database operations

    @pytest.mark.live
    @pytest.mark.skipif(not os.getenv('GITHUB_TOKEN'),
                       reason="Requires GITHUB_TOKEN")
    def test_live_api(self, test_config):
        """Live test with real API"""
        service = ServiceClass(test_config)
        # Test with real API
```

### Best Practices

1. **Descriptive Names**: Use clear, descriptive test names
2. **One Assertion**: Test one thing per test method
3. **Arrange-Act-Assert**: Follow AAA pattern
4. **Use Fixtures**: Leverage pytest fixtures for setup
5. **Mark Tests**: Use appropriate markers
6. **Mock External**: Mock external services in unit tests
7. **Clean Up**: Use fixtures for automatic cleanup
8. **Document**: Add docstrings to complex tests

### Example Test

```python
@pytest.mark.unit
def test_calculate_baseline_hash(self, test_config):
    """Test baseline hash calculation is deterministic"""
    # Arrange
    initializer = BaselineInitializer(test_config)
    baseline = create_test_baseline()

    # Act
    hash1 = initializer._calculate_baseline_hash(baseline)
    hash2 = initializer._calculate_baseline_hash(baseline)

    # Assert
    assert isinstance(hash1, str)
    assert len(hash1) == 64  # SHA256
    assert hash1 == hash2  # Deterministic
```

---

## Troubleshooting

### Common Issues

#### Tests Fail with "No GITHUB_TOKEN"

```bash
# Set environment variable
export GITHUB_TOKEN="ghp_your_token"

# Or skip live tests
pytest tests/ -m "not live"
```

#### Database Connection Errors

```bash
# Check PostgreSQL is running
pg_isready

# Create test database
createdb repo_analysis_test

# Initialize schema
make db-setup
```

#### Import Errors

```bash
# Set PYTHONPATH
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"

# Or use make commands which handle this
make test
```

#### Permission Errors

```bash
# Make test script executable
chmod +x scripts/run_tests.sh

# Check file permissions
ls -la tests/
```

---

## Performance Testing

### Running Performance Tests

```bash
# Run stress tests
pytest tests/ -m "stress" -v

# With timing information
pytest tests/ --durations=10
```

### Benchmarking

```python
@pytest.mark.stress
def test_preprocessing_performance(test_config, temp_repo_dir):
    """Test preprocessing performance meets goals"""
    import time

    engine = PreProcessingEngine(test_config)

    start = time.time()
    result = engine.preprocess_repository(...)
    duration = time.time() - start

    # Verify performance goals
    assert duration < 60, "Preprocessing should complete in <60s"
```

---

## Continuous Improvement

### Adding New Tests

1. Write test first (TDD)
2. Implement feature
3. Ensure test passes
4. Add to appropriate test file
5. Mark with appropriate markers
6. Document in this guide

### Monitoring Coverage

```bash
# Check current coverage
make coverage

# Identify uncovered code
pytest tests/ --cov=src --cov-report=term-missing

# Focus on specific module
pytest tests/ --cov=src.sync --cov-report=term-missing
```

---

## Summary

- **Quick Start**: `make test`
- **Live Tests**: `export GITHUB_TOKEN=... && make test-live`
- **Coverage**: `make coverage`
- **CI/CD**: Automatic on push/PR
- **Best Practices**: One test, one assertion, descriptive names

For questions or issues, see the main documentation or open an issue on GitHub.
