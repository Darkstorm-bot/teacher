"""Tutor Agents - Pedagogical engines with structured decomposition and deep personalities."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum
import random
from api.core.config import AGENT_CONFIGS


# ============================================================================
# DEEP PERSONALITY SYSTEM
# ============================================================================

@dataclass
class PersonalityTraits:
    """Big Five + Teaching-specific personality dimensions (0-1 scale)."""
    
    # Big Five personality dimensions
    openness: float = 0.7          # Einstein: 0.95, Knuth: 0.85
    conscientiousness: float = 0.6  # Detail-oriented vs spontaneous
    extraversion: float = 0.5       # Feynman: 0.9, Grothendieck: 0.1
    agreeableness: float = 0.7      # Supportive vs challenging
    neuroticism: float = 0.3        # Emotional stability
    
    # Teaching-specific traits
    patience_level: float = 0.8     # How many re-explanations before frustration
    humor_frequency: float = 0.3    # How often to use jokes/analogies
    rigor_demand: float = 0.6       # How strict about precision
    abstraction_preference: float = 0.5  # Concrete (0) vs abstract (1) first
    
    # Communication style
    verbosity: float = 0.5          # Concise (0) vs verbose (1)
    socratic_ratio: float = 0.7     # Questions (1) vs statements (0)
    interruption_tolerance: float = 0.8
    feedback_directness: float = 0.6  # Gentle (0) vs direct (1)
    
    # Error response style
    error_response_type: str = "constructive"  # constructive, challenging, supportive
    
    def openness_description(self) -> str:
        if self.openness > 0.8:
            "meget åben for nye ideer og utraditionelle tilgange"
        elif self.openness > 0.5:
            return "åben for nye ideer men foretrækker beviste metoder"
        return "forsigtig med nye ideer, foretrækker traditionelle tilgange"
    
    def patience_description(self) -> str:
        if self.patience_level > 0.8:
            return "meget tålmodig og giver gerne mange forklaringer"
        elif self.patience_level > 0.5:
            return "tålmodig men forventer aktiv indsats fra eleven"
        return "kræver at eleven tænker selv før hjælp gives"
    
    def humor_description(self) -> str:
        if self.humor_frequency > 0.6:
            return "ofte humoristisk med vittigheder og sjove analogier"
        elif self.humor_frequency > 0.3:
            return "bruger lejlighedsvis humor til at gøre det mere engagerende"
        return "alvorlig og fokuseret på fagligt indhold"
    
    def socratic_description(self) -> str:
        pct = int(self.socratic_ratio * 100)
        return f"stiller spørgsmål {pct}% af tiden fremfor at give direkte svar"
    
    def error_response_style(self) -> str:
        styles = {
            "constructive": "påpeger fejl konstruktivt og hjælper med at forstå hvorfor",
            "challenging": "bruger fejl som læringsmulighed ved at udfordre eleven",
            "supportive": "opmuntrer og understreger at fejl er en naturlig del af læring"
        }
        return styles.get(self.error_response_type, styles["constructive"])


# Pre-defined personality profiles inspired by famous educators/scientists
PERSONALITY_PROFILES = {
    "einstein": PersonalityTraits(
        openness=0.95, conscientiousness=0.6, extraversion=0.6,
        agreeableness=0.8, neuroticism=0.2,
        patience_level=0.9, humor_frequency=0.5, rigor_demand=0.7,
        abstraction_preference=0.8, verbosity=0.6, socratic_ratio=0.8,
        error_response_type="constructive"
    ),
    "feynman": PersonalityTraits(
        openness=0.9, conscientiousness=0.5, extraversion=0.9,
        agreeableness=0.7, neuroticism=0.3,
        patience_level=0.85, humor_frequency=0.8, rigor_demand=0.8,
        abstraction_preference=0.3, verbosity=0.7, socratic_ratio=0.9,
        error_response_type="challenging"
    ),
    "knuth": PersonalityTraits(
        openness=0.85, conscientiousness=0.95, extraversion=0.3,
        agreeableness=0.6, neuroticism=0.2,
        patience_level=0.95, humor_frequency=0.2, rigor_demand=0.95,
        abstraction_preference=0.7, verbosity=0.8, socratic_ratio=0.6,
        error_response_type="constructive"
    ),
    "montessori": PersonalityTraits(
        openness=0.8, conscientiousness=0.7, extraversion=0.5,
        agreeableness=0.9, neuroticism=0.2,
        patience_level=0.95, humor_frequency=0.4, rigor_demand=0.5,
        abstraction_preference=0.2, verbosity=0.4, socratic_ratio=0.85,
        error_response_type="supportive"
    ),
    "socrates": PersonalityTraits(
        openness=0.7, conscientiousness=0.8, extraversion=0.7,
        agreeableness=0.5, neuroticism=0.3,
        patience_level=0.9, humor_frequency=0.3, rigor_demand=0.9,
        abstraction_preference=0.6, verbosity=0.3, socratic_ratio=0.95,
        error_response_type="challenging"
    ),
}


@dataclass
class PedagogicalStep:
    """A single step in a pedagogical decomposition."""
    step_number: int
    step_type: str
    description: str
    prompt_template: str
    expected_duration_minutes: int = 5
    branching_conditions: Dict[str, str] = field(default_factory=dict)
    success_criteria: List[str] = field(default_factory=list)
    
    def instantiate(self, topic: str, level: str, student_profile: Dict) -> str:
        """Instantiate the step template with specific values."""
        template = self.prompt_template
        return (template
                .replace("{topic}", topic)
                .replace("{level}", level)
                .replace("{student_name}", student_profile.get("name", "Elev"))
                .replace("{step_num}", str(self.step_number)))


@dataclass
class PedagogicalPlan:
    """Complete learning path for a topic."""
    topic: str
    agent_id: str
    student_id: str
    steps: List[PedagogicalStep] = field(default_factory=list)
    current_step: int = 0
    completed_steps: List[int] = field(default_factory=list)
    branch_taken: Optional[str] = None
    estimated_total_minutes: int = 30
    
    def add_step(self, step: PedagogicalStep):
        self.steps.append(step)
        self.estimated_total_minutes += step.expected_duration_minutes
    
    def get_current_step(self) -> Optional[PedagogicalStep]:
        if self.current_step < len(self.steps):
            return self.steps[self.current_step]
        return None
    
    def advance(self) -> bool:
        if self.current_step < len(self.steps) - 1:
            self.completed_steps.append(self.current_step)
            self.current_step += 1
            return True
        return False
    
    def is_complete(self) -> bool:
        return self.current_step >= len(self.steps)


@dataclass
class AgentResponse:
    text: str
    agent_id: str
    agent_name: str
    topic: str
    subtopic: Optional[str] = None
    teaching_state: str = "EXPLAINING"
    protocol: str = "DIRECT_TUTORING"
    contains_analogy: bool = False
    contains_math: bool = False
    suggested_followup: Optional[str] = None
    personality_traits: Optional[PersonalityTraits] = None
    stance: Optional[str] = None  # For panel discussions
    pedagogical_step: Optional[int] = None
    confidence_score: float = 1.0
    sources: List[Dict] = field(default_factory=list)


class TutorAgent:
    """Base class for all tutor agents with deep personality support."""

    def __init__(self, agent_id: str, personality_profile: str = None):
        self.agent_id = agent_id
        self.config = AGENT_CONFIGS.get(agent_id, {})
        self.name = self.config.get("name", agent_id)
        self.philosophy = self.config.get("philosophy", "")
        self.method = self.config.get("method", "")
        self.steps = self.config.get("steps", [])
        self.color = self.config.get("color", "#58a6ff")
        self.icon = self.config.get("icon", "🤖")
        
        # Deep personality
        if personality_profile and personality_profile in PERSONALITY_PROFILES:
            self.personality = PERSONALITY_PROFILES[personality_profile]
        else:
            self.personality = self._create_default_personality()
        
        # Pedagogical strategies per domain
        self.decomposition_strategies = self._load_decomposition_strategies()
        
        # Current pedagogical plan
        self.current_plan: Optional[PedagogicalPlan] = None

    def _create_default_personality(self) -> PersonalityTraits:
        """Create default personality based on agent domain."""
        defaults = {
            "matematik": PersonalityTraits(
                conscientiousness=0.8, rigor_demand=0.8, abstraction_preference=0.6,
                patience_level=0.85, socratic_ratio=0.7
            ),
            "fysik": PersonalityTraits(
                openness=0.85, humor_frequency=0.5, abstraction_preference=0.4,
                socratic_ratio=0.8, error_response_type="challenging"
            ),
            "datalogi": PersonalityTraits(
                conscientiousness=0.75, patience_level=0.9, verbosity=0.6,
                humor_frequency=0.4, error_response_type="constructive"
            ),
            "kommunikation": PersonalityTraits(
                agreeableness=0.8, extraversion=0.7, verbosity=0.7,
                socratic_ratio=0.75, feedback_directness=0.7
            ),
        }
        return defaults.get(self.agent_id, PersonalityTraits())

    def _load_decomposition_strategies(self) -> Dict:
        """Load agent-specific pedagogical decomposition strategies."""
        strategies = {
            "matematik": {
                "concrete_to_abstract": [
                    PedagogicalStep(1, "REAL_WORLD_EXAMPLE", 
                                   "Start med dagligdags eksempel",
                                   "Lad os starte med et eksempel fra hverdagen: {topic} kan ses i..."),
                    PedagogicalStep(2, "VISUALIZATION",
                                   "Visualiser problemet",
                                   "Forestil dig grafen/diagrammet for {topic}. Hvad viser den?"),
                    PedagogicalStep(3, "PATTERN_RECOGNITION",
                                   "Identificer mønsteret",
                                   "Hvad er det gennemgående mønster du kan se i {topic}?"),
                    PedagogicalStep(4, "FORMAL_NOTATION",
                                   "Indfør formel notation",
                                   "Matematikere skriver dette som... {topic}"),
                    PedagogicalStep(5, "GUIDED_PRACTICE",
                                   "Øv sammen",
                                   "Lad os løse et eksempel sammen trin for trin..."),
                    PedagogicalStep(6, "GENERALIZATION",
                                   "Generaliser reglen",
                                   "Hvad er den generelle regel vi har fundet?"),
                ],
                "spiral_progression": {
                    "cycles": [
                        {"depth": 1, "focus": "intuition", "rigor": 0.2},
                        {"depth": 2, "focus": "procedure", "rigor": 0.5},
                        {"depth": 3, "focus": "proof", "rigor": 0.9},
                    ]
                }
            },
            "fysik": {
                "thought_experiment_first": [
                    PedagogicalStep(1, "PHENOMENON_DEMONSTRATION",
                                   "Vis fænomenet",
                                   "Har du nogensinde lagt mærke til at... {topic}?"),
                    PedagogicalStep(2, "STUDENT_PREDICTION",
                                   "Aktivér forforståelse",
                                   "Hvad tror du sker hvis...? Forklar din tankegang."),
                    PedagogicalStep(3, "THOUGHT_EXPERIMENT",
                                   "Tankeeksperiment",
                                   "Lad os lave et tankeeksperiment: Forestil dig at..."),
                    PedagogicalStep(4, "PRINCIPLE_EXTRACTION",
                                   "Udled princippet",
                                   "Det fysiske princip bag dette er..."),
                    PedagogicalStep(5, "MATHEMATICAL_FORMULATION",
                                   "Matematisk formulering",
                                   "Dette kan beskrives matematisk som..."),
                    PedagogicalStep(6, "REAL_WORLD_APPLICATION",
                                   "Anvendelse i virkeligheden",
                                   "Dette bruges i virkeligheden til..."),
                ]
            },
            "datalogi": {
                "build_to_understand": [
                    PedagogicalStep(1, "FINAL_PRODUCT_SHOWCASE",
                                   "Vis slutproduktet",
                                   "Vi skal bygge dette: {topic}. Se hvad det kan gøre."),
                    PedagogicalStep(2, "DECOMPOSITION",
                                   "Nedbryd i delproblemer",
                                   "Lad os dele {topic} op i mindre dele..."),
                    PedagogicalStep(3, "MVP_IMPLEMENTATION",
                                   "Byg den simpleste version",
                                   "Først laver vi den mest basale version..."),
                    PedagogicalStep(4, "DEBUGGING_SESSION",
                                   "Fejlretning som læring",
                                   "Der er en bug her - kan du finde den?"),
                    PedagogicalStep(5, "ITERATIVE_ENHANCEMENT",
                                   "Forbedr gradvist",
                                   "Nu tilføjer vi flere funktioner..."),
                    PedagogicalStep(6, "PATTERN_ABSTRACTION",
                                   "Find mønsteret",
                                   "Hvad er det generelle mønster vi kan bruge igen?"),
                ]
            },
            "kommunikation": {
                "analyse_produce_reflect": [
                    PedagogicalStep(1, "AUTHENTIC_EXAMPLE",
                                   "Autentisk eksempel",
                                   "Her er et rigtigt eksempel på {topic} fra danske medier..."),
                    PedagogicalStep(2, "ANALYSIS_GUIDED",
                                   "Analyser sammen",
                                   "Hvad er afsenderens hensigt med dette? Hvilke virkemidler bruges?"),
                    PedagogicalStep(3, "DEVICE_IDENTIFICATION",
                                   "Identificer virkemidler",
                                   "Kan du finde eksempler på retoriske/visuelle virkemidler?"),
                    PedagogicalStep(4, "PRODUCTION_SCAFFOLDED",
                                   "Lav din egen version",
                                   "Prøv at skrive/lave din egen version af..."),
                    PedagogicalStep(5, "PEER_REVIEW",
                                   "Feedback som sensor",
                                   "Her er feedback på din produktion..."),
                    PedagogicalStep(6, "REVISION",
                                   "Revider og forbedr",
                                   "Brug feedbacken til at forbedre dit arbejde..."),
                ]
            },
        }
        return strategies.get(self.agent_id, {})

    def build_personality_prompt(self) -> str:
        """Build detailed personality description for system prompt."""
        p = self.personality
        return f"""
