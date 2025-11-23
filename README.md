# Repository Analysis System - New Architecture

## Overview

This is the **new greenfield architecture** for the Repository Analysis System, rebuilt from the ground up with LangGraph orchestration and PostgreSQL backend for multi-user concurrent access.

## 🚀 What's New

### Architecture Improvements

- **LangGraph Integration**: Modern graph-based orchestration replacing sequential execution
- **PostgreSQL Backend**: Multi-user concurrent access with proper indexing and relationships
- **Modular Design**: Clean separation of concerns with dedicated modules
- **Enhanced Storage**: Comprehensive data models with audit trails
- **Docker Deployment**: Containerized deployment for zo.computer
- **Configuration Migration**: Automated migration from legacy format

### Key Benefits

1. **Scalability**: Support for multiple concurrent users and repositories
2. **Performance**: Optimized database queries and parallel processing
3. **Maintainability**: Modular codebase with clear interfaces
4. **Reliability**: Proper error handling and retry mechanisms
5. **Deployability**: Docker containers for consistent environments

## 📁 Architecture

```
┌─────────────────┐
│   CLI Entry    │
│  scripts/      │
│   run_graph.py   │
└─────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    LangGraph Orchestration                       │
│                     src/orchestration/graph.py              │
└─────────────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  Data Collection │  Analysis │  Visualization │  Output │
├─────────────────┼─────────────────┼─────────────────┼─────────────────┤
│ src/agents/    │ src/agents/   │ src/agents/    │ src/agents/    │
│ data_collection │ analysis.py   │ visualization.py │ output.py     │
└─────────────────┴─────────────────┴─────────────────┴─────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│     Model Management    │    Storage Layer    │
├─────────────────────────┼──────────────────────┼──────────────────────┤
│   src/models/         │ src/storage/       │
│   model_manager.py    │   adapter.py       │
│                      │   schema.sql       │
└─────────────────────────┴──────────────────────┴──────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│               Configuration & Utilities                    │
├──────────────────────────────────────────────────────────────────────┼──────────────────────┤
│     src/utils/        │  config/          │  preprocessing/    │
│   config.py, logging.py, │ migration.py      │  repo_sync.py,   │
│   validation.py        │                  │  change_detector.py │
└─────────────────────────┴──────────────────────┴──────────────────────┘
```

## 🛠️ Migration from Prototype

The original prototype has been archived in [`archive/`](archive/) with all components preserved for reference.

### What Was Migrated

- ✅ **Data Collection**: Enhanced GitHub API client with better error handling
- ✅ **Model Management**: Multi-model routing with fallback support
- ✅ **Visualization**: Improved Mermaid generation with quality assurance
- ✅ **Output Generation**: Multi-format reports with metadata storage
- ✅ **Orchestration**: LangGraph-based workflow with state management

### What Was Replaced

- ❌ **Sequential Execution**: Replaced with parallel LangGraph orchestration
- ❌ **File-based Storage**: Replaced with PostgreSQL database
- ❌ **Monolithic Code**: Replaced with modular architecture
- ❌ **Manual Configuration**: Replaced with automated migration

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- PostgreSQL 12+
- Docker & Docker Compose
- LangGraph (optional, fallback available)
- Bitwarden Secrets Manager CLI (`bws`) - for secrets management

### 1. Setup Secrets Management (Bitwarden)

