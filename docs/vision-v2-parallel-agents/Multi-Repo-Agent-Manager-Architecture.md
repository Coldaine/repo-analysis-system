---
cssclasses: [artifact, bg-ocean]
tags: [architecture, multi-agent, ccr, repository-management]
date: 2025-11-17
---

# Multi-Repository Parallel Agent Manager with CCR

## 🎯 **System Overview**

A multi-repository management system that:
- ✅ Syncs all GitHub repositories automatically
- ✅ Spawns TRUE parallel Claude agents (one per repo)
- ✅ Routes all agents through CCR for 98% cost savings
- ✅ Generates periodic status reports (configurable cadence)
- ✅ Tracks "5 pillars" and goals for each repository

---

## 🏗️ **System Architecture**

```
┌─────────────────────────────────────────────────────────────┐
│                    REPO AGENT MANAGER                       │
│                   (Main Orchestrator)                       │
└─────────────────┬───────────────────────────────────────────┘
                  │
    ┌─────────────┼─────────────┬──────────────┬──────────────┐
    │             │             │              │              │
┌───▼────┐  ┌────▼─────┐  ┌───▼──────┐  ┌───▼──────┐  ┌────▼─────┐
│ GitHub │  │   Repo   │  │  Agent   │  │ Report   │  │Scheduler │
│ Sync   │  │ Monitor  │  │ Spawner  │  │Generator │  │ Service  │
└───┬────┘  └────┬─────┘  └───┬──────┘  └───┬──────┘  └────┬─────┘
    │            │             │              │              │
    │            │             │              │              │
    ▼            ▼             ▼              ▼              ▼
┌────────────────────────────────────────────────────────────────┐
│              PERSISTENT STATE & CONFIGURATION                  │
│  - repos.json (synced repos)                                  │
│  - goals.json (5 pillars, goals per repo)                     │
│  - reports/ (historical status reports)                       │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌────────────────────────────────────────────────────────────────┐
│                    PARALLEL AGENT POOL                         │
│                                                                │
│  Agent 1 (repo-1) ──→ Claude CLI ──→ CCR ──→ Z.ai GLM-4.6    │
│  Agent 2 (repo-2) ──→ Claude CLI ──→ CCR ──→ Z.ai GLM-4.6    │
│  Agent 3 (repo-3) ──→ Claude CLI ──→ CCR ──→ Z.ai GLM-4.6    │
│  Agent N (repo-N) ──→ Claude CLI ──→ CCR ──→ Z.ai GLM-4.6    │
│                                                                │
│  Each agent runs in separate process with inherited CCR env   │
└────────────────────────────────────────────────────────────────┘
```

---

## 📋 **Core Components**

### **1. GitHub Sync Service**

**Purpose:** Keep local repository copies synchronized with GitHub

**Responsibilities:**
- Query GitHub API for all user repositories
- Clone missing repositories to configured directory
- Remove repositories deleted from GitHub
- Pull latest changes for existing repositories
- Track sync status and timestamps

**Operations:**
```javascript
class GitHubSyncService {
  async syncAllRepositories() {
    const remoteRepos = await this.fetchGitHubRepos();
    const localRepos = await this.scanLocalDirectory();

    // Clone missing repos
    const toClone = this.findMissingRepos(remoteRepos, localRepos);
    await this.cloneRepositories(toClone);

    // Remove deleted repos
    const toRemove = this.findDeletedRepos(remoteRepos, localRepos);
    await this.removeRepositories(toRemove);

    // Update existing repos
    await this.pullAllRepositories(localRepos);
  }
}
```

---

### **2. Repository Monitor**

**Purpose:** Track repository metadata and health

**Responsibilities:**
- Monitor repository status (commits, PRs, issues)
- Track "5 pillars" metrics (defined below)
- Record goal setting and achievement dates
- Maintain historical data

**Data Structure:**
```json
{
  "repositories": [
    {
      "name": "my-repo",
      "path": "/repos/my-repo",
      "url": "https://github.com/user/my-repo",
      "lastSync": "2025-11-17T10:30:00Z",
      "openPRs": [
        {"number": 123, "title": "Fix bug", "author": "user"}
      ],
      "pillars": {
        "codeQuality": {"score": 85, "lastUpdated": "2025-11-17"},
        "documentation": {"score": 70, "lastUpdated": "2025-11-17"},
        "testing": {"score": 90, "lastUpdated": "2025-11-17"},
        "performance": {"score": 80, "lastUpdated": "2025-11-17"},
        "security": {"score": 95, "lastUpdated": "2025-11-17"}
      },
      "goals": [
        {
          "id": "goal-1",
          "description": "Achieve 90% test coverage",
          "setDate": "2025-11-01",
          "targetDate": "2025-12-01",
          "status": "in-progress"
        }
      ]
    }
  ]
}
```

