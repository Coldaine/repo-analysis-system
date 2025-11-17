---
cssclasses: [artifact, bg-teal]
tags: [architecture, preprocessing, review-gathering]
date: 2025-11-17
---

# Pre-Processing Script Design

## 🎯 Purpose

Run BEFORE spawning CCR agents to gather and prepare all review items, so the AI doesn't waste time/tokens discovering what needs to be reviewed.

---

## 📋 Script Flow

```
┌─────────────────────────────────────────────┐
│     Pre-Processing Script (per repo)       │
└─────────────────┬───────────────────────────┘
                  │
    ┌─────────────┼─────────────┬──────────────┐
    │             │             │              │
┌───▼────┐  ┌────▼─────┐  ┌───▼──────┐  ┌───▼──────┐
│  Git   │  │ GitHub   │  │  Code    │  │ Baseline │
│Analysis│  │   API    │  │ Analysis │  │  Diff    │
└───┬────┘  └────┬─────┘  └───┬──────┘  └───┬──────┘
    │            │             │              │
    └────────────┼─────────────┴──────────────┘
                 │
                 ▼
    ┌─────────────────────────────────┐
    │   Review Items JSON             │
    │   (Pre-gathered data)           │
    └─────────────┬───────────────────┘
                  │
                  ▼
    ┌─────────────────────────────────┐
    │   CCR Agent Spawner             │
    │   (Receives pre-gathered data)  │
    └─────────────────────────────────┘
```

---

## 🔧 Implementation

### **Script: `gather-review-items.js`**

