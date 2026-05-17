"""
MACT System Integrator - Main Entry Point (Phase 2 Complete)
Connects all layers: Curriculum Engine, Memory Schema, Panel Discussion, Canvas UI, PDF Ingestion, SearXNG Research
"""

import json
from typing import Dict, Any, Optional
from curriculum_engine import CurriculumEngine
from memory_schema import MemorySchema
from panel_discussion import PanelDiscussion
from pdf_ingestion_pipeline import PDFIngestionPipeline
from searxng_integration import SearXNGResearcher, ResearchTrigger

class MACTSystem:
    """
    Multi-Agent Cognitive Tutor - Complete System
    """
    
    def __init__(self, llm_client, mempalace_client, searxng_url: str = "http://localhost:8080"):
        """
        Initialize all layers including Phase 2 enhancements
        
        :param llm_client: LLM client for generating responses
        :param mempalace_client: MemPalace client for memory operations
        :param searxng_url: Base URL for SearXNG instance
        """
        # Layer 1: Memory Schema (foundation)
        self.memory = MemorySchema(mempalace_client)
        
        # Layer 2: Curriculum Engine (uses memory)
        self.curriculum = CurriculumEngine(mempalace_client)
        
        # Layer 3: Panel Discussion (uses memory + curriculum)
        self.panel = PanelDiscussion(llm_client, self.memory)
        
        # Layer 4: PDF Ingestion Pipeline (Phase 2)
        self.pdf_pipeline = PDFIngestionPipeline(llm_client)
        
        # Layer 5: SearXNG Research (Phase 2)
        self.researcher = SearXNGResearcher(searxng_url)
        self.research_trigger = ResearchTrigger(self.researcher, confidence_threshold=0.6)
        
        # Layer 6: Frontend (served separately via HTTP)
        self.frontend_path = "frontend/index.html"
        
        print("✅ MACT System Initialized (Phase 2 Complete)")
        print("   - Memory Schema: Ready")
        print("   - Curriculum Engine: Ready")
        print("   - Panel Discussion: Ready")
        print("   - PDF Ingestion: Ready")
        print("   - SearXNG Research: Ready")
        print("   - Canvas UI: Available at frontend/index.html")

    def learn_topic(self, topic: str, concept_graph: Optional[Dict] = None, 
                   use_research: bool = True) -> Dict[str, Any]:
        """
        Main learning flow: User requests to learn a topic
        
        :param topic: Topic name (e.g., "Neural Networks")
        :param concept_graph: Optional pre-extracted concept graph from PDF
        :param use_research: Enable automatic SearXNG research when needed
        :return: Complete lesson with debate history and final synthesis
        """
        print(f"\n📚 Starting lesson on: {topic}")
        
        # Step 1: Get or generate concept graph
        if not concept_graph:
            # Try to get from memory first
            concept_graph = self.memory.get_concept_graph(topic)
            
            if not concept_graph:
                # Create minimal graph
                concept_graph = {
                    "id": topic.lower().replace(" ", "_"),
                    "name": topic,
                    "prerequisites": [],
                    "difficulty": 0.5,
                    "base_time": 60,
                    "nodes": {}
                }
        
        # Step 2: Check user's current state
        mastery = self.memory.get_mastery(concept_graph['id'])
        profile = self.memory.get_style_profile()
        
        print(f"   Current mastery: {mastery*100:.0f}%")
        if profile:
            print(f"   Learning style: {profile.preferred_mode}")
        
        # Step 3: Run panel discussion
        print("   🎙️  Starting panel discussion...")
        debate_messages = self.panel.run_debate(topic, concept_graph)
        
        # Convert to dict for research trigger check
        agent_outputs_dict = {msg.role: msg for msg in debate_messages}
        
        # Step 4: Check if research is needed (NEW - Phase 2)
        if use_research and self.research_trigger.should_research(
            agent_outputs_dict, topic, concept_graph
        ):
            print("   🔬 Auto-triggering research...")
            
            # In production, use actual LLM client passed to constructor
            research_findings = self.research_trigger.conduct_research(
                topic, 
                self.panel.llm,  # Use the same LLM client
                context=str(debate_messages[-1].content)[:200] if debate_messages else ""
            )
            
            if research_findings['success']:
                print(f"   ✅ Research complete: {research_findings['sources_count']} sources")
                
                # Re-run debate with research context
                print("   🎙️  Re-running debate with research findings...")
                debate_messages = self.panel.run_debate(
                    topic, 
                    concept_graph,
                    research_context=research_findings['summary']
                )
        
        # Step 5: Synthesize final explanation
        print("   ✨ Synthesizing final explanation...")
        final_output = self.panel.synthesize_final(debate_messages)
        
        # Step 6: Update memory (if successful)
        # Assume success if critic confidence > 0.6
        critic_msgs = [m for m in debate_messages if m.role == "Critic"]
        if critic_msgs and critic_msgs[-1].confidence > 0.6:
            # Estimate learning completion (in real system, quiz-based)
            new_mastery = min(1.0, mastery + 0.2)
            self.memory.update_mastery(
                concept_graph['id'],
                new_mastery,
                f"Completed lesson: {topic}"
            )
            print(f"   💾 Updated mastery to: {new_mastery*100:.0f}%")
        
        # Step 7: Format output for frontend
        result = {
            "topic": topic,
            "concept_id": concept_graph['id'],
            "initial_mastery": mastery,
            "final_mastery": self.memory.get_mastery(concept_graph['id']),
            "debate_log": [
                {
                    "agent": msg.role,
                    "content": msg.content,
                    "confidence": msg.confidence,
                    "issues": msg.issues_found
                }
                for msg in debate_messages
            ],
            "final_explanation": final_output,
            "next_steps": self._suggest_next_steps(concept_graph)
        }
        
        return result

    def _suggest_next_steps(self, current_concept: Dict) -> list:
        """Suggest what to learn next based on dependency graph."""
        # In production: query full concept graph for dependencies
        return []

    def upload_pdf(self, pdf_path: str, subject: str = "General") -> Dict[str, Any]:
        """
        Upload and process a textbook/notes PDF (Phase 2 - Full Implementation)
        
        :param pdf_path: Path to PDF file
        :param subject: Subject area (Math, CS, Physics, etc.)
        :return: Extracted concept graph with learning path
        """
        print(f"\n📄 Processing PDF: {pdf_path}")
        print(f"   Subject: {subject}")
        
        # Call PDF ingestion pipeline
        concept_graph = self.pdf_pipeline.process_pdf(pdf_path, subject)
        
        # Store in memory
        self.memory.store_concept_graph(concept_graph)
        
        # Get user profile for personalized learning path
        profile = self.memory.get_style_profile() or {
            "pace": "medium",
            "attention_span_mins": 25,
            "sessions_per_day": 2
        }
        
        # Generate learning path
        learning_path = self.pdf_pipeline.generate_learning_path(
            concept_graph, 
            user_profile=profile
        )
        
        print(f"   📊 Extracted {len(concept_graph['nodes'])} concepts")
        print(f"   📅 Generated {learning_path[-1]['day'] if learning_path else 0} day learning plan")
        print(f"   ⏱️  Total estimated time: {concept_graph.get('total_estimated_time_hours', 0)} hours")
        
        return {
            "concept_graph": concept_graph,
            "learning_path": learning_path
        }

    def get_dashboard_data(self) -> Dict[str, Any]:
        """
        Get data for frontend dashboard visualization
        
        :return: Graph nodes, links, and progress stats
        """
        # Get all mastery scores
        mastery_matrix = self.memory.get_full_mastery_matrix()
        
        # Build graph data for D3 visualization
        nodes = []
        for concept_id, score in mastery_matrix.items():
            status = "locked"
            if score > 0.8:
                status = "mastered"
            elif score > 0.2:
                status = "learning"
            
            nodes.append({
                "id": concept_id,
                "label": concept_id.replace("_", " ").title(),
                "status": status
            })
        
        # Add default nodes if empty
        if not nodes:
            nodes = [
                {"id": "functions", "label": "Functions", "status": "mastered"},
                {"id": "limits", "label": "Limits", "status": "learning"},
                {"id": "derivatives", "label": "Derivatives", "status": "locked"}
            ]
        
        # Create links (in production: from actual dependency graph)
        links = []
        for i in range(len(nodes) - 1):
            links.append({
                "source": nodes[i]["id"],
                "target": nodes[i+1]["id"]
            })
        
        # Calculate overall progress
        total = len(nodes)
        mastered = len([n for n in nodes if n["status"] == "mastered"])
        progress = round((mastered / total) * 100) if total > 0 else 0
        
        return {
            "graph": {
                "nodes": nodes,
                "links": links
            },
            "progress": progress,
            "total_concepts": total,
            "mastered_concepts": mastered
        }