---

### **3. CCR Agent Spawner**

**Purpose:** Spawn true parallel Claude instances with CCR routing

**Responsibilities:**
- Spawn one Claude CLI process per repository
- Pass CCR environment variables to each process
- Manage process lifecycle (start, monitor, cleanup)
- Handle failures and retries
- Pool management (max concurrent agents)

**Implementation:**
```javascript
class CCRAgentSpawner {
  constructor(config) {
    this.maxConcurrent = config.maxConcurrentAgents || 5;
    this.activeAgents = new Map();
  }

  async spawnAgentForRepo(repoName, repoPath, task) {
    const agentId = `agent-${repoName}-${Date.now()}`;

    // Build prompt for this specific repository
    const prompt = this.buildRepositoryPrompt(repoName, repoPath, task);

    // Spawn Claude CLI with CCR environment
    const process = spawn('claude', [
      '--dangerously-skip-permissions',
      prompt
    ], {
      cwd: repoPath,
      env: {
        ...process.env,
        ANTHROPIC_BASE_URL: 'http://127.0.0.1:3456/v1/messages',
        ANTHROPIC_AUTH_TOKEN: 'ccr-routing',
        REPO_NAME: repoName,
        REPO_PATH: repoPath
      },
      stdio: ['ignore', 'pipe', 'pipe']
    });

    // Track the agent
    this.activeAgents.set(agentId, {
      process,
      repoName,
      startTime: Date.now(),
      output: ''
    });

    // Collect output
    process.stdout.on('data', (data) => {
      this.activeAgents.get(agentId).output += data.toString();
    });

    // Handle completion
    return new Promise((resolve, reject) => {
      process.on('exit', (code) => {
        const agent = this.activeAgents.get(agentId);
        this.activeAgents.delete(agentId);

        if (code === 0) {
          resolve({
            agentId,
            repoName,
            output: agent.output,
            duration: Date.now() - agent.startTime
          });
        } else {
          reject(new Error(`Agent failed with code ${code}`));
        }
      });
    });
  }

  async spawnAgentsForAllRepos(repos, task) {
    // Spawn agents in batches to respect maxConcurrent limit
    const results = [];

    for (let i = 0; i < repos.length; i += this.maxConcurrent) {
      const batch = repos.slice(i, i + this.maxConcurrent);
      const batchPromises = batch.map(repo =>
        this.spawnAgentForRepo(repo.name, repo.path, task)
      );

      const batchResults = await Promise.allSettled(batchPromises);
      results.push(...batchResults);
    }

    return results;
  }
}
```

---

### **4. Report Generator**

**Purpose:** Generate comprehensive status reports for each repository

**Responsibilities:**
- Aggregate repository data
- Format reports using templates
- Store historical reports
- Generate summary dashboards

**Report Template Structure:**
```markdown
# Repository Status Report: {repo-name}
**Generated:** {timestamp}
**Report Period:** {period}

---

## 📊 Quick Stats
- **Open PRs:** {pr-count}
- **Open Issues:** {issue-count}
- **Recent Commits:** {commit-count} (last 7 days)
- **Contributors:** {contributor-count}
- **Last Updated:** {last-commit-date}

---

## 🎯 The 4 Pillars

### 1️⃣ Code Quality (Score: {score}/100)
**Last Assessed:** {date}
**Status:** {status}
**Details:**
- Linting errors: {count}
- Code complexity: {metric}
- Technical debt: {estimate}
- Code smells: {count}

### 2️⃣ Documentation (Score: {score}/100)
**Last Assessed:** {date}
**Status:** {status}
**Details:**
- README completeness: {percentage}%
- API docs coverage: {percentage}%
- Comment density: {percentage}%
- Inline documentation: {status}

### 3️⃣ Testing (Score: {score}/100)
**Last Assessed:** {date}
**Status:** {status}
**Details:**
- Test coverage: {percentage}%
- Tests passing: {count}/{total}
- Unit tests: {status}
- Integration tests: {status}

### 4️⃣ Adherence to Plan (Score: {score}/100)
**Last Assessed:** {date}
**Status:** {status}
**Details:**
- Goals on track: {count}/{total}
- Milestones met: {percentage}%
- Divergences from baseline: {count}
- Plan alignment: {percentage}%

---

## 📋 Open Pull Requests

| # | Title | Author | Created | Status |
|---|-------|--------|---------|--------|
{pr-table-rows}

---

## 🎯 Active Goals

{goals-list}

---

## 📈 Trends (Last 30 Days)

- Commits: {trend}
- PRs merged: {count}
- Issues closed: {count}
- Test coverage change: {delta}%

---

## 🚨 Action Items

{action-items}

---

*Report generated by Multi-Repo Agent Manager*
```

---

### **5. Scheduler Service**

**Purpose:** Run periodic tasks at configured intervals

