"""Panel Discussion Engine - True multi-agent conversations where tutors talk to EACH OTHER."""
import asyncio
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum
import random

from api.services.agents import TutorAgent, AgentResponse, PersonalityTraits, AgentRegistry
from api.services.llm import OllamaClient as LLMClient
from api.services.memory_palace import MemoryPalace


class PanelStance(Enum):
    """How an agent responds to previous statements in panel discussion."""
    INITIAL_STATEMENT = "INITIAL_STATEMENT"
    AGREE_AND_EXTEND = "AGREE_AND_EXTEND"
    RESPECTFUL_DISAGREEMENT = "RESPECTFUL_DISAGREEMENT"
    ASK_CLARIFYING_QUESTION = "ASK_CLARIFYING_QUESTION"
    PROVIDE_COUNTEREXAMPLE = "PROVIDE_COUNTEREXAMPLE"
    SUPPORTIVE_ECHO = "SUPPORTIVE_ECHO"
    SYNTHESIZE = "SYNTHESIZE"


@dataclass
class PanelStatement:
    """A single statement in a panel discussion."""
    agent_id: str
    agent_name: str
    response: str
    stance: PanelStance
    round_num: int
    refers_to_agent: Optional[str] = None
    confidence_score: float = 1.0
    contains_math: bool = False
    contains_analogy: bool = False


@dataclass
class PanelDiscussionResult:
    """Complete result of a panel discussion."""
    topic: str
    student_query: str
    statements: List[PanelStatement] = field(default_factory=list)
    consensus_reached: bool = False
    synthesis: Optional[str] = None
    rounds_completed: int = 0
    participating_agents: List[str] = field(default_factory=list)


