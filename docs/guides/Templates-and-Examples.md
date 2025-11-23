# Templates and Examples

**Status**: Canonical
**Last Updated**: November 23, 2025

This document contains the canonical templates used by the system agents (Output, Architect, Auditor) to generate reports and initialize repositories. These templates are designed to be machine-readable (for parsing) and human-readable (for review).

## 📝 Repository Initialization Template

Used by the **Architect Agent** when a new repository is added to the system. It establishes the "Locked Repository Charter" (intent record) against which future progress is measured.

> **Source Reference**: `archive/vision-v2-explorations/vision-v2-parallel-agents/Repository-Initialization-Template.md`

---

### Repository Initialization Analysis Template

**Repository:** {repo-name}
**Initialization Date:** {timestamp}
**Analysis Version:** 1.0
**Status:** 🔒 LOCKED REPOSITORY CHARTER (Non-modifiable)

---

#### 📋 Repository Classification

##### Type
- [ ] Greenfield (New project, no history)
- [ ] Legacy (Established codebase with history)
- [ ] Migration (Being moved/refactored)
- [ ] Fork (Derivative of another project)
- [ ] Archive (Maintenance-only mode)

##### Development Stage
- [ ] Planning / Design
- [ ] Active Development
- [ ] Beta / Testing
- [ ] Production / Stable
- [ ] Maintenance
- [ ] Deprecated

##### Primary Technology Stack
**Languages:** {languages}
**Frameworks:** {frameworks}
**Build System:** {build-system}
**Dependencies:** {key-dependencies}

---

#### 🎯 Core Repository Goals

##### Primary Objective
{1-2 sentence description of what this repository exists to achieve}

##### Goal 1: {Goal Title}
**Priority:** High | Medium | Low
**Target Date:** {date}
**Description:** {detailed-description}
**Success Criteria:**
- {criterion-1}
- {criterion-2}
- {criterion-3}

##### Goal 2: {Goal Title}
**Priority:** High | Medium | Low
**Target Date:** {date}
**Description:** {detailed-description}
**Success Criteria:**
- {criterion-1}
- {criterion-2}

##### Goal 3: {Goal Title}
**Priority:** High | Medium | Low
**Target Date:** {date}
**Description:** {detailed-description}
**Success Criteria:**
- {criterion-1}
- {criterion-2}

##### Goal 4: {Goal Title}
**Priority:** High | Medium | Low
**Target Date:** {date}
**Description:** {detailed-description}
**Success Criteria:**
- {criterion-1}
- {criterion-2}

##### [Additional Goals 5-10 as needed]

---

#### 📅 Development Phases

##### Phase 1: {Phase Name}
**Status:** Planned | In Progress | Completed | Skipped
**Start Date:** {date}
**Target Completion:** {date}
**Actual Completion:** {date-or-ongoing}

**Objectives:**
- {objective-1}
- {objective-2}
- {objective-3}

**Key Deliverables:**
- {deliverable-1}
- {deliverable-2}

**Status Summary:**
{1-2 sentences on current state}

##### Phase 2: {Phase Name}
**Status:** Planned | In Progress | Completed | Skipped
**Start Date:** {date}
**Target Completion:** {date}
**Actual Completion:** {date-or-ongoing}

**Objectives:**
- {objective-1}
- {objective-2}

**Key Deliverables:**
- {deliverable-1}
- {deliverable-2}

**Status Summary:**
{1-2 sentences on current state}

##### [Additional Phases as documented]

---

#### 📚 Historical Context

##### Repository Creation
**Created:** {date}
**Initial Commit:** {commit-hash}
**Creator:** {username}
**Initial Purpose:** {purpose}

##### Development History Summary
**Total Commits:** {count}
**Active Contributors:** {count}
**First Commit Date:** {date}
**Most Recent Commit:** {date}
**Average Commits per Week:** {count}

##### Major Milestones Achieved
1. **{milestone-1}** - {date}
   - {description}

2. **{milestone-2}** - {date}
   - {description}

3. **{milestone-3}** - {date}
   - {description}

##### Breaking Changes / Pivots
1. **{date}:** {description-of-major-change}
2. **{date}:** {description-of-pivot}

---

#### 📖 Documentation Analysis

