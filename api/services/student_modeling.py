"""Advanced Student Modeling - Cognitive state tracking and adaptive personalization."""
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import math

from api.core.database import DatabaseManager
from api.services.memory_palace import MemoryPalace


class CognitiveState(Enum):
    """Student's current cognitive/emotional state."""
    FOCUSED = "FOCUSED"
    CONFUSED = "CONFUSED"
    FRUSTRATED = "FRUSTRATED"
    BORED = "BORED"
    CURIOUS = "CURIOUS"
    OVERWHELMED = "OVERWHELMED"


class LearningStyle(Enum):
    """Primary learning style preferences."""
    VISUAL = "VISUAL"
    AUDITORY = "AUDITORY"
    KINESTHETIC = "KINESTHETIC"
    READ_WRITE = "READ_WRITE"
    BALANCED = "BALANCED"


@dataclass
class KnowledgeComponent:
    """Represents a specific skill or concept the student is learning."""
    name: str
    subject: str
    mastery_level: float = 0.0  # 0-1 scale
    last_practiced: str = ""
    practice_count: int = 0
    success_rate: float = 0.0
    difficulty_rating: float = 0.5  # How hard is this for THIS student
    decay_rate: float = 0.01  # How fast knowledge decays without practice
    
    def update_mastery(self, performance: float, time_delta_days: float = 0):
        """Update mastery using Ebbinghaus forgetting curve + performance."""
        if not self.last_practiced:
            self.mastery_level = performance * 0.3
        else:
            # Apply decay
            if time_delta_days > 0:
                decay_factor = math.exp(-self.decay_rate * time_delta_days)
                self.mastery_level *= decay_factor
            
            # Blend with new performance (weighted average)
            weight = min(0.5, 0.1 * self.practice_count)  # More practice = more stable
            self.mastery_level = (1 - weight) * self.mastery_level + weight * performance
        
        self.mastery_level = max(0.0, min(1.0, self.mastery_level))
        self.practice_count += 1
        self.last_practiced = datetime.utcnow().isoformat()
        
        # Update success rate (running average)
        self.success_rate = ((self.success_rate * (self.practice_count - 1)) + performance) / self.practice_count