```javascript
#!/usr/bin/env node

import { Octokit } from '@octokit/rest';
import { execSync } from 'child_process';
import fs from 'fs/promises';
import path from 'path';

class ReviewItemGatherer {
  constructor(repoPath, config) {
    this.repoPath = repoPath;
    this.config = config;
    this.octokit = new Octokit({ auth: config.github.token });

    // Extract repo info from path or git remote
    this.repoInfo = this.extractRepoInfo();
  }

  /**
   * Main gathering function - runs all collection tasks
   */
  async gatherAll() {
    console.log(`[${this.repoInfo.name}] Gathering review items...`);

    const startTime = Date.now();

    // Run all gathering tasks in parallel
    const [
      gitData,
      githubData,
      codeAnalysis,
      baselineComparison
    ] = await Promise.all([
      this.gatherGitData(),
      this.gatherGitHubData(),
      this.analyzeCodeChanges(),
      this.compareToBaseline()
    ]);

    const reviewItems = {
      timestamp: new Date().toISOString(),
      repository: this.repoInfo,
      gatheringDuration: Date.now() - startTime,

      // Pre-gathered data sections
      git: gitData,
      github: githubData,
      code: codeAnalysis,
      baseline: baselineComparison,

      // Summary counts for quick reference
      summary: {
        newCommits: gitData.recentCommits.length,
        newPRs: githubData.openPRs.filter(pr => this.isNew(pr)).length,
        newIssues: githubData.openIssues.filter(i => this.isNew(i)).length,
        filesChanged: gitData.filesChanged.length,
        divergences: baselineComparison.divergences.length
      }
    };

    // Save to temp file for agent to consume
    const outputPath = path.join(
      this.config.tempDir,
      `review-items-${this.repoInfo.name}.json`
    );
    await fs.writeFile(outputPath, JSON.stringify(reviewItems, null, 2));

    console.log(`[${this.repoInfo.name}] Review items gathered: ${outputPath}`);
    console.log(`  - ${reviewItems.summary.newCommits} new commits`);
    console.log(`  - ${reviewItems.summary.newPRs} new PRs`);
    console.log(`  - ${reviewItems.summary.newIssues} new issues`);
    console.log(`  - ${reviewItems.summary.filesChanged} files changed`);
    console.log(`  - ${reviewItems.summary.divergences} divergences`);

    return { outputPath, reviewItems };
  }

  /**
   * Gather Git data (commits, changes, etc.)
   */
  async gatherGitData() {
    const lastReportTime = await this.getLastReportTime();

    // Get recent commits since last report
    const gitLog = execSync(
      `git log --since="${lastReportTime}" --pretty=format:"%H|%an|%ae|%ad|%s" --date=iso`,
      { cwd: this.repoPath, encoding: 'utf-8' }
    );

    const recentCommits = gitLog
      .split('\n')
      .filter(line => line.trim())
      .map(line => {
        const [hash, author, email, date, message] = line.split('|');
        return { hash, author, email, date, message };
      });

    // Get files changed in those commits
    const filesChanged = execSync(
      `git diff --name-status ${lastReportTime}..HEAD`,
      { cwd: this.repoPath, encoding: 'utf-8' }
    )
      .split('\n')
      .filter(line => line.trim())
      .map(line => {
        const [status, ...pathParts] = line.split('\t');
        return { status, path: pathParts.join('\t') };
      });

    // Get diff stats
    const diffStats = execSync(
      `git diff --stat ${lastReportTime}..HEAD`,
      { cwd: this.repoPath, encoding: 'utf-8' }
    );

    return {
      recentCommits,
      filesChanged,
      diffStats,
      period: {
        since: lastReportTime,
        until: new Date().toISOString()
      }
    };
  }

  /**
   * Gather GitHub data (PRs, issues, etc.)
   */
  async gatherGitHubData() {
    const { owner, repo } = this.repoInfo;

    // Fetch open PRs
    const { data: openPRs } = await this.octokit.pulls.list({
      owner,
      repo,
      state: 'open',
      sort: 'created',
      direction: 'desc'
    });

    // Fetch open issues
    const { data: openIssues } = await this.octokit.issues.listForRepo({
      owner,
      repo,
      state: 'open',
      sort: 'created',
      direction: 'desc'
    });

    // Fetch recently closed items (for trend analysis)
    const lastReportTime = await this.getLastReportTime();
    const { data: recentlyClosed } = await this.octokit.issues.listForRepo({
      owner,
      repo,
      state: 'closed',
      since: lastReportTime
    });

    return {
      openPRs: openPRs.map(this.formatPR),
      openIssues: openIssues.map(this.formatIssue),
      recentlyClosed: recentlyClosed.map(this.formatIssue),
      stats: {
        openPRCount: openPRs.length,
        openIssueCount: openIssues.length,
        closedSinceLastReport: recentlyClosed.length
      }
    };
  }

  /**
   * Analyze code changes for quality/testing/docs
   */
  async analyzeCodeChanges() {
    const filesChanged = execSync(
      'git diff --name-only HEAD~10..HEAD',
      { cwd: this.repoPath, encoding: 'utf-8' }
    ).split('\n').filter(Boolean);

    const analysis = {
      sourceFilesChanged: [],
      testFilesChanged: [],
      docFilesChanged: [],
      configFilesChanged: [],
      dependencyChanges: []
    };

    for (const file of filesChanged) {
      if (file.match(/\.(js|ts|jsx|tsx|py|java|go)$/)) {
        analysis.sourceFilesChanged.push(file);
      } else if (file.match(/\.(test|spec)\.(js|ts|jsx|tsx)$/) || file.includes('test/')) {
        analysis.testFilesChanged.push(file);
      } else if (file.match(/\.(md|txt|rst)$/) || file.includes('docs/')) {
        analysis.docFilesChanged.push(file);
      } else if (file.match(/package\.json|requirements\.txt|go\.mod|pom\.xml/)) {
        analysis.dependencyChanges.push(file);
      } else if (file.match(/\.(json|yaml|yml|toml|ini|conf)$/)) {
        analysis.configFilesChanged.push(file);
      }
    }

    // Check for dependency updates
    if (analysis.dependencyChanges.length > 0) {
      analysis.dependencyDetails = await this.analyzeDependencyChanges();
    }

    return analysis;
  }

  /**
   * Compare current state to locked baseline
   */
  async compareToBaseline() {
    const baselinePath = path.join(
      this.config.dataDir,
      'baselines',
      this.repoInfo.name,
      'baseline-v1.0.json'
    );

    try {
      const baselineData = JSON.parse(await fs.readFile(baselinePath, 'utf-8'));

      const divergences = [];

      // Compare goals
      for (const baselineGoal of baselineData.goals) {
        const currentGoal = await this.getCurrentGoalStatus(baselineGoal.id);

        if (this.hasGoalDiverged(baselineGoal, currentGoal)) {
          divergences.push({
            type: 'goal',
            goalId: baselineGoal.id,
            goalTitle: baselineGoal.title,
            baseline: baselineGoal,
            current: currentGoal,
            severity: this.assessDivergenceSeverity(baselineGoal, currentGoal),
            description: this.describeDivergence(baselineGoal, currentGoal)
          });
        }
      }

      // Compare phases
      const currentPhase = await this.getCurrentPhase();
      const baselinePhase = baselineData.currentPhase;

      if (currentPhase !== baselinePhase) {
        divergences.push({
          type: 'phase',
          baseline: baselinePhase,
          current: currentPhase,
          severity: 'moderate',
          description: `Phase changed from "${baselinePhase}" to "${currentPhase}"`
        });
      }

      return {
        baselineVersion: baselineData.version,
        baselineDate: baselineData.lockDate,
        divergences,
        overallAlignment: this.calculateAlignmentScore(divergences)
      };

    } catch (error) {
      // No baseline found - this might be a new repo
      return {
        baselineVersion: null,
        baselineDate: null,
        divergences: [],
        overallAlignment: null,
        note: 'No baseline found - repository may need initialization'
      };
    }
  }

  // Helper methods...

  extractRepoInfo() {
    const remote = execSync('git remote get-url origin', {
      cwd: this.repoPath,
      encoding: 'utf-8'
    }).trim();

    const match = remote.match(/github\.com[:/](.+?)\/(.+?)(?:\.git)?$/);
    if (!match) throw new Error('Could not parse GitHub repo from remote');

    return {
      owner: match[1],
      repo: match[2],
      name: match[2]
    };
  }

  async getLastReportTime() {
    // Get timestamp from last report, or default to 30 minutes ago
    const reportDir = path.join(this.config.reportsDir, this.repoInfo.name);

    try {
      const reports = await fs.readdir(reportDir);
      const latestReport = reports.sort().reverse()[0];
      const reportData = JSON.parse(
        await fs.readFile(path.join(reportDir, latestReport), 'utf-8')
      );
      return reportData.timestamp;
    } catch {
      // No previous report, use 30 minutes ago
      return new Date(Date.now() - 30 * 60 * 1000).toISOString();
    }
  }

  formatPR(pr) {
    return {
      number: pr.number,
      title: pr.title,
      author: pr.user.login,
      created: pr.created_at,
      updated: pr.updated_at,
      filesChanged: pr.changed_files,
      additions: pr.additions,
      deletions: pr.deletions,
      status: pr.draft ? 'draft' : 'ready',
      labels: pr.labels.map(l => l.name)
    };
  }

  formatIssue(issue) {
    return {
      number: issue.number,
      title: issue.title,
      author: issue.user.login,
      created: issue.created_at,
      updated: issue.updated_at,
      labels: issue.labels.map(l => l.name),
      assignees: issue.assignees.map(a => a.login),
      state: issue.state
    };
  }

  isNew(item) {
    const lastReportTime = new Date(this.lastReportTime);
    const itemTime = new Date(item.created);
    return itemTime > lastReportTime;
  }
}

// Export for use in main manager
export { ReviewItemGatherer };
```

