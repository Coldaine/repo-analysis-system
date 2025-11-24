"""
Storage Adapter Layer
Provides database abstraction with PostgreSQL backend for multi-user concurrent access
"""

import os
import json
import logging
from typing import Dict, List, Any, Optional, Union
from datetime import datetime, timezone
from dataclasses import dataclass, asdict
from contextlib import contextmanager

from sqlalchemy import create_engine, Column, Integer, String, Text, Boolean, DateTime, Numeric, ForeignKey
from sqlalchemy.orm import sessionmaker, Session, relationship, declarative_base
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.pool import QueuePool
import uuid

logger = logging.getLogger(__name__)

Base = declarative_base()

# Database Models
class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    api_key_hash = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    repositories = relationship("Repository", back_populates="creator")
    analysis_runs = relationship("AnalysisRun", back_populates="creator")

class Repository(Base):
    __tablename__ = 'repositories'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    owner = Column(String(255), nullable=False)
    github_id = Column(Integer, unique=True)
    description = Column(Text)
    language = Column(String(100))
    last_sync = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)
    is_monitored = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    creator = relationship("User", back_populates="repositories")
    baselines = relationship("Baseline", back_populates="repository")
    analysis_runs = relationship("AnalysisRun", back_populates="repository")

class Baseline(Base):
    __tablename__ = 'baselines'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    repo_id = Column(Integer, ForeignKey('repositories.id', ondelete='CASCADE'))
    goals = Column(JSONB, nullable=False)
    phases = Column(JSONB, nullable=False)
    extra_metadata = Column(JSONB)
    hash = Column(String(64), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    created_by = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    repository = relationship("Repository", back_populates="baselines")
    analysis_runs = relationship("AnalysisRun", back_populates="baseline")

class AnalysisRun(Base):
    __tablename__ = 'analysis_runs'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    repo_id = Column(Integer, ForeignKey('repositories.id', ondelete='CASCADE'))
    baseline_id = Column(Integer, ForeignKey('baselines.id'))
    run_type = Column(String(50), default='full')
    status = Column(String(20), default='pending')
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Integer)
    metrics = Column(JSONB)
    error_message = Column(Text)
    created_by = Column(Integer, ForeignKey('users.id'))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    repository = relationship("Repository", back_populates="analysis_runs")
    baseline = relationship("Baseline", back_populates="analysis_runs")
    creator = relationship("User", back_populates="analysis_runs")
    pull_requests = relationship("PullRequest", back_populates="run")
    pain_points = relationship("PainPoint", back_populates="run")
    visualizations = relationship("Visualization", back_populates="run")

class PullRequest(Base):
    __tablename__ = 'pull_requests'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    run_id = Column(Integer, ForeignKey('analysis_runs.id', ondelete='CASCADE'))
    github_pr_id = Column(Integer, nullable=False)
    title = Column(String(500), nullable=False)
    description = Column(Text)
    author = Column(String(255))
    state = Column(String(20))
    created_at = Column(DateTime(timezone=True))
    updated_at = Column(DateTime(timezone=True))
    merged_at = Column(DateTime(timezone=True))
    additions = Column(Integer)
    deletions = Column(Integer)
    changed_files = Column(Integer)
    extra_metadata = Column(JSONB)
    
    # Relationships
    run = relationship("AnalysisRun", back_populates="pull_requests")
    pain_points = relationship("PainPoint", back_populates="pr")

class PainPoint(Base):
    __tablename__ = 'pain_points'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    run_id = Column(Integer, ForeignKey('analysis_runs.id', ondelete='CASCADE'))
    pr_id = Column(Integer, ForeignKey('pull_requests.id', ondelete='SET NULL'))
    type = Column(String(50), nullable=False)
    severity = Column(Integer, nullable=False)
    description = Column(Text, nullable=False)
    raw_context = Column(JSONB)
    confidence_score = Column(Numeric(3, 2))
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    run = relationship("AnalysisRun", back_populates="pain_points")
    pr = relationship("PullRequest", back_populates="pain_points")
    recommendations = relationship("Recommendation", back_populates="pain_point")

class Recommendation(Base):
    __tablename__ = 'recommendations'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    pain_point_id = Column(Integer, ForeignKey('pain_points.id', ondelete='CASCADE'))
    text = Column(Text, nullable=False)
    source = Column(String(100))
    source_url = Column(String(500))
    rank = Column(Integer)
    confidence_score = Column(Numeric(3, 2))
    is_accepted = Column(Boolean)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    pain_point = relationship("PainPoint", back_populates="recommendations")

