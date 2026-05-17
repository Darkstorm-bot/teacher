# MACT v2.0 - Feature Roadmap

## Current Status: Phase 2 Complete ✅

### Completed Features (v1.5)
- ✅ Multi-agent debate loop (5 agents)
- ✅ Structured memory schema (mistakes, mastery, style)
- ✅ Dependency-aware curriculum planning
- ✅ Time estimation per concept
- ✅ PDF ingestion pipeline (concept extraction + graph building)
- ✅ SearXNG integration for unknown topics
- ✅ Real-time knowledge graph visualization
- ✅ Color-coded agent chat stream
- ✅ Progress tracking (0-100% mastered)

---

## 🎯 v2.0 Vision: Adaptive Intelligence Layer

### Core Philosophy Shift
**From:** Static multi-agent tutor  
**To:** Self-improving adaptive learning system

---

## 📋 Phase 3 Features (v2.0 Core)

### 1. **Comprehension Assessment Engine** 🔍
**Problem:** System assumes understanding but never verifies  
**Solution:** Active comprehension checks with adaptive difficulty

#### Features:
- **Auto-generated quizzes** from lesson content
- **Socratic questioning** by Critic agent
- **Confidence calibration** (user rates understanding vs actual performance)
- **Misconception detection** through wrong answer analysis
- **Spaced repetition scheduling** (SM-2 algorithm)

#### Implementation:
```python
class ComprehensionEngine:
    def generate_quiz(self, lesson, bloom_level):
        # Generate questions at appropriate cognitive level
        
    def analyze_wrong_answer(self, question, user_answer, correct):
        # Identify specific misconception
        
    def schedule_review(self, concept, performance):
        # SM-2 spaced repetition algorithm
```

**Priority:** 🔴 CRITICAL  
**Estimated Effort:** 3-4 days  
**Dependencies:** Memory schema (existing), Panel discussion (existing)

---

### 2. **Adaptive Difficulty Adjustment** 📈
**Problem:** One-size-fits-all explanations don't optimize learning  
**Solution:** Real-time difficulty tuning based on performance signals

