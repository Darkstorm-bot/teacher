# MACT - Multi-Agent Cognitive Tutor

A personalized multi-agent tutoring system with structured reasoning, memory-driven personalization, and visual progress tracking.

## 🏗️ System Architecture

```
User Input
    ↓
Orchestrator (main_system.py)
    ↓
[Memory Recall - MemPalace]
    ↓
Curriculum Engine → Lesson Plan with Time Estimates
    ↓
Panel Discussion:
  - Teacher → Structure
  - Simplifier (Einstein) → Intuition/Analogy
  - Builder (Programmer) → Technical Breakdown
  - Critic → Error Detection
  - Synthesizer → Final Output
    ↓
[Memory Store - Validated Only]
    ↓
Canvas UI (Real-time Visualization)
```

## 📁 Core Components

### 1. Curriculum Engine (`curriculum_engine.py`)
- **Dependency Resolver**: Topological sort ensures prerequisites before advanced topics
- **Time Estimation**: `Time = Base × Difficulty × (1 - Mastery)`
- **Learning Path Generator**: Creates day-by-day roadmaps

### 2. Memory Schema (`memory_schema.py`)
- **Misconception Log**: Tracks specific errors with frequency
- **Style Profile**: Stores preferred learning mode (analogy/math/code/visual)
- **Mastery Matrix**: 0.0-1.0 scores for each concept with exponential smoothing

### 3. Panel Discussion (`panel_discussion.py`)
- **Strict Turn-Taking**: Teacher → Simplifier → Builder → Critic → Refinement
- **Conflict Detection**: Triggers extra rounds if disagreement > threshold
- **Hard-Constrained Personas**: Prevents personality blending in 8B models

### 4. Canvas UI (`frontend/index.html`)
- **Left Pane**: Interactive D3.js knowledge graph (nodes light up as you learn)
- **Right Pane**: Multi-agent chat stream with color-coded agents
- **Future Hooks**: TTS and video generation buttons ready for integration

### 5. System Integrator (`main_system.py`)
- Connects all 4 layers
- Provides unified API for learning topics
- Manages PDF ingestion workflow

## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- MemPalace installed and configured
- Local LLM (Mistral 7B / Llama 3 8B / Mixtral recommended)

### Run the System

```bash
# Test with mock clients
python main_system.py

# Serve frontend (in separate terminal)
cd frontend
python -m http.server 8000
# Open http://localhost:8000
```

### Integration Example

```python
from main_system import MACTSystem

# Initialize with real clients
mact = MACTSystem(llm_client, mempalace_client)

# Set user preferences
mact.memory.update_style_profile({
    "preferred_mode": "analogy",
    "pace": "medium",
    "attention_span_mins": 25
})

# Learn a topic
result = mact.learn_topic("Neural Networks")
print(result['final_explanation'])

# Get dashboard data for frontend
dashboard = mact.get_dashboard_data()
# Send to frontend via WebSocket/REST
```

## 📊 Features

### ✅ Implemented
- [x] Multi-agent debate loop with 5 specialized agents
- [x] Structured memory schema (mistakes, mastery, style)
- [x] Dependency-aware curriculum planning
- [x] Time estimation per concept
- [x] Real-time knowledge graph visualization
- [x] Color-coded agent chat stream
- [x] Progress tracking (0-100% mastered)

### 🔜 Future Extensions
- [ ] PDF ingestion pipeline (concept extraction + graph building)
- [ ] SearXNG integration for unknown topics
- [ ] TTS integration (hooks ready in UI)
- [ ] Video generation (hooks ready in UI)
- [ ] Quiz-based mastery assessment
- [ ] Adaptive difficulty adjustment

## 🎯 Agent Roles

| Agent | Role | Constraint |
|-------|------|------------|
| **Teacher** | Curriculum structure | Never explain, only organize |
| **Simplifier** | Intuition/analogies | No equations first |
| **Builder** | Technical precision | Step-by-step decomposition |
| **Critic** | Error detection | MUST find flaws |
| **Synthesizer** | Final output | Merge only, no new info |

## 🧠 Key Insights

1. **Structure > Model Size**: 8B models work well with hard constraints
2. **Memory Quality > Quantity**: Store only validated learning signals
3. **Debate > Explanation**: Conflict drives clarity
4. **Personalization > Personalities**: Adapt to user, not vice versa

## 📝 License

MIT License - Build your own personalized tutor!
