"""
MACT v2.0 - Database Schema
Defines tables for Spaced Repetition, Quizzes, Analytics, and User Profiles.
"""
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    quizzes = relationship("QuizResult", back_populates="user")
    sr_cards = relationship("SpacedRepetitionCard", back_populates="user")
    style_profile = relationship("LearningStyleProfile", back_populates="user", uselist=False)
    sessions = relationship("CognitiveLoadSession", back_populates="user")

class LearningStyleProfile(Base):
    __tablename__ = "learning_style_profiles"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True)
    
    # Scores 0.0 - 1.0
    visual_pref = Column(Float, default=0.5)
    logical_pref = Column(Float, default=0.5)
    analogy_pref = Column(Float, default=0.5)
    code_pref = Column(Float, default=0.5)
    
    # Dynamic metrics
    avg_cognitive_load = Column(Float, default=0.0)
    motivation_score = Column(Float, default=0.5)
    
    user = relationship("User", back_populates="style_profile")

class QuizResult(Base):
    __tablename__ = "quiz_results"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    concept_id = Column(String, index=True)  # Matches Knowledge Graph Node ID
    question_type = Column(String)  # MCQ, TrueFalse, FillBlank
    difficulty = Column(Float)
    is_correct = Column(Boolean)
    response_time_sec = Column(Float)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="quizzes")

class SpacedRepetitionCard(Base):
    __tablename__ = "spaced_repetition_cards"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    concept_id = Column(String, index=True)
    
    # SM-2 Algorithm Data
    interval = Column(Integer, default=0)  # Days
    repetition = Column(Integer, default=0)
    efactor = Column(Float, default=2.5)  # Ease Factor
    next_review_date = Column(DateTime, default=datetime.utcnow)
    last_review_date = Column(DateTime, nullable=True)
    
    # Content
    question_text = Column(String)
    answer_text = Column(String)
    
    user = relationship("User", back_populates="sr_cards")

class CognitiveLoadSession(Base):
    __tablename__ = "cognitive_load_sessions"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime, nullable=True)
    
    # Metrics
    avg_load_score = Column(Float, default=0.0)  # 0.0 (Low) to 1.0 (Overload)
    confusion_events = Column(Integer, default=0)
    simplification_triggers = Column(Integer, default=0)
    
    user = relationship("User", back_populates="sessions")

class UserMetacognition(Base):
    __tablename__ = "user_metacognition"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    concept_id = Column(String)
    
    # Self-reported confidence vs actual performance
    self_confidence = Column(Float)
    actual_accuracy = Column(Float)
    calibration_error = Column(Float)  # Abs(confidence - accuracy)
    
    timestamp = Column(DateTime, default=datetime.utcnow)

# Database Setup Helper
DATABASE_URL = "sqlite:///./mact_v2.db"

def get_engine():
    return create_engine(DATABASE_URL, connect_args={"check_same_thread": False})

def init_db():
    engine = get_engine()
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)

if __name__ == "__main__":
    print("Initializing MACT v2.0 Database...")
    init_db()
    print("Database tables created successfully at mact_v2.db")
