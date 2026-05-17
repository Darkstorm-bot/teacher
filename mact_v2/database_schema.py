"""
MACT v2.0 Database Schema
Connects Phase 1/2 Memory with Phase 3 Analytics & Quizzes
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    quiz_results = relationship("QuizResult", back_populates="user")
    sr_cards = relationship("SpacedRepetitionCard", back_populates="user")
    style_profile = relationship("LearningStyleProfile", back_populates="user", uselist=False)
    sessions = relationship("LearningSession", back_populates="user")

class LearningStyleProfile(Base):
    __tablename__ = "learning_style_profiles"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="style_profile")
    
    # Scores 0.0 - 1.0
    visual_pref = Column(Float, default=0.5)
    logical_pref = Column(Float, default=0.5)
    analogy_pref = Column(Float, default=0.5)
    code_pref = Column(Float, default=0.5)
    
    # Dynamic metrics
    cognitive_load_threshold = Column(Float, default=0.7)
    last_updated = Column(DateTime, default=datetime.utcnow)

class ConceptNode(Base):
    """Extends Phase 2 Knowledge Graph with DB persistence"""
    __tablename__ = "concept_nodes"
    id = Column(Integer, primary_key=True)
    name = Column(String, index=True)
    subject = Column(String)
    difficulty = Column(Float)
    bloom_level = Column(Integer) # 1-6
    
    # Graph structure
    prerequisites = Column(JSON) # List of concept IDs
    dependencies = Column(JSON)  # List of concept IDs depending on this

class SpacedRepetitionCard(Base):
    """SM-2 Algorithm Data"""
    __tablename__ = "spaced_repetition_cards"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="sr_cards")
    
    concept_id = Column(Integer, ForeignKey("concept_nodes.id"))
    question = Column(String)
    answer = Column(String)
    
    # SM-2 Metrics
    interval = Column(Integer, default=0) # Days
    repetition = Column(Integer, default=0)
    efactor = Column(Float, default=2.5) # Ease Factor
    next_review = Column(DateTime)
    
    last_reviewed = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow)

class QuizResult(Base):
    __tablename__ = "quiz_results"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="quiz_results")
    
    concept_id = Column(Integer, ForeignKey("concept_nodes.id"))
    score = Column(Float) # 0.0 - 1.0
    time_taken = Column(Float) # Seconds
    difficulty_attempted = Column(Float)
    
    answers_detail = Column(JSON) # {question_id: {"correct": bool, "time": float}}
    created_at = Column(DateTime, default=datetime.utcnow)

class LearningSession(Base):
    """Tracks temporal patterns for Analytics"""
    __tablename__ = "learning_sessions"
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    user = relationship("User", back_populates="sessions")
    
    start_time = Column(DateTime)
    end_time = Column(DateTime)
    duration_minutes = Column(Integer)
    
    concepts_covered = Column(JSON) # List of concept IDs
    avg_cognitive_load = Column(Float)
    motivation_score = Column(Float)
    
    completed = Column(Boolean, default=False)

# Database Manager
class DatabaseManager:
    def __init__(self, db_url="sqlite:///mact_v2.db"):
        self.engine = create_engine(db_url, echo=False)
        Base.metadata.create_all(self.engine)
        SessionLocal = sessionmaker(bind=self.engine)
        self.session = SessionLocal()

    def get_session(self):
        return self.session

# Initialize DB
db_manager = DatabaseManager()
