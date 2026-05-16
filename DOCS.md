# HF-Tutor Complete Documentation

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Features](#features)
4. [Installation](#installation)
5. [Configuration](#configuration)
6. [API Reference](#api-reference)
7. [Agent Personalities](#agent-personalities)
8. [Teaching Methods](#teaching-methods)

## Overview

HF-Tutor is a multi-agent AI tutoring system for Danish HF (Higher Preparatory Examination) students. It features personality-driven tutors based on famous scientists who engage in panel discussions, peer review, and autonomous research.

## Architecture

See README.md for architecture diagram.

## Features

### 1. Deep Personality System
- Big Five traits (Openness, Conscientiousness, Extraversion, Agreeableness, Neuroticism)
- Teaching-specific traits (Patience, Humor, Rigor, Abstraction preference)
- Communication style (Verbosity, Socratic ratio, Feedback directness)

### 2. Panel Discussions
Tutors engage in real debates with stances:
- INITIAL_STATEMENT
- AGREE_AND_EXTEND
- RESPECTFUL_DISAGREEMENT
- ASK_CLARIFYING_QUESTION
- PROVIDE_COUNTEREXAMPLE
- SUPPORTIVE_ECHO
- SYNTHESIZE

### 3. Pedagogical Decomposition
Domain-specific strategies:
- **Matematik**: Concrete → Abstract, Spiral Progression
- **Fysik**: Thought Experiment First
- **Datalogi**: Build to Understand
- **Kommunikation**: Analyze → Produce → Reflect

### 4. Peer Review
Multi-criteria evaluation:
- Accuracy (0-10)
- Clarity (0-10)
- Completeness (0-10)
- Pedagogical Soundness (0-10)
- Level Appropriateness (0-10)

### 5. Autonomous Research
6-phase verification:
1. Multi-query search
2. Source credibility scoring
3. Claim extraction
4. Consensus detection
5. Contradiction flagging
6. Confidence scoring

### 6. Student Modeling
Tracks:
- Cognitive states (FOCUSED, CONFUSED, FRUSTRATED, BORED, ENGAGED)
- Knowledge components with mastery scores
- Ebbinghaus forgetting curve
- Burnout risk prediction

### 7. Meta-Cognition
- Learning pattern detection
- Question-asking behavior analysis
- Error recovery tracking
- Conversation quality analytics

## Installation

Run the setup script:
```bash
./setup.sh
```

Manual installation:
```bash
# Python dependencies
pip install -r requirements.txt

# Node.js dependencies
npm install

# Ollama models
ollama pull qwen2.5:14b-instruct-q4_K_M
ollama pull llama3.2:3b
ollama pull mistral:7b-instruct

# SearXNG (optional)
docker-compose up -d searxng
```

## Configuration

Create `.env` file:
```bash
OLLAMA_HOST=http://localhost:11434
DEFAULT_MODEL=qwen2.5:14b-instruct-q4_K_M
SEARXNG_URL=http://localhost:8080
DATABASE_URL=sqlite:///data/hf_agent.db
PALACE_PATH=data/mempalace
CHROMA_PATH=data/chromadb
```

## API Reference

### Chat Endpoints
- `POST /api/chat/message` - Send message
- `GET /api/chat/history/{student_id}` - Get history
- `DELETE /api/chat/history/{student_id}` - Clear history

### Student Endpoints
- `GET /api/students/{student_id}` - Get profile
- `PUT /api/students/{student_id}` - Update profile
- `GET /api/students/{student_id}/progress` - Get progress

## Agent Personalities

### Einstein (Matematik)
- Openness: 0.95
- Patience: 0.9
- Socratic ratio: 0.8
- Style: Abstract thinking, thought experiments

### Feynman (Fysik)
- Extraversion: 0.9
- Humor: 0.8
- Style: Concrete examples, challenging questions

### Knuth (Datalogi)
- Conscientiousness: 0.95
- Rigor: 0.95
- Style: Detail-oriented, systematic

### Montessori (Kommunikation)
- Agreeableness: 0.9
- Patience: 0.95
- Style: Student-centered, gentle guidance

## Teaching Methods

### State Machine
1. ASSESSING → 2. SCAFFOLDING → 3. EXPLAINING → 4. RE_EXPLAINING → 5. CHALLENGING → 6. SYNTHESIZING → 7. META_REFLECTING

### Spiral Progression
Returns to concepts at increasing depth:
- Cycle 1: Intuition (rigor: 0.2)
- Cycle 2: Procedure (rigor: 0.5)
- Cycle 3: Proof (rigor: 0.9)
