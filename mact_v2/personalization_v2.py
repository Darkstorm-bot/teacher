"""
MACT v2.0 - Personalization Engine v2
Features: Dynamic Style Detection, Cognitive Load Monitoring, Motivation Adapter
"""

import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import random


class LearningStyle(Enum):
    VISUAL = "visual"
    ANALOGY = "analogy"
    LOGICAL = "logical"
    CODE = "code"
    KINESTHETIC = "kinesthetic"


class CognitiveLoadLevel(Enum):
    LOW = "low"
    OPTIMAL = "optimal"
    HIGH = "high"
    OVERLOAD = "overload"


class MotivationLevel(Enum):
    LOW = "low"
    MODERATE = "moderate"
    HIGH = "high"


@dataclass
class StylePreference:
    primary_style: LearningStyle
    secondary_style: LearningStyle
    confidence: float  # 0.0-1.0
    samples_count: int
    last_updated: str


@dataclass
class CognitiveLoadState:
    current_load: CognitiveLoadLevel
    indicators: Dict[str, float]  # e.g., {"confusion": 0.7, "frustration": 0.3}
    recommended_action: str
    timestamp: str


@dataclass
class MotivationState:
    level: MotivationLevel
    streak_days: int
    recent_performance: float  # Last 5 quiz scores avg
    engagement_score: float  # 0.0-1.0
    recommended_tone: str
    timestamp: str


@dataclass
class ContentRanking:
    explanation_type: str
    effectiveness_score: float  # Based on past user performance
    style_match: float
    difficulty_appropriateness: float
    final_rank: float


