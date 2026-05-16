# 🎓 HF-Tutor: Multi-Agent AI Tutoring System

Multi-agent tutoring system with personality-driven tutors (Einstein, Feynman, Knuth) teaching Danish HF subjects through panel discussions, peer review, and autonomous research.

## Features

- **Deep Personalities**: Big Five traits + teaching-specific dimensions
- **Panel Discussions**: Tutors debate each other with 7 stance types
- **Pedagogical Decomposition**: Domain-specific teaching strategies
- **Peer Review**: Agents critique and improve explanations
- **Autonomous Research**: SearXNG integration with verification
- **Student Modeling**: Cognitive state tracking & forgetting curves
- **Meta-Cognition**: Learning pattern detection & reflection
- **Memory Palace**: Spatial memory with cross-agent sharing

## Quick Start

```bash
./setup.sh          # One-time setup
python main.py      # Start backend
npm run dev         # Start frontend
```

## Architecture

- **Backend**: FastAPI + Ollama (qwen2.5:14b, llama3.2:3b)
- **Frontend**: React + TypeScript + Vite
- **Memory**: SQLite + Memory Palace (spatial) + ChromaDB
- **Research**: SearXNG (Docker)

## Agents

| Agent | Domain | Personality |
|-------|--------|-------------|
| Matematik | Math | Einstein |
| Fysik | Physics | Feynman |
| Datalogi | CS | Knuth |
| Kommunikation | Danish | Montessori |

See full README for detailed documentation.
