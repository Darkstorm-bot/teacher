"""
Memory Palace Schema: Structured Student Modeling
Defines how to store/retrieve user mistakes, mastery scores, and learning styles.
"""

import json
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class Misconception:
    concept_id: str
    error_description: str
    frequency: int  # How many times this error occurred
    last_seen: str  # ISO timestamp
    corrected: bool = False

@dataclass
class StyleProfile:
    preferred_mode: str  # "analogy", "math", "code", "visual"
    pace: str  # "fast", "medium", "slow"
    attention_span_mins: int
    best_time_of_day: str  # "morning", "afternoon", "night"

@dataclass
class MasteryRecord:
    concept_id: str
    score: float  # 0.0 - 1.0
    last_tested: str
    evidence: List[str]  # Links to successful explanations or quiz results

class MemorySchema:
    def __init__(self, mempalace_client):
        """
        :param mempalace_client: Initialized MemPalace client
        """
        self.mp = mempalace_client
        self.wing = "student_model"

    def _get_room(self, room_type: str) -> str:
        return f"{self.wing}/{room_type}"

    # === MISCONCEPTION LOG ===
    
    def log_misconception(self, concept_id: str, error: str):
        """Records a specific error made by the user."""
        room = self._get_room("misconceptions")
        
        # Check if exists
        existing = self.mp.search({
            "type": "misconception",
            "concept_id": concept_id,
            "error_description": error
        })
        
        if existing:
            # Increment frequency
            rec = existing[0]
            rec['frequency'] += 1
            rec['last_seen'] = datetime.now().isoformat()
            self.mp.update(rec['id'], rec)
        else:
            # New misconception
            data = asdict(Misconception(
                concept_id=concept_id,
                error_description=error,
                frequency=1,
                last_seen=datetime.now().isoformat()
            ))
            data['type'] = 'misconception'
            self.mp.store(data, room=room)

    def get_active_misconceptions(self, concept_id: str) -> List[Misconception]:
        """Retrieves uncorrected errors for a specific concept."""
        results = self.mp.search({
            "type": "misconception",
            "concept_id": concept_id,
            "corrected": False
        })
        return [Misconception(**{k:v for k,v in r.items() if k in Misconception.__annotations__}) 
                for r in results]

    def mark_corrected(self, concept_id: str, error: str):
        """Marks a misconception as resolved."""
        existing = self.mp.search({
            "type": "misconception",
            "concept_id": concept_id,
            "error_description": error
        })
        if existing:
            existing[0]['corrected'] = True
            self.mp.update(existing[0]['id'], existing[0])

    # === STYLE PROFILE ===

    def update_style_profile(self, profile: Dict[str, Any]):
        """Updates the user's learning style preferences."""
        room = self._get_room("profile")
        data = asdict(StyleProfile(**profile))
        data['type'] = 'style_profile'
        
        # Upsert (only one profile allowed)
        existing = self.mp.search({"type": "style_profile"})
        if existing:
            data['id'] = existing[0]['id']
            self.mp.update(data['id'], data)
        else:
            self.mp.store(data, room=room)

    def get_style_profile(self) -> Optional[StyleProfile]:
        """Retrieves current learning style."""
        results = self.mp.search({"type": "style_profile"})
        if results:
            data = {k:v for k,v in results[0].items() if k in StyleProfile.__annotations__}
            return StyleProfile(**data)
        return None

    # === MASTERY MATRIX ===

    def update_mastery(self, concept_id: str, score: float, evidence: str):
        """
        Updates mastery score for a concept.
        Uses exponential moving average to smooth out fluctuations.
        """
        room = self._get_room("mastery")
        
        existing = self.mp.search({
            "type": "mastery",
            "concept_id": concept_id
        })
        
        if existing:
            rec = existing[0]
            # EMA: new_score = 0.7 * old + 0.3 * current
            smoothed = 0.7 * rec['score'] + 0.3 * score
            rec['score'] = min(1.0, smoothed)
            rec['last_tested'] = datetime.now().isoformat()
            rec['evidence'].append(evidence)
            self.mp.update(rec['id'], rec)
        else:
            data = asdict(MasteryRecord(
                concept_id=concept_id,
                score=score,
                last_tested=datetime.now().isoformat(),
                evidence=[evidence]
            ))
            data['type'] = 'mastery'
            self.mp.store(data, room=room)

    def get_mastery(self, concept_id: str) -> float:
        """Returns current mastery score for a concept."""
        results = self.mp.search({
            "type": "mastery",
            "concept_id": concept_id
        })
        return results[0]['score'] if results else 0.0

    def get_full_mastery_matrix(self) -> Dict[str, float]:
        """Returns all mastery scores."""
        results = self.mp.search({"type": "mastery"})
        return {r['concept_id']: r['score'] for r in results}

# Usage Example
if __name__ == "__main__":
    # Mock MemPalace Client
    class MockMP:
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

    mp = MockMP()
    schema = MemorySchema(mp)

    # Log a mistake
    schema.log_misconception("derivatives", "Thinks derivative is just division")
    
    # Update style
    schema.update_style_profile({
        "preferred_mode": "analogy",
        "pace": "medium",
        "attention_span_mins": 25,
        "best_time_of_day": "morning"
    })
    
    # Update mastery
    schema.update_mastery("functions", 0.8, "Completed quiz with 4/5 correct")
    
    print("Mastery Matrix:", schema.get_full_mastery_matrix())
    print("Style Profile:", schema.get_style_profile())
    print("Misconceptions:", schema.get_active_misconceptions("derivatives"))