class PersonalizationEngineV2:
    def __init__(self, memory_client=None):
        self.memory = memory_client
        self.style_history: Dict[str, List[Tuple[str, float]]] = {}  # concept_id -> [(style, score)]
        self.current_load: Optional[CognitiveLoadState] = None
        self.motivation_cache: Optional[MotivationState] = None
        
    def detect_learning_style(
        self, 
        user_id: str, 
        interaction_history: List[Dict]
    ) -> StylePreference:
        """
        Detect preferred learning style from interaction history
        """
        style_scores = {
            LearningStyle.VISUAL: 0.0,
            LearningStyle.ANALOGY: 0.0,
            LearningStyle.LOGICAL: 0.0,
            LearningStyle.CODE: 0.0,
            LearningStyle.KINESTHETIC: 0.0
        }
        
        for interaction in interaction_history:
            content_type = interaction.get("content_type", "")
            engagement = interaction.get("engagement_score", 0.5)
            comprehension = interaction.get("comprehension_score", 0.5)
            
            # Combined score
            score = (engagement + comprehension) / 2
            
            if content_type in ["diagram", "graph", "chart", "image"]:
                style_scores[LearningStyle.VISUAL] += score
            elif content_type in ["analogy", "metaphor", "story"]:
                style_scores[LearningStyle.ANALOGY] += score
            elif content_type in ["proof", "derivation", "logic", "structured"]:
                style_scores[LearningStyle.LOGICAL] += score
            elif content_type in ["code", "implementation", "example_code"]:
                style_scores[LearningStyle.CODE] += score
            elif content_type in ["interactive", "hands_on", "practice"]:
                style_scores[LearningStyle.KINESTHETIC] += score
        
        # Normalize scores
        total = sum(style_scores.values())
        if total > 0:
            style_scores = {k: v/total for k, v in style_scores.items()}
        
        # Sort by score
        sorted_styles = sorted(style_scores.items(), key=lambda x: x[1], reverse=True)
        
        primary = sorted_styles[0][0] if sorted_styles else LearningStyle.VISUAL
        secondary = sorted_styles[1][0] if len(sorted_styles) > 1 else primary
        primary_confidence = sorted_styles[0][1] if sorted_styles else 0.2
        
        preference = StylePreference(
            primary_style=primary,
            secondary_style=secondary,
            confidence=primary_confidence,
            samples_count=len(interaction_history),
            last_updated=datetime.now().isoformat()
        )
        
        # Store in memory
        if self.memory:
            self.memory.store(f"style_preference_{user_id}", asdict(preference))
        
        return preference
    
    def monitor_cognitive_load(
        self,
        user_signals: Dict
    ) -> CognitiveLoadState:
        """
        Monitor cognitive load from user signals
        Signals: response_time, error_rate, self_reported_confusion, request_repetition
        """
        indicators = {
            "response_time": user_signals.get("avg_response_time_seconds", 30) / 60,  # Normalize to 0-1
            "error_rate": user_signals.get("recent_error_rate", 0.3),
            "confusion_signals": user_signals.get("confusion_count", 0) / max(1, user_signals.get("total_interactions", 1)),
            "repetition_requests": user_signals.get("repetition_requests", 0) / max(1, user_signals.get("total_interactions", 1)),
            "help_requests": user_signals.get("help_requests", 0) / max(1, user_signals.get("total_interactions", 1))
        }
        
        # Calculate overall load
        load_score = sum(indicators.values()) / len(indicators)
        
        if load_score < 0.3:
            level = CognitiveLoadLevel.LOW
            action = "Increase challenge, introduce complex problems"
        elif load_score < 0.5:
            level = CognitiveLoadLevel.OPTIMAL
            action = "Maintain current pace and difficulty"
        elif load_score < 0.7:
            level = CognitiveLoadLevel.HIGH
            action = "Simplify explanations, add more examples, slow down"
        else:
            level = CognitiveLoadLevel.OVERLOAD
            action = "Take a break, review fundamentals, reduce complexity drastically"
        
        state = CognitiveLoadState(
            current_load=level,
            indicators=indicators,
            recommended_action=action,
            timestamp=datetime.now().isoformat()
        )
        
        self.current_load = state
        return state
    
    def adapt_motivation(
        self,
        user_id: str,
        streak_days: int,
        recent_scores: List[float],
        session_frequency: float  # Sessions per week
    ) -> MotivationState:
        """
        Assess and adapt to user motivation level
        """
        # Calculate recent performance
        avg_performance = sum(recent_scores[-5:]) / min(5, len(recent_scores)) if recent_scores else 0.5
        
        # Engagement score based on consistency and performance
        engagement = (
            min(1.0, streak_days / 14) * 0.3 +  # Streak contribution (max at 2 weeks)
            avg_performance * 0.4 +  # Performance contribution
            min(1.0, session_frequency / 5) * 0.3  # Frequency contribution (max at 5/week)
        )
        
        # Determine motivation level
        if engagement < 0.3:
            level = MotivationLevel.LOW
            tone = "encouraging, celebrate small wins, reduce pressure"
        elif engagement < 0.6:
            level = MotivationLevel.MODERATE
            tone = "supportive, highlight progress, maintain consistency"
        else:
            level = MotivationLevel.HIGH
            tone = "challenging, introduce advanced topics, leverage momentum"
        
        state = MotivationState(
            level=level,
            streak_days=streak_days,
            recent_performance=avg_performance,
            engagement_score=engagement,
            recommended_tone=tone,
            timestamp=datetime.now().isoformat()
        )
        
        self.motivation_cache = state
        
        # Store in memory
        if self.memory:
            self.memory.store(f"motivation_state_{user_id}", asdict(state))
        
        return state
    
    def rank_content_explanations(
        self,
        concept_id: str,
        available_explanations: List[Dict],
        user_style: StylePreference,
        past_performance: Dict[str, float]  # explanation_type -> avg_score
    ) -> List[ContentRanking]:
        """
        Rank explanations based on user style and past effectiveness
        """
        rankings = []
        
        for exp in available_explanations:
            exp_type = exp.get("type", "generic")
            exp_difficulty = exp.get("difficulty", 0.5)
            
            # Style match score
            style_match = 0.0
            if exp_type == "visual" and user_style.primary_style == LearningStyle.VISUAL:
                style_match = 0.9
            elif exp_type == "analogy" and user_style.primary_style == LearningStyle.ANALOGY:
                style_match = 0.9
            elif exp_type == "logical" and user_style.primary_style == LearningStyle.LOGICAL:
                style_match = 0.9
            elif exp_type == "code" and user_style.primary_style == LearningStyle.CODE:
                style_match = 0.9
            elif exp_type == "interactive" and user_style.primary_style == LearningStyle.KINESTHETIC:
                style_match = 0.9
            else:
                # Partial match for secondary style
                if exp_type == user_style.secondary_style.value:
                    style_match = 0.5
                else:
                    style_match = 0.3
            
            # Effectiveness from past performance
            effectiveness = past_performance.get(exp_type, 0.5)
            
            # Difficulty appropriateness (prefer optimal challenge)
            difficulty_score = 1.0 - abs(exp_difficulty - 0.6)  # Prefer ~0.6 difficulty
            
            # Final ranking score
            final_rank = (
                effectiveness * 0.4 +
                style_match * 0.4 +
                difficulty_score * 0.2
            )
            
            rankings.append(ContentRanking(
                explanation_type=exp_type,
                effectiveness_score=effectiveness,
                style_match=style_match,
                difficulty_appropriateness=difficulty_score,
                final_rank=final_rank
            ))
        
        # Sort by final rank
        rankings.sort(key=lambda x: x.final_rank, reverse=True)
        
        return rankings
    
    def generate_personalized_prompt(
        self,
        concept: str,
        user_style: StylePreference,
        cognitive_load: CognitiveLoadState,
        motivation: MotivationState,
        mastery_level: float
    ) -> str:
        """
        Generate a personalized teaching prompt for the LLM
        """
        # Base instruction
        prompt_parts = [f"Teach the concept: {concept}"]
        
        # Style adaptation
        style_instructions = {
            LearningStyle.VISUAL: "Use visual descriptions, diagrams (describe them), spatial metaphors, and color-coding.",
            LearningStyle.ANALOGY: "Start with a real-world analogy, use metaphors, relate to familiar concepts.",
            LearningStyle.LOGICAL: "Present structured step-by-step reasoning, proofs, logical flow, clear definitions.",
            LearningStyle.CODE: "Provide code examples, implementation details, pseudocode, practical applications.",
            LearningStyle.KINESTHETIC: "Include interactive elements, practice problems, hands-on exercises."
        }
        
        prompt_parts.append(f"\nLEARNING STYLE: {user_style.primary_style.value}")
        prompt_parts.append(f"Instruction: {style_instructions[user_style.primary_style]}")
        
        if user_style.secondary_style != user_style.primary_style:
            prompt_parts.append(f"Also incorporate {user_style.secondary_style.value} elements as supplementary.")
        
        # Cognitive load adaptation
        if cognitive_load.current_load == CognitiveLoadLevel.HIGH:
            prompt_parts.append("\nCOGNITIVE LOAD: HIGH - Simplify explanations, break into smaller chunks, avoid jargon.")
        elif cognitive_load.current_load == CognitiveLoadLevel.OVERLOAD:
            prompt_parts.append("\nCOGNITIVE LOAD: OVERLOAD - Use only fundamental concepts, provide encouragement, suggest break.")
        elif cognitive_load.current_load == CognitiveLoadLevel.LOW:
            prompt_parts.append("\nCOGNITIVE LOAD: LOW - Increase complexity, introduce advanced connections, challenge assumptions.")
        
        # Motivation adaptation
        if motivation.level == MotivationLevel.LOW:
            prompt_parts.append("\nMOTIVATION: LOW - Be encouraging, celebrate progress, emphasize relevance, keep sessions short.")
        elif motivation.level == MotivationLevel.HIGH:
            prompt_parts.append("\nMOTIVATION: HIGH - Challenge with advanced topics, introduce cutting-edge applications.")
        
        # Mastery level adaptation
        if mastery_level < 0.3:
            prompt_parts.append("\nMASTERY: BEGINNER - Focus on intuition, avoid equations initially, build mental models.")
        elif mastery_level < 0.6:
            prompt_parts.append("\nMASTERY: INTERMEDIATE - Balance intuition with formalism, connect to related concepts.")
        else:
            prompt_parts.append("\nMASTERY: ADVANCED - Dive deep into technical details, explore edge cases, discuss research frontiers.")
        
        return "\n".join(prompt_parts)
    
    def update_style_history(
        self,
        concept_id: str,
        explanation_type: str,
        effectiveness_score: float
    ):
        """
        Update style history with new interaction data
        """
        if concept_id not in self.style_history:
            self.style_history[concept_id] = []
        
        self.style_history[concept_id].append((explanation_type, effectiveness_score))
        
        # Keep only last 20 interactions per concept
        if len(self.style_history[concept_id]) > 20:
            self.style_history[concept_id] = self.style_history[concept_id][-20:]
        
        # Store in memory
        if self.memory:
            self.memory.store(f"style_history_{concept_id}", self.style_history[concept_id])