# === EXAMPLE USAGE ===
if __name__ == "__main__":
    # Mock clients for testing
    class MockLLM:
        def generate(self, prompt, max_tokens=500):
            if "TEACHER" in prompt:
                return json.dumps({"content": "Step 1: Fundamentals → Step 2: Practice", "confidence": 0.9})
            elif "SIMPLIFIER" in prompt:
                return json.dumps({"content": "Imagine it like building with LEGO blocks...", "confidence": 0.85})
            elif "BUILDER" in prompt:
                return json.dumps({"content": "def concept(x): return understanding(x)", "confidence": 0.88})
            elif "CRITIC" in prompt:
                return json.dumps({"content": "Analogy is good but needs more rigor", "issues_found": ["Missing formal definition"], "confidence": 0.75})
            else:
                return json.dumps({"content": "## Final Explanation\n\nConcepts build on each other systematically.", "confidence": 0.95})
    
    class MockMemPalace:
        def __init__(self):
            self.db = []
        
        def search(self, query):
            results = []
            for item in self.db:
                match = True
                for k, v in query.items():
                    if item.get(k) != v:
                        match = False
                        break
                if match:
                    results.append(item)
            return results
        
        def store(self, data, room=None):
            data['id'] = len(self.db) + 1
            self.db.append(data)
            return data['id']
        
        def update(self, id, data):
            for i, item in enumerate(self.db):
                if item['id'] == id:
                    self.db[i] = data
                    break
    
    # Initialize system
    llm = MockLLM()
    mp = MockMemPalace()
    mact = MACTSystem(llm, mp)
    
    # Set user profile
    mact.memory.update_style_profile({
        "preferred_mode": "analogy",
        "pace": "medium",
        "attention_span_mins": 25,
        "best_time_of_day": "morning"
    })
    
    # Learn a topic
    result = mact.learn_topic("Machine Learning Basics")
    
    print("\n" + "="*60)
    print("FINAL EXPLANATION:")
    print("="*60)
    print(result['final_explanation'])
    
    print("\n" + "="*60)
    print("DASHBOARD DATA:")
    print("="*60)
    dashboard = mact.get_dashboard_data()
    print(f"Progress: {dashboard['progress']}%")
    print(f"Concepts: {dashboard['total_concepts']} total, {dashboard['mastered_concepts']} mastered")
    
    print("\n✅ System test complete!")
