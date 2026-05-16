"""Memory Palace - Spatial, hierarchical, verbatim memory storage."""
import json
import hashlib
from datetime import datetime
from typing import List, Dict, Optional
from api.core.database import DatabaseManager
from api.core.config import AGENT_CONFIGS


class MemoryPalace:
    """
    Spatial memory system with wings (subjects), rooms (topics),
    halls (categories), closets (levels), and drawers (entries).
    """

    WINGS = ["wing_matematik", "wing_fysik", "wing_datalogi", "wing_kommunikation", "wing_fælles"]

    def __init__(self):
        self.db = DatabaseManager()

    def store(self, content: str, wing: str, room: str, **metadata) -> int:
        """Store a memory entry in the palace."""
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
        entry_id = self.db.store_memory(
            wing=wing,
            room=room,
            content=content,
            content_hash=content_hash,
            timestamp=datetime.utcnow().isoformat(),
            **metadata
        )
        return entry_id

    def get_recent(self, agent_id: str, topic: str, k: int = 5) -> List[Dict]:
        """Get recent memory entries for an agent on a topic."""
        wing = f"wing_{agent_id}"
        return self.db.search_memory(wing=wing, topic=topic, limit=k)

    def search_own_wing(self, agent_id: str, query: str, k: int = 5) -> List[Dict]:
        """Search within an agent's own wing."""
        wing = f"wing_{agent_id}"
        return self.db.search_memory(wing=wing, query=query, limit=k)

    def search_other_wings(self, agent_id: str, query: str, k: int = 3) -> List[Dict]:
        """Search in all wings except the agent's own."""
        results = []
        own_wing = f"wing_{agent_id}"
        for wing in self.WINGS:
            if wing != own_wing:
                wing_results = self.db.search_memory(wing=wing, query=query, limit=k)
                results.extend(wing_results)
        return results[:k]

    def get_agent_card(self, agent_id: str) -> Dict:
        """Get the identity card for an agent."""
        config = AGENT_CONFIGS.get(agent_id, {})
        return {
            "id": agent_id,
            "name": config.get("name", agent_id),
            "philosophy": config.get("philosophy", ""),
            "method": config.get("method", ""),
            "color": config.get("color", "#58a6ff"),
            "icon": config.get("icon", "🤖"),
        }

    def get_student_profile(self, student_id: str) -> Dict:
        """Get compressed student profile."""
        student = self.db.get_student(student_id)
        if not student:
            return {}
        mastery = self.db.get_mastery(student_id)
        return {
            "name": student.get("name"),
            "hf_year": student.get("hf_year"),
            "pace": student.get("pace", 1.0),
            "modality": student.get("preferred_modality", "balanced"),
            "depth": student.get("preferred_depth", "balanced"),
            "mastery_summary": self._summarize_mastery(mastery),
        }

    def get_research_findings(self, topic: str, k: int = 3) -> List[Dict]:
        """Get cached research findings on a topic."""
        return self.db.search_memory(wing="wing_fælles", room="room_forskning",
                                      topic=topic, limit=k)

    def coverage_score(self, agent_id: str, topic: str, query: str) -> float:
        """Calculate how well-covered a topic is in memory."""
        wing = f"wing_{agent_id}"
        entries = self.db.search_memory(wing=wing, topic=topic, limit=50)
        if not entries:
            return 0.0
        # Simple coverage: ratio of entries with relevant content
        query_words = set(query.lower().split())
        matched = 0
        for entry in entries:
            content_words = set(entry.get("content", "").lower().split())
            if query_words & content_words:
                matched += 1
        return min(1.0, matched / max(1, len(entries) * 0.3))

    def _summarize_mastery(self, mastery: List[Dict]) -> Dict:
        """Create a summary of mastery scores by subject."""
        summary = {}
        for m in mastery:
            subject = m.get("subject", "unknown")
            if subject not in summary:
                summary[subject] = {"concepts": 0, "avg_score": 0.0, "mastered": 0}
            summary[subject]["concepts"] += 1
            summary[subject]["avg_score"] += m.get("score", 0)
            if m.get("score", 0) >= 0.75:
                summary[subject]["mastered"] += 1

        for subject in summary:
            count = summary[subject]["concepts"]
            if count > 0:
                summary[subject]["avg_score"] /= count

        return summary

    def update_student_profile(self, student_id: str, **updates):
        """Update student profile in memory."""
        with self.db.get_db() as conn:
            cursor = conn.cursor()
            allowed_fields = ["preferred_modality", "preferred_depth",
                             "preferred_language", "pace"]
            set_clauses = []
            values = []
            for field in allowed_fields:
                if field in updates:
                    set_clauses.append(f"{field} = ?")
                    values.append(updates[field])
            if set_clauses:
                values.append(student_id)
                cursor.execute(
                    f"UPDATE students SET {', '.join(set_clauses)}, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    tuple(values)
                )
                conn.commit()