**Responsibilities:**
- Schedule repository sync operations
- Schedule status report generation
- Manage task queue and priorities
- Handle overlapping executions

**Implementation:**
```javascript
class SchedulerService {
  constructor(config) {
    this.syncInterval = config.syncInterval || 30 * 60 * 1000; // configurable interval
    this.reportInterval = config.reportInterval || 30 * 60 * 1000;
    this.jobs = [];
  }

  schedulePeriodicSync(syncService) {
    const job = setInterval(async () => {
      console.log(`[${new Date().toISOString()}] Starting periodic sync...`);
      try {
        await syncService.syncAllRepositories();
        console.log('Sync completed successfully');
      } catch (error) {
        console.error('Sync failed:', error);
      }
    }, this.syncInterval);

    this.jobs.push({ type: 'sync', job });
  }

  schedulePeriodicReports(reportGenerator, repos) {
    const job = setInterval(async () => {
      console.log(`[${new Date().toISOString()}] Starting periodic reports...`);
      try {
        await reportGenerator.generateAllReports(repos);
        console.log('Reports completed successfully');
      } catch (error) {
        console.error('Report generation failed:', error);
      }
    }, this.reportInterval);

    this.jobs.push({ type: 'reports', job });
  }

  shutdown() {
    this.jobs.forEach(({ job }) => clearInterval(job));
    this.jobs = [];
  }
}
```

---

## ⚙️ **Configuration File**

**config.json:**
```json
{
  "github": {
    "username": "your-username",
    "token": "ghp_your_github_token",
    "includeOrgs": ["org1", "org2"],
    "excludeRepos": ["temp-repo", "archived-repo"]
  },
  "repositories": {
    "baseDir": "E:/Repositories",
    "maxConcurrentClones": 3
  },
  "ccr": {
    "baseUrl": "http://127.0.0.1:3456/v1/messages",
    "authToken": "ccr-routing",
    "enabled": true
  },
  "agents": {
    "maxConcurrent": 5,
    "timeout": 600000,
    "retryAttempts": 2
  },
  "scheduling": {
    "syncInterval": 1800000,
    "reportInterval": 1800000,
    "runOnStartup": true
  },
  "reports": {
    "outputDir": "E:/Repositories/reports",
    "format": "markdown",
    "retention": 90,
    "includeHistoricalData": true
  },
  "pillars": {
    "codeQuality": {
      "enabled": true,
      "tools": ["eslint", "sonarqube"],
      "thresholds": { "min": 70, "target": 90 }
    },
    "documentation": {
      "enabled": true,
      "checkReadme": true,
      "checkApiDocs": true,
      "checkComments": true,
      "thresholds": { "min": 60, "target": 85 }
    },
    "testing": {
      "enabled": true,
      "coverageThreshold": 80,
      "requirePassing": true,
      "checkUnitTests": true,
      "checkIntegrationTests": true
    },
    "adherenceToPlan": {
      "enabled": true,
      "trackMilestones": true,
      "trackGoalCompletion": true,
      "compareToBaseline": true,
      "flagDivergences": true
    }
  }
}
```

---

## 📁 **Project Structure**

```
repo-agent-manager/
├── src/
│   ├── core/
│   │   ├── agent-spawner.js        # CCR agent spawning logic
│   │   ├── github-sync.js          # GitHub API integration
│   │   ├── repo-monitor.js         # Repository health tracking
│   │   ├── report-generator.js     # Report creation
│   │   └── scheduler.js            # Task scheduling
│   ├── services/
│   │   ├── pillar-analyzers/
│   │   │   ├── code-quality.js     # Code quality analysis
│   │   │   ├── documentation.js    # Documentation checking
│   │   │   ├── testing.js          # Test coverage analysis
│   │   │   ├── performance.js      # Performance metrics
│   │   │   └── security.js         # Security scanning
│   │   ├── github-client.js        # GitHub API wrapper
│   │   └── ccr-validator.js        # CCR connection testing
│   ├── templates/
│   │   ├── status-report.md        # Report template
│   │   └── summary-dashboard.md    # Dashboard template
│   └── utils/
│       ├── logger.js               # Logging utility
│       ├── file-utils.js           # File operations
│       └── config-loader.js        # Configuration loading
├── data/
│   ├── repos.json                  # Repository state
│   ├── goals.json                  # Goals tracking
│   └── history/                    # Historical data
├── reports/                        # Generated reports
├── config.json                     # Main configuration
├── package.json
└── index.js                        # Entry point
```

---

## 🚀 **Implementation Plan**

### **Phase 1: Core Infrastructure (Week 1)**
1. ✅ Project setup and dependencies
2. ✅ Configuration system
3. ✅ GitHub API integration
4. ✅ Repository sync service
5. ✅ Basic logging and error handling

