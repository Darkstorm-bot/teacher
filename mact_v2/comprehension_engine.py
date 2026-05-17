"""
MACT v2.0 - Comprehension Engine
Features: Quiz Generation, Spaced Repetition (SM-2), Adaptive Difficulty (ZPD)
"""

import random
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum


class BloomLevel(Enum):
    REMEMBER = "remember"
    UNDERSTAND = "understand"
    APPLY = "apply"
    ANALYZE = "analyze"
    EVALUATE = "evaluate"
    CREATE = "create"


@dataclass
class Question:
    id: str
    concept_id: str
    question_text: str
    question_type: str  # mcq, true_false, fill_blank
    options: List[str]
    correct_answer: str
    explanation: str
    bloom_level: BloomLevel
    difficulty: float  # 0.0-1.0


@dataclass
class QuizResult:
    quiz_id: str
    user_id: str
    timestamp: str
    questions: List[Dict]
    answers: List[str]
    score: float
    time_taken_seconds: int
    difficulty_adjustment: float


@dataclass
class SpacedRepetitionCard:
    concept_id: str
    ease_factor: float  # SM-2 EF (default 2.5)
    interval: int  # days until next review
    repetitions: int  # consecutive correct answers
    last_reviewed: Optional[str]
    next_review: str


class ComprehensionEngine:
    def __init__(self, memory_client=None):
        self.memory = memory_client
        self.question_bank: Dict[str, List[Question]] = {}
        self.spaced_cards: Dict[str, SpacedRepetitionCard] = {}
        
    def generate_quiz(
        self, 
        concept_ids: List[str], 
        num_questions: int = 5,
        target_difficulty: float = 0.5,
        user_mastery: Dict[str, float] = None
    ) -> List[Question]:
        """
        Generate adaptive quiz based on concept mastery and ZPD
        """
        if user_mastery is None:
            user_mastery = {}
            
        questions = []
        
        for concept_id in concept_ids:
            mastery = user_mastery.get(concept_id, 0.5)
            
            # Zone of Proximal Development: optimal difficulty = mastery + 0.1-0.2
            optimal_difficulty = min(0.9, max(0.1, mastery + 0.15))
            
            # Adjust bloom level based on mastery
            if mastery < 0.3:
                bloom_levels = [BloomLevel.REMEMBER, BloomLevel.UNDERSTAND]
            elif mastery < 0.6:
                bloom_levels = [BloomLevel.UNDERSTAND, BloomLevel.APPLY]
            elif mastery < 0.8:
                bloom_levels = [BloomLevel.APPLY, BloomLevel.ANALYZE]
            else:
                bloom_levels = [BloomLevel.ANALYZE, BloomLevel.EVALUATE, BloomLevel.CREATE]
            
            # Generate questions (in production, call LLM here)
            for i in range(num_questions // len(concept_ids) + 1):
                q = self._generate_question_for_concept(
                    concept_id=concept_id,
                    difficulty=optimal_difficulty,
                    bloom_levels=bloom_levels
                )
                questions.append(q)
        
        return questions[:num_questions]
    
    def _generate_question_for_concept(
        self, 
        concept_id: str, 
        difficulty: float,
        bloom_levels: List[BloomLevel]
    ) -> Question:
        """
        Generate a single question (placeholder - in production calls LLM)
        """
        bloom = random.choice(bloom_levels)
        q_type = random.choice(["mcq", "true_false", "fill_blank"])
        
        # Template questions (replace with LLM generation)
        templates = {
            BloomLevel.REMEMBER: f"What is the definition of {concept_id}?",
            BloomLevel.UNDERSTAND: f"Explain the concept of {concept_id} in your own words.",
            BloomLevel.APPLY: f"How would you apply {concept_id} to solve a problem?",
            BloomLevel.ANALYZE: f"Analyze the relationship between {concept_id} and related concepts.",
            BloomLevel.EVALUATE: f"Evaluate the effectiveness of {concept_id} in different scenarios.",
            BloomLevel.CREATE: f"Design a solution using {concept_id} for a novel problem."
        }
        
        return Question(
            id=f"q_{concept_id}_{random.randint(1000, 9999)}",
            concept_id=concept_id,
            question_text=templates.get(bloom, f"Question about {concept_id}?"),
            question_type=q_type,
            options=["Option A", "Option B", "Option C", "Option D"] if q_type == "mcq" else [],
            correct_answer="A",
            explanation=f"This tests {bloom.value} level understanding of {concept_id}",
            bloom_level=bloom,
            difficulty=difficulty
        )
    
    def evaluate_quiz(
        self, 
        quiz: List[Question], 
        user_answers: List[str],
        time_taken: int
    ) -> QuizResult:
        """
        Evaluate quiz and calculate metrics
        """
        correct = sum(1 for q, a in zip(quiz, user_answers) if q.correct_answer == a)
        score = correct / len(quiz) if quiz else 0
        
        # Calculate difficulty adjustment for next quiz
        if score > 0.8:
            adjustment = 0.1  # Increase difficulty
        elif score < 0.4:
            adjustment = -0.1  # Decrease difficulty
        else:
            adjustment = 0.0
            
        return QuizResult(
            quiz_id=f"quiz_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
            user_id="user_001",  # Replace with actual user ID
            timestamp=datetime.now().isoformat(),
            questions=[asdict(q) for q in quiz],
            answers=user_answers,
            score=score,
            time_taken_seconds=time_taken,
            difficulty_adjustment=adjustment
        )
    
    def update_spaced_repetition(
        self, 
        concept_id: str, 
        quality: int  # 0-5 scale (0=wrong, 5=perfect)
    ) -> SpacedRepetitionCard:
        """
        Update spaced repetition schedule using SM-2 algorithm
        """
        # Initialize card if doesn't exist
        if concept_id not in self.spaced_cards:
            self.spaced_cards[concept_id] = SpacedRepetitionCard(
                concept_id=concept_id,
                ease_factor=2.5,
                interval=1,
                repetitions=0,
                last_reviewed=None,
                next_review=datetime.now().strftime("%Y-%m-%d")
            )
        
        card = self.spaced_cards[concept_id]
        
        # SM-2 Algorithm
        if quality >= 3:  # Correct answer
            if card.repetitions == 0:
                card.interval = 1
            elif card.repetitions == 1:
                card.interval = 6
            else:
                card.interval = round(card.interval * card.ease_factor)
            
            card.repetitions += 1
        else:  # Wrong answer
            card.repetitions = 0
            card.interval = 1
        
        # Update ease factor
        card.ease_factor = max(1.3, card.ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))
        
        # Set next review date
        card.last_reviewed = datetime.now().strftime("%Y-%m-%d")
        card.next_review = (datetime.now() + timedelta(days=card.interval)).strftime("%Y-%m-%d")
        
        # Store in memory
        if self.memory:
            self.memory.store(f"spaced_card_{concept_id}", asdict(card))
        
        return card
    
    def get_due_cards(self, user_id: str) -> List[SpacedRepetitionCard]:
        """
        Get cards due for review today
        """
        today = datetime.now().strftime("%Y-%m-%d")
        due_cards = []
        
        for card in self.spaced_cards.values():
            if card.next_review <= today:
                due_cards.append(card)
        
        return due_cards
    
    def get_concept_mastery(self, concept_id: str) -> float:
        """
        Calculate mastery score based on spaced repetition performance
        """
        if concept_id not in self.spaced_cards:
            return 0.0
        
        card = self.spaced_cards[concept_id]
        
        # Mastery based on repetitions and ease factor
        base_mastery = min(1.0, card.repetitions / 10)
        ease_bonus = (card.ease_factor - 2.5) * 0.1
        
        return min(1.0, max(0.0, base_mastery + ease_bonus))


# Example usage
if __name__ == "__main__":
    engine = ComprehensionEngine()
    
    # Generate quiz
    concepts = ["neural_networks", "backpropagation", "activation_functions"]
    quiz = engine.generate_quiz(concepts, num_questions=5, user_mastery={"neural_networks": 0.6})
    
    print(f"Generated {len(quiz)} questions:")
    for q in quiz:
        print(f"  - {q.question_text} (Difficulty: {q.difficulty:.2f}, Bloom: {q.bloom_level.value})")
    
    # Simulate user answers
    answers = [q.correct_answer for q in quiz]  # Perfect score simulation
    result = engine.evaluate_quiz(quiz, answers, time_taken=120)
    
    print(f"\nQuiz Result: Score={result.score:.2%}, Time={result.time_taken_seconds}s")
    print(f"Difficulty Adjustment: {result.difficulty_adjustment:+.2f}")
    
    # Update spaced repetition
    for concept in concepts:
        quality = 5 if result.score > 0.8 else 3
        card = engine.update_spaced_repetition(concept, quality)
        print(f"\n{concept}: Next review in {card.interval} days (EF: {card.ease_factor:.2f})")
