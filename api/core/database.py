"""SQLite Database for HF-Agent"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from contextlib import contextmanager
from api.core.config import DATA_DIR

DB_PATH = DATA_DIR / "hf_agent.db"

def init_db():
    """Initialize all database tables."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    # Students
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            hf_year INTEGER CHECK (hf_year IN (1, 2)),
            target_program TEXT DEFAULT 'BSc AI / Software Engineering',
            preferred_modality TEXT DEFAULT 'balanced',
            preferred_depth TEXT DEFAULT 'balanced',
            preferred_language TEXT DEFAULT 'da',
            pace REAL DEFAULT 1.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Sessions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id TEXT PRIMARY KEY,
            student_id TEXT REFERENCES students(id),
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            ended_at TIMESTAMP,
            primary_subject TEXT,
            turns_count INTEGER DEFAULT 0,
            agents_used TEXT DEFAULT '[]',
            protocols_used TEXT DEFAULT '[]'
        )
    """)

    # Conversation turns
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS turns (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT REFERENCES sessions(id),
            turn_number INTEGER,
            agent_id TEXT,
            student_message TEXT,
            agent_response TEXT,
            topic TEXT,
            subtopic TEXT,
            teaching_state TEXT,
            difficulty_level TEXT,
            protocol TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Mastery scores
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS mastery_scores (
            student_id TEXT REFERENCES students(id),
            concept_id TEXT NOT NULL,
            subject TEXT NOT NULL,
            level TEXT CHECK (level IN ('C', 'B', 'A')),
            score REAL DEFAULT 0.0 CHECK (score >= 0 AND score <= 1),
            times_practiced INTEGER DEFAULT 0,
            last_practiced TIMESTAMP,
            PRIMARY KEY (student_id, concept_id)
        )
    """)

    # Level promotions
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS level_promotions (
            id TEXT PRIMARY KEY,
            student_id TEXT REFERENCES students(id),
            subject TEXT NOT NULL,
            from_level TEXT NOT NULL,
            to_level TEXT NOT NULL,
            promoted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            mastery_at_promotion REAL,
            remaining_gaps TEXT DEFAULT '[]'
        )
    """)

    # Memory Palace entries
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS memory_entries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            wing TEXT NOT NULL,
            room TEXT NOT NULL,
            hall TEXT,
            closet TEXT,
            drawer TEXT,
            content TEXT NOT NULL,
            content_hash TEXT,
            agent_id TEXT,
            memory_type TEXT,
            topic TEXT,
            subtopic TEXT,
            teaching_state TEXT,
            difficulty_level TEXT,
            curriculum_ref TEXT,
            confusion_signals TEXT DEFAULT '[]',
            aha_moment BOOLEAN DEFAULT 0,
            student_rating INTEGER,
            references_agents TEXT DEFAULT '[]',
            corrects_agent TEXT,
            session_id TEXT,
            turn_number INTEGER,
            source TEXT,
            source_url TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Knowledge Graph - Concept Nodes
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS concept_nodes (
            id TEXT PRIMARY KEY,
            subject TEXT NOT NULL,
            level TEXT NOT NULL,
            display_name TEXT NOT NULL,
            description TEXT,
            mastery REAL DEFAULT 0.0,
            last_taught TIMESTAMP,
            times_taught INTEGER DEFAULT 0,
            curriculum_ref TEXT
        )
    """)

    # Knowledge Graph - Concept Edges
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS concept_edges (
            source_id TEXT REFERENCES concept_nodes(id),
            target_id TEXT REFERENCES concept_nodes(id),
            relation TEXT NOT NULL,
            weight REAL DEFAULT 1.0,
            cross_subject BOOLEAN DEFAULT 0,
            PRIMARY KEY (source_id, target_id, relation)
        )
    """)

    # Student profile - effective analogies
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS student_analogies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT REFERENCES students(id),
            concept_id TEXT NOT NULL,
            analogy TEXT NOT NULL,
            effectiveness_score REAL DEFAULT 1.0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Student profile - failed explanations
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS student_failed_explanations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT REFERENCES students(id),
            concept_id TEXT NOT NULL,
            approach_summary TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Research cache
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS research_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL,
            query TEXT NOT NULL,
            synthesis TEXT NOT NULL,
            source_urls TEXT DEFAULT '[]',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Tutor effectiveness
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tutor_effectiveness (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agent_id TEXT NOT NULL,
            topic TEXT NOT NULL,
            approach_used TEXT,
            student_rating INTEGER,
            understanding_signal BOOLEAN,
            session_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


@contextmanager
def get_db():
    """Get database connection with proper cleanup."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


