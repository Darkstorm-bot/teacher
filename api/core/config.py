"""HF-Agent Configuration"""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"


def _load_dotenv_file(path: Path) -> None:
    """Load simple KEY=VALUE pairs from .env without adding a dependency."""
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv_file(BASE_DIR / ".env")

OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "qwen2.5:14b-instruct-q4_K_M")
SEARXNG_URL = os.getenv("SEARXNG_URL", "http://localhost:8080")
LMSTUDIO_HOST = os.getenv("LMSTUDIO_HOST", "")
"""
Optional: set `LMSTUDIO_HOST` to point to an LMStudio instance (e.g. http://localhost:8081).
If present, the LLM client will prefer LMStudio over other local backends.
"""
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{DATA_DIR}/hf_agent.db")
PALACE_PATH = DATA_DIR / "mempalace"
CHROMA_PATH = DATA_DIR / "chromadb"

# Danish HF Curriculum Level Markers
LEVEL_MARKERS = {
    "C": ["grundlæggende", "introducere", "kende til", "anvende simple", "forstå"],
    "B": ["redegøre for", "analysere", "anvende", "demonstrere", " forklare"],
    "A": ["vurdere", "bevise", "perspektivere", "reflektere kritisk", "generalisere"],
}

# Agent configurations
AGENT_CONFIGS = {
    "matematik": {
        "name": "Matematik-Tutoren",
        "language": "da",
        "philosophy": "concrete_to_abstract",
        "method": "spiral_progression",
        "color": "#58a6ff",
        "icon": "📐",
        "levels": ["C", "B", "A"],
        "steps": [
            "1. Start med et dagligdags eksempel",
            "2. Tegn grafen / visualiser problemet",
            "3. Identificer det matematiske mønster",
            "4. Indfør den formelle notation gradvist",
            "5. Løs et eksempel trin-for-trin med eleven",
            "6. Giv et lignende problem med én ændring",
            "7. Generaliser: 'Hvad er reglen her?'",
            "8. Forbind til næste emne i læreplanen",
        ],
    },
    "fysik": {
        "name": "Fysik-Tutoren",
        "language": "da",
        "philosophy": "thought_experiment_first",
        "method": "phenomenon_to_principle_to_math",
        "color": "#3fb950",
        "icon": "⚛️",
        "levels": ["C", "B"],
        "steps": [
            "1. Vis det fysiske fænomen",
            "2. Stil spørgsmålet: 'Hvorfor sker det?'",
            "3. Lad eleven gætte (aktivér forforståelse)",
            "4. Introducér det fysiske princip med et tankeeksperiment",
            "5. Vis at matematikken følger af princippet",
            "6. Beregn med konkrete tal (SI-enheder!)",
            "7. Forbind til teknologi eller natur eleven kender",
        ],
    },
    "datalogi": {
        "name": "Datalogi-Tutoren",
        "language": "da",
        "philosophy": "build_to_understand",
        "method": "incremental_project_based",
        "color": "#d2a8ff",
        "icon": "💻",
        "levels": ["C", "B", "A"],
        "steps": [
            "1. Vis det færdige produkt: 'Vi skal bygge dette'",
            "2. Nedbryd i delproblemer (dekomposition)",
            "3. Kode den simpleste del først (MVP)",
            "4. Test og fejlret sammen (debugging som læringsværktøj)",
            "5. Tilføj kompleksitet gradvist",
            "6. Reflektér: 'Hvad er mønsteret her?' (abstraktion)",
            "7. Forbind til universitets-niveau",
        ],
    },
    "kommunikation": {
        "name": "Kommunikation-Tutoren",
        "language": "da",
        "philosophy": "analyse_produce_reflect",
        "method": "genre_aware_scaffolding",
        "color": "#f0883e",
        "icon": "📝",
        "levels": ["C", "B", "A"],
        "steps": [
            "1. Vis et autentisk dansk eksempel",
            "2. Analysér sammen: 'Hvad er afsenderens hensigt?'",
            "3. Identificér virkemidler (retoriske, visuelle, sproglige)",
            "4. Øv: Skriv din egen version",
            "5. Peer review: Tutor giver feedback som sensor",
            "6. Revider og forbedre",
        ],
    },
}

# Routing table: topic → agent
ROUTING_TABLE = {
    "differentialregning": "matematik",
    "integralregning": "matematik",
    "vektorer": "matematik",
    "statistik": "matematik",
    "funktioner": "matematik",
    "trigonometri": "matematik",
    "sandsynlighed": "matematik",
    "mekanik": "fysik",
    "termodynamik": "fysik",
    "bølger": "fysik",
    "elektricitet": "fysik",
    "atomfysik": "fysik",
    "energi": "fysik",
    "python": "datalogi",
    "algoritmer": "datalogi",
    "datastrukturer": "datalogi",
    "logisk_tænkning": "datalogi",
    "digitalt_design": "datalogi",
    "argumentation": "kommunikation",
    "medieanalyse": "kommunikation",
    "retorik": "kommunikation",
    "skriftlig_fremstilling": "kommunikation",
}

# Progression gates
PROGRESSION_GATES = {
    "C_to_B": {
        "min_mastery": 0.75,
        "min_problems_solved": 20,
        "no_critical_gaps": True,
    },
    "B_to_A": {
        "min_mastery": 0.80,
        "min_problems_solved": 30,
        "no_critical_gaps": True,
        "cross_subject_connections": 3,
    },
}