##### Existing Documentation
- [ ] README.md (Completeness: {percentage}%)
- [ ] CONTRIBUTING.md
- [ ] CODE_OF_CONDUCT.md
- [ ] LICENSE
- [ ] CHANGELOG.md
- [ ] API Documentation
- [ ] User Guide
- [ ] Developer Guide
- [ ] Architecture Docs

##### Documentation Quality Assessment
**Overall Score:** {score}/100

**README.md Analysis:**
- Purpose clearly stated: {yes/no}
- Installation instructions: {yes/no}
- Usage examples: {yes/no}
- API reference: {yes/no}
- Contributing guide: {yes/no}

**Missing Critical Documentation:**
- {item-1}
- {item-2}
- {item-3}

---

#### 🏗️ Current Architecture

##### High-Level Structure
```
{ascii-diagram-of-architecture}
```

##### Key Components
1. **{component-1}**
   - Purpose: {description}
   - Location: {path}
   - Dependencies: {list}

2. **{component-2}**
   - Purpose: {description}
   - Location: {path}
   - Dependencies: {list}

##### External Dependencies
- {dependency-1} ({version}) - {purpose}
- {dependency-2} ({version}) - {purpose}
- {dependency-3} ({version}) - {purpose}

##### Known Technical Debt
1. {debt-item-1} (Priority: High/Medium/Low)
2. {debt-item-2} (Priority: High/Medium/Low)
3. {debt-item-3} (Priority: High/Medium/Low)

---

#### 🧪 Testing Infrastructure

##### Test Coverage
**Current Coverage:** {percentage}%
**Target Coverage:** {percentage}%

##### Test Types Present
- [ ] Unit Tests ({count} tests)
- [ ] Integration Tests ({count} tests)
- [ ] E2E Tests ({count} tests)
- [ ] Performance Tests ({count} tests)
- [ ] Security Tests ({count} tests)

##### CI/CD Status
- [ ] Automated Testing Enabled
- [ ] Coverage Reports Generated
- [ ] Tests Run on PR
- [ ] Deployment Pipeline Exists

**CI/CD Platform:** {platform-name}

---

#### 📊 Repository Charter Benchmarks

##### Code Quality Charter Benchmark
- **Linting Errors:** {count}
- **Code Complexity:** {metric}
- **Technical Debt Ratio:** {percentage}%
- **Maintainability Index:** {score}

##### Documentation Charter Benchmark
- **README Completeness:** {percentage}%
- **API Docs Coverage:** {percentage}%
- **Comment Density:** {percentage}%
- **Documentation Score:** {score}/100

##### Testing Charter Benchmark
- **Test Coverage:** {percentage}%
- **Tests Passing:** {count}/{total}
- **Test Execution Time:** {time}
- **Testing Score:** {score}/100

##### Adherence to Plan Charter Benchmark
- **Goals Defined:** {count}
- **Phases Documented:** {count}
- **Current Phase:** {phase-name}
- **On Track:** {yes/no}

---

#### 🎯 Repository Charter Goal Lock

**The following goals are LOCKED as of {date}:**

```json
{
  "goals": [
    {
      "id": "goal-1",
      "title": "{title}",
      "priority": "high",
      "targetDate": "{date}",
      "successCriteria": ["{criterion-1}", "{criterion-2}"]
    },
    {
      "id": "goal-2",
      "title": "{title}",
      "priority": "medium",
      "targetDate": "{date}",
      "successCriteria": ["{criterion-1}", "{criterion-2}"]
    }
  ],
  "phases": [
    {
      "id": "phase-1",
      "name": "{name}",
      "startDate": "{date}",
      "targetCompletion": "{date}",
      "objectives": ["{obj-1}", "{obj-2}"]
    }
  ]
}
```

**Hash:** {sha256-hash-of-locked-data}

---

## 📊 Status Report Template

Used by the **Output Agent** to generate periodic status reports. It compares current metrics against the Locked Repository Charter and the 4 Pillars of Health.

> **Source Reference**: `archive/vision-v2-explorations/vision-v2-parallel-agents/Status-Report-Template.md`

---

### Repository Status Report: {repo-name}

**Generated:** {timestamp}
**Report Period:** {period}
**Report Type:** Periodic Status Update
**Charter Version:** v{version}

---

#### 🔍 Pre-Gathered Review Items

*These items were identified BEFORE AI analysis to streamline the review process.*

