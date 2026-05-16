"""Personalization Engine - Adaptive learning and progression gates."""
from typing import Dict, Optional
from api.core.config import PROGRESSION_GATES
from api.core.database import DatabaseManager
from api.services.knowledge_graph import KnowledgeGraph


class PersonalizationEngine:
    """Adapts tutoring to individual student needs."""

    def __init__(self):
        self.db = DatabaseManager()
        self.kg = KnowledgeGraph()

    def adapt_response(self, raw_response: str, student_id: str) -> str:
        """Post-process tutor response based on student profile."""
        student = self.db.get_student(student_id)
        if not student:
            return raw_response

        adaptations = []

        # Depth adaptation
        depth = student.get("preferred_depth", "balanced")
        if depth == "intuitive":
            adaptations.append("Tilføj en analogi eller hverdagseksempel.")
        elif depth == "formal":
            adaptations.append("Tilføj den formelle notation og bevis-skitse.")

        # Pace adaptation
        pace = student.get("pace", 1.0)
        if pace < 0.8:
            adaptations.append("Opdel i mindre trin. Stil et kontrolspørgsmål efter hvert trin.")
        elif pace > 1.5:
            adaptations.append("Komprimér. Spring trivielle trin over. Gå direkte til kernen.")

        if adaptations:
            # In a real implementation, this would do a second LLM pass
            # For now, prepend adaptation hints as HTML comments
            hint = "\n".join(f"<!-- {a} -->" for a in adaptations)
            return f"{hint}\n\n{raw_response}"

        return raw_response

    def update_profile_from_interaction(self, student_id: str,
                                         student_message: str,
                                         tutor_response: str,
                                         topic: str):
        """Update student profile based on interaction signals."""
        msg_lower = student_message.lower()

        # Detect confusion signals
        confusion_words = ["forstår ikke", "huh", "forvirret", "svært",
                          "kompliceret", "ikke helt", "gentag"]
        if any(w in msg_lower for w in confusion_words):
            # Lower mastery slightly
            current = self.db.get_mastery(student_id, topic)
            if current:
                new_score = max(0.0, current.get("score", 0.5) - 0.05)
                self.db.update_mastery(student_id, topic,
                                       current.get("subject", "unknown"),
                                       current.get("level", "C"), new_score)

        # Detect understanding signals
        understanding_words = ["forstår", "giver mening", "klart", "selvfølgelig",
                              "rigtigt", "præcis", "godt"]
        if any(w in msg_lower for w in understanding_words):
            current = self.db.get_mastery(student_id, topic)
            if current:
                new_score = min(1.0, current.get("score", 0.5) + 0.1)
                self.db.update_mastery(student_id, topic,
                                       current.get("subject", "unknown"),
                                       current.get("level", "C"), new_score)
            else:
                # Initialize mastery for new topic
                self.db.update_mastery(student_id, topic, "unknown", "C", 0.55)

    def check_progression(self, student_id: str, subject: str,
                          current_level: str) -> Dict:
        """Check if student is ready to progress to next level."""
        gate_key = f"{current_level}_to_{self._next_level(current_level)}"
        gate = PROGRESSION_GATES.get(gate_key)

        if not gate:
            return {"ready": False, "reason": "No next level defined"}

        mastery = self.db.get_mastery(student_id)
        subject_mastery = [m for m in mastery if m.get("subject") == subject
                          and m.get("level") == current_level]

        if not subject_mastery:
            return {"ready": False, "reason": "No mastery data"}

        mastered = [m for m in subject_mastery
                   if m.get("score", 0) >= gate["min_mastery"]]
        mastery_pct = len(mastered) / len(subject_mastery) if subject_mastery else 0

        gaps = [m.get("concept_id") for m in subject_mastery
                if m.get("score", 0) < 0.6]

        ready = mastery_pct >= gate["min_mastery"] and len(gaps) == 0

        return {
            "ready": ready,
            "mastery_pct": round(mastery_pct * 100, 1),
            "required_mastery": gate["min_mastery"] * 100,
            "gaps": gaps,
            "recommendation": "Klar til næste niveau!" if ready
                            else f"Fokuser på: {', '.join(gaps[:3])}"
        }

    def _next_level(self, current: str) -> str:
        levels = {"C": "B", "B": "A", "A": "A"}
        return levels.get(current, current)

    def get_student_dashboard(self, student_id: str) -> Dict:
        """Get comprehensive dashboard data for a student."""
        student = self.db.get_student(student_id)
        if not student:
            return {}

        mastery = self.db.get_mastery(student_id)

        # Organize by subject
        by_subject = {}
        for m in mastery:
            subj = m.get("subject", "unknown")
            if subj not in by_subject:
                by_subject[subj] = []
            by_subject[subj].append(m)

        # Calculate stats
        stats = {}
        for subject, concepts in by_subject.items():
            total = len(concepts)
            avg_score = sum(c.get("score", 0) for c in concepts) / total if total else 0
            mastered = sum(1 for c in concepts if c.get("score", 0) >= 0.75)
            stats[subject] = {
                "total_concepts": total,
                "avg_score": round(avg_score, 2),
                "mastered": mastered,
                "in_progress": sum(1 for c in concepts if 0.3 <= c.get("score", 0) < 0.75),
                "not_started": sum(1 for c in concepts if c.get("score", 0) < 0.3),
            }

        return {
            "student": {
                "name": student.get("name"),
                "hf_year": student.get("hf_year"),
                "pace": student.get("pace"),
                "modality": student.get("preferred_modality"),
            },
            "stats": stats,
            "mastery": mastery,
        }