---

## 📊 Output Format

### **`review-items-{repo-name}.json`**

```json
{
  "timestamp": "2025-11-17T10:30:00Z",
  "repository": {
    "owner": "username",
    "repo": "repo-name",
    "name": "repo-name"
  },
  "gatheringDuration": 1234,

  "git": {
    "recentCommits": [
      {
        "hash": "abc123",
        "author": "John Doe",
        "email": "john@example.com",
        "date": "2025-11-17T09:15:00Z",
        "message": "Fix authentication bug"
      }
    ],
    "filesChanged": [
      { "status": "M", "path": "src/auth.js" },
      { "status": "A", "path": "tests/auth.test.js" }
    ],
    "diffStats": "2 files changed, 45 insertions(+), 12 deletions(-)",
    "period": {
      "since": "2025-11-17T10:00:00Z",
      "until": "2025-11-17T10:30:00Z"
    }
  },

  "github": {
    "openPRs": [
      {
        "number": 123,
        "title": "Add user dashboard",
        "author": "contributor",
        "created": "2025-11-16T14:00:00Z",
        "filesChanged": 8,
        "status": "ready"
      }
    ],
    "openIssues": [
      {
        "number": 456,
        "title": "Performance issue on large datasets",
        "author": "user",
        "created": "2025-11-15T10:00:00Z",
        "labels": ["bug", "performance", "high-priority"]
      }
    ],
    "stats": {
      "openPRCount": 5,
      "openIssueCount": 12,
      "closedSinceLastReport": 3
    }
  },

  "code": {
    "sourceFilesChanged": ["src/auth.js", "src/api/users.js"],
    "testFilesChanged": ["tests/auth.test.js"],
    "docFilesChanged": ["README.md"],
    "configFilesChanged": [],
    "dependencyChanges": ["package.json"],
    "dependencyDetails": {
      "express": { "old": "4.18.0", "new": "4.18.2", "type": "patch" }
    }
  },

  "baseline": {
    "baselineVersion": "v1.0",
    "baselineDate": "2025-11-01T00:00:00Z",
    "divergences": [
      {
        "type": "goal",
        "goalId": "goal-1",
        "goalTitle": "Achieve 90% test coverage",
        "baseline": { "targetDate": "2025-12-01", "status": "in-progress" },
        "current": { "targetDate": "2025-12-15", "status": "at-risk" },
        "severity": "moderate",
        "description": "Target date pushed back by 2 weeks, status changed to at-risk"
      }
    ],
    "overallAlignment": 85
  },

  "summary": {
    "newCommits": 15,
    "newPRs": 2,
    "newIssues": 3,
    "filesChanged": 12,
    "divergences": 1
  }
}
```