##### Changes Since Last Report
- **New Commits:** {count} commits
- **New PRs:** {count} pull requests
- **New Issues:** {count} issues
- **Closed Items:** {count} PRs merged, {count} issues closed

##### Items Requiring Review

###### 📝 New Pull Requests ({count})
| # | Title | Author | Created | Files Changed | Status |
|---|-------|--------|---------|---------------|--------|
| #{pr-number} | {title} | {author} | {date} | {count} | {status} |
| #{pr-number} | {title} | {author} | {date} | {count} | {status} |

###### 🐛 New Issues ({count})
| # | Title | Author | Created | Labels | Priority |
|---|-------|--------|---------|--------|----------|
| #{issue-number} | {title} | {author} | {date} | {labels} | {priority} |
| #{issue-number} | {title} | {author} | {date} | {labels} | {priority} |

###### 🔄 Recent Commits (Last 7 Days)
| Hash | Message | Author | Date | Files |
|------|---------|--------|------|-------|
| {short-hash} | {message} | {author} | {date} | {count} |
| {short-hash} | {message} | {author} | {date} | {count} |

###### 📦 Dependency Updates
| Package | Old Version | New Version | Type | Risk |
|---------|-------------|-------------|------|------|
| {package} | {old} | {new} | {major/minor/patch} | {high/medium/low} |

###### 🔧 Configuration Changes
- {file-path}: {description-of-change}
- {file-path}: {description-of-change}

---

#### 📊 Quick Stats

##### Repository Health
- **Overall Health Score:** {score}/100 ({trend} from last report)
- **Active Contributors:** {count} (last 30 days)
- **Commit Velocity:** {commits-per-week} commits/week
- **PR Merge Rate:** {percentage}% within 48 hours
- **Issue Resolution Rate:** {percentage}% within 7 days

##### Current Status
- **Open PRs:** {count} ({age-distribution})
- **Open Issues:** {count} ({priority-breakdown})
- **Recent Activity:** {commits} commits, {prs} PRs, {issues} issues (last 7 days)
- **Last Commit:** {date} by {author}

---

#### 🎯 The 4 Pillars

##### 1️⃣ Code Quality (Score: {score}/100)
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

##### 2️⃣ Documentation (Score: {score}/100)
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

##### 3️⃣ Testing (Score: {score}/100)
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

##### 4️⃣ Adherence to Plan (Score: {score}/100)
**Last Assessed:** {date}
**Trend:** {↑ Improving | → Stable | ↓ Declining}
**Status:** {🟢 On Track | 🟡 Minor Deviation | 🔴 Significant Divergence}

**Charter Comparison:**
- **Locked Charter:** v{version} (Established: {date})
- **Goals on Track:** {on-track}/{total} ({percentage}%)
- **Milestones Met:** {met}/{total} ({percentage}%)
- **Phase Alignment:** {current-phase} vs. planned {planned-phase}

**Goal Progress:**

###### Goal 1: {Goal Title} (Priority: {priority})
**Target Date:** {date}
**Status:** {🟢 On Track | 🟡 At Risk | 🔴 Delayed}
**Progress:** {percentage}%

**Success Criteria:**
- [x] {completed-criterion-1}
- [ ] {pending-criterion-2}
- [ ] {pending-criterion-3}

**Notes:** {progress-notes}

###### Goal 2: {Goal Title} (Priority: {priority})
**Target Date:** {date}
**Status:** {🟢 On Track | 🟡 At Risk | 🔴 Delayed}
**Progress:** {percentage}%

**Success Criteria:**
- [ ] {pending-criterion-1}
- [ ] {pending-criterion-2}

**Notes:** {progress-notes}

**Divergences from Charter:**

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
- **Charter Phase:** {planned-phase}
- **Alignment:** {aligned/ahead/behind}
- **Days Off Track:** {days} ({ahead/behind})

**Action Items:**
- [ ] {action-item-1}
- [ ] {action-item-2}

---

#### 📋 Open Pull Requests

##### High Priority ({count})
| # | Title | Author | Created | Age | Files | Status | CI |
|---|-------|--------|---------|-----|-------|--------|----|
| #{pr} | {title} | {author} | {date} | {days}d | {count} | {status} | {✅/❌} |