class DatabaseManager:
    """High-level database operations."""

    @staticmethod
    def create_student(student_id: str, name: str, hf_year: int = 1, **kwargs):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO students (id, name, hf_year, target_program, preferred_modality,
                    preferred_depth, preferred_language, pace)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (student_id, name, hf_year,
                 kwargs.get("target_program", "BSc AI / Software Engineering"),
                 kwargs.get("preferred_modality", "balanced"),
                 kwargs.get("preferred_depth", "balanced"),
                 kwargs.get("preferred_language", "da"),
                 kwargs.get("pace", 1.0))
            )
            conn.commit()

    @staticmethod
    def get_student(student_id: str):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM students WHERE id = ?", (student_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    @staticmethod
    def create_session(session_id: str, student_id: str):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO sessions (id, student_id) VALUES (?, ?)",
                (session_id, student_id)
            )
            conn.commit()

    @staticmethod
    def get_session(session_id: str):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE id = ?", (session_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def add_turn(session_id: str, turn_number: int, agent_id: str, student_message: str,
                 agent_response: str, topic: str, subtopic: str = None,
                 teaching_state: str = None, difficulty_level: str = None, protocol: str = "DIRECT"):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO turns
                    (session_id, turn_number, agent_id, student_message, agent_response,
                     topic, subtopic, teaching_state, difficulty_level, protocol)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (session_id, turn_number, agent_id, student_message, agent_response,
                 topic, subtopic, teaching_state, difficulty_level, protocol)
            )
            cursor.execute(
                "UPDATE sessions SET turns_count = turns_count + 1 WHERE id = ?",
                (session_id,)
            )
            conn.commit()

    @staticmethod
    def get_recent_turns(session_id: str, k: int = 5):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """SELECT * FROM turns WHERE session_id = ?
                    ORDER BY turn_number DESC LIMIT ?""",
                (session_id, k)
            )
            rows = cursor.fetchall()
            return [dict(r) for r in reversed(rows)]

    @staticmethod
    def get_mastery(student_id: str, concept_id: str = None):
        with get_db() as conn:
            cursor = conn.cursor()
            if concept_id:
                cursor.execute(
                    "SELECT * FROM mastery_scores WHERE student_id = ? AND concept_id = ?",
                    (student_id, concept_id)
                )
                row = cursor.fetchone()
                return dict(row) if row else None
            else:
                cursor.execute(
                    "SELECT * FROM mastery_scores WHERE student_id = ?",
                    (student_id,)
                )
                return [dict(r) for r in cursor.fetchall()]

    @staticmethod
    def update_mastery(student_id: str, concept_id: str, subject: str, level: str, score: float):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO mastery_scores
                    (student_id, concept_id, subject, level, score, times_practiced, last_practiced)
                    VALUES (?, ?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
                    ON CONFLICT(student_id, concept_id) DO UPDATE SET
                        score = ?,
                        times_practiced = times_practiced + 1,
                        last_practiced = CURRENT_TIMESTAMP""",
                (student_id, concept_id, subject, level, score, score)
            )
            conn.commit()

    @staticmethod
    def store_memory(wing: str, room: str, content: str, **kwargs):
        with get_db() as conn:
            cursor = conn.cursor()
            fields = ["wing", "room", "content"]
            values = [wing, room, content]
            optional_fields = ["hall", "closet", "drawer", "content_hash", "agent_id",
                               "memory_type", "topic", "subtopic", "teaching_state",
                               "difficulty_level", "curriculum_ref", "confusion_signals",
                               "aha_moment", "student_rating", "references_agents",
                               "corrects_agent", "session_id", "turn_number", "source", "source_url"]
            for field in optional_fields:
                if field in kwargs and kwargs[field] is not None:
                    fields.append(field)
                    val = kwargs[field]
                    if isinstance(val, (list, dict)):
                        val = json.dumps(val)
                    elif isinstance(val, bool):
                        val = 1 if val else 0
                    values.append(val)

            placeholders = ", ".join(["?"] * len(values))
            cursor.execute(
                f"INSERT INTO memory_entries ({', '.join(fields)}) VALUES ({placeholders})",
                tuple(values)
            )
            conn.commit()
            return cursor.lastrowid

    @staticmethod
    def search_memory(wing: str = None, room: str = None, agent_id: str = None,
                      topic: str = None, query: str = None, limit: int = 10):
        with get_db() as conn:
            cursor = conn.cursor()
            conditions = []
            params = []
            if wing:
                conditions.append("wing = ?")
                params.append(wing)
            if room:
                conditions.append("room = ?")
                params.append(room)
            if agent_id:
                conditions.append("agent_id = ?")
                params.append(agent_id)
            if topic:
                conditions.append("topic = ?")
                params.append(topic)
            if query:
                conditions.append("content LIKE ?")
                params.append(f"%{query}%")

            where_clause = " AND ".join(conditions) if conditions else "1=1"
            cursor.execute(
                f"SELECT * FROM memory_entries WHERE {where_clause} ORDER BY timestamp DESC LIMIT ?",
                tuple(params) + (limit,)
            )
            return [dict(r) for r in cursor.fetchall()]

    @staticmethod
    def add_concept_node(concept_id: str, subject: str, level: str, display_name: str,
                         description: str = None, curriculum_ref: str = None):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT OR IGNORE INTO concept_nodes
                    (id, subject, level, display_name, description, curriculum_ref)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                (concept_id, subject, level, display_name, description, curriculum_ref)
            )
            conn.commit()

    @staticmethod
    def add_concept_edge(source_id: str, target_id: str, relation: str,
                         weight: float = 1.0, cross_subject: bool = False):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT OR IGNORE INTO concept_edges
                    (source_id, target_id, relation, weight, cross_subject)
                    VALUES (?, ?, ?, ?, ?)""",
                (source_id, target_id, relation, weight, 1 if cross_subject else 0)
            )
            conn.commit()

    @staticmethod
    def get_concept_graph(subject: str = None):
        with get_db() as conn:
            cursor = conn.cursor()
            if subject:
                cursor.execute("SELECT * FROM concept_nodes WHERE subject = ?", (subject,))
            else:
                cursor.execute("SELECT * FROM concept_nodes")
            nodes = [dict(r) for r in cursor.fetchall()]

            if subject:
                cursor.execute(
                    """SELECT e.* FROM concept_edges e
                        JOIN concept_nodes sn ON e.source_id = sn.id
                        JOIN concept_nodes tn ON e.target_id = tn.id
                        WHERE sn.subject = ? AND tn.subject = ?""",
                    (subject, subject)
                )
            else:
                cursor.execute("SELECT * FROM concept_edges")
            edges = [dict(r) for r in cursor.fetchall()]
            return {"nodes": nodes, "edges": edges}

    @staticmethod
    def store_research(agent_id: str, query: str, synthesis: str, source_urls: list = None):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO research_cache (agent_id, query, synthesis, source_urls) VALUES (?, ?, ?, ?)",
                (agent_id, query, synthesis, json.dumps(source_urls or []))
            )
            conn.commit()

    @staticmethod
    def get_cached_research(agent_id: str, query: str):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM research_cache WHERE agent_id = ? AND query = ? ORDER BY created_at DESC LIMIT 1",
                (agent_id, query)
            )
            row = cursor.fetchone()
            return dict(row) if row else None

    @staticmethod
    def record_tutor_effectiveness(agent_id: str, topic: str, approach_used: str = None,
                                    student_rating: int = None, understanding_signal: bool = None,
                                    session_id: str = None):
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """INSERT INTO tutor_effectiveness
                    (agent_id, topic, approach_used, student_rating, understanding_signal, session_id)
                    VALUES (?, ?, ?, ?, ?, ?)""",
                (agent_id, topic, approach_used, student_rating,
                 1 if understanding_signal else 0 if understanding_signal is not None else None,
                 session_id)
            )
            conn.commit()
