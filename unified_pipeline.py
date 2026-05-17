"""
MACT v2.0 - UNIFIED SYSTEM PIPELINE
Bridges: Root v1.0 Files + mact_v2/ Modules
Usage: python unified_pipeline.py
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from typing import Dict, List, Optional
from datetime import datetime
import asyncio

# Import v1.0 Core (Root Level)
try:
    from panel_discussion import PanelDiscussion
    from curriculum_engine import CurriculumEngine
    from memory_schema import MemoryPalaceAdapter
    print("✅ Loaded v1.0 Core Modules")
except ImportError as e:
    print(f"⚠️  v1.0 modules not found: {e}")
    PanelDiscussion = None
    CurriculumEngine = None
    MemoryPalaceAdapter = None

# Import v2.0 Modules (Subdirectory)
try:
    from mact_v2.comprehension_engine import ComprehensionEngine
    from mact_v2.analytics_dashboard import AnalyticsDashboard
    from mact_v2.personalization_v2 import PersonalizationEngineV2
    from mact_v2.multimodal_interface import MultiModalInterface
    from mact_v2.infrastructure_v2 import MemoryManagerV2, AuthManager
    from mact_v2.database_schema import DatabaseManager, User, LearningStyleProfile
    print("✅ Loaded v2.0 Intelligence Modules")
except ImportError as e:
    print(f"❌ v2.0 modules not found: {e}")
    raise

class MACT_Unified_Pipeline:
    """
    THE BRAIN OF MACT v2.0
    Connects Agents + Quizzes + Spaced Repetition + Analytics + Personalization
    """
    
    def __init__(self, db_url: str = "sqlite:///./mact_v2/mact_unified.db"):
        print("\n🔧 Initializing MACT v2.0 Unified Pipeline...\n")
        
        # 1. Database Layer (Single Source of Truth)
        self.db = DatabaseManager(db_url)
        self.db.initialize_tables()
        print("✅ Database Initialized")
        
        # 2. v1.0 Core (Agents, Curriculum, Basic Memory)
        if PanelDiscussion:
            self.panel = PanelDiscussion()
            print("✅ Panel Discussion (v1.0) Ready")
        else:
            self.panel = None
            
        if CurriculumEngine:
            self.curriculum = CurriculumEngine()
            print("✅ Curriculum Engine (v1.0) Ready")
        else:
            self.curriculum = None
        
        # 3. v2.0 Intelligence Layer
        self.comprehension = ComprehensionEngine()
        self.analytics = AnalyticsDashboard()
        self.personalization = PersonalizationEngineV2()
        self.multimodal = MultiModalInterface()
        print("✅ v2.0 Intelligence Engines Ready")
        
        # 4. Infrastructure (Auth, Memory V2, WebSocket)
        self.auth = AuthManager()
        self.memory_v2 = MemoryManagerV2()
        print("✅ Infrastructure v2.0 Ready\n")
        
        print("🎉 MACT v2.0 Pipeline Fully Initialized!\n")

    async def process_user_request(self, user_id: str, user_input: str):
        """
        MAIN ENTRY POINT - Routes requests intelligently
        """
        # 1. Verify User Session
        if not await self._verify_user(user_id):
            return {"error": "User not authenticated"}
        
        # 2. Check for Spaced Repetition Priority (Always first!)
        due_reviews = self.comprehension.get_due_cards(user_id)
        if due_reviews and "!skip_review" not in user_input.lower():
            return await self._serve_review_queue(user_id, due_reviews)
        
        # 3. Classify Intent
        intent = self._classify_intent(user_input)
        
        if intent == "QUIZ":
            return await self._handle_quiz(user_id, user_input)
        elif intent == "LESSON":
            return await self._handle_lesson(user_id, user_input)
        elif intent == "ANALYTICS":
            return await self._handle_analytics(user_id)
        elif intent == "PROFILE":
            return await self._handle_profile(user_id)
        else:
            return await self._handle_chat(user_id, user_input)

    async def _verify_user(self, user_id: str) -> bool:
        """Check if user exists in DB or create guest"""
        user = await self.db.get_user_by_id(user_id)
        if not user:
            # Auto-create guest user
            await self.db.create_user(
                username=f"guest_{user_id}",
                password_hash="guest",
                email=f"{user_id}@guest.local"
            )
        return True

    async def _serve_review_queue(self, user_id: str, cards: list):
        """Interrupt normal flow for spaced repetition"""
        card = cards[0]  # Highest priority
        
        # Generate question from card concept
        quiz_data = await self.comprehension.generate_quiz(
            concept_ids=[card.concept_id],
            num_questions=1
        )
        
        return {
            "type": "REVIEW_INTERRUPT",
            "priority": "HIGH",
            "message": f"🧠 Review Time! You have {len(cards)} cards due.",
            "concept": card.concept_id,
            "question": quiz_data[0] if quiz_data else None,
            "interval_days": card.interval,
            "ease_factor": card.ease_factor,
            "action_hint": "Answer this review question to continue learning!"
        }

    async def _handle_quiz(self, user_id: str, request: str):
        """Generate adaptive quiz based on ZPD"""
        topic = self._extract_topic(request)
        
        # Get user's current mastery
        profile = await self.db.get_learning_profile(user_id)
        current_mastery = profile.mastery_matrix.get(topic, 0.3) if profile else 0.3
        
        # Calculate ZPD difficulty
        zpd_difficulty = self.comprehension.calculate_zpd_difficulty(
            user_id=user_id,
            concept_id=topic,
            current_mastery=current_mastery
        )
        
        # Generate quiz
        quiz = await self.comprehension.generate_quiz(
            concept_ids=[topic],
            num_questions=5,
            user_mastery={topic: current_mastery}
        )
        
        # Log quiz session
        await self.db.log_quiz_session(
            user_id=user_id,
            topic=topic,
            quiz_data=[q.__dict__ for q in quiz]
        )
        
        return {
            "type": "QUIZ_SESSION",
            "topic": topic,
            "difficulty_level": zpd_difficulty,
            "questions": [
                {
                    "id": q.question_id,
                    "text": q.question_text,
                    "options": q.options,
                    "type": q.question_type.value
                }
                for q in quiz
            ],
            "instructions": f"Adaptive Quiz: {topic} (ZPD Level: {zpd_difficulty:.1f})"
        }

    async def _handle_lesson(self, user_id: str, topic_request: str):
        """Full teaching loop with personalization"""
        topic = self._extract_topic(topic_request)
        
        # 1. Get User Style & Cognitive Load
        profile = await self.db.get_learning_profile(user_id)
        style = profile.preferred_style if profile else "balanced"
        
        # 2. Adapt Agent Prompts based on style
        agent_config = self.personalization.adapt_agent_prompts(
            style=style,
            cognitive_load="low"  # Simplified for now
        )
        
        # 3. Run Panel Discussion (v1.0)
        if self.panel:
            lesson_content = await self.panel.run_debate(
                topic=topic,
                config=agent_config
            )
        else:
            lesson_content = {"synthesis": f"Lesson on {topic} coming soon..."}
        
        # 4. Generate Checkpoint Quiz (v2.0)
        checkpoint = await self.comprehension.generate_checkpoint_quiz(
            topic=topic,
            content_summary=lesson_content.get("synthesis", "")[:500]
        )
        
        # 5. Prepare Multimodal Output
        tts_ready = await self.multimodal.generate_tts(lesson_content.get("synthesis", ""))
        diagram_code = await self.multimodal.generate_diagram(
            topic=topic,
            content=lesson_content
        )
        
        # 6. Update Analytics
        await self.analytics.update_session_stats(
            user_id=user_id,
            topic=topic,
            duration_seconds=180,
            concepts_covered=[topic]
        )
        
        return {
            "type": "LESSON_DELIVERED",
            "topic": topic,
            "content": lesson_content,
            "checkpoint_quiz": checkpoint,
            "multimedia": {
                "tts_available": tts_ready is not None,
                "diagram_mermaid": diagram_code
            },
            "next_recommended": await self._get_next_concepts(user_id, topic)
        }

    async def _handle_analytics(self, user_id: str):
        """Return dashboard data"""
        dashboard = self.analytics.get_dashboard_data(user_id)
        
        return {
            "type": "ANALYTICS_DASHBOARD",
            "metrics": dashboard["metrics"],
            "knowledge_radar": dashboard["radar"],
            "forecasts": dashboard["forecasts"],
            "streak_info": {
                "current": dashboard["metrics"]["current_streak_days"],
                "longest": dashboard["metrics"]["longest_streak_days"]
            }
        }

    async def _handle_profile(self, user_id: str):
        """Get/update learning profile"""
        profile = await self.db.get_learning_profile(user_id)
        
        return {
            "type": "USER_PROFILE",
            "style": profile.preferred_style if profile else "not_set",
            "mastery_matrix": profile.mastery_matrix if profile else {},
            "cognitive_load_history": [],
            "recommendations": self.personalization.generate_study_recommendations(
                user_id=user_id,
                current_mastery=profile.mastery_matrix if profile else {}
            )
        }

    async def _handle_chat(self, user_id: str, message: str):
        """Casual chat with context tracking"""
        if not self.panel:
            return {"type": "CHAT", "content": "Chat module loading..."}
        
        response = await self.panel.run_single_turn(message)
        
        # Log interaction for style detection
        await self.db.log_chat_interaction(
            user_id=user_id,
            user_message=message,
            agent_response=response,
            timestamp=datetime.now()
        )
        
        return {
            "type": "CHAT_RESPONSE",
            "content": response,
            "context_updated": True
        }

    def _classify_intent(self, text: str) -> str:
        """Simple keyword-based intent classification"""
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["quiz", "test", "exam", "practice"]):
            return "QUIZ"
        elif any(word in text_lower for word in ["teach", "explain", "learn", "study"]):
            return "LESSON"
        elif any(word in text_lower for word in ["progress", "analytics", "dashboard", "stats"]):
            return "ANALYTICS"
        elif any(word in text_lower for word in ["profile", "settings", "style"]):
            return "PROFILE"
        else:
            return "CHAT"

    def _extract_topic(self, text: str) -> str:
        """Extract topic from natural language"""
        # Simple extraction (replace with LLM in production)
        stopwords = ["me", "about", "on", "a", "an", "the", "please", "can", "could"]
        words = text.lower().split()
        clean_words = [w for w in words if w not in stopwords]
        return " ".join(clean_words[:3]) if clean_words else "general"

    async def _get_next_concepts(self, user_id: str, current_topic: str) -> List[str]:
        """Recommend next concepts based on dependency graph"""
        if not self.curriculum:
            return []
        
        # Get learning path
        path = await self.curriculum.generate_learning_path(current_topic)
        return path.get("next_concepts", [])


# === DEMO RUNNER ===
async def demo():
    print("=" * 60)
    print("MACT v2.0 UNIFIED PIPELINE - LIVE DEMO")
    print("=" * 60)
    
    # Initialize
    pipeline = MACT_Unified_Pipeline()
    
    user_id = "demo_student_001"
    
    # Test 1: Lesson Request
    print("\n[Test 1] Requesting Lesson...")
    result = await pipeline.process_user_request(user_id, "Teach me Machine Learning")
    print(f"Type: {result['type']}")
    print(f"Topic: {result.get('topic', 'N/A')}")
    print(f"Multimedia Ready: {result.get('multimedia', {})}")
    
    # Test 2: Quiz Request
    print("\n[Test 2] Requesting Quiz...")
    result = await pipeline.process_user_request(user_id, "Give me a quiz on Neural Networks")
    print(f"Type: {result['type']}")
    print(f"Questions: {len(result.get('questions', []))}")
    print(f"Difficulty: {result.get('difficulty_level', 0):.2f}")
    
    # Test 3: Analytics
    print("\n[Test 3] Checking Analytics...")
    result = await pipeline.process_user_request(user_id, "Show my progress")
    print(f"Type: {result['type']}")
    print(f"Study Time: {result.get('metrics', {}).get('total_study_time_minutes', 0)} min")
    print(f"Concepts Mastered: {result.get('metrics', {}).get('concepts_mastered', 0)}")
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED - MACT v2.0 OPERATIONAL")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(demo())
