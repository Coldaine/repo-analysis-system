# Migration Guide: From Prototype to Greenfield Architecture

This guide helps you migrate from the legacy prototype to the new greenfield architecture with minimal disruption.

## 🎯 Migration Overview

The Repository Analysis System has been completely restructured from a monolithic prototype to a modular, LangGraph-based architecture. This migration preserves all your existing data while enabling new capabilities.

## 📋 Prerequisites

Before starting migration, ensure you have:

1. **Python 3.8+** installed
2. **PostgreSQL 12+** available (for production)
3. **Docker & Docker Compose** installed
4. **Git repository** backed up
5. **Configuration backup** of current `config.yaml`

## 🔄 Migration Steps

### Step 1: Backup Current Configuration

```bash
# Create backup directory
mkdir -p config/backups

# Backup current configuration with timestamp
cp config.yaml config/backups/config_backup_$(date +%Y%m%d_%H%M%S).yaml

# Verify backup
ls -la config/backups/
```

### Step 2: Run Configuration Migration

```bash
# Run the automated migration
python scripts/run_graph.py migrate --legacy-config config.yaml

# Verify new configuration was created
ls -la config/

# Check migration log
cat config/migration_log.json
```

### Step 3: Update Environment Variables

```bash
# Set database credentials (replace with your actual values)
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=repo_analysis
export DB_USER=postgres
export DB_PASSWORD=your_secure_password

# Set API keys (replace with your actual values)
export GITHUB_TOKEN=your_github_token
export GLM_API_KEY=your_glm_api_key
export MINIMAX_API_KEY=your_minimax_api_key
export GOOGLE_SEARCH_KEY=your_google_search_key
```

### Step 4: Initialize Database

```bash
# Start PostgreSQL and Redis
docker-compose up -d postgres redis

# Wait for services to be ready
sleep 15

# Initialize database schema
docker exec repo-analysis-system-postgres-1 psql -U postgres -d repo_analysis -f /docker-entrypoint-initdb.d/init.sql

# Verify database is ready
docker exec repo-analysis-system-postgres-1 python -c "
import psycopg2
try:
    conn = psycopg2.connect('postgresql://postgres:changeme@postgres:5432/repo_analysis')
    print('✅ Database connection successful')
    conn.close()
except Exception as e:
    print(f'❌ Database connection failed: {e}')
```

### Step 5: Test New System

```bash
# Run basic health check
python scripts/run_graph.py health

# Run test analysis
python scripts/run_graph.py analyze --repos "test-owner/test-repo"

# Verify output
ls -la review_logging/
```

### Step 6: Update Deployment Configuration

```bash
# Update Docker Compose for production
cp docker-compose.yml docker-compose.prod.yml

# Edit production configuration
# Update database connection strings, API endpoints, etc.
```

## 🗂️ What Changes

### Configuration Format Changes

| Component | Legacy Format | New Format | Migration Impact |
|------------|---------------|----------------|----------------|
| API Keys | Flat in `config.yaml` | Environment variables | ✅ Improved security |
| Models | Nested in `config.yaml` | Structured with validation | ✅ Better validation |
| Database | None | PostgreSQL with schema | ✅ Multi-user support |
| Repositories | Simple array | Structured with metadata | ✅ Enhanced tracking |
| Output | Single format | Multiple formats + metadata | ✅ Richer reports |

### Code Structure Changes

| Legacy | New | Description |
|--------|------|-----------|
| `agentic_prototype.py` | `src/orchestration/graph.py` | LangGraph orchestration |
| `side_agent.py` | `src/agents/*.py` | Modular agents |
| File-based storage | `src/storage/adapter.py` | PostgreSQL backend |
| Manual execution | `scripts/run_graph.py` | CLI with subcommands |

### Database Schema

The new system includes a comprehensive PostgreSQL schema with:

- **Users table**: Multi-user support with API key management
- **Repositories table**: Enhanced metadata and tracking
- **Analysis runs table**: Complete audit trail with metrics
- **Pull requests table**: Detailed PR tracking
- **Pain points table**: Structured issue management
- **Recommendations table**: Solution tracking with ranking
- **Visualizations table**: Diagram metadata and storage

## 🔄 Rollback Plan

If migration fails, you can rollback:

```bash
# Stop new system
docker-compose down

# Restore legacy configuration
cp config/backups/config_backup_latest.yaml config.yaml

# Restore legacy files
git checkout prototype-archive

# Restart with legacy system
python agentic_prototype.py
```

## ⚠️ Common Issues & Solutions

### Issue: Database Connection Failed

**Symptoms**: 
```
FATAL: database "repo_analysis" does not exist
```

**Solutions**:
1. Check PostgreSQL is running: `docker ps | grep postgres`
2. Verify database name: `docker exec postgres psql -l`
3. Check environment variables: `docker exec postgres env | grep DB_`
4. Restart services: `docker-compose restart`

### Issue: Configuration Validation Errors

**Symptoms**:
```
ValueError: Missing required section: database
```

**Solutions**:
1. Verify `config/new_config.yaml` exists
2. Check migration log: `cat config/migration_log.json`
3. Run validation: `python -c "from utils.config import ConfigLoader; ConfigLoader().load_config('config/new_config.yaml')._validate_config(config)"`

### Issue: Agent Import Errors

**Symptoms**:
```
ModuleNotFoundError: No module named 'src.orchestration.graph'
```

**Solutions**:
1. Check PYTHONPATH: `echo $PYTHONPATH`
2. Run from project root: `cd /path/to/repo-analysis-system && python scripts/run_graph.py`
3. Install dependencies: `pip install -r requirements.txt`

## 📞 Post-Migration Checklist

- [ ] Database initialized successfully
- [ ] All API keys configured
- [ ] Test analysis runs successfully
- [ ] Visualizations generated correctly
- [ ] Reports output in expected format
- [ ] Health checks passing
- [ ] Docker services running in production

## 🆘 Support

If you encounter issues during migration:

1. **Check the logs**: `docker-compose logs app`
2. **Review migration log**: `config/migration_log.json`
3. **Consult troubleshooting**: See [Troubleshooting Guide](../troubleshooting/)

4. **Create an issue**: [GitHub Issues](https://github.com/your-org/repo-analysis-system/issues)

## 🎉 Success Metrics

Successful migration should result in:

- ✅ Zero downtime during transition
- ✅ All historical data preserved
- ✅ New system fully operational
- ✅ Enhanced performance and scalability
- ✅ Improved maintainability and debugging

---

**🔄 Ready to migrate?** Run `python scripts/run_graph.py migrate` to begin your journey to the new architecture!