# Services - Multi-Agent Tutoring System

from api.services.agents import (
    TutorAgent, AgentResponse, AgentRegistry,
    PersonalityTraits, PERSONALITY_PROFILES,
    PedagogicalStep, PedagogicalPlan
)
from api.services.orchestrator import (
    Orchestrator, TeachingState, Protocol,
    TopicClassifier, ConversationContext
)
from api.services.memory_palace import MemoryPalace, ContextAssembler
from api.services.llm import OllamaClient
from api.services.panel_discussion import (
    PanelDiscussionEngine, PanelStance, PanelStatement,
    PanelDiscussionResult
)
from api.services.peer_review import (
    PeerReviewSystem, ReviewResult, ReviewCriteria
)
from api.services.searxng import (
    SearXNGClient, AutonomousResearchAgent, VerifiedKnowledge,
    TutorResearchEngine
)
from api.services.student_modeling import (
    StudentModelingEngine, StudentCognitiveModel,
    CognitiveState, LearningStyle, KnowledgeComponent
)
from api.services.meta_cognition import (
    MetaCognitionEngine, ConversationQualityAnalyzer,
    SessionSummary, MetaCognitiveInsight, LearningPattern
)
from api.services.curriculum import CurriculumEngine
from api.services.personalization import PersonalizationEngine

__all__ = [
    # Core agents
    "TutorAgent", "AgentResponse", "AgentRegistry",
    "PersonalityTraits", "PERSONALITY_PROFILES",
    "PedagogicalStep", "PedagogicalPlan",
    
    # Orchestration
    "Orchestrator", "TeachingState", "Protocol",
    "TopicClassifier", "ConversationContext",
    
    # Memory
    "MemoryPalace", "ContextAssembler",
    
    # LLM
    "OllamaClient",
    
    # Panel discussions
    "PanelDiscussionEngine", "PanelStance", "PanelStatement",
    "PanelDiscussionResult",
    
    # Peer review
    "PeerReviewSystem", "ReviewResult", "ReviewCriteria",
    
    # Research
    "SearXNGClient", "AutonomousResearchAgent", "VerifiedKnowledge",
    "TutorResearchEngine",
    
    # Student modeling
    "StudentModelingEngine", "StudentCognitiveModel",
    "CognitiveState", "LearningStyle", "KnowledgeComponent",
    
    # Meta-cognition
    "MetaCognitionEngine", "ConversationQualityAnalyzer",
    "SessionSummary", "MetaCognitiveInsight", "LearningPattern",
    
    # Curriculum & personalization
    "CurriculumEngine", "PersonalizationEngine",
]