All API keys and secrets are managed securely using [Bitwarden Secrets Manager](https://bitwarden.com/products/secrets-manager/).

**Required Secrets:**
- `GITHUB_TOKEN` - GitHub API access
- `GLM_API_KEY` - GLM 4.6 AI model
- `GITHUB_OWNER` - Repository owner (optional)
- `MINIMAX_API_KEY` - MiniMax AI model (optional)

**Setup:**

```bash
# Install bws CLI (if not already installed)
# Download from: https://github.com/bitwarden/sdk/releases

# Set your Bitwarden access token (once)
$env:BWS_ACCESS_TOKEN = "your_token_here"

# Test secrets are accessible
bws run -- powershell -File check-secrets.ps1
```

**Usage:**

```bash
# Run any command with secrets injected
bws run -- python scripts/run_graph.py

# Secrets are automatically injected as environment variables
# No .env files or manual configuration needed!
```

See [docs/Bitwarden-Secrets-Integration.md](docs/Bitwarden-Secrets-Integration.md) for complete setup guide.

### 2. Setup Database

```bash
# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Wait for services to be ready
sleep 10

# Initialize database schema
docker exec -i postgres psql -U postgres -d repo_analysis -f /docker-entrypoint-initdb.d/init.sql
```

### 2. Migrate Configuration

```bash
# Migrate from legacy config (if exists)
python scripts/run_graph.py migrate --legacy-config config.yaml

# Set environment variables
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=repo_analysis
export DB_USER=postgres
export DB_PASSWORD=your_secure_password
```

### 3. Run Analysis

```bash
# Basic analysis
python scripts/run_graph.py analyze --repos "owner/repo1" "owner/repo2"

# With specific user
python scripts/run_graph.py analyze --repos "owner/repo" --user-id 1

# Different run types
python scripts/run_graph.py analyze --repos "owner/repo" --run-type webhook
python scripts/run_graph.py analyze --repos "owner/repo" --run-type incremental
```

### 4. System Health Check

```bash
python scripts/run_graph.py health
```

## 📊 Configuration

### New Configuration Structure

The system now uses `config/new_config.yaml` with the following structure:

```yaml
version: "2.0"
database:
  type: "postgresql"
  host: "${DB_HOST:localhost}"
  port: "${DB_PORT:5432}"
  name: "${DB_NAME:repo_analysis}"
  user: "${DB_USER:postgres}"
  password: "${DB_PASSWORD}"
  pool_size: 10
  max_overflow: 20

api_keys:
  github_token: "${GITHUB_TOKEN}"
  glm_api_key: "${GLM_API_KEY}"
  minimax_api_key: "${MINIMAX_API_KEY}"
  google_search_key: "${GOOGLE_SEARCH_KEY}"

models:
  glm_4_6:
    model: "glm-4.6"
    temperature: 0.3
    max_tokens: 4000
  minimax:
    model: "abab6.5s-chat"
    temperature: 0.2
    max_tokens: 2000

orchestration:
  langgraph:
    max_concurrent_runs: 5
    timeout_seconds: 3600
    retry_attempts: 3

agents:
  visualization_agent:
    output_format: "mermaid"
    max_diagrams: 5
    render_svg: true
```

### Environment Variables

| Variable | Description | Default |
|-----------|-------------|---------|
| `DB_HOST` | PostgreSQL host | localhost |
| `DB_PORT` | PostgreSQL port | 5432 |
| `DB_NAME` | Database name | repo_analysis |
| `DB_USER` | Database user | postgres |
| `DB_PASSWORD` | Database password | - |
| `GITHUB_TOKEN` | GitHub API token | - |
| `GLM_API_KEY` | GLM API key | - |
| `MINIMAX_API_KEY` | MiniMax API key | - |
| `GOOGLE_SEARCH_KEY` | Google Search key | - |

## 🐳 Docker Deployment

### Quick Start with Docker Compose

```bash
# Clone and setup
git clone <repository-url>
cd repo-analysis-system

# Configure environment
cp config/new_config.yaml.example config/new_config.yaml
# Edit config/new_config.yaml with your settings

# Start services
docker-compose up -d

# Run analysis
docker-compose exec app python scripts/run_graph.py analyze --repos "your-org/your-repo"

# View logs
docker-compose logs -f app

# Stop services
docker-compose down
```

### Production Deployment

For production deployment on zo.computer:

1. **Security**: Update all default passwords and API keys
2. **Networking**: Configure proper firewall rules for ports 8000, 5432, 6379
3. **Monitoring**: Set up log aggregation and health checks
4. **Backups**: Configure PostgreSQL backups and volume persistence
5. **SSL**: Configure SSL certificates for HTTPS

## 📚 Documentation

- **[Architecture Guide](docs/architecture/)**: Detailed system design
- **[API Documentation](docs/api/)**: Component interfaces
- **[Migration Guide](docs/migration/)**: Step-by-step migration instructions
- **[Troubleshooting](docs/troubleshooting/)**: Common issues and solutions

## 🔧 Development

### Running Tests

```bash
# Install test dependencies
pip install -r requirements-test.txt

# Run test suite
python -m pytest tests/ -v

# Run specific component tests
python -m pytest tests/test_data_collection.py -v
python -m pytest tests/test_model_manager.py -v
```

### Adding New Agents

1. Create agent class in `src/agents/`
2. Implement required methods
3. Add agent to `src/agents/__init__.py`
4. Update orchestration graph to use new agent
5. Add tests in `tests/`

## 🔄 Migration from Legacy

### Automated Migration

```bash
# Run the migration utility
python scripts/run_graph.py migrate --legacy-config config.yaml

# Verify migration
ls config/
cat config/new_config.yaml
```

### Manual Migration Steps

1. **Backup**: Copy existing `config.yaml` to `config.yaml.backup`
2. **API Keys**: Update all API keys to use environment variables
3. **Repository List**: Convert target_repos array to new format if needed
4. **Model Configs**: Update model configurations to new structure
5. **Validation**: Run `python scripts/run_graph.py health` to verify setup

## 📈 Legacy vs New Comparison

| Feature | Legacy Prototype | New Architecture |
|---------|----------------|----------------|
| **Execution Model** | Sequential script | LangGraph orchestration |
| **Database** | File-based storage | PostgreSQL with relationships |
| **Concurrency** | Single-user | Multi-user support |
| **Configuration** | Single YAML file | Migrated + environment variables |
| **Deployment** | Manual setup | Docker Compose ready |
| **Error Handling** | Basic retry | Comprehensive error handling |
| **Testing** | Manual testing | Test suite included |
| **Monitoring** | Basic logging | Health checks + metrics |

## 🏗️ System Status

### Current Status: 🟢 Ready for Production

The greenfield architecture is complete and ready for deployment. All core components have been refactored:

- ✅ **Data Collection**: Enhanced with storage integration
- ✅ **Model Management**: Multi-model routing with fallbacks
- ✅ **Visualization**: Quality-assured Mermaid generation
- ✅ **Output Generation**: Multi-format reports with metadata
- ✅ **Orchestration**: LangGraph-based workflow management
- ✅ **Storage Layer**: PostgreSQL with full schema
- ✅ **CLI Interface**: New command-line interface
- ✅ **Docker Support**: Multi-service deployment ready
- ✅ **Configuration Migration**: Automated migration utility
- ✅ **Testing Framework**: Comprehensive test structure

### Next Steps

1. **Production Deployment**: Deploy to zo.computer using Docker Compose
2. **Performance Testing**: Load test with multiple concurrent users
3. **Monitoring Setup**: Configure log aggregation and alerting
4. **Documentation**: Complete API and architecture documentation

---

**Version**: 2.0.0  
**Last Updated**: November 17, 2025  
**Migration Date**: See [`config/migration_log.json`](config/migration_log.json)

## 🤝 Contributing

See [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) for development guidelines.

## 📄 License

This project is licensed under the MIT License. See [`LICENSE`](LICENSE) for details.

---

**🔄 Migrated from Prototype with Enhanced Architecture for Production Deployment 🚀**