# Example usage
if __name__ == "__main__":
    engine = PersonalizationEngineV2()
    
    # Simulate interaction history
    interactions = [
        {"content_type": "analogy", "engagement_score": 0.9, "comprehension_score": 0.8},
        {"content_type": "analogy", "engagement_score": 0.85, "comprehension_score": 0.75},
        {"content_type": "code", "engagement_score": 0.7, "comprehension_score": 0.6},
        {"content_type": "visual", "engagement_score": 0.6, "comprehension_score": 0.5},
        {"content_type": "analogy", "engagement_score": 0.88, "comprehension_score": 0.82},
    ]
    
    # Detect learning style
    style = engine.detect_learning_style("user_001", interactions)
    print(f"Detected Style: {style.primary_style.value} (confidence: {style.confidence:.2%})")
    print(f"Secondary Style: {style.secondary_style.value}\n")
    
    # Monitor cognitive load
    user_signals = {
        "avg_response_time_seconds": 45,
        "recent_error_rate": 0.25,
        "confusion_count": 2,
        "total_interactions": 10,
        "repetition_requests": 1,
        "help_requests": 1
    }
    
    load_state = engine.monitor_cognitive_load(user_signals)
    print(f"Cognitive Load: {load_state.current_load.value}")
    print(f"Recommendation: {load_state.recommended_action}\n")
    
    # Adapt motivation
    motivation = engine.adapt_motivation(
        user_id="user_001",
        streak_days=7,
        recent_scores=[0.7, 0.75, 0.8, 0.65, 0.85],
        session_frequency=4.0
    )
    
    print(f"Motivation Level: {motivation.level.value}")
    print(f"Engagement Score: {motivation.engagement_score:.2%}")
    print(f"Recommended Tone: {motivation.recommended_tone}\n")
    
    # Generate personalized prompt
    prompt = engine.generate_personalized_prompt(
        concept="Backpropagation",
        user_style=style,
        cognitive_load=load_state,
        motivation=motivation,
        mastery_level=0.5
    )
    
    print("=== PERSONALIZED TEACHING PROMPT ===")
    print(prompt)
