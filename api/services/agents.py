"""Tutor Agents - Pedagogical engines with structured decomposition."""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from api.core.config import AGENT_CONFIGS


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


class TutorAgent:
    """Base class for all tutor agents."""

    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.config = AGENT_CONFIGS.get(agent_id, {})
        self.name = self.config.get("name", agent_id)
        self.philosophy = self.config.get("philosophy", "")
        self.method = self.config.get("method", "")
        self.steps = self.config.get("steps", [])
        self.color = self.config.get("color", "#58a6ff")
        self.icon = self.config.get("icon", "🤖")

    def build_system_prompt(self, context: str, level: str = "B") -> str:
        """Build the system prompt for this agent."""
        prompt = f"""Du er {self.name}, en dansk HF-tutor specialiseret i dit fag.

DIN UNDERVISNINGSFILOSOFI:
- {self.philosophy}
- {self.method}

DIN TILGANG:
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

{self._get_agent_specific_rules()}

KONTEKST FRA TIDIGERE SAMTALER:
{context}

Svar som {self.name}. Vær pedagogisk, tålmodig og engageret."""
        return prompt

    def _get_agent_specific_rules(self) -> str:
        """Override in subclasses for agent-specific rules."""
        return ""

    def format_response(self, raw_text: str, topic: str, subtopic: str = None,
                        protocol: str = "DIRECT_TUTORING") -> AgentResponse:
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
        )


class MatematikAgent(TutorAgent):
    """Matematik Tutor - C → B → A progression."""

    def __init__(self):
        super().__init__("matematik")

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

    def __init__(self):
        super().__init__("fysik")

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

    def __init__(self):
        super().__init__("datalogi")

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

    def __init__(self):
        super().__init__("kommunikation")

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
    """Registry for all tutor agents."""

    def __init__(self):
        self.agents: Dict[str, TutorAgent] = {
            "matematik": MatematikAgent(),
            "fysik": FysikAgent(),
            "datalogi": DatalogiAgent(),
            "kommunikation": KommunikationAgent(),
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
            "levels": agent.config.get("levels", ["C", "B", "A"]),
        } for aid, agent in self.agents.items()]
