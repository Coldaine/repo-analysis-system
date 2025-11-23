---
cssclasses: [artifact, bg-ocean]
tags: [template, status-report, periodic]
date: 2025-11-17
---

# Repository Status Report: {repo-name}

**Generated:** {timestamp}
**Report Period:** {period}
**Report Type:** Periodic Status Update
**Baseline Version:** v{version}

---

## 🔍 Pre-Gathered Review Items

*These items were identified BEFORE AI analysis to streamline the review process.*

### Changes Since Last Report
- **New Commits:** {count} commits
- **New PRs:** {count} pull requests
- **New Issues:** {count} issues
- **Closed Items:** {count} PRs merged, {count} issues closed

### Items Requiring Review

#### 📝 New Pull Requests ({count})
| # | Title | Author | Created | Files Changed | Status |
|---|-------|--------|---------|---------------|--------|
| #{pr-number} | {title} | {author} | {date} | {count} | {status} |
| #{pr-number} | {title} | {author} | {date} | {count} | {status} |

#### 🐛 New Issues ({count})
| # | Title | Author | Created | Labels | Priority |
|---|-------|--------|---------|--------|----------|
| #{issue-number} | {title} | {author} | {date} | {labels} | {priority} |
| #{issue-number} | {title} | {author} | {date} | {labels} | {priority} |

#### 🔄 Recent Commits (Last 7 Days)
| Hash | Message | Author | Date | Files |
|------|---------|--------|------|-------|
| {short-hash} | {message} | {author} | {date} | {count} |
| {short-hash} | {message} | {author} | {date} | {count} |

#### 📦 Dependency Updates
| Package | Old Version | New Version | Type | Risk |
|---------|-------------|-------------|------|------|
| {package} | {old} | {new} | {major/minor/patch} | {high/medium/low} |

#### 🔧 Configuration Changes
- {file-path}: {description-of-change}
- {file-path}: {description-of-change}

---

## 📊 Quick Stats

### Repository Health
- **Overall Health Score:** {score}/100 ({trend} from last report)
- **Active Contributors:** {count} (last 30 days)
- **Commit Velocity:** {commits-per-week} commits/week
- **PR Merge Rate:** {percentage}% within 48 hours
- **Issue Resolution Rate:** {percentage}% within 7 days

### Current Status
- **Open PRs:** {count} ({age-distribution})
- **Open Issues:** {count} ({priority-breakdown})
- **Recent Activity:** {commits} commits, {prs} PRs, {issues} issues (last 7 days)
- **Last Commit:** {date} by {author}

---

## 🎯 The 4 Pillars

### 1️⃣ Code Quality (Score: {score}/100)
**Last Assessed:** {date}
**Trend:** {↑ Improving | → Stable | ↓ Declining}
**Status:** {🟢 Good | 🟡 Needs Attention | 🔴 Critical}

**Metrics:**
- **Linting Errors:** {count} ({delta} from last report)
- **Code Complexity:** {metric} (Target: <{target})
- **Technical Debt:** {hours} hours ({percentage}% of codebase)
- **Code Smells:** {count} ({severity-breakdown})
- **Maintainability Index:** {score}/100

**Recent Changes:**
- {change-1-description}
- {change-2-description}

**Action Items:**
- [ ] {action-item-1}
- [ ] {action-item-2}

---

### 2️⃣ Documentation (Score: {score}/100)
**Last Assessed:** {date}
**Trend:** {↑ Improving | → Stable | ↓ Declining}
**Status:** {🟢 Good | 🟡 Needs Attention | 🔴 Critical}

**Metrics:**
- **README Completeness:** {percentage}% (Target: {target}%)
- **API Docs Coverage:** {percentage}% of public APIs documented
- **Comment Density:** {percentage}% (lines with comments)
- **Inline Documentation:** {count} functions documented / {total} total
- **Documentation Build:** {✅ Passing | ❌ Failing}

**Recent Updates:**
- {update-1-description}
- {update-2-description}

**Missing Documentation:**
- {missing-1}
- {missing-2}