DIN PERSONLIGHED SOM {self.name}:
- Du er {p.openness_description()}
- Din tålmodighedsniveau: {p.patience_description()}
- Humor: {p.humor_description()}
- Dialogstil: {p.socratic_description()}
- Ved fejl: {p.error_response_style()}
- Du er {'meget detaljeorienteret' if p.conscientiousness > 0.7 else 'mere fleksibel'} omkring præcision
- Du foretrækker at starte {'med abstrakte koncepter' if p.abstraction_preference > 0.6 else 'med konkrete eksempler'}
- Din kommunikationsstil er {'detaljeret og udførlig' if p.verbosity > 0.6 else 'koncis og fokuseret'}
"""

    def build_system_prompt(self, context: str, level: str = "B",
                            current_state: str = "EXPLAINING") -> str:
        """Build comprehensive system prompt with personality and pedagogy."""
        prompt = f"""Du er {self.name}, en dansk HF-tutor specialiseret i dit fag.
{self.build_personality_prompt()}

DIN UNDERVISNINGSFILOSOFI:
- {self.philosophy}
- {self.method}

DIN PÆDAGOGISKE TILGANG:
"""
        for step in self.steps:
            prompt += f"{step}\n"

        prompt += f"""
VIKTIGE REGLER:
1. Svar ALTID på dansk, medmindre eleven specifikt spørger på engelsk.
2. Tilpas svarets sværhedsgrad til {level}-niveau i den danske HF-læreplan.
3. Vær opmuntrende men krævende. Stil opfølgningsspørgsmål.
4. Brug konkrete danske eksempler når muligt.
5. Referer til HF-pensum og eksamensformater.
6. Hvis du ikke er sikker på noget, sig det ærligt.
7. Følg din personlighedsprofil i alle interaktioner.