##### Standard Priority ({count})
| # | Title | Author | Created | Age | Files | Status | CI |
|---|-------|--------|---------|-----|-------|--------|----|
| #{pr} | {title} | {author} | {date} | {days}d | {count} | {status} | {✅/❌} |

##### Stale PRs (>{threshold} days old)
| # | Title | Author | Created | Age | Last Activity |
|---|-------|--------|---------|-----|---------------|
| #{pr} | {title} | {author} | {date} | {days}d | {date} |

---

#### 🐛 Open Issues

##### Critical ({count})
| # | Title | Author | Created | Age | Labels | Assigned |
|---|-------|--------|---------|-----|--------|----------|
| #{issue} | {title} | {author} | {date} | {days}d | {labels} | {assignee} |

##### High Priority ({count})
| # | Title | Author | Created | Age | Labels | Assigned |
|---|-------|--------|---------|-----|--------|----------|
| #{issue} | {title} | {author} | {date} | {days}d | {labels} | {assignee} |

##### Other ({count})
*View full issue list on GitHub*

---

#### 📈 Trends (Last 30 Days)

##### Activity Metrics
```
Commits:  ████████████░░░░░░░░ {count} ({trend} vs. previous period)
PRs:      ██████░░░░░░░░░░░░░░ {count} merged ({percentage}% merge rate)
Issues:   ████████░░░░░░░░░░░░ {count} closed ({percentage}% close rate)
Coverage: ████████████████░░░░ {percentage}% ({delta}% change)
```

##### Velocity Trends
- **Commit Frequency:** {commits-per-week} commits/week ({trend})
- **PR Merge Time:** {avg-hours} hours average ({trend})
- **Issue Resolution:** {avg-days} days average ({trend})
- **Code Churn:** {percentage}% ({trend})

##### Quality Trends
- **Test Coverage:** {percentage}% ({delta}%)
- **Code Quality:** {score}/100 ({delta})
- **Documentation:** {score}/100 ({delta})
- **Plan Adherence:** {score}/100 ({delta})

---

#### 🚨 Action Items Summary

##### High Priority
- [ ] **{repo-name}**: {action-item-1}
- [ ] **{repo-name}**: {action-item-2}

##### Medium Priority
- [ ] **{repo-name}**: {action-item-3}
- [ ] **{repo-name}**: {action-item-4}

##### Low Priority
- [ ] **{repo-name}**: {action-item-5}

##### Divergence Reviews Required
- [ ] **Review divergence:** {divergence-description}
- [ ] **Review goal change:** {goal-change-description}

---

#### 📊 Comparison to Charter Benchmarks

##### Goals Alignment
| Goal | Charter Status | Current Status | Alignment |
|------|----------------|----------------|-----------|
| {goal-1} | {charter} | {current} | {🟢/🟡/🔴} |
| {goal-2} | {charter} | {current} | {🟢/🟡/🔴} |

##### Metrics Drift
| Metric | Charter Benchmark | Current | Delta | Status |
|--------|----------|---------|-------|--------|
| Test Coverage | {charter}% | {current}% | {delta}% | {🟢/🟡/🔴} |
| Code Quality | {charter} | {current} | {delta} | {🟢/🟡/🔴} |
| Documentation | {charter}% | {current}% | {delta}% | {🟢/🟡/🔴} |

---

#### 🔍 AI Analysis Notes

*This section contains observations from the AI agent review:*

##### Key Observations
- {observation-1}
- {observation-2}
- {observation-3}

##### Potential Concerns
- {concern-1}
- {concern-2}

##### Recommendations
1. {recommendation-1}
2. {recommendation-2}
3. {recommendation-3}

##### Questions for Human Review
- {question-1}
- {question-2}

---

#### 📝 Next Actions

##### Immediate (Next 24 hours)
- {action-1}
- {action-2}

##### Short Term (Next 7 days)
- {action-1}
- {action-2}

##### Medium Term (Next 30 days)
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
*Charter Version: v{version} | Report Version: {report-version}*

## 📂 Examples
- Prototype/dated run reports are archived under `archive/run-reports/` for reference only.
- Live examples should be produced by the Output agent using the templates above and linked in GH comments/status (Levels 1–3) when enabled.

## ✅ Guidance
- Keep examples lightweight; avoid embedding large diffs/logs.
- Visuals: adhere to configured limits (node/event caps) and approved types (timeline, gantt, flowchart, sequence).