**Action Items:**
- [ ] {action-item-1}
- [ ] {action-item-2}

---

### 3️⃣ Testing (Score: {score}/100)
**Last Assessed:** {date}
**Trend:** {↑ Improving | → Stable | ↓ Declining}
**Status:** {🟢 Good | 🟡 Needs Attention | 🔴 Critical}

**Metrics:**
- **Overall Coverage:** {percentage}% (Target: {target}%)
- **Unit Test Coverage:** {percentage}%
- **Integration Test Coverage:** {percentage}%
- **Tests Passing:** {passing}/{total} ({percentage}%)
- **Test Execution Time:** {time}s (Target: <{target}s)
- **Flaky Tests:** {count} tests with intermittent failures

**Coverage by Module:**
| Module | Coverage | Tests | Status |
|--------|----------|-------|--------|
| {module-1} | {percentage}% | {count} | {status} |
| {module-2} | {percentage}% | {count} | {status} |

**Recent Test Updates:**
- {update-1}
- {update-2}

**Action Items:**
- [ ] {action-item-1}
- [ ] {action-item-2}

---

### 4️⃣ Adherence to Plan (Score: {score}/100)
**Last Assessed:** {date}
**Trend:** {↑ Improving | → Stable | ↓ Declining}
**Status:** {🟢 On Track | 🟡 Minor Deviation | 🔴 Significant Divergence}

**Baseline Comparison:**
- **Locked Baseline:** v{version} (Established: {date})
- **Goals on Track:** {on-track}/{total} ({percentage}%)
- **Milestones Met:** {met}/{total} ({percentage}%)
- **Phase Alignment:** {current-phase} vs. planned {planned-phase}

**Goal Progress:**

#### Goal 1: {Goal Title} (Priority: {priority})
**Target Date:** {date}
**Status:** {🟢 On Track | 🟡 At Risk | 🔴 Delayed}
**Progress:** {percentage}%

**Success Criteria:**
- [x] {completed-criterion-1}
- [ ] {pending-criterion-2}
- [ ] {pending-criterion-3}

**Notes:** {progress-notes}

#### Goal 2: {Goal Title} (Priority: {priority})
**Target Date:** {date}
**Status:** {🟢 On Track | 🟡 At Risk | 🔴 Delayed}
**Progress:** {percentage}%

**Success Criteria:**
- [ ] {pending-criterion-1}
- [ ] {pending-criterion-2}

**Notes:** {progress-notes}

**Divergences from Baseline:**

⚠️ **Divergence 1: {Description}**
- **Type:** Goal Change | Phase Slip | Scope Creep | Deprioritization
- **Severity:** Minor | Moderate | Major
- **Detected:** {date}
- **Details:** {detailed-description}
- **Impact:** {impact-assessment}
- **Requires Review:** {yes/no}

⚠️ **Divergence 2: {Description}**
- **Type:** {type}
- **Severity:** {severity}
- **Detected:** {date}
- **Details:** {detailed-description}
- **Impact:** {impact-assessment}
- **Requires Review:** {yes/no}

**Phase Status:**
- **Current Phase:** {phase-name}
- **Baseline Phase:** {planned-phase}
- **Alignment:** {aligned/ahead/behind}
- **Days Off Track:** {days} ({ahead/behind})

**Action Items:**
- [ ] {action-item-1}
- [ ] {action-item-2}

---

## 📋 Open Pull Requests

### High Priority ({count})
| # | Title | Author | Created | Age | Files | Status | CI |
|---|-------|--------|---------|-----|-------|--------|----|
| #{pr} | {title} | {author} | {date} | {days}d | {count} | {status} | {✅/❌} |

### Standard Priority ({count})
| # | Title | Author | Created | Age | Files | Status | CI |
|---|-------|--------|---------|-----|-------|--------|----|
| #{pr} | {title} | {author} | {date} | {days}d | {count} | {status} | {✅/❌} |