{self._get_agent_specific_rules()}

KONTEKST FRA TIDIGERE SAMTALER:
{context}

AKTUEL UNDERVISNINGSSTATE: {current_state}

Svar som {self.name}. Vær pedagogisk, tålmodig og engageret. Husk din unikke personlighed!"""
        return prompt

    def _get_agent_specific_rules(self) -> str:
        """Override in subclasses for agent-specific rules."""
        return ""

    def decompose_topic(self, topic: str, student_level: str,
                       student_profile: Dict) -> PedagogicalPlan:
        """Create dynamic pedagogical plan for a topic."""
        plan = PedagogicalPlan(
            topic=topic,
            agent_id=self.agent_id,
            student_id=student_profile.get("id", "unknown")
        )
        
        # Select strategy based on agent and topic complexity
        strategy_name = self._select_strategy(topic, student_level)
        strategy = self.decomposition_strategies.get(strategy_name, [])
        
        if isinstance(strategy, dict) and "cycles" in strategy:
            # Spiral progression - adjust based on level
            cycles = strategy["cycles"]
            target_cycle = min(len(cycles) - 1, 
                              {"C": 0, "B": 1, "A": 2}.get(student_level, 1))
            cycle = cycles[target_cycle]
            
            # Create adapted steps for this cycle
            for i, base_step in enumerate(self.decomposition_strategies.get(
                    "concrete_to_abstract", [])):
                adapted = PedagogicalStep(
                    step_number=i+1,
                    step_type=base_step.step_type,
                    description=base_step.description,
                    prompt_template=base_step.prompt_template,
                    expected_duration_minutes=int(base_step.expected_duration_minutes * 
                                                  (0.5 + cycle["rigor"]))
                )
                plan.add_step(adapted)
        else:
            # Standard linear progression
            for step in strategy:
                plan.add_step(step)
        
        self.current_plan = plan
        return plan

    def _select_strategy(self, topic: str, level: str) -> str:
        """Select best pedagogical strategy for topic and level."""
        # Default to first available strategy
        if self.decomposition_strategies:
            if isinstance(list(self.decomposition_strategies.keys())[0], str):
                return list(self.decomposition_strategies.keys())[0]
        return "concrete_to_abstract"

    def format_response(self, raw_text: str, topic: str, subtopic: str = None,
                        protocol: str = "DIRECT_TUTORING",
                        stance: str = None) -> AgentResponse:
        """Format raw LLM response into structured agent response."""
        contains_analogy = any(word in raw_text.lower() for word in
                                ["analogi", "som", "ligesom", "tænk på", "forestil dig"])
        contains_math = any(symbol in raw_text for symbol in
                            ["$", "\\", "∫", "∂", "Σ", "√", "²", "³"])

        return AgentResponse(
            text=raw_text,
            agent_id=self.agent_id,
            agent_name=self.name,
            topic=topic,
            subtopic=subtopic,
            protocol=protocol,
            contains_analogy=contains_analogy,
            contains_math=contains_math,
            personality_traits=self.personality,
            stance=stance,
            pedagogical_step=self.current_plan.current_step if self.current_plan else None,
        )


class MatematikAgent(TutorAgent):
    """Matematik Tutor - C → B → A progression."""

    def __init__(self, personality_profile: str = "einstein"):
        super().__init__("matematik", personality_profile)

    def _get_agent_specific_rules(self) -> str:
        return """MATEMATIK-SPECIFIKKE REGLER:
