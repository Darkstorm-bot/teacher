"""Meta-Cognition Engine - Self-reflection, learning-to-learn, and conversation analytics."""
import json
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import statistics

from api.services.memory_palace import MemoryPalace
from api.services.student_modeling import StudentCognitiveModel, CognitiveState


class ReflectionTrigger(Enum):
    """Events that trigger meta-cognitive reflection."""
    SESSION_END = "SESSION_END"
    TOPIC_MASTERY = "TOPIC_MASTERY"
    REPEATED_STRUGGLE = "REPEATED_STRUGGLE"
    BREAKTHROUGH = "BREAKTHROUGH"
    STATE_CHANGE = "STATE_CHANGE"
    TIME_INTERVAL = "TIME_INTERVAL"


@dataclass
class MetaCognitiveInsight:
    """An insight about the student's learning process."""
    insight_type: str
    description: str
    evidence: List[str] = field(default_factory=list)
    actionable_advice: str = ""
    confidence: float = 1.0
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.utcnow().isoformat()


@dataclass
class LearningPattern:
    """Identified pattern in student's learning behavior."""
    pattern_type: str
    description: str
    frequency: float = 0.0  # How often this occurs (0-1)
    impact_on_learning: float = 0.0  # Correlation with success (-1 to 1)
    examples: List[str] = field(default_factory=list)
    recommendations: List[str] = field(default_factory=list)


@dataclass
class SessionSummary:
    """Summary of a learning session."""
    session_id: str
    student_id: str
    start_time: str
    end_time: str
    duration_minutes: int
    topics_covered: List[str] = field(default_factory=list)
    problems_attempted: int = 0
    problems_solved: int = 0
    help_requests: int = 0
    cognitive_states: List[str] = field(default_factory=list)
    key_insights: List[MetaCognitiveInsight] = field(default_factory=list)
    mastery_gains: List[Tuple[str, float]] = field(default_factory=list)  # (topic, gain)


