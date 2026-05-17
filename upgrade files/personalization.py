"""Personalization Engine — Adaptive learning with Ebbinghaus forgetting curve."""
import math
from datetime import datetime, timezone
from typing import Dict, List, Optional
from api.core.config import PROGRESSION_GATES
from api.core.database import DatabaseManager
from api.services.knowledge_graph import KnowledgeGraph


# ── Ebbinghaus helpers ────────────────────────────────────────────────────────

def _ebbinghaus_retention(last_score: float, hours_since: float, stability: float = 24.0) -> float:
    """
    R = S · e^(-t / stability)
    stability grows with each successful retrieval (spaced repetition).
    """
    if hours_since <= 0:
        return last_score
    return last_score * math.exp(-hours_since / stability)


def _hours_since(iso_ts: Optional[str]) -> float:
    if not iso_ts:
        return 0.0
    try:
        last = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
        now  = datetime.now(timezone.utc)
        return (now - last).total_seconds() / 3600.0
    except Exception:
        return 0.0


# ── Engine ─────────────────────────────────────────────────────────────────────

class PersonalizationEngine:
    """Adapts tutoring to individual student needs."""

    def __init__(self):
        self.db = DatabaseManager()
        self.kg = KnowledgeGraph()

    # ── adapt_response ──────────────────────────────────────────────────────

    def adapt_response(self, raw_response: str, student_id: str) -> str:
        """
        Return the response unchanged.

        Previously this prepended HTML comments that leaked into the chat UI.
        Adaptation hints are now incorporated via the system prompt by the
        orchestrator (ContextAssembler L1 student profile layer), so there is
        nothing left to do here — we simply pass the text through.
        """
        return raw_response

    # ── update_profile_from_interaction ────────────────────────────────────

    def update_profile_from_interaction(
        self,
        student_id: str,
        student_message: str,
        tutor_response: str,
        topic: str,
    ) -> None:
        """Update mastery based on interaction signals with forgetting-curve decay."""
        msg_lower = student_message.lower()

        confusion_words = [
            "forstår ikke", "huh", "forvirret", "svært", "kompliceret",
            "ikke helt", "gentag", "confused", "lost",
        ]
        understanding_words = [
            "forstår", "giver mening", "klart", "selvfølgelig", "rigtigt",
            "præcis", "godt", "yes", "ja", "ok", "got it",
        ]

        has_confusion    = any(w in msg_lower for w in confusion_words)
        has_understanding = any(w in msg_lower for w in understanding_words)

        current = self.db.get_mastery(student_id, topic)

        if has_confusion:
            if current:
                # Apply forgetting-curve decay then subtract confusion penalty
                hrs  = _hours_since(current.get("last_practiced"))
                decayed = _ebbinghaus_retention(current.get("score", 0.5), hrs)
                new_score = max(0.0, decayed - 0.08)
                self.db.update_mastery(
                    student_id, topic,
                    current.get("subject", "unknown"),
                    current.get("level", "C"),
                    new_score,
                )

        if has_understanding:
            if current:
                hrs  = _hours_since(current.get("last_practiced"))
                # Decayed baseline + understanding boost; repeated success grows stability
                decayed   = _ebbinghaus_retention(current.get("score", 0.5), hrs)
                # Use times_practiced as proxy for stability
                stability = 24.0 * (1 + 0.5 * current.get("times_practiced", 0))
                new_score = min(1.0, decayed + 0.12)
                self.db.update_mastery(
                    student_id, topic,
                    current.get("subject", "unknown"),
                    current.get("level", "C"),
                    new_score,
                )
            else:
                self.db.update_mastery(student_id, topic, "unknown", "C", 0.55)

    # ── check_progression ──────────────────────────────────────────────────

    def check_progression(self, student_id: str, subject: str,
                          current_level: str) -> Dict:
        gate_key = f"{current_level}_to_{self._next_level(current_level)}"
        gate = PROGRESSION_GATES.get(gate_key)
        if not gate:
            return {"ready": False, "reason": "No next level defined"}

        mastery = self.db.get_mastery(student_id)
        subject_mastery = [
            m for m in mastery
            if m.get("subject") == subject and m.get("level") == current_level
        ]
        if not subject_mastery:
            return {"ready": False, "reason": "No mastery data"}

        mastered    = [m for m in subject_mastery if m.get("score", 0) >= gate["min_mastery"]]
        mastery_pct = len(mastered) / len(subject_mastery)
        gaps        = [m.get("concept_id") for m in subject_mastery if m.get("score", 0) < 0.6]
        ready       = mastery_pct >= gate["min_mastery"] and len(gaps) == 0

        return {
            "ready": ready,
            "mastery_pct": round(mastery_pct * 100, 1),
            "required_mastery": gate["min_mastery"] * 100,
            "gaps": gaps,
            "recommendation": "Klar til næste niveau!" if ready
                              else f"Fokuser på: {', '.join(gaps[:3])}",
        }

    def _next_level(self, current: str) -> str:
        return {"C": "B", "B": "A", "A": "A"}.get(current, current)

    # ── get_student_dashboard ───────────────────────────────────────────────

    def get_student_dashboard(self, student_id: str) -> Dict:
        student = self.db.get_student(student_id)
        if not student:
            return {}

        mastery = self.db.get_mastery(student_id)

        by_subject: Dict[str, List] = {}
        for m in mastery:
            subj = m.get("subject", "unknown")
            by_subject.setdefault(subj, []).append(m)

        stats = {}
        for subject, concepts in by_subject.items():
            total     = len(concepts)
            avg_score = sum(c.get("score", 0) for c in concepts) / total if total else 0
            mastered  = sum(1 for c in concepts if c.get("score", 0) >= 0.75)
            stats[subject] = {
                "total_concepts": total,
                "avg_score":      round(avg_score, 2),
                "mastered":       mastered,
                "in_progress":    sum(1 for c in concepts if 0.3 <= c.get("score", 0) < 0.75),
                "not_started":    sum(1 for c in concepts if c.get("score", 0) < 0.3),
            }

        return {
            "student": {
                "name":     student.get("name"),
                "hf_year":  student.get("hf_year"),
                "pace":     student.get("pace"),
                "modality": student.get("preferred_modality"),
            },
            "stats":   stats,
            "mastery": mastery,
        }