class Visualization(Base):
    __tablename__ = 'visualizations'
    
    id = Column(Integer, primary_key=True)
    uuid = Column(UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False)
    run_id = Column(Integer, ForeignKey('analysis_runs.id', ondelete='CASCADE'))
    type = Column(String(50), nullable=False)
    title = Column(String(255))
    description = Column(Text)
    mermaid_code = Column(Text)
    file_path = Column(String(500))
    extra_metadata = Column(JSONB)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    run = relationship("AnalysisRun", back_populates="visualizations")

@dataclass
class DatabaseConfig:
    """Database configuration"""
    host: str = "localhost"
    port: int = 5432
    name: str = "repo_analysis"
    user: str = "postgres"
    password: str = ""
    pool_size: int = 10
    max_overflow: int = 20
    echo: bool = False

class StorageAdapter:
    """Storage adapter with PostgreSQL backend"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.engine = None
        self.SessionLocal = None
        self._initialize()
    
    def _initialize(self):
        """Initialize database connection and session factory"""
        database_url = (
            f"postgresql://{self.config.user}:{self.config.password}@"
            f"{self.config.host}:{self.config.port}/{self.config.name}"
        )
        
        self.engine = create_engine(
            database_url,
            poolclass=QueuePool,
            pool_size=self.config.pool_size,
            max_overflow=self.config.max_overflow,
            echo=self.config.echo,
            pool_pre_ping=True,
            pool_recycle=3600
        )
        
        self.SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )
        
        # Create tables if they don't exist
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database initialized successfully")
    
    @contextmanager
    def get_session(self):
        """Get database session with automatic cleanup"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    # User Management
    def create_user(self, username: str, email: str, api_key_hash: str = None) -> Optional[User]:
        """Create a new user"""
        with self.get_session() as session:
            user = User(
                username=username,
                email=email,
                api_key_hash=api_key_hash
            )
            session.add(user)
            session.flush()
            session.refresh(user)
            return user
    
    def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by ID"""
        with self.get_session() as session:
            return session.query(User).filter(User.id == user_id).first()
    
    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get user by username"""
        with self.get_session() as session:
            return session.query(User).filter(User.username == username).first()
    
    # Repository Management
    def create_repository(self, name: str, owner: str, created_by: int, 
                        github_id: int = None, description: str = None, 
                        language: str = None) -> Optional[Repository]:
        """Create a new repository"""
        with self.get_session() as session:
            repo = Repository(
                name=name,
                owner=owner,
                github_id=github_id,
                description=description,
                language=language,
                created_by=created_by
            )
            session.add(repo)
            session.flush()
            session.refresh(repo)
            return repo
    
    def get_repository_by_id(self, repo_id: int) -> Optional[Repository]:
        """Get repository by ID"""
        with self.get_session() as session:
            return session.query(Repository).filter(Repository.id == repo_id).first()
    
    def get_repositories_by_user(self, user_id: int) -> List[Repository]:
        """Get all repositories for a user"""
        with self.get_session() as session:
            return session.query(Repository).filter(
                Repository.created_by == user_id,
                Repository.is_active == True
            ).all()
    
    def get_monitored_repositories(self) -> List[Repository]:
        """Get all monitored repositories"""
        with self.get_session() as session:
            return session.query(Repository).filter(
                Repository.is_active == True,
                Repository.is_monitored == True
            ).all()
    
    # Baseline Management
    def create_baseline(self, repo_id: int, goals: Dict, phases: Dict, 
                      hash_value: str, created_by: int, 
                      metadata: Dict = None) -> Optional[Baseline]:
        """Create a new baseline"""
        with self.get_session() as session:
            baseline = Baseline(
                repo_id=repo_id,
                goals=goals,
                phases=phases,
                metadata=metadata,
                hash=hash_value,
                created_by=created_by
            )
            session.add(baseline)
            session.flush()
            session.refresh(baseline)
            return baseline
    
    def get_active_baseline(self, repo_id: int) -> Optional[Baseline]:
        """Get active baseline for repository"""
        with self.get_session() as session:
            return session.query(Baseline).filter(
                Baseline.repo_id == repo_id,
                Baseline.is_active == True
            ).first()
    
    # Analysis Run Management
    def create_analysis_run(self, repo_id: int, run_type: str = 'full', 
                          baseline_id: int = None, created_by: int = None) -> Optional[AnalysisRun]:
        """Create a new analysis run"""
        with self.get_session() as session:
            run = AnalysisRun(
                repo_id=repo_id,
                run_type=run_type,
                baseline_id=baseline_id,
                status='pending',
                created_by=created_by
            )
            session.add(run)
            session.flush()
            session.refresh(run)
            return run
    
    def update_analysis_run_status(self, run_id: int, status: str, 
                                error_message: str = None) -> bool:
        """Update analysis run status"""
        with self.get_session() as session:
            run = session.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
            if not run:
                return False
            
            run.status = status
            if error_message:
                run.error_message = error_message
            
            if status == 'running':
                run.started_at = datetime.now(timezone.utc)
            elif status in ['completed', 'failed', 'cancelled']:
                run.completed_at = datetime.now(timezone.utc)
                if run.started_at:
                    run.duration_seconds = int((run.completed_at - run.started_at).total_seconds())
            
            return True
    
    def get_analysis_run_by_id(self, run_id: int) -> Optional[AnalysisRun]:
        """Get analysis run by ID"""
        with self.get_session() as session:
            return session.query(AnalysisRun).filter(AnalysisRun.id == run_id).first()
    
    def get_pending_runs(self, limit: int = 10) -> List[AnalysisRun]:
        """Get pending analysis runs"""
        with self.get_session() as session:
            return session.query(AnalysisRun).filter(
                AnalysisRun.status == 'pending'
            ).order_by(AnalysisRun.created_at).limit(limit).all()
    
    # Pain Point Management
    def create_pain_point(self, run_id: int, pain_type: str, severity: int, 
                         description: str, raw_context: Dict = None, 
                         pr_id: int = None, confidence_score: float = None) -> Optional[PainPoint]:
        """Create a new pain point"""
        with self.get_session() as session:
            pain_point = PainPoint(
                run_id=run_id,
                pr_id=pr_id,
                type=pain_type,
                severity=severity,
                description=description,
                raw_context=raw_context,
                confidence_score=confidence_score
            )
            session.add(pain_point)
            session.flush()
            session.refresh(pain_point)
            return pain_point
    
    def get_pain_points_by_run(self, run_id: int) -> List[PainPoint]:
        """Get pain points for an analysis run"""
        with self.get_session() as session:
            return session.query(PainPoint).filter(
                PainPoint.run_id == run_id
            ).order_by(PainPoint.severity.desc()).all()
    
    # Recommendation Management
    def create_recommendation(self, pain_point_id: int, text: str, source: str = None,
                           source_url: str = None, rank: int = None,
                           confidence_score: float = None) -> Optional[Recommendation]:
        """Create a new recommendation"""
        with self.get_session() as session:
            recommendation = Recommendation(
                pain_point_id=pain_point_id,
                text=text,
                source=source,
                source_url=source_url,
                rank=rank,
                confidence_score=confidence_score
            )
            session.add(recommendation)
            session.flush()
            session.refresh(recommendation)
            return recommendation
    
    def get_recommendations_by_pain_point(self, pain_point_id: int) -> List[Recommendation]:
        """Get recommendations for a pain point"""
        with self.get_session() as session:
            return session.query(Recommendation).filter(
                Recommendation.pain_point_id == pain_point_id
            ).order_by(Recommendation.rank).all()
    
    # Visualization Management
    def create_visualization(self, run_id: int, viz_type: str, title: str = None,
                          description: str = None, mermaid_code: str = None,
                          file_path: str = None, extra_metadata: Dict = None) -> Optional[Visualization]:
        """Create a new visualization"""
        with self.get_session() as session:
            visualization = Visualization(
                run_id=run_id,
                type=viz_type,
                title=title,
                description=description,
                mermaid_code=mermaid_code,
                file_path=file_path,
                extra_metadata=extra_metadata
            )
            session.add(visualization)
            session.flush()
            session.refresh(visualization)
            return visualization
    
    def get_visualizations_by_run(self, run_id: int) -> List[Visualization]:
        """Get visualizations for an analysis run"""
        with self.get_session() as session:
            return session.query(Visualization).filter(
                Visualization.run_id == run_id
            ).order_by(Visualization.type).all()
    
    # Health and Monitoring
    def health_check(self) -> Dict[str, Any]:
        """Perform database health check"""
        try:
            with self.get_session() as session:
                # Test basic connectivity
                session.execute("SELECT 1")
                
                # Get basic stats
                user_count = session.query(User).count()
                repo_count = session.query(Repository).count()
                run_count = session.query(AnalysisRun).count()
                
                return {
                    "status": "healthy",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "statistics": {
                        "users": user_count,
                        "repositories": repo_count,
                        "analysis_runs": run_count
                    }
                }
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return {
                "status": "unhealthy",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "error": str(e)
            }

# Factory function for creating storage adapter
def create_storage_adapter(config_dict: Dict[str, Any]) -> StorageAdapter:
    """Create storage adapter from configuration dictionary"""
    db_config = DatabaseConfig(
        host=config_dict.get("host", "localhost"),
        port=config_dict.get("port", 5432),
        name=config_dict.get("name", "repo_analysis"),
        user=config_dict.get("user", "postgres"),
        password=config_dict.get("password", ""),
        pool_size=config_dict.get("pool_size", 10),
        max_overflow=config_dict.get("max_overflow", 20),
        echo=config_dict.get("echo", False)
    )
    
    return StorageAdapter(db_config)