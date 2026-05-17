"""
Curriculum Engine: Dynamic Lesson Planning & Time Estimation
Transforms raw concept graphs into structured, personalized learning paths.
"""

import json
from typing import List, Dict, Any
from dataclasses import dataclass, asdict

@dataclass
class ConceptNode:
    id: str
    name: str
    difficulty: float  # 0.1 - 1.0
    prerequisites: List[str]
    estimated_base_time: int  # minutes for average student
    mastery_score: float = 0.0  # 0.0 - 1.0

@dataclass
class LessonPlan:
    day: int
    topic: str
    estimated_time: int
    focus_area: str
    prerequisites_met: bool

class CurriculumEngine:
    def __init__(self, memory_client):
        """
        :param memory_client: MemPalace client for retrieving user mastery data
        """
        self.memory = memory_client

    def calculate_time(self, concept: ConceptNode) -> int:
        """
        Formula: Time = Base_Time × Difficulty × (1 - Mastery_Score) + Buffer
        """
        if concept.mastery_score >= 0.9:
            return 0  # Already mastered
        
        difficulty_factor = max(0.2, concept.difficulty)
        learning_gap = 1.0 - concept.mastery_score
        base_time = concept.estimated_base_time
        
        calculated = base_time * difficulty_factor * learning_gap
        return int(max(15, calculated))  # Minimum 15 mins per session

    def resolve_dependencies(self, concepts: List[ConceptNode]) -> List[str]:
        """
        Topological sort to ensure prerequisites are taught first.
        Returns ordered list of concept IDs.
        """
        graph = {c.id: c.prerequisites for c in concepts}
        visited = set()
        temp_mark = set()
        ordered = []

        def visit(node_id):
            if node_id in temp_mark:
                raise ValueError(f"Circular dependency detected at {node_id}")
            if node_id in visited:
                return
            
            temp_mark.add(node_id)
            for prereq in graph.get(node_id, []):
                if prereq in graph:  # Only visit if prereq exists in our set
                    visit(prereq)
            temp_mark.remove(node_id)
            visited.add(node_id)
            ordered.append(node_id)

        for node in graph:
            if node not in visited:
                visit(node)
        
        return ordered

    def generate_learning_path(self, topic: str, raw_concepts: List[Dict]) -> List[LessonPlan]:
        """
        Main entry point: Generates a day-by-day roadmap.
        """
        # 1. Enrich raw concepts with user mastery data from Memory
        enriched_concepts = []
        for item in raw_concepts:
            # Fetch mastery from MemPalace
            memory_data = self.memory.search({"type": "mastery", "concept": item['id']})
            mastery = memory_data[0]['score'] if memory_data else 0.0
            
            node = ConceptNode(
                id=item['id'],
                name=item['name'],
                difficulty=item.get('difficulty', 0.5),
                prerequisites=item.get('prerequisites', []),
                estimated_base_time=item.get('base_time', 60),
                mastery_score=mastery
            )
            enriched_concepts.append(node)

        # 2. Resolve Order
        try:
            ordered_ids = self.resolve_dependencies(enriched_concepts)
        except ValueError as e:
            print(f"Dependency Error: {e}")
            ordered_ids = [c.id for c in enriched_concepts]  # Fallback

        # 3. Create Daily Plan
        plan = []
        current_day = 1
        concept_map = {c.id: c for c in enriched_concepts}

        for cid in ordered_ids:
            node = concept_map[cid]
            time_needed = self.calculate_time(node)
            
            if time_needed == 0:
                continue  # Skip mastered topics

            # Check if prereqs are actually met in this plan (simple check)
            prereqs_met = all(
                concept_map[p].mastery_score > 0.8 or p not in concept_map 
                for p in node.prerequisites
            )

            plan.append(LessonPlan(
                day=current_day,
                topic=node.name,
                estimated_time=time_needed,
                focus_area="New Concept" if node.mastery_score < 0.5 else "Reinforcement",
                prerequisites_met=prereqs_met
            ))
            current_day += 1

        return plan

# Usage Example
if __name__ == "__main__":
    # Mock Memory Client
    class MockMemory:
        def search(self, query):
            if query['concept'] == 'limits':
                return [{'score': 0.8}]  # User knows limits well
            return []

    engine = CurriculumEngine(MockMemory())
    
    raw_data = [
        {'id': 'functions', 'name': 'Functions', 'difficulty': 0.4, 'prerequisites': [], 'base_time': 45},
        {'id': 'limits', 'name': 'Limits', 'difficulty': 0.6, 'prerequisites': ['functions'], 'base_time': 60},
        {'id': 'derivatives', 'name': 'Derivatives', 'difficulty': 0.8, 'prerequisites': ['limits'], 'base_time': 90},
    ]
    
    path = engine.generate_learning_path("Calculus", raw_data)
    print(json.dumps([asdict(p) for p in path], indent=2))
