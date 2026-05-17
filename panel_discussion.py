"""
Panel Discussion Protocol: Structured Multi-Agent Debate Loop
Enforces strict turn-taking, conflict resolution, and persona constraints.
"""

import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from enum import Enum

class AgentRole(Enum):
    TEACHER = "Teacher"
    SIMPLIFIER = "Simplifier"  # Einstein-style
    BUILDER = "Builder"        # Programmer-style
    CRITIC = "Critic"
    SYNTHESIZER = "Synthesizer"

@dataclass
class AgentMessage:
    role: str
    content: str
    targets: List[str]  # Which previous messages this responds to
    confidence: float   # 0.0 - 1.0
    issues_found: List[str]

@dataclass
class DebateRound:
    round_number: int
    messages: List[AgentMessage]
    conflicts_detected: bool

class PanelDiscussion:
    def __init__(self, llm_client, memory_schema=None):
        """
        :param llm_client: LLM client for generating agent responses
        :param memory_schema: Optional MemorySchema for injecting user context
        """
        self.llm = llm_client
        self.memory = memory_schema
        self.max_rounds = 2
        self.conflict_threshold = 0.3  # If confidence diff > this, trigger debate

    def _get_system_prompt(self, role: AgentRole) -> str:
        """Hard-constrained system prompts to prevent personality blending."""
        
        prompts = {
            AgentRole.TEACHER: """
You are the TEACHER. Your ONLY job is curriculum structure.
RULES:
- Break topics into 3-5 sequential steps
- Identify prerequisites
- Adapt pacing based on user weaknesses
- NEVER explain concepts, only structure them
- Output format: JSON with "steps" array
""",
            AgentRole.SIMPLIFIER: """
You are the SIMPLIFIER (Einstein-style). Your ONLY job is intuition.
RULES:
- ALWAYS start with a real-world analogy
- NEVER use equations in your first explanation
- Reduce complex ideas to mental models
- Keep explanations under 100 words
- If criticized, refine the analogy, don't add math
""",
            AgentRole.BUILDER: """
You are the BUILDER (Programmer-style). Your ONLY job is technical precision.
RULES:
- Provide step-by-step decomposition
- Use pseudocode or structured lists
- Define terms explicitly
- NEVER use vague hand-waving
- If criticized, add more detail, not less
""",
            AgentRole.CRITIC: """
You are the CRITIC. Your ONLY job is error detection.
RULES:
- ALWAYS find at least one gap or contradiction
- Attack weak reasoning, not the person
- Flag missing prerequisites
- Force clarity on ambiguous terms
- Severity levels: "low", "medium", "high"
- You MUST disagree with something
""",
            AgentRole.SYNTHESIZER: """
You are the SYNTHESIZER. Your ONLY job is merging explanations.
RULES:
- Combine intuition (Simplifier) + technical (Builder)
- Resolve conflicts identified by Critic
- Maintain the lesson structure (Teacher)
- Output final clean explanation
- NO new information, only synthesis
"""
        }
        return prompts.get(role, "")

    def _generate_response(self, role: AgentRole, context: Dict) -> AgentMessage:
        """Generates a single agent response with hard constraints."""
        
        prompt = self._get_system_prompt(role)
        
        # Inject memory context if available
        if self.memory and role in [AgentRole.TEACHER, AgentRole.CRITIC]:
            profile = self.memory.get_style_profile()
            if profile:
                context['user_style'] = f"User prefers {profile.preferred_mode} explanations"
            
            if role == AgentRole.CRITIC:
                # Inject known misconceptions
                misconceptions = self.memory.get_active_misconceptions(context.get('concept_id', ''))
                if misconceptions:
                    context['known_errors'] = [m.error_description for m in misconceptions]

        # Build full prompt
        full_prompt = f"{prompt}\n\nCONTEXT:\n{json.dumps(context, indent=2)}\n\nRESPOND IN JSON:"
        
        # Call LLM
        response_text = self.llm.generate(full_prompt, max_tokens=500)
        
        # Parse response
        try:
            data = json.loads(response_text)
            return AgentMessage(
                role=role.value,
                content=data.get('content', ''),
                targets=data.get('targets', []),
                confidence=data.get('confidence', 0.8),
                issues_found=data.get('issues_found', [])
            )
        except:
            # Fallback if JSON parsing fails
            return AgentMessage(
                role=role.value,
                content=response_text,
                targets=[],
                confidence=0.5,
                issues_found=["Failed to parse structured response"]
            )

    def _detect_conflict(self, messages: List[AgentMessage]) -> bool:
        """Checks if there's significant disagreement requiring resolution."""
        critic_msgs = [m for m in messages if m.role == "Critic"]
        if not critic_msgs:
            return False
        
        # Conflict if critic found high-severity issues
        for msg in critic_msgs:
            if len(msg.issues_found) >= 2:
                return True
        
        # Conflict if confidence scores diverge significantly
        scores = [m.confidence for m in messages if m.confidence > 0]
        if len(scores) >= 2:
            if max(scores) - min(scores) > self.conflict_threshold:
                return True
        
        return False

    def run_debate(self, topic: str, concept_graph: Dict) -> List[AgentMessage]:
        """
        Main entry point: Executes the structured debate loop.
        Returns all messages from the debate.
        """
        all_messages = []
        current_context = {
            "topic": topic,
            "concept_graph": concept_graph,
            "concept_id": concept_graph.get('id', topic)
        }

        for round_num in range(1, self.max_rounds + 1):
            round_messages = []
            
            # Round Structure:
            # Round 1: Teacher → Simplifier → Builder → Critic
            # Round 2: Simplifier(refine) → Builder(refine) → Critic(final)
            
            if round_num == 1:
                # Teacher sets structure
                teacher_msg = self._generate_response(AgentRole.TEACHER, current_context)
                round_messages.append(teacher_msg)
                current_context['lesson_plan'] = teacher_msg.content
                
                # Simplifier explains intuitively
                simp_msg = self._generate_response(AgentRole.SIMPLIFIER, current_context)
                round_messages.append(simp_msg)
                
                # Builder explains technically
                build_msg = self._generate_response(AgentRole.BUILDER, current_context)
                round_messages.append(build_msg)
                
                # Critic attacks both
                critic_ctx = {**current_context, 
                             "simplifier_output": simp_msg.content,
                             "builder_output": build_msg.content}
                critic_msg = self._generate_response(AgentRole.CRITIC, critic_ctx)
                round_messages.append(critic_msg)
                
            else:
                # Refinement round
                # Simplifier refines based on critic
                refine_ctx = {**current_context,
                             "critic_issues": critic_msg.issues_found,
                             "previous_attempt": simp_msg.content}
                simp_refined = self._generate_response(AgentRole.SIMPLIFIER, refine_ctx)
                round_messages.append(simp_refined)
                
                # Builder refines based on critic
                build_ctx = {**current_context,
                            "critic_issues": critic_msg.issues_found,
                            "previous_attempt": build_msg.content}
                build_refined = self._generate_response(AgentRole.BUILDER, build_ctx)
                round_messages.append(build_refined)
                
                # Final critic check
                final_critic_ctx = {**current_context,
                                   "refined_simplifier": simp_refined.content,
                                   "refined_builder": build_refined.content}
                critic_final = self._generate_response(AgentRole.CRITIC, final_critic_ctx)
                round_messages.append(critic_final)
                critic_msg = critic_final  # Update for next iteration

            all_messages.extend(round_messages)
            
            # Check for conflicts
            if not self._detect_conflict(round_messages):
                break  # Exit early if no significant conflicts

        return all_messages

    def synthesize_final(self, debate_messages: List[AgentMessage]) -> str:
        """Generates the final synthesized output."""
        
        context = {
            "debate_history": [asdict(m) for m in debate_messages],
        }
        
        final_msg = self._generate_response(AgentRole.SYNTHESIZER, context)
        return final_msg.content