### Stale PRs (>{threshold} days old)
| # | Title | Author | Created | Age | Last Activity |
|---|-------|--------|---------|-----|---------------|
| #{pr} | {title} | {author} | {date} | {days}d | {date} |

---

## 🐛 Open Issues

### Critical ({count})
| # | Title | Author | Created | Age | Labels | Assigned |
|---|-------|--------|---------|-----|--------|----------|
| #{issue} | {title} | {author} | {date} | {days}d | {labels} | {assignee} |

### High Priority ({count})
| # | Title | Author | Created | Age | Labels | Assigned |
|---|-------|--------|---------|-----|--------|----------|
| #{issue} | {title} | {author} | {date} | {days}d | {labels} | {assignee} |

### Other ({count})
*View full issue list on GitHub*

---

## 📈 Trends (Last 30 Days)

### Activity Metrics
```
Commits:  ████████████░░░░░░░░ {count} ({trend} vs. previous period)
PRs:      ██████░░░░░░░░░░░░░░ {count} merged ({percentage}% merge rate)
Issues:   ████████░░░░░░░░░░░░ {count} closed ({percentage}% close rate)
Coverage: ████████████████░░░░ {percentage}% ({delta}% change)
```

### Velocity Trends
- **Commit Frequency:** {commits-per-week} commits/week ({trend})
- **PR Merge Time:** {avg-hours} hours average ({trend})
- **Issue Resolution:** {avg-days} days average ({trend})
- **Code Churn:** {percentage}% ({trend})

### Quality Trends
- **Test Coverage:** {percentage}% ({delta}%)
- **Code Quality:** {score}/100 ({delta})
- **Documentation:** {score}/100 ({delta})
- **Plan Adherence:** {score}/100 ({delta})

---

## 🚨 Action Items Summary

### High Priority
- [ ] **{repo-name}**: {action-item-1}
- [ ] **{repo-name}**: {action-item-2}

### Medium Priority
- [ ] **{repo-name}**: {action-item-3}
- [ ] **{repo-name}**: {action-item-4}

### Low Priority
- [ ] **{repo-name}**: {action-item-5}

### Divergence Reviews Required
- [ ] **Review divergence:** {divergence-description}
- [ ] **Review goal change:** {goal-change-description}

---

## 📊 Comparison to Baseline

### Goals Alignment
| Goal | Baseline Status | Current Status | Alignment |
|------|----------------|----------------|-----------|
| {goal-1} | {baseline} | {current} | {🟢/🟡/🔴} |
| {goal-2} | {baseline} | {current} | {🟢/🟡/🔴} |

### Metrics Drift
| Metric | Baseline | Current | Delta | Status |
|--------|----------|---------|-------|--------|
| Test Coverage | {baseline}% | {current}% | {delta}% | {🟢/🟡/🔴} |
| Code Quality | {baseline} | {current} | {delta} | {🟢/🟡/🔴} |
| Documentation | {baseline}% | {current}% | {delta}% | {🟢/🟡/🔴} |

---

## 🔍 AI Analysis Notes

*This section contains observations from the AI agent review:*

### Key Observations
- {observation-1}
- {observation-2}
- {observation-3}

### Potential Concerns
- {concern-1}
- {concern-2}

### Recommendations
1. {recommendation-1}
2. {recommendation-2}
3. {recommendation-3}

### Questions for Human Review
- {question-1}
- {question-2}

---

## 📝 Next Actions

### Immediate (Next 24 hours)
- {action-1}
- {action-2}

### Short Term (Next 7 days)
- {action-1}
- {action-2}

### Medium Term (Next 30 days)
- {action-1}
- {action-2}

---

**Report Generation Metadata:**
- **Agent ID:** {agent-id}
- **Analysis Duration:** {duration}
- **Data Sources:** GitHub API, Git Log, Test Results, Linting Tools
- **API Cost:** ${cost} (via CCR → Z.ai)
- **Next Report:** {next-report-time}

---

*Generated by Multi-Repo Agent Manager v1.0*
*Baseline: v{version} | Report Version: {report-version}*
