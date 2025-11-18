"""
Baseline Initialization System (Goal 2)
AI-powered baseline analysis for repositories on first encounter

Success Metrics:
- 100% repositories with baselines
- <10 min generation time per repository
- SHA256 hash verification for integrity
"""

import os
import logging
import hashlib
import json
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from pathlib import Path
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class RepositoryClassification:
    """Classification of repository type"""
    type: str  # greenfield, legacy, migration, fork, archive
    confidence: float  # 0.0 - 1.0
    reasoning: str


@dataclass
class RepositoryGoal:
    """A core goal for the repository"""
    id: str
    title: str
    description: str
    success_criteria: List[str]
    priority: int  # 1-5, where 1 is highest
    category: str  # feature, quality, performance, security, docs


@dataclass
class DevelopmentPhase:
    """A development phase or milestone"""
    id: str
    name: str
    description: str
    goals: List[str]  # Goal IDs
    estimated_duration: str
    dependencies: List[str]  # Other phase IDs
    status: str  # not_started, in_progress, completed


@dataclass
class RepositoryBaseline:
    """Complete baseline for a repository"""
    repo_name: str
    repo_owner: str
    classification: RepositoryClassification
    goals: List[RepositoryGoal]
    phases: List[DevelopmentPhase]
    metadata: Dict[str, Any]
    generated_at: str
    hash: str