# Usage Example
if __name__ == "__main__":
    # Mock LLM Client
    class MockLLM:
        def generate(self, prompt, max_tokens=500):
            # Simulate different personalities
            if "TEACHER" in prompt:
                return json.dumps({"content": "Step 1: Basics → Step 2: Application", "confidence": 0.9})
            elif "SIMPLIFIER" in prompt:
                return json.dumps({"content": "Think of it like adjusting volume knobs...", "confidence": 0.85})
            elif "BUILDER" in prompt:
                return json.dumps({"content": "for x in inputs: output = f(x)", "confidence": 0.88})
            elif "CRITIC" in prompt:
                return json.dumps({"content": "Analogy hides the math", "issues_found": ["Missing gradient explanation"], "confidence": 0.75})
            else:
                return json.dumps({"content": "Final merged explanation here", "confidence": 0.95})

    panel = PanelDiscussion(MockLLM())
    
    concept = {"id": "neural_networks", "name": "Neural Networks"}
    messages = panel.run_debate("Neural Networks", concept)
    
    print("\n=== DEBATE LOG ===")
    for msg in messages:
        print(f"[{msg.role}]: {msg.content[:50]}...")
    
    final = panel.synthesize_final(messages)
    print(f"\n=== FINAL OUTPUT ===\n{final}")