class PanelDiscussionEngine:
    """
    Manages real multi-agent conversations where tutors talk to EACH OTHER.
    
    Simulates a roundtable where:
    1. Moderator (orchestrator) poses question
    2. Primary agent responds
    3. Other agents can:
       - AGREE_AND_EXTEND: "Yes, and additionally..."
       - DISAGREE_RESPECTFULLY: "I see it differently..."
       - ASK_CLARIFICATION: "But how does that account for...?"
       - PROVIDE_COUNTEREXAMPLE: "What about when..."
    4. Student observes the debate
    5. Synthesis agent summarizes consensus
    """
    
    def __init__(self, agent_registry: AgentRegistry = None):
        self.agent_registry = agent_registry or AgentRegistry()
        self.llm = LLMClient()
        self.memory = MemoryPalace()
        
        # Stance determination prompts per stance type
        self.stance_prompts = {
            PanelStance.AGREE_AND_EXTEND: 
                "Du er enig men vil tilføje noget vigtigt. Start med 'Ja, og...' eller 'Det er rigtigt, og derudover...'",
            PanelStance.RESPECTFUL_DISAGREEMENT:
                "Du ser det lidt anderledes. Vær respektfuld men tydelig. Start med 'Jeg forstår dit synspunkt, men...' eller 'Fra mit fags perspektiv...'",
            PanelStance.ASK_CLARIFYING_QUESTION:
                "Du har opdaget en uklarhed eller et hul i ræsonnementet. Stil et præcist spørgsmål.",
            PanelStance.PROVIDE_COUNTEREXAMPLE:
                "Du kender et tilfælde hvor den tidligere forklaring ikke holder. Præsenter det klart.",
            PanelStance.SUPPORTIVE_ECHO:
                "Du styrker pointen med et andet eksempel eller analogi fra dit fagområde.",
        }
    
    async def run_panel(self, topic: str, student_query: str, 
                       agent_ids: List[str], max_rounds: int = 3,
                       student_level: str = "B") -> PanelDiscussionResult:
        """
        Run a full panel discussion with multiple agents.
        
        Args:
            topic: Main topic being discussed
            student_query: Original student question
            agent_ids: List of agent IDs to participate
            max_rounds: Maximum number of discussion rounds
            student_level: HF level (C, B, A)
        
        Returns:
            PanelDiscussionResult with all statements and synthesis
        """
        result = PanelDiscussionResult(
            topic=topic,
            student_query=student_query,
            participating_agents=agent_ids
        )
        
        conversation_history: List[PanelStatement] = []
        
        for round_num in range(max_rounds):
            round_statements = []
            
            for agent_id in agent_ids:
                # Build context for this agent
                context = self._build_panel_context(
                    topic=topic,
                    student_query=student_query,
                    previous_statements=conversation_history,
                    current_speaker=agent_id,
                    current_round=round_num
                )
                
                # Determine stance based on conversation history
                if not conversation_history:
                    stance = PanelStance.INITIAL_STATEMENT
                else:
                    stance = await self._determine_stance(
                        agent_id=agent_id,
                        history=conversation_history,
                        topic=topic
                    )
                
                # Generate response with appropriate stance
                response = await self._generate_panel_response(
                    agent_id=agent_id,
                    context=context,
                    stance=stance,
                    topic=topic,
                    level=student_level
                )
                
                statement = PanelStatement(
                    agent_id=agent_id,
                    agent_name=self.agent_registry.get_agent(agent_id).name,
                    response=response,
                    stance=stance,
                    round_num=round_num,
                    refers_to_agent=conversation_history[-1].agent_id if conversation_history else None,
                    contains_math=any(s in response for s in ["$", "\\", "∫", "∂"]),
                    contains_analogy=any(w in response.lower() for w in ["analogi", "som", "ligesom"])
                )
                
                round_statements.append(statement)
                conversation_history.append(statement)
                
                # Check if consensus reached
                if self._check_consensus(conversation_history):
                    result.consensus_reached = True
                    break
            
            result.statements = conversation_history.copy()
            result.rounds_completed = round_num + 1
            
            if result.consensus_reached:
                break
        
        # Generate synthesis
        result.synthesis = await self._synthesize_debate(conversation_history, topic, student_level)
        
        return result
    
    def _build_panel_context(self, topic: str, student_query: str,
                            previous_statements: List[PanelStatement],
                            current_speaker: str, current_round: int) -> str:
        """Build context for panel participant."""
        context_parts = [
            f"EMNE: {topic}",
            f"ELEVEN SPØRGER: {student_query}",
            f"\n=== SAMTALEHISTORIK ({len(previous_statements)} indlæg hidtil) ===\n"
        ]
        
        if previous_statements:
            for stmt in previous_statements:
                context_parts.append(
                    f"[{stmt.agent_name}]: {stmt.response[:300]}{'...' if len(stmt.response) > 300 else ''}"
                )
        else:
            context_parts.append("(Ingen tidligere indlæg - du starter diskussionen)")
        
        context_parts.append(f"\nRUNDE: {current_round + 1}")
        context_parts.append(f"DIN ROLLE: {current_speaker}")
        
        return "\n".join(context_parts)
    
    async def _determine_stance(self, agent_id: str, 
                               history: List[PanelStatement],
                               topic: str) -> PanelStance:
        """
        Determine how agent should respond based on conversation history.
        
        Uses heuristic rules combined with LLM judgment.
        """
        if not history:
            return PanelStance.INITIAL_STATEMENT
        
        last_statement = history[-1]
        last_agent = last_statement.agent_id
        
        # Get agent personalities
        current_agent = self.agent_registry.get_agent(agent_id)
        previous_agent = self.agent_registry.get_agent(last_agent)
        
        if not current_agent or not previous_agent:
            return PanelStance.SUPPORTIVE_ECHO
        
        # Rule 1: Check for conceptual conflict between domains
        if self._has_conceptual_conflict(agent_id, last_agent, last_statement):
            return PanelStance.RESPECTFUL_DISAGREEMENT
        
        # Rule 2: Can extend conceptually?
        if self._can_extend_conceptually(agent_id, last_statement):
            return PanelStance.AGREE_AND_EXTEND
        
        # Rule 3: Detect gap in reasoning
        if self._detects_gap_in_reasoning(last_statement):
            return PanelStance.ASK_CLARIFYING_QUESTION
        
        # Rule 4: Has counterexample?
        if self._has_counterexample(agent_id, last_statement):
            return PanelStance.PROVIDE_COUNTEREXAMPLE
        
        # Default: Supportive echo with different perspective
        return PanelStance.SUPPORTIVE_ECHO
    
    def _has_conceptual_conflict(self, agent_id: str, last_agent: str,
                                 statement: PanelStatement) -> bool:
        """Check if there's intellectual tension between agents' perspectives."""
        conflicts = {
            ("matematik", "fysik"): ["approach", "rigor", "abstraction"],
            ("fysik", "datalogi"): ["modeling", "simulation"],
            ("datalogi", "matematik"): ["proof", "algorithm"],
        }
        
        pair = (agent_id, last_agent)
        reverse_pair = (last_agent, agent_id)
        
        # Check for known conflict areas
        if pair in conflicts or reverse_pair in conflicts:
            # Look for trigger words
            triggers = conflicts.get(pair) or conflicts.get(reverse_pair) or []
            return any(trigger in statement.response.lower() for trigger in triggers)
        
        return False
    
    def _can_extend_conceptually(self, agent_id: str,
                                statement: PanelStatement) -> bool:
        """Check if agent can meaningfully extend the previous statement."""
        extension_patterns = {
            "matematik": ["formel", "bevis", "struktur", "mønster"],
            "fysik": ["eksperiment", "observation", "natur", "fænomen"],
            "datalogi": ["implementering", "algoritme", "kode", "system"],
            "kommunikation": ["formidling", "forståelse", "perspektiv", "analyse"],
        }
        
        patterns = extension_patterns.get(agent_id, [])
        return any(pattern in statement.response.lower() for pattern in patterns)
    
    def _detects_gap_in_reasoning(self, statement: PanelStatement) -> bool:
        """Detect if there's a logical gap or unclear point."""
        gap_indicators = [
            "antager vi", "uden at vise", "det følger at",
            "naturligvis", "selvfølgelig", "det er klart"
        ]
        return any(indicator in statement.response.lower() for indicator in gap_indicators)
    
    def _has_counterexample(self, agent_id: str,
                           statement: PanelStatement) -> bool:
        """Check if agent has a relevant counterexample."""
        # This would ideally check against knowledge base
        # For now, use simple heuristic
        counterexample_triggers = ["altid", "alle", "ingen", "hver", "enhver"]
        return any(trigger in statement.response.lower() for trigger in counterexample_triggers)
    
    async def _generate_panel_response(self, agent_id: str, context: str,
                                       stance: PanelStance, topic: str,
                                       level: str) -> str:
        """Generate response with specific stance."""
        agent = self.agent_registry.get_agent(agent_id)
        if not agent:
            return "Fejl: Agent ikke fundet."
        
        stance_instruction = self.stance_prompts.get(
            stance, 
            "Bidrag til diskussionen på en konstruktiv måde."
        )
        
        prompt = f"""{context}

=== DINE INSTRUKTIONER ===
{stance_instruction}

VIKTIGT:
- Bevar din personlighed ({agent.name})
- Tilpas til {level}-niveau
- Hold dit indlæg koncist (max 200 ord)
- Referer til hvad den/de tidligere talere sagde
- Brug dit fags specifikke perspektiv

SVAR SOM {agent.name}:"""
        
        try:
            response = await self.llm.generate(prompt, temperature=0.7)
            return response.strip()
        except Exception as e:
            return f"[Fejl i panel-generering: {str(e)}]"
    
    def _check_consensus(self, statements: List[PanelStatement]) -> bool:
        """Check if panel has reached consensus."""
        if len(statements) < 3:
            return False
        
        # Simple heuristic: last 3 statements all agree or extend
        recent = statements[-3:]
        agreement_stances = [
            PanelStance.AGREE_AND_EXTEND,
            PanelStance.SUPPORTIVE_ECHO,
            PanelStance.SYNTHESIZE
        ]
        
        agreement_count = sum(1 for s in recent if s.stance in agreement_stances)
        return agreement_count >= 2
    
    async def _synthesize_debate(self, statements: List[PanelStatement],
                                topic: str, level: str) -> str:
        """Generate synthesis of panel discussion."""
        if not statements:
            return "Ingen diskussion fandt sted."
        
        # Format statements for synthesis
        summary_parts = []
        for stmt in statements:
            summary_parts.append(f"{stmt.agent_name}: {stmt.response[:150]}...")
        
        prompt = f"""OPGAVE: Opsummer paneldebatten og giv en konklusion til eleven.

EMNE: {topic}
NIVEAU: {level}

DEBATOVERSIGT:
{chr(10).join(summary_parts)}

SKRIV EN KONKLUSION DER:
1. Opsummerer de vigtigste pointer alle var enige om
2. Nævner eventuelle uafklarede spørgsmål
3. Giver eleven et klart svar på deres oprindelige spørgsmål
4. Antyder næste skridt i læringen

KONKLUSION:"""
        
        try:
            synthesis = await self.llm.generate(prompt, temperature=0.5)
            return synthesis.strip()
        except Exception as e:
            return f"[Syntese fejlede: {str(e)}]"
    
    def format_for_student(self, result: PanelDiscussionResult) -> str:
        """Format panel result for student consumption."""
        output_parts = [
            "🎙️ **PANELDEBAT** 🎙️",
            f"**Emne:** {result.topic}",
            f"**Spørgsmål:** {result.student_query}",
            "",
            "--- DEBAT ---",
        ]
        
        for stmt in result.statements:
            icon = "💬"
            if stmt.stance == PanelStance.RESPECTFUL_DISAGREEMENT:
                icon = "🤔"
            elif stmt.stance == PanelStance.AGREE_AND_EXTEND:
                icon = "➕"
            elif stmt.stance == PanelStance.ASK_CLARIFYING_QUESTION:
                icon = "❓"
            
            output_parts.append(
                f"{icon} **{stmt.agent_name}**: {stmt.response}"
            )
        
        output_parts.extend([
            "",
            "--- KONKLUSION ---",
            result.synthesis or "Ingen konklusion tilgængelig.",
            "",
            f"*Diskussionen varede {result.rounds_completed} runde(r) med {len(result.participating_agents)} deltagere.*"
        ])
        
        return "\n".join(output_parts)