class ContextAssembler:
    """Assembles 7 layers of context for tutor agents."""

    def __init__(self, palace: MemoryPalace):
        self.palace = palace

    def assemble(self, agent_id: str, topic: str, student_query: str,
                 student_id: str, session_id: str, curriculum_engine=None) -> str:
        """Assemble L0-L6 context layers."""
        layers = []

        # L0: Agent Identity Card (~50 tokens)
        card = self.palace.get_agent_card(agent_id)
        layers.append(f"=== Du er {card['name']} ===\n"
                      f"Filosofi: {card['philosophy']}\n"
                      f"Metode: {card['method']}")

        # L1: Compressed Student Profile (~120 tokens)
        profile = self.palace.get_student_profile(student_id)
        if profile:
            layers.append(f"=== Elevprofil ===\n"
                          f"Navn: {profile.get('name', 'Elev')}\n"
                          f"HF-år: {profile.get('hf_year', 1)}\n"
                          f"Læringsstil: {profile.get('modality', 'balanced')}\n"
                          f"Forklaringstype: {profile.get('depth', 'balanced')}\n"
                          f"Tempo: {profile.get('pace', 1.0)}")

        # L2: Recent conversation turns (~300 tokens)
        recent = self.palace.get_recent(agent_id, topic, k=5)
        if recent:
            recent_text = "=== Seneste samtale ===\n"
            for r in recent:
                recent_text += f"Elev: {r.get('student_message', '')}\n"
                recent_text += f"Tutor: {r.get('agent_response', '')[:200]}...\n\n"
            layers.append(recent_text)

        # L3: Other tutors' views (~200 tokens)
        other_views = self.palace.search_other_wings(agent_id, student_query, k=3)
        if other_views:
            other_text = "=== Andre tutors har sagt ===\n"
            for v in other_views[:3]:
                other_text += f"[{v.get('agent_id', 'andet fag')}] {v.get('content', '')[:150]}...\n\n"
            layers.append(other_text)

        # L4: Own past explanations (~300 tokens)
        own_past = self.palace.search_own_wing(agent_id, student_query, k=5)
        if own_past:
            own_text = "=== Dine tidligere forklaringer ===\n"
            for p in own_past[:3]:
                own_text += f"- {p.get('content', '')[:200]}...\n"
            layers.append(own_text)

        # L5: Research findings (~200 tokens)
        research = self.palace.get_research_findings(topic, k=3)
        if research:
            research_text = "=== Forskning/fund ===\n"
            for r in research[:2]:
                research_text += f"- {r.get('content', '')[:200]}...\n"
            layers.append(research_text)

        # L6: Curriculum goals (~100 tokens)
        if curriculum_engine:
            objectives = curriculum_engine.get_objectives(topic)
            if objectives:
                layers.append(f"=== Læreplansmål ===\n{objectives}")

        return "\n\n---\n\n".join(layers)