class MetaCognitionEngine:
    """
    Meta-cognition engine that helps students learn how to learn.
    
    Features:
    - Self-reflection prompts based on performance patterns
    - Learning strategy recommendations
    - Pattern detection in study habits
    - Growth mindset reinforcement
    - Conversation quality analysis
    """
    
    def __init__(self, student_id: str):
        self.student_id = student_id
        self.memory = MemoryPalace()
        self.insights: List[MetaCognitiveInsight] = []
        self.patterns: List[LearningPattern] = []
    
    def analyze_session(self, session_data: Dict, 
                       cognitive_model: Optional[StudentCognitiveModel]) -> SessionSummary:
        """Analyze a complete learning session and extract insights."""
        
        # Extract basic metrics
        summary = SessionSummary(
            session_id=session_data.get("session_id", ""),
            student_id=self.student_id,
            start_time=session_data.get("start_time", datetime.utcnow().isoformat()),
            end_time=datetime.utcnow().isoformat(),
            duration_minutes=session_data.get("duration_minutes", 0),
            topics_covered=session_data.get("topics", []),
            problems_attempted=session_data.get("problems_attempted", 0),
            problems_solved=session_data.get("problems_solved", 0),
            help_requests=session_data.get("help_requests", 0),
            cognitive_states=session_data.get("cognitive_states", []),
        )
        
        # Calculate success rate
        if summary.problems_attempted > 0:
            success_rate = summary.problems_solved / summary.problems_attempted
        else:
            success_rate = 0
        
        # Detect patterns
        self._detect_learning_patterns(session_data, cognitive_model)
        
        # Generate insights
        self._generate_insights(session_data, cognitive_model, success_rate)
        summary.key_insights = self.insights.copy()
        
        # Calculate mastery gains
        if cognitive_model:
            for topic in summary.topics_covered:
                # This would compare pre/post session mastery
                # For now, estimate from success rate
                estimated_gain = success_rate * 0.1
                summary.mastery_gains.append((topic, estimated_gain))
        
        # Store in memory palace
        self._store_session_summary(summary)
        
        return summary
    
    def _detect_learning_patterns(self, session_data: Dict,
                                  cognitive_model: Optional[StudentCognitiveModel]):
        """Detect recurring patterns in learning behavior."""
        interactions = session_data.get("interactions", [])
        
        if not interactions:
            return
        
        # Pattern 1: Question-asking behavior
        question_count = sum(1 for i in interactions if "?" in i.get("student_message", ""))
        question_ratio = question_count / len(interactions) if interactions else 0
        
        if question_ratio > 0.3:
            self.patterns.append(LearningPattern(
                pattern_type="ACTIVE_QUESTIONER",
                description="Du stiller mange spørgsmål - det er et tegn på aktiv læring!",
                frequency=question_ratio,
                impact_on_learning=0.7,  # Questions correlate with better outcomes
                recommendations=[
                    "Fortsæt med at stille spørgsmål",
                    "Prøv også at besvare dine egne spørgsmål først før du spørger"
                ]
            ))
        elif question_ratio < 0.05 and len(interactions) > 10:
            self.patterns.append(LearningPattern(
                pattern_type="PASSIVE_LEARNER",
                description="Du stiller få spørgsmål. Husk at spørgsmål er kraftfulde!",
                frequency=question_ratio,
                impact_on_learning=-0.3,
                recommendations=[
                    "Prøv at stille mindst ét spørgsmål per emne",
                    "Spørg 'hvorfor?' når noget virker uklart",
                    "Bed om eksempler hvis noget virker abstrakt"
                ]
            ))
        
        # Pattern 2: Response time patterns
        response_times = [i.get("response_time_seconds", 30) for i in interactions]
        if response_times:
            avg_response = statistics.mean(response_times)
            std_response = statistics.stdev(response_times) if len(response_times) > 1 else 0
            
            if avg_response < 10 and std_response < 5:
                self.patterns.append(LearningPattern(
                    pattern_type="RAPID_RESPONDER",
                    description="Du svarer meget hurtigt - pas på ikke at gætte for hurtigt!",
                    frequency=1.0,
                    impact_on_learning=-0.4,
                    recommendations=[
                        "Tag dig tid til at tænke grundigt efter hver opgave",
                        "Tæl til 10 før du sender dit svar",
                        "Skriv dine mellemregninger ned"
                    ]
                ))
            elif avg_response > 60:
                self.patterns.append(LearningPattern(
                    pattern_type="DELIBERATE_THINKER",
                    description="Du bruger god tid på at tænke - det er godt for dyb læring!",
                    frequency=1.0,
                    impact_on_learning=0.5,
                    recommendations=[
                        "Fortsæt med at tænke grundigt",
                        "Men husk at tage pauser hvis du sidder fast for længe"
                    ]
                ))
        
        # Pattern 3: Error recovery
        error_sequences = self._detect_error_recovery_patterns(interactions)
        if error_sequences["quick_recovery"] > 3:
            self.patterns.append(LearningPattern(
                pattern_type="RESILIENT_LEARNER",
                description="Du kommer hurtigt videre efter fejl - fremragende væksttankesæt!",
                frequency=error_sequences["quick_recovery"] / max(1, error_sequences["total_errors"]),
                impact_on_learning=0.8,
                recommendations=[
                    "Denne evne til at komme videre er værdifuld - behold den!",
                    "Prøv at analysere hvad der gik galt inden du fortsætter"
                ]
            ))
        elif error_sequences["gave_up"] > 2:
            self.patterns.append(LearningPattern(
                pattern_type="GIVES_UP_EASILY",
                description="Du giver op ret hurtigt efter fejl. Prøv at være mere tålmodig med dig selv.",
                frequency=error_sequences["gave_up"] / max(1, error_sequences["total_errors"]),
                impact_on_learning=-0.6,
                recommendations=[
                    "Fejl er en naturlig del af læring - alle laver dem",
                    "Prøv at se fejl som information om hvad du skal øve dig på",
                    "Tag en dyb indånding og prøv en anden tilgang"
                ]
            ))
        
        # Pattern 4: Topic switching
        topic_switches = self._count_topic_switches(interactions)
        if topic_switches > len(set(session_data.get("topics", []))) * 3:
            self.patterns.append(LearningPattern(
                pattern_type="CONTEXT_SWITCHER",
                description="Du skifter ofte mellem emner. Dette kan forhindre dyb læring.",
                frequency=topic_switches / max(1, len(interactions)),
                impact_on_learning=-0.4,
                recommendations=[
                    "Prøv at fokusere på ét emne ad gangen i mindst 15 minutter",
                    "Afslut et emne før du går videre til næste",
                    "Brug Pomodoro-teknikken for bedre fokus"
                ]
            ))
    
    def _detect_error_recovery_patterns(self, interactions: List[Dict]) -> Dict:
        """Detect how student responds to errors."""
        result = {"quick_recovery": 0, "gave_up": 0, "total_errors": 0}
        
        prev_was_error = False
        for i, interaction in enumerate(interactions):
            content = (interaction.get("agent_response", "") or "").lower()
            student_msg = (interaction.get("student_message", "") or "").lower()
            
            # Detect error feedback from agent
            is_error = any(word in content for word in ["ikke helt", "forkert", "prøv igen", "fejl"])
            
            if is_error:
                result["total_errors"] += 1
                prev_was_error = True
            elif prev_was_error:
                # Check student response after error
                if any(word in student_msg for word in ["giver op", "for svært", "kan ikke"]):
                    result["gave_up"] += 1
                elif "?" in student_msg or len(student_msg) > 20:
                    result["quick_recovery"] += 1
                prev_was_error = False
        
        return result
    
    def _count_topic_switches(self, interactions: List[Dict]) -> int:
        """Count how many times student switches topics."""
        switches = 0
        prev_topic = None
        
        for interaction in interactions:
            topic = interaction.get("topic")
            if topic and topic != prev_topic:
                switches += 1
                prev_topic = topic
        
        return switches
    
    def _generate_insights(self, session_data: Dict,
                          cognitive_model: Optional[StudentCognitiveModel],
                          success_rate: float):
        """Generate meta-cognitive insights from session."""
        self.insights = []
        
        # Insight 1: Performance vs effort
        duration = session_data.get("duration_minutes", 30)
        problems = session_data.get("problems_attempted", 0)
        
        if problems > 0:
            pace = duration / problems
            if pace < 2 and success_rate < 0.5:
                self.insights.append(MetaCognitiveInsight(
                    insight_type="PACE_TOO_FAST",
                    description="Du går meget hurtigt frem, men succesraten er lav. Kvalitet over kvantitet!",
                    evidence=[f"Gennemsnitlig tid per opgave: {pace:.1f} min", f"Succesrate: {success_rate:.0%}"],
                    actionable_advice="Brug 5-10 minutter per opgave. Tænk grundigt før du svarer.",
                    confidence=0.8
                ))
            elif pace > 15 and problems < 3:
                self.insights.append(MetaCognitiveInsight(
                    insight_type="POSSIBLY_STUCK",
                    description="Du bruger meget lang tid på få opgaver. Måske er du gået i stå?",
                    evidence=[f"Tid per opgave: {pace:.1f} min", f"Antal opgaver: {problems}"],
                    actionable_advice="Hvis du sidder fast i mere end 10 minutter, så bed om hjælp eller tag en pause.",
                    confidence=0.7
                ))
        
        # Insight 2: Cognitive state progression
        states = session_data.get("cognitive_states", [])
        if len(states) >= 3:
            # Check trajectory
            state_scores = {
                "FRUSTRATED": 1, "CONFUSED": 2, "BORED": 2, "FOCUSED": 3,
                "CURIOUS": 4, "OVERWHELMED": 1
            }
            scores = [state_scores.get(s, 2) for s in states]
            
            if scores[-1] > scores[0]:
                self.insights.append(MetaCognitiveInsight(
                    insight_type="POSITIVE_TRAJECTORY",
                    description="Din læringsstil udviklede sig positivt i denne session!",
                    evidence=[f"Starttilstand: {states[0]}", f"Sluttilstand: {states[-1]}"],
                    actionable_advice="Denne fremgang viser at din indsats virker. Fortsæt sådan!",
                    confidence=0.9
                ))
            elif scores[-1] < scores[0] and scores[-1] <= 2:
                self.insights.append(MetaCognitiveInsight(
                    insight_type="NEEDS_BREAK",
                    description="Du ser ud til at blive mere frustreret/forvirret. Tid til en pause?",
                    evidence=[f"Starttilstand: {states[0]}", f"Sluttilstand: {states[-1]}"],
                    actionable_advice="Tag 5-10 minutters pause. Gå en tur, drik vand, og kom frisk tilbage.",
                    confidence=0.85
                ))
        
        # Insight 3: Help-seeking behavior
        help_requests = session_data.get("help_requests", 0)
        if help_requests == 0 and success_rate < 0.4:
            self.insights.append(MetaCognitiveInsight(
                insight_type="RELUCTANT_TO_ASK_HELP",
                description="Du kæmper men beder ikke om hjælp. Det er okay at have brug for støtte!",
                evidence=[f"Succesrate: {success_rate:.0%}", f"Hjælpeforespørgsler: {help_requests}"],
                actionable_advice="At bede om hjælp er et tegn på styrke, ikke svaghed. Brug dine tutor-agenter!",
                confidence=0.75
            ))
        elif help_requests > 10 and session_data.get("duration_minutes", 0) < 60:
            self.insights.append(MetaCognitiveInsight(
                insight_type="DEPENDENT_ON_HELP",
                description="Du beder om hjælp meget ofte. Prøv at kæmpe lidt mere selv først.",
                evidence=[f"Hjælpeforespørgsler: {help_requests}", f"Varighed: {session_data.get('duration_minutes', 0)} min"],
                actionable_advice="Prøv 3x selv før du beder om hjælp. Skriv dine forsøg ned.",
                confidence=0.7
            ))
        
        # Insight 4: Growth mindset reinforcement
        if cognitive_model:
            if cognitive_model.frustration_level > 0.5 and cognitive_model.motivation_level > 0.5:
                self.insights.append(MetaCognitiveInsight(
                    insight_type="GROWTH_MINDSET_DETECTED",
                    description="Selvom det er svært, bevarer du motivationen. Det er væksttankesæt i aktion!",
                    evidence=[f"Frustration: {cognitive_model.frustration_level:.0%}", 
                             f"Motivation: {cognitive_model.motivation_level:.0%}"],
                    actionable_advice="Denne evne til at holde motivationen trods udfordringer er nøglen til succes!",
                    confidence=0.9
                ))
    
    def _store_session_summary(self, summary: SessionSummary):
        """Store session summary in memory palace."""
        self.memory.store(
            content=json.dumps({
                "session_id": summary.session_id,
                "duration": summary.duration_minutes,
                "topics": summary.topics_covered,
                "success_rate": summary.problems_solved / max(1, summary.problems_attempted),
                "insights_count": len(summary.key_insights),
            }),
            wing="wing_fælles",
            room="room_analytics",
            topic="session_summary",
            student_id=self.student_id,
            event_type="session_summary"
        )
    
    def generate_reflection_prompts(self, summary: SessionSummary) -> List[str]:
        """Generate personalized reflection prompts for student."""
        prompts = []
        
        # Based on performance
        if summary.problems_attempted > 0:
            success_rate = summary.problems_solved / summary.problems_attempted
            
            if success_rate > 0.8:
                prompts.append("🌟 Du havde en rigtig god session! Hvad tror du var nøglen til din succes?")
                prompts.append("Kan du formulere én ting du lærte, som du kan bruge næste gang?")
            elif success_rate < 0.4:
                prompts.append("💪 Denne session var udfordrende. Hvad var det sværeste koncept?")
                prompts.append("Hvilken strategi vil du prøve anderledes næste gang?")
        
        # Based on help-seeking
        if summary.help_requests == 0 and summary.problems_attempted > 5:
            prompts.append("🤔 Du klarede dig selv hele vejen! Hvordan føles det at løse problemer selvstændigt?")
        elif summary.help_requests > 5:
            prompts.append("💬 Du fik en del hjælp i dag. Hvilket spørgsmål var mest nyttigt?")
        
        # Based on time
        if summary.duration_minutes > 60:
            prompts.append("⏰ Du arbejdede i over en time. Hvordan mærker du din energi nu?")
            prompts.append("Hvad kunne hjælpe dig med at opretholde fokus i lange sessioner?")
        elif summary.duration_minutes < 15:
            prompts.append("⚡ Kort session i dag! Hvad ville hjælpe dig til at arbejde lidt længere næste gang?")
        
        # Based on cognitive states
        if "FRUSTRATED" in summary.cognitive_states or "OVERWHELMED" in summary.cognitive_states:
            prompts.append("🧘 Jeg bemærkede at du blev frustreret/overvældet. Hvad kunne have hjulpet i det øjeblik?")
        
        if "CURIOUS" in summary.cognitive_states:
            prompts.append("✨ Du virkede nysgerrig undervejs! Hvad var det mest interessante du opdagede?")
        
        # Forward-looking
        prompts.append("🎯 Hvad er dit mål for næste læringsession?")
        
        return prompts[:5]  # Limit to 5 prompts
    
    def get_long_term_trends(self, days: int = 30) -> Dict:
        """Analyze long-term learning trends."""
        # This would query memory palace for historical sessions
        # For now, return placeholder structure
        return {
            "trend_direction": "improving",  # improving, stable, declining
            "mastery_velocity": 0.05,  # Average mastery gain per day
            "consistency_score": 0.7,  # How regular is study habit
            "optimal_session_length": 45,  # Minutes
            "best_performing_topics": [],
            "struggling_topics": [],
            "recommendations": [
                "Fortsæt med din nuværende strategi",
                "Overvej at øge tiden på svære emner"
            ]
        }