- Start med et konkret dansk eksempel (DSB togpriser, Netto tilbud, cykelture)
- Vis graf eller tabel før formel
- Brug SI-enheder og dansk matematisk notation
- Reference HF eksamensspørgsmålsformater
- Trin-for-trin løsninger, ikke bare svar
- Forbind matematik til fysik når det giver mening"""

    def get_level_prompt(self, level: str) -> str:
        prompts = {
            "C": "Du underviser på C-niveau: fokuser på funktioner, lineære modeller, procentregning og deskriptiv statistik. Brug simple tal og visualisering.",
            "B": "Du underviser på B-niveau: fokuser på differentialregning, vektorer, sandsynlighedsregning og trigonometri. Vis mellemregninger.",
            "A": "Du underviser på A-niveau: fokuser på integralregning, differentialligninger, beviser og statistisk hypotesetest. Kræv matematisk præcision.",
        }
        return prompts.get(level, prompts["B"])


class FysikAgent(TutorAgent):
    """Fysik Tutor - Thought experiment first approach."""

    def __init__(self, personality_profile: str = "feynman"):
        super().__init__("fysik", personality_profile)

    def _get_agent_specific_rules(self) -> str:
        return """FYSIK-SPECIFIKKE REGLER:
- Start med fænomenet, ikke formlen
- Brug 'hvad hvis...' tankeeksperimenter
- Altid SI-enheder i beregninger
- Forbind til dansk teknologi og natur
- Forslå eksperimenter hvor muligt
- Vis at matematikken følger af fysikken, ikke omvendt"""

    def get_level_prompt(self, level: str) -> str:
        prompts = {
            "C": "Du underviser på C-niveau: mekanik, energi, simpel elektricitet. Fokuser på begrebsforståelse og simple beregninger.",
            "B": "Du underviser på B-niveau: bølger, termodynamik, atomfysik, astrofysik. Inkluder mere matematisk behandling.",
        }
        return prompts.get(level, prompts["C"])


class DatalogiAgent(TutorAgent):
    """Datalogi Tutor - Build-to-Understand approach."""

    def __init__(self, personality_profile: str = "knuth"):
        super().__init__("datalogi", personality_profile)

    def _get_agent_specific_rules(self) -> str:
        return """DATALOGI-SPECIFIKKE REGLER:
