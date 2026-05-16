"""Peer Review System - Agents critique and improve each other's explanations."""
import asyncio
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import random

from api.services.agents import TutorAgent, AgentResponse, AgentRegistry
from api.services.llm import OllamaClient as LLMClient
from api.services.memory_palace import MemoryPalace


@dataclass
class ReviewCriteria:
    """Criteria for reviewing explanations."""
    accuracy: float = 0.0  # 0-10 scale
    clarity: float = 0.0
    completeness: float = 0.0
    pedagogical_soundness: float = 0.0
    level_appropriateness: float = 0.0
    
    @property
    def overall_score(self) -> float:
        return (self.accuracy + self.clarity + self.completeness + 
                self.pedagogical_soundness + self.level_appropriateness) / 5.0


@dataclass
class ReviewResult:
    """Result of a peer review."""
    reviewer_agent_id: str
    reviewer_name: str
    original_agent_id: str
    topic: str
    criteria: ReviewCriteria
    strengths: List[str] = field(default_factory=list)
    weaknesses: List[str] = field(default_factory=list)
    misconceptions: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)
    improved_version: Optional[str] = None
    detailed_feedback: str = ""


class PeerReviewSystem:
    """
    Agents review and improve each other's explanations.
    
    Features:
    - Multi-criteria evaluation (accuracy, clarity, completeness, pedagogy, level)
    - Constructive feedback with specific suggestions
    - Iterative improvement loops
    - Cross-domain perspective (math agent reviews physics explanation, etc.)
    """
    
    def __init__(self, agent_registry: AgentRegistry = None):
        self.agent_registry = agent_registry or AgentRegistry()
        self.llm = LLMClient()
        self.memory = MemoryPalace()
        
        self.review_criteria_descriptions = {
            "accuracy": "Er det fagligt korrekt? Er der nogen fejl eller misvisninger?",
            "clarity": "Er forklaringen forståelig for HF-elev? Er den tydelig og velstruktureret?",
            "completeness": "Mangler der vigtige trin eller koncepter? Er noget udeladt?",
            "pedagogical_soundness": "Følger det god pædagogik? Er rækkefølgen logisk?",
            "level_appropriateness": "Passer det til HF-niveau? Er det for simpelt/avanceret?",
        }
    
    async def review_explanation(self, explanation: str, reviewer_agent_id: str,
                                original_agent_id: str, topic: str,
                                student_level: str = "B") -> ReviewResult:
        """
        Have one agent review another agent's explanation.
        
        Args:
            explanation: The explanation text to review
            reviewer_agent_id: ID of agent doing the review
            original_agent_id: ID of agent who wrote the explanation
            topic: Topic being explained
            student_level: HF level (C, B, A)
        
        Returns:
            ReviewResult with scores and feedback
        """
        reviewer = self.agent_registry.get_agent(reviewer_agent_id)
        if not reviewer:
            raise ValueError(f"Reviewer agent {reviewer_agent_id} not found")
        
        # Build review prompt
        prompt = f"""Du er {reviewer.name} og skal bedømme en forklaring skrevet af en kollega.

ORIGINAL FORKLARING (af {original_agent_id}):
{explanation}

EMNE: {topic}
NIVEAU: {student_level}

=== BEDØMMELSESKRITERIER ===
1. FAGLIG KORREKTHED (0-10): {self.review_criteria_descriptions['accuracy']}
2. KLARHED (0-10): {self.review_criteria_descriptions['clarity']}
3. KOMPLETHED (0-10): {self.review_criteria_descriptions['completeness']}
4. PÆDAGOGISK KVALITET (0-10): {self.review_criteria_descriptions['pedagogical_soundness']}
5. NIVEAUAPASSNING (0-10): {self.review_criteria_descriptions['level_appropriateness']}

=== DIN OPGAVER ===
1. Giv en score (0-10) for hvert kriterium
2. Identificer 2-3 STÆRKE punkter ved forklaringen
3. Identificer 2-3 SVAGE punkter eller mangler
4. Påpeg eventuelle MISVISNINGER eller FEJL
5. Kom med konkrete FORBEDRINGSFORSLAG
6. Hvis nødvendigt, skriv en REVIDERET VERSION

=== FORMAT FOR DIT SVAR ===
SCORES:
- Accuracy: X/10
- Clarity: X/10
- Completeness: X/10
- Pedagogy: X/10
- Level: X/10

STÆRKE PUNKTER:
- [punkt 1]
- [punkt 2]
- [punkt 3]

SVAGE PUNKTER/MANGLER:
- [punkt 1]
- [punkt 2]
- [punkt 3]

MISVISNINGER/FEJL (hvis nogen):
- [eller skriv "Inge"]

FORBEDRINGSFORSLAG:
- [forslag 1]
- [forslag 2]
- [forslag 3]

REVIDERET VERSION (valgfrit, hvis store forbedringer muligt):
[skriv kun hvis du kan gøre det markant bedre]

SVAR SOM {reviewer.name}:"""
        
        try:
            response = await self.llm.generate(prompt, temperature=0.3)
            return self._parse_review_response(response, reviewer_agent_id, 
                                               original_agent_id, topic)
        except Exception as e:
            return self._create_error_review(reviewer_agent_id, original_agent_id, 
                                            topic, str(e))
    
    def _parse_review_response(self, response: str, reviewer_id: str,
                               original_id: str, topic: str) -> ReviewResult:
        """Parse LLM response into structured ReviewResult."""
        # Simple parsing - in production would use more robust method
        lines = response.split('\n')
        
        criteria = ReviewCriteria()
        strengths = []
        weaknesses = []
        misconceptions = []
        suggestions = []
        improved_version = None
        
        current_section = None
        
        for line in lines:
            line_lower = line.lower().strip()
            
            # Detect section
            if 'accuracy' in line_lower and ':' in line:
                criteria.accuracy = self._extract_score(line)
            elif 'clarity' in line_lower and ':' in line:
                criteria.clarity = self._extract_score(line)
            elif 'completeness' in line_lower and ':' in line:
                criteria.completeness = self._extract_score(line)
            elif 'pedagogy' in line_lower or 'pædagogisk' in line_lower:
                criteria.pedagogical_soundness = self._extract_score(line)
            elif 'level' in line_lower and ':' in line:
                criteria.level_appropriateness = self._extract_score(line)
            elif 'stærke' in line_lower or 'strong' in line_lower:
                current_section = 'strengths'
            elif 'svage' in line_lower or 'weak' in line_lower:
                current_section = 'weaknesses'
            elif 'misvisning' in line_lower or 'fejl' in line_lower or 'error' in line_lower:
                current_section = 'misconceptions'
            elif 'forbedring' in line_lower or 'suggestion' in line_lower:
                current_section = 'suggestions'
            elif 'revideret' in line_lower or 'improved' in line_lower:
                current_section = 'improved'
            elif line.strip().startswith('-') and current_section:
                item = line.strip()[1:].strip()
                if item and item.lower() not in ['inge', 'none', '']:
                    if current_section == 'strengths':
                        strengths.append(item)
                    elif current_section == 'weaknesses':
                        weaknesses.append(item)
                    elif current_section == 'misconceptions':
                        misconceptions.append(item)
                    elif current_section == 'suggestions':
                        suggestions.append(item)
                    elif current_section == 'improved':
                        if improved_version is None:
                            improved_version = item
                        else:
                            improved_version += '\n' + item
        
        reviewer = self.agent_registry.get_agent(reviewer_id)
        
        return ReviewResult(
            reviewer_agent_id=reviewer_id,
            reviewer_name=reviewer.name if reviewer else reviewer_id,
            original_agent_id=original_id,
            topic=topic,
            criteria=criteria,
            strengths=strengths,
            weaknesses=weaknesses,
            misconceptions=misconceptions,
            suggestions=suggestions,
            improved_version=improved_version,
            detailed_feedback=response
        )
    
    def _extract_score(self, line: str) -> float:
        """Extract numeric score from line like 'Accuracy: 8/10'."""
        try:
            # Look for pattern like "X/10" or "X out of 10"
            import re
            match = re.search(r'(\d+)\s*[/\s]\s*(\d+)', line)
            if match:
                numerator = float(match.group(1))
                denominator = float(match.group(2))
                return min(10.0, (numerator / denominator) * 10.0) if denominator > 0 else 0.0
            
            # Try just extracting a number
            match = re.search(r'\b(\d+(?:\.\d+)?)\b', line)
            if match:
                score = float(match.group(1))
                return min(10.0, score) if score <= 10 else (score / 10.0 * 10.0)
        except:
            pass
        return 5.0  # Default middle score
    
    def _create_error_review(self, reviewer_id: str, original_id: str,
                            topic: str, error_msg: str) -> ReviewResult:
        """Create a minimal review when parsing fails."""
        reviewer = self.agent_registry.get_agent(reviewer_id)
        return ReviewResult(
            reviewer_agent_id=reviewer_id,
            reviewer_name=reviewer.name if reviewer else reviewer_id,
            original_agent_id=original_id,
            topic=topic,
            criteria=ReviewCriteria(),
            detailed_feedback=f"Review failed: {error_msg}",
            weaknesses=["Could not parse review properly"]
        )
    
    async def iterative_improvement_loop(self, initial_explanation: str,
                                        original_agent_id: str, topic: str,
                                        student_level: str = "B",
                                        max_iterations: int = 3,
                                        threshold_score: float = 8.5) -> Tuple[str, List[ReviewResult]]:
        """
        Run iterative peer review cycles to improve an explanation.
        
        Args:
            initial_explanation: Starting explanation
            original_agent_id: ID of agent who wrote it
            topic: Topic being explained
            student_level: HF level
            max_iterations: Maximum review cycles
            threshold_score: Stop if overall score >= this
        
        Returns:
            Tuple of (final_explanation, list_of_reviews)
        """
        current_version = initial_explanation
        all_reviews = []
        
        for iteration in range(max_iterations):
            # Select random reviewer (not original author)
            available_reviewers = [
                aid for aid in self.agent_registry.list_agents()
                if aid != original_agent_id
            ]
            
            if not available_reviewers:
                break
            
            reviewer_id = random.choice(available_reviewers)
            
            # Get review
            review = await self.review_explanation(
                explanation=current_version,
                reviewer_agent_id=reviewer_id,
                original_agent_id=original_agent_id,
                topic=topic,
                student_level=student_level
            )
            
            all_reviews.append(review)
            
            # Check if good enough
            if review.criteria.overall_score >= threshold_score:
                break
            
            # If reviewer provided improved version, use it
            if review.improved_version:
                current_version = review.improved_version
            elif review.suggestions:
                # Ask original agent to revise based on feedback
                revision_prompt = f"""Du er {original_agent_id} og har modtaget feedback på din forklaring.

DIN oprindelige FORKLARING:
{current_version}

FEEDBACK fra {review.reviewer_name}:
- Score: {review.criteria.overall_score:.1f}/10
- Stærke punkter: {', '.join(review.strengths[:2]) if review.strengths else 'None'}
- Svage punkter: {', '.join(review.weaknesses[:2]) if review.weaknesses else 'None'}
- Forslag: {', '.join(review.suggestions[:3]) if review.suggestions else 'None'}

SKRIV EN REVIDERET VERSION der:
1. Beholder det der var godt
2. Adresserer de identificerede svagheder
3. Implementerer mindst 2 af forslagene

REVIDERET VERSION:"""
                
                try:
                    current_version = await self.llm.generate(revision_prompt, temperature=0.5)
                except:
                    pass
        
        return current_version, all_reviews
    
    async def multi_agent_review(self, explanation: str, topic: str,
                                original_agent_id: str,
                                student_level: str = "B") -> List[ReviewResult]:
        """Get reviews from multiple agents simultaneously."""
        reviewers = [
            aid for aid in self.agent_registry.list_agents()
            if aid != original_agent_id
        ]
        
        tasks = [
            self.review_explanation(
                explanation=explanation,
                reviewer_agent_id=reviewer_id,
                original_agent_id=original_agent_id,
                topic=topic,
                student_level=student_level
            )
            for reviewer_id in reviewers
        ]
        
        results = await asyncio.gather(*tasks)
        return list(results)
    
    def aggregate_reviews(self, reviews: List[ReviewResult]) -> Dict:
        """Aggregate multiple reviews into summary statistics."""
        if not reviews:
            return {}
        
        avg_scores = {
            'accuracy': sum(r.criteria.accuracy for r in reviews) / len(reviews),
            'clarity': sum(r.criteria.clarity for r in reviews) / len(reviews),
            'completeness': sum(r.criteria.completeness for r in reviews) / len(reviews),
            'pedagogy': sum(r.criteria.pedagogical_soundness for r in reviews) / len(reviews),
            'level': sum(r.criteria.level_appropriateness for r in reviews) / len(reviews),
            'overall': sum(r.criteria.overall_score for r in reviews) / len(reviews),
        }
        
        all_strengths = []
        all_weaknesses = []
        for r in reviews:
            all_strengths.extend(r.strengths)
            all_weaknesses.extend(r.weaknesses)
        
        return {
            'average_scores': avg_scores,
            'common_strengths': all_strengths[:5],
            'common_weaknesses': all_weaknesses[:5],
            'num_reviews': len(reviews),
            'consensus_reached': avg_scores['overall'] >= 8.0,
        }