#### Features:
- **Dynamic Bloom level adjustment** (L1→L5 based on mastery)
- **Analogy density control** (more for struggling users)
- **Technical depth scaling** (equations/code vs intuition)
- **Pacing adaptation** (fast/slow based on attention signals)
- **Challenge point optimization** (Vygotsky's ZPD)

#### Signals to Track:
- Quiz performance (accuracy + time)
- User self-ratings ("I don't get it" buttons)
- Engagement metrics (time on task, re-reads)
- Question complexity (user asks deeper questions = ready for more)

#### Implementation:
```python
class AdaptiveEngine:
    def calculate_zone_of_proximal_development(self, concept, user_state):
        # Find optimal difficulty: not too easy, not too hard
        
    def adjust_explanation_style(self, performance_history):
        # Increase/decrease technical depth
        
    def recommend_next_concept(self, mastery_matrix, dependencies):
        # Optimal learning path selection
```

**Priority:** 🔴 CRITICAL  
**Estimated Effort:** 2-3 days  
**Dependencies:** Comprehension engine, Memory schema

---

### 3. **Multi-Modal Output System** 🎨
**Problem:** Text-only limits learning styles (visual/auditory learners)  
**Solution:** Prepare infrastructure for TTS + Visual generation

#### Features:
- **TTS Integration Hooks** (ready-to-use when you add it)
  - Agent-specific voices (Einstein = calm, Programmer = energetic)
  - Emotion tagging in text for prosody control
  - Pause points for comprehension checks
  
- **Diagram Generation Pipeline**
  - Auto-generate simple SVG diagrams from explanations
  - Flow charts for processes
  - Graph visualizations for relationships
  
- **Code Execution Sandbox** (for Programmer agent)
  - Safe Python execution environment
  - Live output visualization
  - Interactive parameter tweaking

#### Implementation:
```python
class MultimodalOutput:
    def prepare_for_tts(self, text, agent_name):
        # Add SSML tags, emotion markers, pause points
        
    def generate_diagram(self, concept, explanation):
        # Create SVG from structured data
        
    def execute_code_safely(self, code_snippet, inputs):
        # Run in sandbox, return output + visualization
```

**Priority:** 🟡 HIGH (future-proofing)  
**Estimated Effort:** 2 days (hooks only, full TTS/diagrams later)  
**Dependencies:** Panel discussion (existing)

---

### 4. **Learning Analytics Dashboard** 📊
**Problem:** Users can't see their progress patterns  
**Solution:** Actionable insights from learning data

#### Features:
- **Mastery Heatmap** (concepts colored by proficiency)
- **Time Investment Tracker** (actual vs estimated)
- **Weakness Pattern Detection** (e.g., "struggles with abstraction")
- **Learning Velocity Graph** (concepts/week trend)
- **Optimal Study Time Recommendations** (based on performance by time-of-day)
- **Retention Curve Visualization** (forgetting curve tracking)

#### Metrics to Display:
```json
{
  "overall_mastery": 0.67,
  "concepts_learned": 23,
  "total_time_hours": 12.5,
  "average_retention_rate": 0.82,
  "weakest_areas": ["abstraction", "mathematical proofs"],
  "strongest_areas": ["pattern recognition", "analogical thinking"],
  "optimal_study_duration": "25 minutes",
  "best_time_of_day": "morning",
  "predicted_mastery_date": "2025-03-15"
}
```

**Priority:** 🟡 HIGH (user motivation)  
**Estimated Effort:** 3 days  
**Dependencies:** Memory schema, Comprehension engine

---

### 5. **Collaborative Learning Mode** 👥
**Problem:** Learning alone lacks social accountability  
**Solution:** Multi-user study groups with shared goals

#### Features:
- **Study Group Creation** (2-5 users learning same topic)
- **Peer Explanation Exchange** (users teach each other)
- **Group Debates** (users join agent panel as "student advocate")
- **Progress Sharing** (optional leaderboard)
- **Collaborative Problem Solving** (group projects)

#### Implementation:
```python
class CollaborativeLearning:
    def create_study_group(self, topic, users):
        # Match users by pace + complementary strengths
        
    def facilitate_peer_teaching(self, group_id, concept):
        # Assign roles: teacher, student, observer
        
    def moderate_group_debate(self, group_id, topic):
        # Users + agents discuss together
```

**Priority:** 🟢 MEDIUM (nice-to-have)  
**Estimated Effort:** 4-5 days  
**Dependencies:** Multi-user memory schema, Panel discussion

---

### 6. **Advanced Research Capabilities** 🔬
**Problem:** SearXNG gives static results, no deep analysis  
**Solution:** Multi-step research with synthesis

#### Features:
- **Multi-source triangulation** (compare 3+ sources)
- **Contradiction resolution** (when sources disagree)
- **Citation quality scoring** (peer-reviewed > blog posts)
- **Temporal relevance** (prefer recent papers for fast-moving fields)
- **Cross-domain analogy finding** (find similar concepts in other fields)

#### Implementation:
```python
class AdvancedResearch:
    def triangulate_sources(self, query, min_sources=3):
        # Find consensus across multiple sources
        
    def resolve_contradictions(self, conflicting_info):
        # Analyze why sources disagree, present both views
        
    def find_cross_domain_analogies(self, concept, target_field):
        # "Neural networks are like..." in biology, economics, etc.
```

**Priority:** 🟢 MEDIUM (enhancement)  
**Estimated Effort:** 2 days  
**Dependencies:** SearXNG integration (existing)

---

### 7. **Personalization Engine v2** 🎯
**Problem:** Current style profile is static  
**Solution:** Dynamic personalization that evolves with user

#### Features:
- **Learning style evolution tracking** (preferences change over time)
- **Context-aware adaptation** (different styles for different subjects)
- **Motivation state detection** (frustrated → more encouragement)
- **Cognitive load monitoring** (reduce complexity when overwhelmed)
- **Goal-based customization** (exam prep vs casual learning)

#### Implementation:
```python
class PersonalizationV2:
    def detect_frustration(self, interaction_pattern):
        # Analyze response time, question types, self-ratings
        
    def adapt_to_subject_context(self, subject, topic):
        # Math needs more rigor, literature needs more interpretation
        
    def optimize_for_goal(self, goal_type, deadline):
        # Exam cram vs deep understanding strategies
```

**Priority:** 🟡 HIGH (core differentiator)  
**Estimated Effort:** 3 days  
**Dependencies:** Memory schema v2, Analytics dashboard

---

## 🛠️ Infrastructure Upgrades (v2.0 Foundation)

### A. **Memory Schema v2** 💾
**Current:** Basic mistake/mastery tracking  
**Upgrade:** Rich temporal + relational modeling

#### New Fields:
```json
{
  "temporal_patterns": {
    "best_performance_time": "09:00-11:00",
    "attention_decay_curve": [25, 20, 15, 10], // mins
    "optimal_session_length": 25
  },
  "social_learning": {
    "study_groups": ["group_123"],
    "peer_teaching_sessions": 5,
    "collaborative_score": 0.78
  },
  "metacognition": {
    "confidence_calibration": 0.85, // how well user predicts own understanding
    "self_explanation_quality": 0.72,
    "question_asking_frequency": 0.45
  }
}
```

**Effort:** 2 days

---

### B. **Agent System v2** 🤖
**Current:** 5 fixed agents  
**Upgrade:** Dynamic agent activation + specialization

#### New Agents:
1. **Motivator Agent** - Encouragement + growth mindset
2. **Connector Agent** - Cross-domain analogies
3. **Assessor Agent** - Quiz generation + evaluation
4. **Metacognition Coach** - Teaches learning strategies

#### Dynamic Activation:
```python
if user_state.frustration > 0.7:
    activate_agent("Motivator")
    
if topic.cross_domain_potential > 0.6:
    activate_agent("Connector")
    
if lesson.phase == "assessment":
    activate_agent("Assessor")
```

**Effort:** 3 days

---

### C. **API & Backend Scalability** ⚡
**Current:** Single-user, synchronous  
**Upgrade:** Multi-user, async, WebSocket support

#### Requirements:
- **WebSocket server** for real-time chat updates
- **Async task queue** (Celery/RQ) for long-running tasks
- **User authentication** (JWT tokens)
- **Rate limiting** (prevent abuse)
- **Database migration** (SQLite → PostgreSQL for production)

**Effort:** 4-5 days

---

## 📅 Development Timeline

### Sprint 1 (Week 1-2): Assessment Foundation
- [ ] Comprehension Engine (quiz generation, analysis)
- [ ] Memory Schema v2 (temporal patterns)
- [ ] Spaced repetition scheduler

### Sprint 2 (Week 3-4): Adaptation Layer
- [ ] Adaptive Difficulty Engine
- [ ] Personalization v2 (dynamic styles)
- [ ] Agent System v2 (new agents)

### Sprint 3 (Week 5-6): Analytics & Insights
- [ ] Learning Analytics Dashboard
- [ ] Progress visualization components
- [ ] Predictive modeling (mastery dates)

### Sprint 4 (Week 7-8): Multi-Modal & Social
- [ ] TTS hooks + SSML preparation
- [ ] Diagram generation pipeline
- [ ] Collaborative learning mode
- [ ] WebSocket backend

### Sprint 5 (Week 9-10): Polish & Scale
- [ ] Advanced research features
- [ ] API scalability upgrades
- [ ] Performance optimization
- [ ] Documentation + testing

---

## 🎯 Success Metrics for v2.0

| Metric | Current (v1.5) | Target (v2.0) |
|--------|----------------|---------------|
| Learning retention (7-day) | ~60% | >80% |
| User engagement (sessions/week) | ~3 | >5 |
| Mastery velocity (concepts/week) | ~5 | ~8 |
| User satisfaction (self-reported) | ~7/10 | >9/10 |
| Misconception detection rate | ~50% | >85% |
| Adaptive accuracy (right difficulty) | ~65% | >90% |

---

## 🚀 Quick Wins (Can Build in 1-2 Days)

1. **Add "I don't understand" button** → triggers simpler explanation
2. **Session timer** → suggests breaks after 25 mins (Pomodoro)
3. **Daily streak counter** → gamification for motivation
4. **Export progress report** → PDF summary for users
5. **Dark mode** → UI polish

---

## 🔮 Future Vision (v3.0+)

- **Video generation integration** (when tech matures)
- **AR/VR learning environments**
- **Brain-computer interface experiments** (EEG focus detection)
- **Full curriculum coverage** (K-12 + undergraduate)
- **Multilingual support** (teach in 10+ languages)
- **Teacher dashboard** (for classroom use)

---

## 📝 Recommendation: Start Here

**Build Order for Maximum Impact:**

1. **Week 1:** Comprehension Engine + Quiz System
   - Immediate improvement in learning outcomes
   - Enables all adaptive features
   
2. **Week 2:** Adaptive Difficulty + Personalization v2
   - Makes system feel "intelligent"
   - Major user experience upgrade

3. **Week 3:** Analytics Dashboard
   - Visible progress = higher motivation
   - Data-driven insights for users

4. **Week 4:** TTS Hooks + Multi-Modal Prep
   - Future-proofs the system
   - Minimal effort now, huge payoff later

This sequence delivers **measurable learning improvements** first, then **user experience enhancements**, then **future capabilities**.

---

## ❓ Decision Required

Which feature should we build FIRST?

**A.** Comprehension Assessment Engine (quizzes + spaced repetition)  
**B.** Adaptive Difficulty Adjustment (ZPD optimization)  
**C.** Learning Analytics Dashboard (progress visualization)  
**D.** Multi-Modal Output Hooks (TTS/diagram prep)  

Reply with A/B/C/D and I'll start building immediately!