class ConversationQualityAnalyzer:
    """
    Analyzes the quality of tutor-student conversations.
    
    Metrics:
    - Turn-taking balance
    - Question depth
    - Explanation clarity
    - Conceptual coverage
    - Engagement level
    """
    
    def __init__(self):
        self.memory = MemoryPalace()
    
    def analyze_conversation(self, turns: List[Dict]) -> Dict:
        """Analyze conversation quality."""
        if not turns:
            return {"quality_score": 0.0, "metrics": {}}
        
        metrics = {
            "turn_balance": self._calculate_turn_balance(turns),
            "question_depth": self._analyze_question_depth(turns),
            "explanation_clarity": self._estimate_explanation_clarity(turns),
            "conceptual_coverage": self._assess_conceptual_coverage(turns),
            "engagement_score": self._measure_engagement(turns),
        }
        
        # Overall quality score (weighted average)
        weights = {
            "turn_balance": 0.15,
            "question_depth": 0.25,
            "explanation_clarity": 0.25,
            "conceptual_coverage": 0.20,
            "engagement_score": 0.15,
        }
        
        quality_score = sum(metrics[k] * weights[k] for k in metrics)
        
        return {
            "quality_score": min(1.0, quality_score),
            "metrics": metrics,
            "strengths": self._identify_strengths(metrics),
            "areas_for_improvement": self._identify_improvements(metrics),
        }
    
    def _calculate_turn_balance(self, turns: List[Dict]) -> float:
        """Calculate balance between student and tutor talking."""
        student_words = 0
        tutor_words = 0
        
        for turn in turns:
            student_msg = turn.get("student_message", "")
            agent_msg = turn.get("agent_response", "")
            
            student_words += len(student_msg.split()) if student_msg else 0
            tutor_words += len(agent_msg.split()) if agent_msg else 0
        
        total = student_words + tutor_words
        if total == 0:
            return 0.5
        
        student_ratio = student_words / total
        # Ideal ratio: student speaks 30-50% of the time
        if 0.3 <= student_ratio <= 0.5:
            return 1.0
        elif 0.2 <= student_ratio < 0.3 or 0.5 < student_ratio <= 0.6:
            return 0.7
        else:
            return 0.4
    
    def _analyze_question_depth(self, turns: List[Dict]) -> float:
        """Analyze depth of questions asked."""
        student_questions = [
            turn.get("student_message", "")
            for turn in turns
            if "?" in turn.get("student_message", "")
        ]
        
        if not student_questions:
            return 0.3  # No questions is not great
        
        depth_scores = []
        for q in student_questions:
            words = len(q.split())
            # Longer questions tend to be more thoughtful
            if words > 15:
                depth_scores.append(1.0)
            elif words > 8:
                depth_scores.append(0.7)
            else:
                depth_scores.append(0.4)
        
        return statistics.mean(depth_scores)
    
    def _estimate_explanation_clarity(self, turns: List[Dict]) -> float:
        """Estimate clarity of tutor explanations."""
        # Look for understanding signals after explanations
        clarity_signals = 0
        total_explanations = 0
        
        for i, turn in enumerate(turns):
            agent_msg = (turn.get("agent_response", "") or "").lower()
            
            # Assume long agent messages are explanations
            if len(agent_msg.split()) > 50:
                total_explanations += 1
                
                # Check next student response for understanding
                if i + 1 < len(turns):
                    next_student = (turns[i+1].get("student_message", "") or "").lower()
                    if any(word in next_student for word in ["forstår", "giver mening", "klart", "okay", "yes"]):
                        clarity_signals += 1
        
        if total_explanations == 0:
            return 0.5
        
        return clarity_signals / total_explanations
    
    def _assess_conceptual_coverage(self, turns: List[Dict]) -> float:
        """Assess how well concepts were covered."""
        # Count unique concepts mentioned
        concepts = set()
        for turn in turns:
            msg = (turn.get("student_message", "") + " " + 
                  turn.get("agent_response", "")).lower()
            
            # Simple keyword extraction (would use NLP in production)
            words = msg.split()
            for word in words:
                if len(word) > 8 and word.isalpha():
                    concepts.add(word)
        
        # More concepts = better coverage (up to a point)
        concept_count = len(concepts)
        if concept_count >= 20:
            return 1.0
        elif concept_count >= 10:
            return 0.7
        elif concept_count >= 5:
            return 0.5
        else:
            return 0.3
    
    def _measure_engagement(self, turns: List[Dict]) -> float:
        """Measure student engagement level."""
        engagement_indicators = 0
        
        for turn in turns:
            student_msg = (turn.get("student_message", "") or "").lower()
            
            # Active engagement signals
            if "?" in student_msg:
                engagement_indicators += 1
            if any(word in student_msg for word in ["interessant", "spændende", "mere", "hvorfor", "hvordan"]):
                engagement_indicators += 1
            if len(student_msg.split()) > 20:
                engagement_indicators += 1
        
        if not turns:
            return 0.0
        
        # Normalize by number of turns
        engagement_ratio = engagement_indicators / len(turns)
        
        return min(1.0, engagement_ratio * 2)  # Scale up
    
    def _identify_strengths(self, metrics: Dict) -> List[str]:
        """Identify conversation strengths."""
        strengths = []
        
        if metrics.get("turn_balance", 0) > 0.8:
            strengths.append("God balance mellem elev og tutor tale")
        if metrics.get("question_depth", 0) > 0.7:
            strengths.append("Eleven stiller tankevækkende spørgsmål")
        if metrics.get("explanation_clarity", 0) > 0.7:
            strengths.append("Forklaringerne virker klare og forståelige")
        if metrics.get("engagement_score", 0) > 0.7:
            strengths.append("Høj engagement fra eleven")
        
        return strengths
    
    def _identify_improvements(self, metrics: Dict) -> List[str]:
        """Identify areas for improvement."""
        improvements = []
        
        if metrics.get("turn_balance", 0) < 0.5:
            improvements.append("Opfordr eleven til at tale mere")
        if metrics.get("question_depth", 0) < 0.4:
            improvements.append("Stil åbne spørgsmål der inviterer til dybere tænkning")
        if metrics.get("explanation_clarity", 0) < 0.5:
            improvements.append("Brug flere eksempler og analogier i forklaringer")
        if metrics.get("engagement_score", 0) < 0.4:
            improvements.append("Inkluder mere interaktive elementer")
        
        return improvements
