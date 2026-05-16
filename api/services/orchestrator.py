"""Orchestrator Agent - Deterministic state machine for routing and turn management."""
import re
from enum import Enum
from typing import Optional, List, Dict
from dataclasses import dataclass, field
from api.core.config import ROUTING_TABLE, AGENT_CONFIGS
from api.services.memory_palace import MemoryPalace, ContextAssembler
from api.core.database import DatabaseManager


class TeachingState(Enum):
    ASSESSING = "ASSESSING"
    SCAFFOLDING = "SCAFFOLDING"
    EXPLAINING = "EXPLAINING"
    RE_EXPLAINING = "RE_EXPLAINING"
    CHALLENGING = "CHALLENGING"
    SYNTHESIZING = "SYNTHESIZING"
    DIAGNOSING = "DIAGNOSING"
    META_REFLECTING = "META_REFLECTING"


class Protocol(Enum):
    DIRECT_TUTORING = "DIRECT_TUTORING"
    PANEL_DISCUSSION = "PANEL_DISCUSSION"
    SCAFFOLDING_HANDOFF = "SCAFFOLDING_HANDOFF"
    PEER_REVIEW = "PEER_REVIEW"


@dataclass
class AgentSelection:
    agent: str
    protocol: str = "DIRECT_TUTORING"
    agents: List[str] = field(default_factory=list)


@dataclass
class ConversationContext:
    session_id: str
    student_id: str
    current_agent: Optional[str] = None
    current_topic: Optional[str] = None
    current_state: TeachingState = TeachingState.ASSESSING
    turn_count: int = 0
    confusion_count: int = 0


class TopicClassifier:
    """Simple keyword-based topic classifier for Danish HF subjects."""

    KEYWORDS = {
        "differentialregning": ["differenti", "afledet", "tangent", "hældning", "monotoni",
                                "ekstremum", "kæderegel"],
        "integralregning": ["integral", "areal", "stamfunktion", "integralregning"],
        "vektorer": ["vektor", "prikprodukt", "krydsprodukt", "parameter"],
        "statistik": ["statistik", "middelværdi", "spredning", "kvartil", "hypotesetest"],
        "funktioner": ["funktion", "graf", "domæne", "værdimængde", "monoton"],
        "trigonometri": ["trigonometri", "sin", "cos", "tan", "enhedscirkel"],
        "sandsynlighed": ["sandsynlighed", "kombinatorik", "permutation", "binomial"],
        "mekanik": ["mekanik", "newton", "kraft", "bevægelse", "hastighed", "acceleration"],
        "termodynamik": ["termod", "varme", "temperatur", "entropi", "tilstandsligning"],
        "bølger": ["bølge", "frekvens", "bølgelængde", "interferens", "diffraktion"],
        "elektricitet": ["elektricitet", "strøm", "spænding", "modstand", "ohm"],
        "atomfysik": ["atom", "elektron", "bohr", "kvante", "niveau"],
        "energi": ["energi", "kinetisk", "potentiel", "arbejde", "effekt"],
        "python": ["python", "kode", "programmering", "funktion", "klasse", "loop"],
        "algoritmer": ["algoritme", "søgning", "sortering", "kompleksitet", "rekursion"],
        "datastrukturer": ["datastruktur", "liste", "dict", "træ", "graf", "stack"],
        "logisk_tænkning": ["logik", "boolsk", "sandhedstabel", "prædikat"],
        "argumentation": ["argument", "argumentation", "ræsonnement", "præmis", "konklusion"],
        "medieanalyse": ["medie", "analyse", "reklame", "nyhed", "kommunikation"],
        "retorik": ["retorik", "ethos", "pathos", "logos", "tale"],
        "skriftlig_fremstilling": ["skriftlig", "kronik", "essay", "fremstilling"],
    }

    CROSS_DOMAIN_INDICATORS = [
        "hvordan bruges", "sammenhæng", "forbindelse", "anvendes i",
        "relation til", "sammen med", "både og"
    ]

    CONFUSION_SIGNALS = [
        "forstår ikke", "huh", "hvad mener du", "confused", "lost",
        "kan du gentage", "ikke helt med", "forklar igen", "svært",
        "kompliceret", "svær", "forvirret", "hvordan det"
    ]

    def classify(self, message: str) -> tuple:
        """Classify message into (topic, confidence)."""
        message_lower = message.lower()
        scores = {}
        for topic, keywords in self.KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in message_lower)
            if score > 0:
                scores[topic] = score

        if not scores:
            return None, 0.0

        best_topic = max(scores, key=scores.get)
        # Normalize confidence
        max_possible = len(self.KEYWORDS[best_topic])
        confidence = min(1.0, scores[best_topic] / max(max_possible * 0.3, 1))
        return best_topic, confidence

    def is_cross_domain(self, message: str) -> bool:
        """Check if message spans multiple subjects."""
        message_lower = message.lower()
        return any(ind in message_lower for ind in self.CROSS_DOMAIN_INDICATORS)

    def detect_confusion(self, recent_turns: List[Dict]) -> bool:
        """Detect confusion signals in recent turns."""
        if not recent_turns:
            return False
        # Check last student messages for confusion signals
        confusion_count = 0
        for turn in recent_turns[-3:]:
            msg = (turn.get("student_message", "") or "").lower()
            if any(sig in msg for sig in self.CONFUSION_SIGNALS):
                confusion_count += 1
        return confusion_count >= 1

    def detect_explicit_agent(self, message: str) -> Optional[str]:
        """Detect if student explicitly mentions an agent."""
        patterns = {
            "matematik": [r"matematik", r"mat(-|\s)?tutor", r"mat(-|\s)?agent"],
            "fysik": [r"fysik", r"fys(-|\s)?tutor", r"fys(-|\s)?agent"],
            "datalogi": [r"datalogi", r"programmering", r"python(-|\s)?tutor", r"it-tutor"],
            "kommunikation": [r"kommunikation", r"komm(-|\s)?tutor", r"medie(-|\s)?tutor"],
        }
        message_lower = message.lower()
        for agent, patterns_list in patterns.items():
            for pattern in patterns_list:
                if re.search(pattern, message_lower):
                    return agent
        return None