---

## 🚀 Usage in Main System

### **Integration with Agent Spawner:**

```javascript
// In main orchestrator

async function runPeriodicReports() {
  const repos = await loadRepositories();

  // STEP 1: Pre-gather review items for all repos
  console.log('📋 Pre-gathering review items...');
  const reviewItemsFiles = [];

  for (const repo of repos) {
    const gatherer = new ReviewItemGatherer(repo.path, config);
    const { outputPath } = await gatherer.gatherAll();
    reviewItemsFiles.push({ repo, outputPath });
  }

  console.log(`✓ Review items gathered for ${repos.length} repositories`);

  // STEP 2: Spawn CCR agents with pre-gathered data
  console.log('🤖 Spawning CCR agents...');

  const spawner = new CCRAgentSpawner(config);
  const results = await spawner.spawnAgentsForAllRepos(
    reviewItemsFiles.map(({ repo, outputPath }) => ({
      ...repo,
      reviewItemsPath: outputPath  // ← Pass pre-gathered data path
    })),
    'generate-status-report'
  );

  console.log('✓ All reports generated');
}
```

### **Agent Prompt with Pre-Gathered Data:**

```javascript
function buildRepositoryPrompt(repoName, repoPath, reviewItemsPath) {
  return `
You are analyzing repository "${repoName}" for a periodic status report.

PRE-GATHERED REVIEW ITEMS:
All the data you need has been collected and is available at:
${reviewItemsPath}

This file contains:
- Recent commits (${summary.newCommits} new)
- Open PRs (${summary.newPRs} new)
- Open issues (${summary.newIssues} new)
- Files changed (${summary.filesChanged} files)
- Baseline divergences (${summary.divergences} found)

YOUR TASK:
1. Read the review items JSON file
2. Analyze the data against the 4 pillars
3. Generate the status report using the template
4. Save report to: ${reportOutputPath}

DO NOT waste time discovering what changed - it's already in the JSON.
Focus on ANALYSIS and RECOMMENDATIONS.

Working directory: ${repoPath}
Report template: ${templatePath}
Review items: ${reviewItemsPath}

Begin your analysis.
`.trim();
}
```

---

## ⏱️ Performance Benefits

### **Without Pre-Processing:**
```
Agent spawns → Discovers what to review (5-10 min, 50k tokens)
           → Analyzes changes (5 min, 30k tokens)
           → Generates report (3 min, 20k tokens)
Total: 13-18 minutes, ~100k tokens per repo
```

### **With Pre-Processing:**
```
Pre-process script runs (30 sec, 0 tokens) → Gathers all review items
Agent spawns → Reads JSON (10 sec, 2k tokens)
            → Analyzes changes (3 min, 20k tokens)
            → Generates report (2 min, 15k tokens)
Total: 5.5 minutes, ~37k tokens per repo
```

**Savings:**
- ⏱️ **60-70% faster** (13-18 min → 5.5 min)
- 💰 **60% cheaper** (100k tokens → 37k tokens)
- 🎯 **Better quality** (AI focuses on analysis, not discovery)

---

**This pre-processing approach makes the system far more efficient and cost-effective!**