@dataclass
class StudentCognitiveModel:
    """Complete cognitive model of a student."""
    student_id: str
    name: str
    hf_year: int = 1
    
    # Learning preferences
    learning_style: LearningStyle = LearningStyle.BALANCED
    preferred_modality: str = "balanced"
    preferred_depth: str = "balanced"
    pace: float = 1.0
    
    # Current state
    cognitive_state: CognitiveState = CognitiveState.FOCUSED
    attention_level: float = 0.8  # 0-1
    motivation_level: float = 0.7  # 0-1
    frustration_level: float = 0.2  # 0-1
    
    # Knowledge components by subject
    knowledge_components: Dict[str, List[KnowledgeComponent]] = field(default_factory=dict)
    
    # Session metrics
    session_start: str = ""
    total_problems_attempted: int = 0
    total_problems_solved: int = 0
    avg_response_time_seconds: float = 30.0
    help_requests: int = 0
    
    # Historical patterns
    best_time_of_day: str = "afternoon"
    typical_session_length_minutes: int = 45
    burnout_risk: float = 0.1  # 0-1
    
    def get_mastery(self, subject: str, component_name: str) -> Optional[float]:
        """Get mastery level for a specific knowledge component."""
        if subject not in self.knowledge_components:
            return None
        for kc in self.knowledge_components[subject]:
            if kc.name == component_name:
                return kc.mastery_level
        return None
    
    def update_knowledge_component(self, subject: str, component_name: str,
                                   performance: float) -> KnowledgeComponent:
        """Update or create a knowledge component."""
        if subject not in self.knowledge_components:
            self.knowledge_components[subject] = []
        
        # Find existing or create new
        for kc in self.knowledge_components[subject]:
            if kc.name == component_name:
                # Calculate time delta
                if kc.last_practiced:
                    last_time = datetime.fromisoformat(kc.last_practiced)
                    time_delta = (datetime.utcnow() - last_time).total_seconds() / 86400
                else:
                    time_delta = 0
                
                kc.update_mastery(performance, time_delta)
                return kc
        
        # Create new
        new_kc = KnowledgeComponent(
            name=component_name,
            subject=subject,
            mastery_level=performance * 0.3
        )
        new_kc.update_mastery(performance)
        self.knowledge_components[subject].append(new_kc)
        return new_kc
    
    def detect_cognitive_state(self, recent_interactions: List[Dict]) -> CognitiveState:
        """Detect current cognitive state from interaction patterns."""
        if not recent_interactions:
            return self.cognitive_state
        
        # Analyze last 5 interactions
        recent = recent_interactions[-5:]
        
        confusion_signals = 0
        frustration_signals = 0
        engagement_signals = 0
        rapid_guessing = 0
        
        for interaction in recent:
            response = (interaction.get("student_message", "") or "").lower()
            response_time = interaction.get("response_time_seconds", 30)
            
            # Confusion detection
            if any(word in response for word in ["forstår ikke", "huh", "hvad", "forvirret"]):
                confusion_signals += 1
            
            # Frustration detection
            if any(word in response for word in ["svært", "irriterende", "giver op", "for meget"]):
                frustration_signals += 1
            
            # Engagement detection
            if any(word in response for word in ["interessant", "spændende", "mere", "hvorfor"]):
                engagement_signals += 1
            
            # Rapid guessing (possible disengagement)
            if response_time < 5:
                rapid_guessing += 1
        
        # Determine state
        if frustration_signals >= 2 or (confusion_signals >= 3 and frustration_signals >= 1):
            return CognitiveState.FRUSTRATED
        elif confusion_signals >= 2:
            return CognitiveState.CONFUSED
        elif rapid_guessing >= 3:
            return CognitiveState.BORED
        elif engagement_signals >= 2 and confusion_signals == 0:
            return CognitiveState.CURIOUS
        elif confusion_signals >= 4:
            return CognitiveState.OVERWHELMED
        else:
            return CognitiveState.FOCUSED
    
    def update_attention_motivation(self, interaction_type: str, 
                                    response_time: float,
                                    correctness: Optional[float] = None):
        """Update attention and motivation based on interaction."""
        # Attention decays over time, boosted by engagement
        if interaction_type == "question_asked":
            self.attention_level = min(1.0, self.attention_level + 0.05)
        elif interaction_type == "off_topic":
            self.attention_level = max(0.3, self.attention_level - 0.1)
        else:
            self.attention_level = max(0.4, self.attention_level - 0.01)
        
        # Motivation updates based on success/failure
        if correctness is not None:
            if correctness > 0.7:
                self.motivation_level = min(1.0, self.motivation_level + 0.08)
                self.frustration_level = max(0.0, self.frustration_level - 0.05)
            elif correctness < 0.3:
                self.motivation_level = max(0.3, self.motivation_level - 0.05)
                self.frustration_level = min(1.0, self.frustration_level + 0.1)
        
        # Response time affects attention
        if response_time > 120:
            self.attention_level = max(0.3, self.attention_level - 0.05)
        elif response_time < 10 and interaction_type != "quick_answer":
            self.attention_level = max(0.4, self.attention_level - 0.03)
    
    def should_introduce_challenge(self) -> bool:
        """Decide if student is ready for harder material."""
        return (
            self.cognitive_state in [CognitiveState.FOCUSED, CognitiveState.CURIOUS] and
            self.frustration_level < 0.3 and
            self.motivation_level > 0.6 and
            self.attention_level > 0.6
        )
    
    def needs_support(self) -> bool:
        """Check if student needs additional support/scaffolding."""
        return (
            self.cognitive_state in [CognitiveState.CONFUSED, CognitiveState.FRUSTRATED, CognitiveState.OVERWHELMED] or
            self.frustration_level > 0.5 or
            self.motivation_level < 0.4 or
            self.attention_level < 0.4
        )
    
    def optimal_break_time(self) -> bool:
        """Suggest if student should take a break."""
        return (
            self.frustration_level > 0.6 or
            self.attention_level < 0.3 or
            self.burnout_risk > 0.7
        )