- Vis ALTID kodeeksempler, ikke bare koncepter
- Brug danske variabelnavne for begyndere, engelsk for øvede
- Kør kodeeksempler trin-for-trin
- Fejlretning er læring - forklar bugs
- Forbind til universitets-niveau (Software Engineering, AI)
- Inkluder Git, Linux CLI, SQL basics som bro-emner"""

    def get_level_prompt(self, level: str) -> str:
        prompts = {
            "C": "Du underviser på begynder-niveau: Python variabler, løkker, funktioner. Brug danske variabelnavne.",
            "B": "Du underviser på mellem-niveau: datastrukturer, algoritmer, OOP, filhåndtering.",
            "A": "Du underviser på avanceret niveau: AI/ML intro, avancerede projekter, software design patterns.",
        }
        return prompts.get(level, prompts["C"])


class KommunikationAgent(TutorAgent):
    """Kommunikation Tutor - Analyse → Produktion → Refleksion."""

    def __init__(self, personality_profile: str = "socrates"):
        super().__init__("kommunikation", personality_profile)

    def _get_agent_specific_rules(self) -> str:
        return """KOMMUNIKATION-SPECIFIKKE REGLER:
- Brug autentiske danske medieeksempler (DR, TV2, Politiken)
- Scaffolding af akademisk dansk skrivning
- Giv feedback som en HF-sensor ville gøre
- Fokuser på genrebevidsthed
- Inkluder både skriftlig og mundtlig kommunikation
- Analyser virkemidler systematisk"""

    def get_level_prompt(self, level: str) -> str:
        prompts = {
            "C": "Du underviser på C-niveau: kommunikationsmodeller, grundlæggende analyse.",
            "B": "Du underviser på B-niveau: medieanalyse, retorik, argumentation, skriftlig fremstilling.",
            "A": "Du underviser på A-niveau: avanceret analyse, akademisk skrivning, eksamensforberedelse.",
        }
        return prompts.get(level, prompts["C"])


class AgentRegistry:
    """Registry for all tutor agents with personality support."""

    def __init__(self):
        self.agents: Dict[str, TutorAgent] = {
            "matematik": MatematikAgent("einstein"),
            "fysik": FysikAgent("feynman"),
            "datalogi": DatalogiAgent("knuth"),
            "kommunikation": KommunikationAgent("socrates"),
        }

    def get_agent(self, agent_id: str) -> Optional[TutorAgent]:
        return self.agents.get(agent_id)

    def list_agents(self) -> List[str]:
        return list(self.agents.keys())

    def get_agent_info(self) -> List[Dict]:
        return [{
            "id": aid,
            "name": agent.name,
            "color": agent.color,
            "icon": agent.icon,
            "philosophy": agent.philosophy,
            "personality_summary": {
                "openness": agent.personality.openness,
                "humor": agent.personality.humor_frequency,
                "socratic": agent.personality.socratic_ratio,
                "patience": agent.personality.patience_level,
            },
            "levels": agent.config.get("levels", ["C", "B", "A"]),
        } for aid, agent in self.agents.items()]