class BaselineInitializer:
    """
    Service for initializing repository baselines using AI analysis

    Features:
    - AI-powered repository classification
    - Extract 4-10 core goals with success criteria
    - Document development phases and milestones
    - Store baselines in PostgreSQL with SHA256 hash
    - Detect baseline drift and trigger alerts
    """

    def __init__(self, config: Dict[str, Any], storage=None, model_manager=None):
        """
        Initialize baseline service

        Args:
            config: Configuration dictionary
            storage: Storage adapter for database operations
            model_manager: Model manager for AI analysis
        """
        self.config = config
        self.storage = storage
        self.model_manager = model_manager

        # Configuration
        self.baseline_config = config.get('baseline', {})
        self.min_goals = self.baseline_config.get('min_goals', 4)
        self.max_goals = self.baseline_config.get('max_goals', 10)
        self.force_regenerate = self.baseline_config.get('force_regenerate', False)

        logger.info("Baseline Initializer initialized")

    def initialize_repository_baseline(self, repo_path: Path, repo_name: str,
                                      repo_owner: str, user_id: Optional[int] = None) -> RepositoryBaseline:
        """
        Initialize baseline for a repository

        Args:
            repo_path: Path to local repository
            repo_name: Repository name
            repo_owner: Repository owner
            user_id: User ID for tracking

        Returns:
            Complete repository baseline
        """
        logger.info(f"Initializing baseline for {repo_owner}/{repo_name}")

        # Check if baseline already exists
        if not self.force_regenerate:
            existing_baseline = self._get_existing_baseline(repo_owner, repo_name)
            if existing_baseline:
                logger.info(f"Baseline already exists for {repo_owner}/{repo_name}")
                return existing_baseline

        # Analyze repository
        repo_analysis = self._analyze_repository_structure(repo_path)

        # Classify repository
        classification = self._classify_repository(repo_analysis)

        # Extract goals
        goals = self._extract_repository_goals(repo_analysis, classification)

        # Define phases
        phases = self._define_development_phases(goals, repo_analysis)

        # Create baseline object
        baseline = RepositoryBaseline(
            repo_name=repo_name,
            repo_owner=repo_owner,
            classification=classification,
            goals=goals,
            phases=phases,
            metadata={
                'repository_path': str(repo_path),
                'analysis_summary': repo_analysis,
                'generated_by': 'BaselineInitializer',
                'version': '1.0'
            },
            generated_at=datetime.now(timezone.utc).isoformat(),
            hash=''
        )

        # Calculate hash
        baseline.hash = self._calculate_baseline_hash(baseline)

        # Store in database
        if self.storage:
            self._store_baseline_in_db(baseline, user_id)

        # Save to file
        self._save_baseline_to_file(baseline, repo_path)

        logger.info(f"Baseline initialized for {repo_owner}/{repo_name} with {len(goals)} goals and {len(phases)} phases")
        return baseline

    def _analyze_repository_structure(self, repo_path: Path) -> Dict[str, Any]:
        """Analyze repository structure and extract key information"""
        logger.debug(f"Analyzing repository structure: {repo_path}")

        analysis = {
            'has_readme': False,
            'has_tests': False,
            'has_ci': False,
            'has_docs': False,
            'languages': [],
            'frameworks': [],
            'file_count': 0,
            'directory_structure': {},
            'package_managers': [],
            'build_systems': []
        }

        if not repo_path.exists():
            logger.warning(f"Repository path does not exist: {repo_path}")
            return analysis

        # Check for README
        for readme_name in ['README.md', 'README.rst', 'README.txt', 'README']:
            if (repo_path / readme_name).exists():
                analysis['has_readme'] = True
                analysis['readme_path'] = readme_name
                break

        # Check for documentation
        docs_dirs = ['docs', 'doc', 'documentation']
        for docs_dir in docs_dirs:
            if (repo_path / docs_dir).exists():
                analysis['has_docs'] = True
                analysis['docs_path'] = docs_dir
                break

        # Check for tests
        test_indicators = ['tests', 'test', '__tests__', 'spec']
        for test_dir in test_indicators:
            if (repo_path / test_dir).exists():
                analysis['has_tests'] = True
                break

        # Check for CI/CD
        ci_files = [
            '.github/workflows',
            '.gitlab-ci.yml',
            '.travis.yml',
            'circle.yml',
            '.circleci',
            'Jenkinsfile'
        ]
        for ci_file in ci_files:
            if (repo_path / ci_file).exists():
                analysis['has_ci'] = True
                break

        # Detect package managers and languages
        package_files = {
            'package.json': {'language': 'JavaScript/TypeScript', 'package_manager': 'npm'},
            'requirements.txt': {'language': 'Python', 'package_manager': 'pip'},
            'Pipfile': {'language': 'Python', 'package_manager': 'pipenv'},
            'pyproject.toml': {'language': 'Python', 'package_manager': 'poetry'},
            'Cargo.toml': {'language': 'Rust', 'package_manager': 'cargo'},
            'go.mod': {'language': 'Go', 'package_manager': 'go modules'},
            'pom.xml': {'language': 'Java', 'package_manager': 'maven'},
            'build.gradle': {'language': 'Java/Kotlin', 'package_manager': 'gradle'},
            'Gemfile': {'language': 'Ruby', 'package_manager': 'bundler'},
            'composer.json': {'language': 'PHP', 'package_manager': 'composer'}
        }

        for file_name, info in package_files.items():
            if (repo_path / file_name).exists():
                if info['language'] not in analysis['languages']:
                    analysis['languages'].append(info['language'])
                if info['package_manager'] not in analysis['package_managers']:
                    analysis['package_managers'].append(info['package_manager'])

        # Detect build systems
        build_files = {
            'Makefile': 'make',
            'CMakeLists.txt': 'cmake',
            'Dockerfile': 'docker',
            'docker-compose.yml': 'docker-compose'
        }

        for file_name, build_system in build_files.items():
            if (repo_path / file_name).exists():
                analysis['build_systems'].append(build_system)

        # Count files (excluding .git)
        try:
            file_count = 0
            for root, dirs, files in os.walk(repo_path):
                # Skip .git directory
                if '.git' in root:
                    continue
                file_count += len(files)
            analysis['file_count'] = file_count
        except Exception as e:
            logger.warning(f"Failed to count files: {e}")

        return analysis

    def _classify_repository(self, analysis: Dict[str, Any]) -> RepositoryClassification:
        """Classify repository type using analysis data"""
        logger.debug("Classifying repository")

        # Use AI if available, otherwise use heuristics
        if self.model_manager:
            classification = self._ai_classify_repository(analysis)
        else:
            classification = self._heuristic_classify_repository(analysis)

        return classification

    def _ai_classify_repository(self, analysis: Dict[str, Any]) -> RepositoryClassification:
        """Use AI to classify repository"""
        prompt = f"""Analyze this repository and classify it into one of these types:
- greenfield: New project with active development
- legacy: Older project that needs modernization
- migration: Project in the middle of a migration or refactor
- fork: Fork of another project
- archive: Inactive or archived project

Repository Analysis:
- Has README: {analysis['has_readme']}
- Has Tests: {analysis['has_tests']}
- Has CI: {analysis['has_ci']}
- Has Docs: {analysis['has_docs']}
- Languages: {', '.join(analysis['languages']) or 'Unknown'}
- Package Managers: {', '.join(analysis['package_managers']) or 'None'}
- File Count: {analysis['file_count']}

Provide:
1. Classification (one of the types above)
2. Confidence score (0.0-1.0)
3. Brief reasoning (1-2 sentences)

Format as JSON:
{{"type": "...", "confidence": 0.0, "reasoning": "..."}}"""

        try:
            response = self.model_manager.route_request(
                prompt=prompt,
                task_type='classification',
                complexity='simple'
            )

            result = json.loads(response.content)
            return RepositoryClassification(
                type=result['type'],
                confidence=result['confidence'],
                reasoning=result['reasoning']
            )

        except Exception as e:
            logger.warning(f"AI classification failed, falling back to heuristics: {e}")
            return self._heuristic_classify_repository(analysis)

    def _heuristic_classify_repository(self, analysis: Dict[str, Any]) -> RepositoryClassification:
        """Classify repository using heuristics"""
        # Simple heuristic classification
        if analysis['file_count'] < 50:
            return RepositoryClassification(
                type='greenfield',
                confidence=0.6,
                reasoning='Small repository with few files, likely a new project'
            )
        elif not analysis['has_tests'] and not analysis['has_ci']:
            return RepositoryClassification(
                type='legacy',
                confidence=0.7,
                reasoning='No tests or CI/CD, likely a legacy project'
            )
        else:
            return RepositoryClassification(
                type='greenfield',
                confidence=0.5,
                reasoning='Repository has standard development practices'
            )

    def _extract_repository_goals(self, analysis: Dict[str, Any],
                                  classification: RepositoryClassification) -> List[RepositoryGoal]:
        """Extract repository goals using AI analysis"""
        logger.debug("Extracting repository goals")

        # Use AI if available
        if self.model_manager:
            goals = self._ai_extract_goals(analysis, classification)
        else:
            goals = self._default_goals(analysis, classification)

        # Ensure we have between min_goals and max_goals
        if len(goals) < self.min_goals:
            logger.warning(f"Only {len(goals)} goals extracted, expected at least {self.min_goals}")
            goals.extend(self._default_goals(analysis, classification)[:self.min_goals - len(goals)])

        if len(goals) > self.max_goals:
            logger.info(f"Truncating goals from {len(goals)} to {self.max_goals}")
            goals = goals[:self.max_goals]

        return goals

    def _ai_extract_goals(self, analysis: Dict[str, Any],
                         classification: RepositoryClassification) -> List[RepositoryGoal]:
        """Use AI to extract repository goals"""
        prompt = f"""Analyze this repository and extract 4-10 core development goals.

Repository Type: {classification.type}
Repository Analysis:
- Languages: {', '.join(analysis['languages']) or 'Unknown'}
- Has Tests: {analysis['has_tests']}
- Has CI: {analysis['has_ci']}
- Has Docs: {analysis['has_docs']}

For each goal, provide:
1. Title (short, clear)
2. Description (1-2 sentences)
3. Success criteria (2-4 measurable criteria)
4. Priority (1-5, where 1 is highest)
5. Category (feature, quality, performance, security, docs)

Goals should be specific, measurable, and aligned with the repository type.

Format as JSON array:
[
  {{
    "title": "...",
    "description": "...",
    "success_criteria": ["...", "..."],
    "priority": 1,
    "category": "feature"
  }}
]"""

        try:
            response = self.model_manager.route_request(
                prompt=prompt,
                task_type='analysis',
                complexity='moderate'
            )

            goals_data = json.loads(response.content)
            goals = []

            for idx, goal_data in enumerate(goals_data):
                goal = RepositoryGoal(
                    id=f"goal-{idx + 1}",
                    title=goal_data['title'],
                    description=goal_data['description'],
                    success_criteria=goal_data['success_criteria'],
                    priority=goal_data['priority'],
                    category=goal_data['category']
                )
                goals.append(goal)

            return goals

        except Exception as e:
            logger.warning(f"AI goal extraction failed, using defaults: {e}")
            return self._default_goals(analysis, classification)

    def _default_goals(self, analysis: Dict[str, Any],
                      classification: RepositoryClassification) -> List[RepositoryGoal]:
        """Generate default goals based on analysis"""
        goals = []

        # Goal 1: Code Quality (always include)
        goals.append(RepositoryGoal(
            id='goal-1',
            title='Maintain High Code Quality',
            description='Ensure code meets quality standards through testing and reviews',
            success_criteria=[
                'Test coverage > 80%',
                'All PRs reviewed before merge',
                'No critical code quality issues'
            ],
            priority=1,
            category='quality'
        ))

        # Goal 2: CI/CD if not present
        if not analysis['has_ci']:
            goals.append(RepositoryGoal(
                id='goal-2',
                title='Implement CI/CD Pipeline',
                description='Set up automated testing and deployment pipeline',
                success_criteria=[
                    'CI runs on all PRs',
                    'Automated tests pass before merge',
                    'Deployment pipeline configured'
                ],
                priority=2,
                category='quality'
            ))

        # Goal 3: Documentation if not present
        if not analysis['has_docs']:
            goals.append(RepositoryGoal(
                id='goal-3',
                title='Improve Documentation',
                description='Create comprehensive documentation for users and developers',
                success_criteria=[
                    'README with setup instructions',
                    'API documentation',
                    'Contributing guidelines'
                ],
                priority=3,
                category='docs'
            ))

        # Goal 4: Testing if not present
        if not analysis['has_tests']:
            goals.append(RepositoryGoal(
                id='goal-4',
                title='Implement Testing Strategy',
                description='Add comprehensive test coverage',
                success_criteria=[
                    'Unit tests for core functionality',
                    'Integration tests',
                    'Test coverage > 70%'
                ],
                priority=2,
                category='quality'
            ))

        return goals

    def _define_development_phases(self, goals: List[RepositoryGoal],
                                   analysis: Dict[str, Any]) -> List[DevelopmentPhase]:
        """Define development phases based on goals"""
        logger.debug("Defining development phases")

        phases = []

        # Group goals by priority
        high_priority = [g for g in goals if g.priority <= 2]
        medium_priority = [g for g in goals if g.priority == 3]
        low_priority = [g for g in goals if g.priority >= 4]

        # Phase 1: Foundation
        if high_priority:
            phases.append(DevelopmentPhase(
                id='phase-1',
                name='Foundation',
                description='Establish core infrastructure and quality practices',
                goals=[g.id for g in high_priority],
                estimated_duration='2-4 weeks',
                dependencies=[],
                status='not_started'
            ))

        # Phase 2: Enhancement
        if medium_priority:
            phases.append(DevelopmentPhase(
                id='phase-2',
                name='Enhancement',
                description='Improve features and capabilities',
                goals=[g.id for g in medium_priority],
                estimated_duration='4-6 weeks',
                dependencies=['phase-1'] if high_priority else [],
                status='not_started'
            ))

        # Phase 3: Optimization
        if low_priority:
            phases.append(DevelopmentPhase(
                id='phase-3',
                name='Optimization',
                description='Optimize performance and user experience',
                goals=[g.id for g in low_priority],
                estimated_duration='2-3 weeks',
                dependencies=['phase-2'] if medium_priority else ['phase-1'],
                status='not_started'
            ))

        return phases

    def _calculate_baseline_hash(self, baseline: RepositoryBaseline) -> str:
        """Calculate SHA256 hash of baseline for integrity verification"""
        # Create a deterministic JSON representation
        baseline_dict = {
            'repo_name': baseline.repo_name,
            'repo_owner': baseline.repo_owner,
            'classification': asdict(baseline.classification),
            'goals': [asdict(g) for g in baseline.goals],
            'phases': [asdict(p) for p in baseline.phases]
        }

        baseline_json = json.dumps(baseline_dict, sort_keys=True)
        hash_value = hashlib.sha256(baseline_json.encode('utf-8')).hexdigest()

        return hash_value

    def _get_existing_baseline(self, repo_owner: str, repo_name: str) -> Optional[RepositoryBaseline]:
        """Get existing baseline from database"""
        if not self.storage:
            return None

        try:
            with self.storage.get_session() as session:
                from storage.adapter import Repository, Baseline

                # Find repository
                repo = session.query(Repository).filter(
                    Repository.owner == repo_owner,
                    Repository.name == repo_name
                ).first()

                if not repo:
                    return None

                # Get active baseline
                baseline = session.query(Baseline).filter(
                    Baseline.repo_id == repo.id,
                    Baseline.is_active == True
                ).first()

                if not baseline:
                    return None

                # Convert to RepositoryBaseline object
                return self._baseline_from_db(baseline)

        except Exception as e:
            logger.error(f"Failed to get existing baseline: {e}")
            return None

    def _store_baseline_in_db(self, baseline: RepositoryBaseline, user_id: Optional[int]):
        """Store baseline in database"""
        if not self.storage:
            return

        try:
            with self.storage.get_session() as session:
                from storage.adapter import Repository, Baseline

                # Find or create repository
                repo = session.query(Repository).filter(
                    Repository.owner == baseline.repo_owner,
                    Repository.name == baseline.repo_name
                ).first()

                if not repo:
                    repo = Repository(
                        name=baseline.repo_name,
                        owner=baseline.repo_owner,
                        created_by=user_id
                    )
                    session.add(repo)
                    session.flush()

                # Create baseline
                db_baseline = Baseline(
                    repo_id=repo.id,
                    goals={'goals': [asdict(g) for g in baseline.goals]},
                    phases={'phases': [asdict(p) for p in baseline.phases]},
                    metadata={
                        **baseline.metadata,
                        'classification': asdict(baseline.classification)
                    },
                    hash=baseline.hash,
                    created_by=user_id
                )
                session.add(db_baseline)

                logger.info(f"Baseline stored in database for {baseline.repo_owner}/{baseline.repo_name}")

        except Exception as e:
            logger.error(f"Failed to store baseline in database: {e}")

    def _save_baseline_to_file(self, baseline: RepositoryBaseline, repo_path: Path):
        """Save baseline to .baseline.json file in repository"""
        try:
            baseline_file = repo_path / '.baseline.json'

            baseline_dict = {
                'repo_name': baseline.repo_name,
                'repo_owner': baseline.repo_owner,
                'classification': asdict(baseline.classification),
                'goals': [asdict(g) for g in baseline.goals],
                'phases': [asdict(p) for p in baseline.phases],
                'metadata': baseline.metadata,
                'generated_at': baseline.generated_at,
                'hash': baseline.hash
            }

            with open(baseline_file, 'w') as f:
                json.dump(baseline_dict, f, indent=2)

            logger.info(f"Baseline saved to {baseline_file}")

        except Exception as e:
            logger.error(f"Failed to save baseline to file: {e}")

    def _baseline_from_db(self, db_baseline) -> RepositoryBaseline:
        """Convert database baseline to RepositoryBaseline object"""
        goals = [RepositoryGoal(**g) for g in db_baseline.goals.get('goals', [])]
        phases = [DevelopmentPhase(**p) for p in db_baseline.phases.get('phases', [])]

        classification_data = db_baseline.metadata.get('classification', {})
        classification = RepositoryClassification(**classification_data)

        return RepositoryBaseline(
            repo_name=db_baseline.repository.name,
            repo_owner=db_baseline.repository.owner,
            classification=classification,
            goals=goals,
            phases=phases,
            metadata=db_baseline.metadata,
            generated_at=db_baseline.created_at.isoformat(),
            hash=db_baseline.hash
        )

    def verify_baseline_integrity(self, baseline: RepositoryBaseline) -> bool:
        """Verify baseline integrity using hash"""
        calculated_hash = self._calculate_baseline_hash(baseline)
        return calculated_hash == baseline.hash

    def health_check(self) -> Dict[str, Any]:
        """Perform health check on baseline service"""
        try:
            status = 'healthy'
            issues = []

            # Check storage connection
            if self.storage:
                storage_health = self.storage.health_check()
                if storage_health.get('status') != 'healthy':
                    status = 'degraded'
                    issues.append('Storage unhealthy')

            # Check model manager
            if self.model_manager:
                model_stats = self.model_manager.get_model_stats()
                if not model_stats.get('available_models'):
                    status = 'degraded'
                    issues.append('No models available')

            return {
                'status': status,
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'configuration': {
                    'min_goals': self.min_goals,
                    'max_goals': self.max_goals,
                    'force_regenerate': self.force_regenerate
                },
                'issues': issues
            }

        except Exception as e:
            return {
                'status': 'unhealthy',
                'timestamp': datetime.now(timezone.utc).isoformat(),
                'error': str(e)
            }