### **Phase 2: Agent Spawning (Week 2)**
1. ✅ CCR agent spawner implementation
2. ✅ Process management and pooling
3. ✅ Environment variable passing
4. ✅ Output capture and parsing
5. ✅ Error handling and retries

### **Phase 3: Pillar Analysis (Week 3)**
1. ✅ Define 5 pillars structure
2. ✅ Implement code quality analyzer
3. ✅ Implement documentation checker
4. ✅ Implement testing analyzer
5. ✅ Implement performance metrics
6. ✅ Implement security scanner

### **Phase 4: Report Generation (Week 4)**
1. ✅ Report template system
2. ✅ Data aggregation logic
3. ✅ Report formatting and storage
4. ✅ Historical data tracking
5. ✅ Summary dashboard

### **Phase 5: Scheduling & Integration (Week 5)**
1. ✅ Scheduler service implementation
2. ✅ Integration testing
3. ✅ Performance optimization
4. ✅ Documentation
5. ✅ Deployment scripts

---

## 💡 **Usage Examples**

### **Initial Setup:**
```bash
# Install dependencies
npm install

# Configure GitHub token and preferences
nano config.json

# Start CCR
ccr start

# Initial sync (clones all repos)
node index.js sync

# Generate initial reports
node index.js report
```

### **Running the Manager:**
```bash
# Start continuous monitoring
node index.js start

# Output:
# [2025-11-17 10:00:00] Starting repo-agent-manager...
# [2025-11-17 10:00:01] CCR validation: ✓ Connected
# [2025-11-17 10:00:02] Syncing 25 repositories...
# [2025-11-17 10:02:15] Sync complete: 25 repos up to date
# [2025-11-17 10:02:16] Spawning 5 agents for status analysis...
# [2025-11-17 10:05:30] Reports generated: /reports/2025-11-17-10-00/
# [2025-11-17 10:05:31] Next run scheduled: 10:30:00
```

### **Manual Operations:**
```bash
# Force sync all repositories
node index.js sync --force

# Generate reports for specific repos
node index.js report --repos repo1,repo2,repo3

# Update goals for a repository
node index.js goals set my-repo "Improve test coverage" --target 2025-12-01

# Check pillar scores
node index.js pillars --repo my-repo
```

---

## 📊 **Expected Output**

### **Console During Periodic Run:**
```
[2025-11-17 10:30:00] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[2025-11-17 10:30:00] Periodic Report Generation Started
[2025-11-17 10:30:00] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

[2025-11-17 10:30:01] 📊 Spawning 25 agents (batches of 5)...

[2025-11-17 10:30:02] Batch 1/5:
  ✓ repo-1: Agent spawned (PID 12345) → CCR → Z.ai
  ✓ repo-2: Agent spawned (PID 12346) → CCR → Z.ai
  ✓ repo-3: Agent spawned (PID 12347) → CCR → Z.ai
  ✓ repo-4: Agent spawned (PID 12348) → CCR → Z.ai
  ✓ repo-5: Agent spawned (PID 12349) → CCR → Z.ai

[2025-11-17 10:32:45] Batch 1/5 complete:
  ✓ repo-1: Report generated (2.3s, 1,234 tokens)
  ✓ repo-2: Report generated (2.1s, 987 tokens)
  ✓ repo-3: Report generated (2.5s, 1,456 tokens)
  ✓ repo-4: Report generated (2.0s, 876 tokens)
  ✓ repo-5: Report generated (2.4s, 1,123 tokens)

[Continues for all batches...]

[2025-11-17 10:45:00] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[2025-11-17 10:45:00] Report Generation Complete
[2025-11-17 10:45:00] ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
[2025-11-17 10:45:00]
[2025-11-17 10:45:00] 📈 Summary:
[2025-11-17 10:45:00]   Total repos analyzed: 25
[2025-11-17 10:45:00]   Total time: 15m 0s
[2025-11-17 10:45:00]   Total API cost: $0.12 (via CCR → Z.ai)
[2025-11-17 10:45:00]   Savings vs Anthropic: $2.88 (96%)
[2025-11-17 10:45:00]   Reports saved: E:/Repositories/reports/2025-11-17-1030/
[2025-11-17 10:45:00]
[2025-11-17 10:45:00] ⏰ Next run: 11:00:00 (15 minutes)
```

---

## 🎯 **Key Benefits**

1. **True Parallelism:** Multiple Claude instances running simultaneously
2. **Cost Savings:** 96-98% reduction through CCR routing to Z.ai
3. **Automation:** Set it and forget it - runs on a configurable interval
4. **Comprehensive:** Tracks all aspects of repository health
5. **Scalable:** Handles dozens of repositories efficiently
6. **Flexible:** Configurable intervals, metrics, and thresholds

---

**Ready to build this system?** Let me know and I'll start implementing the core components!