class StudentModelingEngine:
    """
    Advanced student modeling engine with:
    - Real-time cognitive state detection
    - Knowledge component tracking with spaced repetition
    - Adaptive difficulty adjustment
    - Burnout prediction
    - Optimal challenge point calculation
    """
    
    def __init__(self, student_id: str):
        self.student_id = student_id
        self.db = DatabaseManager()
        self.memory = MemoryPalace()
        self.model: Optional[StudentCognitiveModel] = None
    
    async def load_or_create_model(self) -> StudentCognitiveModel:
        """Load existing model or create new one."""
        student_data = self.db.get_student(self.student_id)
        
        if student_data:
            self.model = StudentCognitiveModel(
                student_id=self.student_id,
                name=student_data.get("name", "Elev"),
                hf_year=student_data.get("hf_year", 1),
                preferred_modality=student_data.get("preferred_modality", "balanced"),
                preferred_depth=student_data.get("preferred_depth", "balanced"),
                pace=student_data.get("pace", 1.0),
            )
            
            # Load knowledge components from database
            await self._load_knowledge_components()
        else:
            self.model = StudentCognitiveModel(
                student_id=self.student_id,
                name="Elev"
            )
        
        return self.model
    
    async def _load_knowledge_components(self):
        """Load knowledge components from database."""
        # This would query the mastery table and populate knowledge_components
        # For now, initialize empty
        pass
    
    def update_from_interaction(self, student_message: str, agent_response: str,
                                topic: str, subtopic: Optional[str] = None,
                                response_time: float = 30.0,
                                correctness: Optional[float] = None):
        """Update student model based on interaction."""
        if not self.model:
            return
        
        # Update session metrics
        self.model.total_problems_attempted += 1
        if correctness and correctness > 0.7:
            self.model.total_problems_solved += 1
        
        # Update attention/motivation
        interaction_type = "normal"
        if "?" in student_message:
            interaction_type = "question_asked"
        
        self.model.update_attention_motivation(
            interaction_type=interaction_type,
            response_time=response_time,
            correctness=correctness
        )
        
        # Update knowledge component
        if subtopic:
            self.model.update_knowledge_component(
                subject=topic,
                component_name=subtopic,
                performance=correctness or 0.5
            )
    
    def detect_state_from_conversation(self, recent_turns: List[Dict]) -> CognitiveState:
        """Detect and update cognitive state from conversation history."""
        if not self.model:
            return CognitiveState.FOCUSED
        
        new_state = self.model.detect_cognitive_state(recent_turns)
        old_state = self.model.cognitive_state
        self.model.cognitive_state = new_state
        
        # Log state transition if changed
        if new_state != old_state:
            self._log_state_transition(old_state, new_state)
        
        return new_state
    
    def _log_state_transition(self, old_state: CognitiveState, new_state: CognitiveState):
        """Log cognitive state transitions for analysis."""
        # Store in memory palace for later analysis
        self.memory.store(
            content=f"State change: {old_state.value} → {new_state.value}",
            wing="wing_fælles",
            room="room_student_modeling",
            student_id=self.student_id,
            event_type="state_transition",
            timestamp=datetime.utcnow().isoformat()
        )
    
    def get_optimal_next_step(self, topic: str, current_difficulty: float) -> Dict:
        """
        Determine optimal next learning step using Vygotsky's Zone of Proximal Development.
        
        Returns recommendation for:
        - Difficulty adjustment
        - Teaching method
        - Support level needed
        """
        if not self.model:
            return {"difficulty": current_difficulty, "method": "standard", "support": "normal"}
        
        # Get average mastery in this subject
        subject_kcs = self.model.knowledge_components.get(topic, [])
        if subject_kcs:
            avg_mastery = sum(kc.mastery_level for kc in subject_kcs) / len(subject_kcs)
        else:
            avg_mastery = 0.3  # Assume novice
        
        # Calculate optimal challenge
        if self.model.should_introduce_challenge():
            # Student ready for harder material
            target_difficulty = min(1.0, current_difficulty + 0.15)
            method = "discovery"  # Let them explore
            support = "minimal"
        elif self.model.needs_support():
            # Student struggling
            target_difficulty = max(0.2, current_difficulty - 0.2)
            method = "scaffolded"
            support = "high"
        else:
            # Maintain current level
            target_difficulty = current_difficulty
            method = "guided"
            support = "moderate"
        
        # Adjust for cognitive state
        if self.model.cognitive_state == CognitiveState.BORED:
            method = "gamified"
            target_difficulty = min(1.0, target_difficulty + 0.1)
        elif self.model.cognitive_state == CognitiveState.OVERWHELMED:
            support = "very_high"
            target_difficulty = max(0.1, target_difficulty - 0.3)
        
        return {
            "difficulty": target_difficulty,
            "method": method,
            "support": support,
            "avg_mastery": avg_mastery,
            "recommended_action": self._get_action_recommendation(avg_mastery, target_difficulty)
        }
    
    def _get_action_recommendation(self, mastery: float, difficulty: float) -> str:
        """Get specific action recommendation."""
        if mastery < 0.3:
            return "focus_on_basics"
        elif mastery < 0.5:
            return "guided_practice"
        elif mastery < 0.7:
            return "independent_practice"
        elif mastery < 0.9:
            return "challenge_problems"
        else:
            return "explore_advanced_topics"
    
    def predict_burnout_risk(self) -> float:
        """Predict burnout risk based on recent patterns."""
        if not self.model:
            return 0.0
        
        risk = 0.0
        
        # High frustration over time
        risk += self.model.frustration_level * 0.3
        
        # Low motivation sustained
        risk += (1.0 - self.model.motivation_level) * 0.25
        
        # Attention declining
        if self.model.attention_level < 0.4:
            risk += 0.2
        
        # Too many problems without breaks
        if self.model.total_problems_attempted > 20:
            risk += 0.15
        
        # Time of day factor (if known)
        if self.model.best_time_of_day != self._get_current_time_period():
            risk += 0.1
        
        self.model.burnout_risk = min(1.0, risk)
        return risk
    
    def _get_current_time_period(self) -> str:
        """Get current time period."""
        hour = datetime.now().hour
        if hour < 12:
            return "morning"
        elif hour < 17:
            return "afternoon"
        else:
            return "evening"
    
    def generate_personalized_feedback(self) -> str:
        """Generate personalized feedback for student based on model."""
        if not self.model:
            return ""
        
        feedback_parts = []
        
        # Progress summary
        if self.model.total_problems_attempted > 0:
            success_rate = self.model.total_problems_solved / self.model.total_problems_attempted
            feedback_parts.append(f"Du har løst {self.model.total_problems_solved} ud af {self.model.total_problems_attempted} opgaver.")
        
        # State-aware encouragement
        if self.model.cognitive_state == CognitiveState.FRUSTRATED:
            feedback_parts.append("Det ser ud til at du kæmper lidt - det er helt normalt! Skal vi tage en pause eller prøve en anden tilgang?")
        elif self.model.cognitive_state == CognitiveState.CURIOUS:
            feedback_parts.append("Fedt at se din nysgerrighed! Vil du udforske noget dybere?")
        elif self.model.cognitive_state == CognitiveState.BORED:
            feedback_parts.append("Jeg mærker at energien er lav. Skal vi prøve noget mere udfordrende eller anderledes?")
        
        # Mastery-based suggestion
        for subject, kcs in self.model.knowledge_components.items():
            strong = [kc.name for kc in kcs if kc.mastery_level > 0.7]
            weak = [kc.name for kc in kcs if kc.mastery_level < 0.4]
            
            if strong:
                feedback_parts.append(f"Du er stærk i: {', '.join(strong[:2])}")
            if weak and len(weak) <= 2:
                feedback_parts.append(f"Øv dig gerne på: {', '.join(weak)}")
        
        return " ".join(feedback_parts)
