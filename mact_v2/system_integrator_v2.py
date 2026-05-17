"""
MACT v2.0 - Unified System Integrator
Connects all v2.0 components into a single cohesive system
"""

from comprehension_engine import ComprehensionEngine
from analytics_dashboard import AnalyticsDashboard
from personalization_v2 import PersonalizationEngineV2
from multimodal_interface import MultiModalInterface
from infrastructure_v2 import MemoryManagerV2, AuthManager, WebSocketManager
from typing import Dict, List, Optional
import json


class MACTv2System:
    """
    Multi-Agent Cognitive Tutor v2.0
    Complete integrated system with all advanced features
    """
    
    def __init__(self, memory_backend=None):
        # Core engines
        self.comprehension = ComprehensionEngine(memory_backend)
        self.analytics = AnalyticsDashboard(memory_backend)
        self.personalization = PersonalizationEngineV2(memory_backend)
        self.multimodal = MultiModalInterface()
        
        # Infrastructure
        self.memory_mgr = MemoryManagerV2(memory_backend)
        self.auth = AuthManager()
        self.websocket_mgr = WebSocketManager()
        
        # State tracking
        self.active_users: Dict = {}
        
    def register_user(self, username: str, password: str, email: str) -> Dict:
        """Register new user and initialize their learning profile"""
        result = self.auth.register_user(username, password, email)
        
        # Initialize memory schema
        user_id = result["user_id"]
        self.memory_mgr.create_user_schema(user_id)
        
        # Initialize active user state
        self.active_users[user_id] = {
            "username": username,
            "style_preference": None,
            "current_load": None,
            "motivation_state": None,
            "session_count": 0
        }
        
        return result
    
    def login_user(self, username: str, password: str) -> Dict:
        """Authenticate user and load their profile"""
        auth_result = self.auth.login(username, password)
        user_id = auth_result["user_id"]
        
        # Load or initialize user state
        if user_id not in self.active_users:
            self.active_users[user_id] = {
                "username": username,
                "style_preference": None,
                "current_load": None,
                "motivation_state": None,
                "session_count": 0
            }
        
        return auth_result
    
    def start_learning_session(
        self, 
        user_id: str, 
        topic: str,
        interaction_history: List[Dict] = None
    ) -> Dict:
        """
        Start a personalized learning session
        Returns comprehensive session configuration
        """
        if user_id not in self.active_users:
            raise ValueError("User not logged in")
        
        user_state = self.active_users[user_id]
        
        # Update style preference from history
        if interaction_history:
            style = self.personalization.detect_learning_style(
                user_id, interaction_history
            )
            user_state["style_preference"] = style
        
        # Get current mastery for topic
        mastery = self.memory_mgr.user_schemas.get(user_id, {}).mastery_matrix.get(topic, 0.0)
        
        # Generate adaptive quiz to assess current level
        quiz = self.comprehension.generate_quiz(
            concept_ids=[topic],
            num_questions=3,
            user_mastery={topic: mastery}
        )
        
        # Prepare multi-modal output
        sample_content = f"Starting lesson on {topic}..."
        multimodal_output = self.multimodal.create_multimodal_output(
            primary_content=sample_content,
            include_tts=True,
            include_diagrams=True,
            concept_relationships=[
                {"target": f"{topic} Basics", "type": "subtopic"},
                {"target": f"{topic} Applications", "type": "example"}
            ]
        )
        
        # Get dashboard data for progress view
        dashboard_data = self.analytics.get_dashboard_data(user_id)
        
        return {
            "session_id": f"session_{user_id}_{topic}",
            "topic": topic,
            "initial_mastery": mastery,
            "learning_style": user_state["style_preference"].primary_style.value if user_state["style_preference"] else "unknown",
            "quiz": [q.__dict__ for q in quiz],
            "multimodal_ready": multimodal_output.tts_ready,
            "diagram_available": len(multimodal_output.diagrams) > 0,
            "dashboard_summary": {
                "total_study_time": dashboard_data["metrics"]["total_study_time_minutes"],
                "concepts_mastered": dashboard_data["metrics"]["concepts_mastered"],
                "current_streak": dashboard_data["metrics"]["current_streak_days"]
            }
        }
    
    def submit_quiz_answers(
        self,
        user_id: str,
        topic: str,
        quiz: List,
        answers: List[str],
        time_taken: int,
        self_confidence: float
    ) -> Dict:
        """
        Process quiz submission with full v2.0 pipeline
        """
        # Convert dict quizzes back to Question objects if needed
        from comprehension_engine import Question
        quiz_objects = []
        for q in quiz:
            if isinstance(q, dict):
                quiz_objects.append(Question(**q))
            else:
                quiz_objects.append(q)
        
        # Evaluate quiz
        result = self.comprehension.evaluate_quiz(quiz_objects, answers, time_taken)
        
        # Update spaced repetition for each concept
        for i, q in enumerate(quiz_objects):
            quality = 5 if answers[i] == q.correct_answer else 2
            self.comprehension.update_spaced_repetition(q.concept_id, quality)
        
        # Update mastery in memory
        self.memory_mgr.update_mastery(user_id, topic, result.score)
        
        # Log metacognition
        self.memory_mgr.log_metacognition(
            user_id=user_id,
            concept_id=topic,
            self_confidence=self_confidence,
            actual_score=result.score,
            notes=f"Quiz completed in {time_taken}s"
        )
        
        # Update analytics
        from analytics_dashboard import StudySession
        session = StudySession(
            session_id=f"quiz_{topic}_{result.quiz_id}",
            user_id=user_id,
            start_time=result.timestamp,
            end_time=result.timestamp,
            concepts_studied=[topic],
            quiz_scores=[result.score],
            time_spent_minutes=time_taken // 60,
            streak_count=0
        )
        self.analytics.log_session(session)
        
        # Calculate difficulty adjustment
        next_difficulty = min(1.0, max(0.1, 0.5 + result.difficulty_adjustment))
        
        # Get updated mastery
        new_mastery = self.memory_mgr.user_schemas.get(user_id, {}).mastery_matrix.get(topic, 0.0)
        
        return {
            "score": result.score,
            "mastery_updated": new_mastery,
            "calibration_error": abs(self_confidence - result.score),
            "next_difficulty": next_difficulty,
            "spaced_repetition": {
                concept: card.next_review 
                for concept, card in self.comprehension.spaced_cards.items()
            },
            "recommendation": self._generate_recommendation(result.score, new_mastery)
        }
    
    def _generate_recommendation(self, score: float, mastery: float) -> str:
        """Generate personalized recommendation based on performance"""
        if score >= 0.9:
            return "Excellent! Ready for advanced topics. Consider exploring related concepts."
        elif score >= 0.7:
            return "Good understanding. Review weak areas and try practice problems."
        elif score >= 0.5:
            return "Moderate grasp. Revisit core concepts with different explanations."
        else:
            return "Foundational review needed. Start with basics and build up gradually."
    
    def get_personalized_prompt(
        self,
        user_id: str,
        concept: str
    ) -> str:
        """
        Generate fully personalized teaching prompt using all v2.0 features
        """
        if user_id not in self.active_users:
            raise ValueError("User not logged in")
        
        # Get user state
        user_state = self.active_users[user_id]
        schema = self.memory_mgr.user_schemas.get(user_id)
        
        # Get or infer style
        if not user_state["style_preference"]:
            style = self.personalization.detect_learning_style(user_id, [])
            user_state["style_preference"] = style
        else:
            style = user_state["style_preference"]
        
        # Monitor cognitive load (simplified)
        user_signals = {
            "avg_response_time_seconds": 30,
            "recent_error_rate": 0.3,
            "confusion_count": 1,
            "total_interactions": 10,
            "repetition_requests": 0,
            "help_requests": 0
        }
        cognitive_load = self.personalization.monitor_cognitive_load(user_signals)
        user_state["current_load"] = cognitive_load
        
        # Adapt motivation
        mastery_matrix = schema.mastery_matrix if schema else {}
        recent_scores = list(mastery_matrix.values())[-5:] if mastery_matrix else [0.5]
        
        motivation = self.personalization.adapt_motivation(
            user_id=user_id,
            streak_days=self.analytics.calculate_metrics(user_id).current_streak_days,
            recent_scores=recent_scores,
            session_frequency=3.0
        )
        user_state["motivation_state"] = motivation
        
        # Get current mastery
        current_mastery = mastery_matrix.get(concept, 0.3)
        
        # Generate personalized prompt
        prompt = self.personalization.generate_personalized_prompt(
            concept=concept,
            user_style=style,
            cognitive_load=cognitive_load,
            motivation=motivation,
            mastery_level=current_mastery
        )
        
        return prompt
    
    def get_due_reviews(self, user_id: str) -> List[Dict]:
        """Get spaced repetition cards due for review"""
        due_cards = self.comprehension.get_due_cards(user_id)
        
        return [
            {
                "concept": card.concept_id,
                "interval": card.interval,
                "ease_factor": card.ease_factor,
                "repetitions": card.repetitions,
                "next_review": card.next_review
            }
            for card in due_cards
        ]
    
    def export_user_progress(self, user_id: str) -> Dict:
        """Export complete user progress report"""
        dashboard = self.analytics.get_dashboard_data(user_id)
        calibration = self.memory_mgr.get_calibration_score(user_id)
        temporal = self.memory_mgr.analyze_temporal_patterns(user_id)
        
        return {
            "user_id": user_id,
            "generated_at": dashboard["generated_at"],
            "metrics": dashboard["metrics"],
            "knowledge_radar": dashboard["radar"],
            "forecasts": dashboard["forecasts"],
            "metacognition": {
                "calibration_score": calibration,
                "temporal_insights": temporal
            },
            "spaced_repetition": {
                concept: {
                    "mastery": self.comprehension.get_concept_mastery(concept),
                    "next_review": card.next_review
                }
                for concept, card in self.comprehension.spaced_cards.items()
            }
        }