class Orchestrator:
    """Deterministic orchestrator for multi-agent tutoring."""

    def __init__(self):
        self.classifier = TopicClassifier()
        self.memory = MemoryPalace()
        self.context_assembler = ContextAssembler(self.memory)
        self.db = DatabaseManager()
        self.contexts: Dict[str, ConversationContext] = {}

    def get_or_create_context(self, session_id: str, student_id: str) -> ConversationContext:
        """Get or create conversation context."""
        if session_id not in self.contexts:
            self.contexts[session_id] = ConversationContext(
                session_id=session_id,
                student_id=student_id
            )
        return self.contexts[session_id]

    def route(self, message: str, context: ConversationContext) -> AgentSelection:
        """Route message to appropriate agent."""
        # 1. Check explicit agent mention
        explicit = self.classifier.detect_explicit_agent(message)
        if explicit:
            return AgentSelection(agent=explicit, protocol=Protocol.DIRECT_TUTORING.value)

        # 2. Topic classification
        topic, confidence = self.classifier.classify(message)

        # 3. Cross-domain detection
        if self.classifier.is_cross_domain(message):
            if topic:
                primary = ROUTING_TABLE.get(topic, "matematik")
                # Get related agents
                agents = [primary]
                if "python" in message.lower() or "kode" in message.lower():
                    if "datalogi" not in agents:
                        agents.append("datalogi")
                if "fysik" in message.lower() or "mekanik" in message.lower():
                    if "fysik" not in agents:
                        agents.append("fysik")
                return AgentSelection(
                    agent=primary,
                    protocol=Protocol.PANEL_DISCUSSION.value,
                    agents=agents
                )

        # 4. Confusion detection → handoff to complementary tutor
        recent_turns = self.db.get_recent_turns(context.session_id, k=3)
        if self.classifier.detect_confusion(recent_turns):
            context.confusion_count += 1
            if context.confusion_count >= 2 and context.current_agent:
                alt = self._get_complementary_agent(context.current_agent)
                return AgentSelection(
                    agent=alt,
                    protocol=Protocol.SCAFFOLDING_HANDOFF.value
                )

        # 5. Standard routing
        if topic and confidence > 0.3:
            agent = ROUTING_TABLE.get(topic, context.current_agent or "matematik")
        else:
            agent = context.current_agent or "matematik"

        # Check for complex topic that might benefit from peer review
        if topic in ["differentialregning", "integralregning", "atomfysik"] and confidence > 0.7:
            return AgentSelection(agent=agent, protocol=Protocol.PEER_REVIEW.value)

        return AgentSelection(agent=agent, protocol=Protocol.DIRECT_TUTORING.value)

    def _get_complementary_agent(self, current_agent: str) -> str:
        """Get a complementary agent for scaffolding handoff."""
        complements = {
            "matematik": "fysik",
            "fysik": "matematik",
            "datalogi": "matematik",
            "kommunikation": "datalogi",
        }
        return complements.get(current_agent, "matematik")

    def update_state(self, context: ConversationContext, student_message: str,
                     agent_response: str, topic: str) -> TeachingState:
        """Update teaching state based on interaction."""
        msg_lower = student_message.lower()

        # Check for understanding signals
        understanding_signals = ["forstår", "giver mening", "klart", "selvfølgelig",
                                  "okay", "got it", "check", "yes", "ja", "rigtigt"]
        confusion_signals = ["forstår ikke", "huh", "hvad", "forvirret",
                            "ikke helt", "gentag", "svært"]

        has_understanding = any(s in msg_lower for s in understanding_signals)
        has_confusion = any(s in msg_lower for s in confusion_signals)

        current = context.current_state

        if current == TeachingState.ASSESSING:
            if has_confusion:
                return TeachingState.SCAFFOLDING
            return TeachingState.EXPLAINING

        elif current == TeachingState.SCAFFOLDING:
            if has_understanding:
                return TeachingState.EXPLAINING
            return TeachingState.SCAFFOLDING

        elif current == TeachingState.EXPLAINING:
            if has_confusion:
                return TeachingState.RE_EXPLAINING
            if has_understanding:
                return TeachingState.CHALLENGING
            return TeachingState.EXPLAINING

        elif current == TeachingState.RE_EXPLAINING:
            if has_understanding:
                return TeachingState.CHALLENGING
            return TeachingState.DIAGNOSING

        elif current == TeachingState.CHALLENGING:
            if has_confusion:
                return TeachingState.DIAGNOSING
            if has_understanding:
                return TeachingState.SYNTHESIZING
            return TeachingState.CHALLENGING

        elif current == TeachingState.SYNTHESIZING:
            return TeachingState.META_REFLECTING

        elif current == TeachingState.DIAGNOSING:
            if has_understanding:
                return TeachingState.EXPLAINING
            return TeachingState.SCAFFOLDING

        elif current == TeachingState.META_REFLECTING:
            return TeachingState.ASSESSING

        return TeachingState.EXPLAINING

    def detect_subtopic(self, topic: str, message: str) -> Optional[str]:
        """Detect subtopic within a main topic."""
        subtopic_keywords = {
            "differentialregning": {
                "kædereglen": ["kæderegel", "sammensat", "kæde"],
                "tangenter": ["tangent", "tangentligning"],
                "monotoni": ["monoton", "voksende", "aftagende"],
            },
            "integralregning": {
                "stamfunktion": ["stamfunktion", "antideriveret"],
                "areal": ["areal", "område"],
            },
            "mekanik": {
                "newtons_love": ["newton", "kraft"],
                "bevægelse": ["bevægelse", "hastighed", "acceleration"],
            },
            "python": {
                "funktioner": ["funktion", "def"],
                "klasser": ["klasse", "class", "oop"],
                "løkker": ["løkke", "loop", "for", "while"],
            },
        }

        if topic not in subtopic_keywords:
            return None

        msg_lower = message.lower()
        for subtopic, keywords in subtopic_keywords[topic].items():
            if any(kw in msg_lower for kw in keywords):
                return subtopic

        return None