# Example usage
if __name__ == "__main__":
    print("=== MACT v2.0 SYSTEM INTEGRATOR ===\n")
    
    # Initialize system
    system = MACTv2System()
    
    # Register and login user
    print("1. User Registration:")
    reg = system.register_user("bob", "password123", "bob@example.com")
    print(f"   Registered: {reg['user_id']}")
    
    print("\n2. User Login:")
    auth = system.login_user("bob", "password123")
    user_id = auth["user_id"]
    print(f"   Logged in: {user_id}")
    
    # Start learning session
    print("\n3. Start Learning Session:")
    session = system.start_learning_session(
        user_id=user_id,
        topic="machine_learning",
        interaction_history=[
            {"content_type": "analogy", "engagement_score": 0.8, "comprehension_score": 0.75}
        ]
    )
    print(f"   Topic: {session['topic']}")
    print(f"   Learning Style: {session['learning_style']}")
    print(f"   Initial Mastery: {session['initial_mastery']:.2%}")
    print(f"   Quiz Generated: {len(session['quiz'])} questions")
    
    # Simulate quiz submission
    print("\n4. Submit Quiz:")
    quiz = session['quiz']
    answers = [q['correct_answer'] for q in quiz]  # Perfect score
    
    result = system.submit_quiz_answers(
        user_id=user_id,
        topic="machine_learning",
        quiz=quiz,
        answers=answers,
        time_taken=180,
        self_confidence=0.85
    )
    
    print(f"   Score: {result['score']:.2%}")
    print(f"   Updated Mastery: {result['mastery_updated']:.2%}")
    print(f"   Calibration Error: {result['calibration_error']:.2%}")
    print(f"   Recommendation: {result['recommendation']}")
    
    # Get personalized prompt
    print("\n5. Generate Personalized Teaching Prompt:")
    prompt = system.get_personalized_prompt(user_id, "machine_learning")
    print(f"   Prompt Preview: {prompt[:200]}...")
    
    # Export progress
    print("\n6. Export User Progress:")
    progress = system.export_user_progress(user_id)
    print(f"   Concepts Mastered: {progress['metrics']['concepts_mastered']}")
    print(f"   Total Study Time: {progress['metrics']['total_study_time_minutes']} min")
    print(f"   Calibration Score: {progress['metacognition']['calibration_score']:.2%}")
    
    print("\n✓ MACT v2.0 System Fully Operational!")
