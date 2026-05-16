"""HF-Agent FastAPI Application - Multi-Agent Tutoring System."""
import uuid
import json
from contextlib import asynccontextmanager
from typing import Optional, List

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from api.core.config import AGENT_CONFIGS, DATA_DIR
from api.core.database import init_db, DatabaseManager
from api.services.memory_palace import MemoryPalace, ContextAssembler
from api.services.knowledge_graph import KnowledgeGraph
from api.services.orchestrator import Orchestrator, AgentSelection
from api.services.agents import AgentRegistry, AgentResponse
from api.services.llm import OllamaClient
from api.services.searxng import TutorResearchEngine
from api.services.curriculum import CurriculumEngine
from api.services.personalization import PersonalizationEngine


# ─── Pydantic Models ───

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    student_id: str = "default"
    message: str
    target_agent: Optional[str] = None


class ChatResponse(BaseModel):
    agent: str
    agent_name: str
    message: str
    topic: str
    subtopic: Optional[str] = None
    teaching_state: str
    protocol: str


class StudentCreate(BaseModel):
    name: str
    hf_year: int = 1
    target_program: str = "BSc AI / Software Engineering"


class ProgressResponse(BaseModel):
    subject: str
    mastery: list
    stats: dict


# ─── Global Services ───

services = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize all services on startup."""
    # Initialize database
    init_db()

    # Initialize services
    services["db"] = DatabaseManager()
    services["memory"] = MemoryPalace()
    services["kg"] = KnowledgeGraph()
    services["orchestrator"] = Orchestrator()
    services["agents"] = AgentRegistry()
    services["llm"] = OllamaClient()
    services["research"] = TutorResearchEngine()
    services["curriculum"] = CurriculumEngine()
    services["personalization"] = PersonalizationEngine()

    # Initialize default student if none exists
    student = services["db"].get_student("default")
    if not student:
        services["db"].create_student("default", "HF Elev", 1)

    # Initialize knowledge graph
    services["kg"].init_default_graph()

    print("✅ HF-Agent services initialized")
    yield

    # Cleanup
    await services["llm"].client.aclose()
    print("👋 HF-Agent shutting down")


app = FastAPI(
    title="HF-Agent API",
    description="Multi-Agent Cognitive Tutoring System for Danish HF Curriculum",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── WebSocket Connection Manager ───

class ConnectionManager:
    def __init__(self):
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id] = websocket

    def disconnect(self, session_id: str):
        self.active_connections.pop(session_id, None)

    async def send_to_session(self, session_id: str, message: dict):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(message)


manager = ConnectionManager()


# ─── Chat Engine ───

async def process_chat(student_id: str, session_id: str, message: str,
                       target_agent: str = None) -> dict:
    """Process a chat message through the full pipeline."""
    orchestrator = services["orchestrator"]
    memory = services["memory"]
    agents = services["agents"]
    llm = services["llm"]
    research = services["research"]
    curriculum = services["curriculum"]
    personalization = services["personalization"]
    db = services["db"]

    # Get or create context
    context = orchestrator.get_or_create_context(session_id, student_id)
    context.turn_count += 1

    # Route to agent
    if target_agent:
        selection = AgentSelection(agent=target_agent, protocol="DIRECT_TUTORING")
    else:
        selection = orchestrator.route(message, context)

    agent = agents.get_agent(selection.agent)
    if not agent:
        return {"error": f"Agent {selection.agent} not found"}

    # Detect topic and subtopic
    topic, _ = orchestrator.classifier.classify(message)
    if not topic:
        topic = context.current_topic or "general"
    subtopic = orchestrator.detect_subtopic(topic, message)

    # Determine level
    student = db.get_student(student_id) or {}
    hf_year = student.get("hf_year", 1)
    if hf_year == 1:
        level = "C"
    elif hf_year == 2:
        level = "B"
    else:
        level = "B"

    # Auto-research if needed
    research_data = None
    if await research.should_research(topic, message):
        research_data = await research.research(selection.agent, message, topic)
        # Store research findings
        if research_data and research_data.get("results"):
            synthesis = "\n".join([f"- {r.get('title', '')}: {r.get('content', '')[:100]}"
                                    for r in research_data["results"][:3]])
            db.store_research(selection.agent, message, synthesis,
                             [r.get("url") for r in research_data["results"]])

    # Assemble context (L0-L6)
    ctx_text = orchestrator.context_assembler.assemble(
        agent_id=selection.agent,
        topic=topic,
        student_query=message,
        student_id=student_id,
        session_id=session_id,
        curriculum_engine=curriculum,
    )

    # Build system prompt
    system_prompt = agent.build_system_prompt(ctx_text, level)
    if hasattr(agent, 'get_level_prompt'):
        system_prompt += f"\n\n{agent.get_level_prompt(level)}"

    # Build user prompt
    user_prompt = f"""Elevens spørgsmål: {message}

Svar på dansk. Følg din undervisningsmetode trin-for-trin."""

    # Generate response via LLM
    full_response = ""
    async for chunk in llm.generate_stream(
        prompt=user_prompt,
        system=system_prompt,
        temperature=0.7,
    ):
        full_response += chunk
        # Stream chunk to WebSocket
        await manager.send_to_session(session_id, {
            "type": "token",
            "text": chunk,
            "agent": selection.agent,
        })

    # Apply personalization
    adapted_response = personalization.adapt_response(full_response, student_id)

    # Update teaching state
    new_state = orchestrator.update_state(context, message, full_response, topic)
    context.current_state = new_state
    context.current_agent = selection.agent
    context.current_topic = topic

    # Store in memory palace
    memory.store(
        content=full_response,
        wing=f"wing_{selection.agent}",
        room=f"room_{topic}",
        agent_id=selection.agent,
        memory_type="explanation",
        topic=topic,
        subtopic=subtopic,
        teaching_state=new_state.value,
        difficulty_level=level,
        session_id=session_id,
        turn_number=context.turn_count,
    )

    # Update student profile
    personalization.update_profile_from_interaction(
        student_id, message, full_response, topic
    )

    # Update mastery
    current_mastery = db.get_mastery(student_id, topic)
    if current_mastery:
        new_score = min(1.0, current_mastery.get("score", 0.5) + 0.05)
    else:
        new_score = 0.3

    subject_for_topic = selection.agent
    db.update_mastery(student_id, topic, subject_for_topic, level, new_score)

    # Store turn in database
    db.add_turn(
        session_id=session_id,
        turn_number=context.turn_count,
        agent_id=selection.agent,
        student_message=message,
        agent_response=full_response,
        topic=topic,
        subtopic=subtopic,
        teaching_state=new_state.value,
        difficulty_level=level,
        protocol=selection.protocol,
    )

    # Format response
    agent_response = agent.format_response(
        adapted_response, topic, subtopic, selection.protocol
    )

    return {
        "agent": selection.agent,
        "agent_name": agent.name,
        "message": adapted_response,
        "topic": topic,
        "subtopic": subtopic,
        "teaching_state": new_state.value,
        "protocol": selection.protocol,
        "mastery_update": {topic: round(new_score, 2)},
    }


# ─── API Routes ───

@app.get("/")
async def root():
    return {"status": "HF-Agent API running", "version": "1.0.0"}


@app.get("/api/v1/health")
async def health_check():
    """Check system health."""
    llm = services["llm"]
    ollama_ok = await llm.check_connection()
    models = await llm.list_models() if ollama_ok else []

    return {
        "status": "healthy",
        "database": "connected",
        "ollama": "connected" if ollama_ok else "disconnected",
        "ollama_host": llm.host,
        "available_models": models,
        "default_model": llm.model,
        "agents": list(services["agents"].agents.keys()),
    }


@app.get("/api/v1/agents")
async def list_agents():
    """List all available tutor agents."""
    return services["agents"].get_agent_info()


@app.get("/api/v1/agents/{agent_id}")
async def get_agent(agent_id: str):
    """Get detailed info about a specific agent."""
    agent = services["agents"].get_agent(agent_id)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} not found")
    return {
        "id": agent_id,
        "name": agent.name,
        "philosophy": agent.philosophy,
        "method": agent.method,
        "color": agent.color,
        "icon": agent.icon,
        "steps": agent.steps,
        "levels": agent.config.get("levels", []),
    }


# ─── Chat Endpoints ───

@app.post("/api/v1/chat")
async def chat(request: ChatRequest):
    """Non-streaming chat endpoint."""
    session_id = request.session_id or f"sess_{uuid.uuid4().hex[:8]}"

    # Create session if new
    existing = services["db"].get_session(session_id)
    if not existing:
        services["db"].create_session(session_id, request.student_id)

    result = await process_chat(
        request.student_id, session_id, request.message, request.target_agent
    )
    return {**result, "session_id": session_id}


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    """Real-time streaming chat via WebSocket."""
    await websocket.accept()
    session_id = None

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "init":
                session_id = data.get("session_id") or f"sess_{uuid.uuid4().hex[:8]}"
                student_id = data.get("student_id", "default")
                await manager.connect(websocket, session_id)

                # Create session if new
                existing = services["db"].get_session(session_id)
                if not existing:
                    services["db"].create_session(session_id, student_id)

                await websocket.send_json({
                    "type": "connected",
                    "session_id": session_id,
                })

            elif data.get("type") == "message":
                session_id = data.get("session_id", session_id)
                student_id = data.get("student_id", "default")
                message = data.get("text", "")
                target_agent = data.get("target_agent")

                if not session_id:
                    await websocket.send_json({
                        "type": "error",
                        "message": "Session not initialized"
                    })
                    continue

                # Send agent_start event
                agent_id = target_agent or "matematik"
                agent = services["agents"].get_agent(agent_id)
                await websocket.send_json({
                    "type": "agent_start",
                    "agent_id": agent_id,
                    "agent_name": agent.name if agent else agent_id,
                    "color": agent.color if agent else "#58a6ff",
                    "icon": agent.icon if agent else "🤖",
                })

                # Process message
                result = await process_chat(student_id, session_id, message, target_agent)

                # Send agent_end event
                await websocket.send_json({
                    "type": "agent_end",
                    "agent_id": result["agent"],
                    "topic_detected": result.get("topic"),
                    "teaching_state": result.get("teaching_state"),
                    "mastery_update": result.get("mastery_update"),
                })

            elif data.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        if session_id:
            manager.disconnect(session_id)
    except Exception as e:
        try:
            await websocket.send_json({
                "type": "error",
                "message": str(e)
            })
        except:
            pass
        if session_id:
            manager.disconnect(session_id)


# ─── Student Profile Endpoints ───

@app.post("/api/v1/students")
async def create_student(data: StudentCreate):
    """Create a new student profile."""
    student_id = f"stud_{uuid.uuid4().hex[:8]}"
    services["db"].create_student(
        student_id, data.name, data.hf_year,
        target_program=data.target_program
    )
    return {"id": student_id, **data.dict()}


@app.get("/api/v1/students/{student_id}")
async def get_student(student_id: str):
    """Get student profile."""
    student = services["db"].get_student(student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student


@app.get("/api/v1/students/{student_id}/progress")
async def get_progress(student_id: str):
    """Get student progress dashboard."""
    dashboard = services["personalization"].get_student_dashboard(student_id)
    if not dashboard:
        raise HTTPException(status_code=404, detail="Student not found")
    return dashboard


@app.get("/api/v1/students/{student_id}/mastery")
async def get_mastery(student_id: str, subject: str = None):
    """Get mastery scores for a student."""
    mastery = services["db"].get_mastery(student_id)
    if subject:
        mastery = [m for m in mastery if m.get("subject") == subject]
    return mastery


@app.get("/api/v1/students/{student_id}/progression/{subject}")
async def check_progression(student_id: str, subject: str, current_level: str = "C"):
    """Check if student can progress to next level."""
    result = services["personalization"].check_progression(
        student_id, subject, current_level
    )
    return result


# ─── Memory Endpoints ───

@app.get("/api/v1/memory/search")
async def search_memory(query: str, wing: str = None, agent: str = None, topic: str = None):
    """Search memory palace."""
    results = services["db"].search_memory(
        wing=wing, agent_id=agent, topic=topic, query=query, limit=20
    )
    return results


@app.get("/api/v1/memory/wings")
async def list_wings():
    """List memory palace wings."""
    return {
        "wings": [
            {"id": "wing_matematik", "name": "Matematik", "color": "#58a6ff"},
            {"id": "wing_fysik", "name": "Fysik", "color": "#3fb950"},
            {"id": "wing_datalogi", "name": "Datalogi", "color": "#d2a8ff"},
            {"id": "wing_kommunikation", "name": "Kommunikation", "color": "#f0883e"},
            {"id": "wing_fælles", "name": "Fælles", "color": "#79c0ff"},
        ]
    }


# ─── Knowledge Graph Endpoints ───

@app.get("/api/v1/knowledge-graph")
async def get_knowledge_graph(subject: str = None):
    """Get the knowledge graph."""
    return services["kg"].get_graph(subject)


@app.get("/api/v1/knowledge-graph/prerequisites/{concept_id}")
async def get_prerequisites(concept_id: str):
    """Get prerequisites for a concept."""
    return services["kg"].get_prerequisites(concept_id)


@app.get("/api/v1/knowledge-graph/bridges/{subject}")
async def get_cross_subject_bridges(subject: str):
    """Get cross-subject bridges."""
    return services["kg"].get_cross_subject_bridges(subject)


# ─── Curriculum Endpoints ───

@app.get("/api/v1/curriculum/{subject}")
async def get_curriculum(subject: str, level: str = None):
    """Get curriculum for a subject."""
    return services["curriculum"].get_subject_curriculum(subject, level)


@app.get("/api/v1/curriculum/{subject}/topics")
async def get_topics(subject: str):
    """Get all topics for a subject."""
    all_topics = services["curriculum"].get_all_topics()
    return all_topics.get(subject, [])


@app.get("/api/v1/curriculum/topics/all")
async def get_all_topics():
    """Get all curriculum topics."""
    return services["curriculum"].get_all_topics()


# ─── Research Endpoints ───

@app.post("/api/v1/research")
async def trigger_research(agent_id: str, query: str, topic: str):
    """Trigger research for a topic."""
    result = await services["research"].research(agent_id, query, topic)
    return result


# ─── Session Endpoints ───

@app.get("/api/v1/sessions/{session_id}")
async def get_session(session_id: str):
    """Get session info."""
    session = services["db"].get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    turns = services["db"].get_recent_turns(session_id, k=100)
    return {**session, "turns": turns}


@app.get("/api/v1/sessions/{session_id}/turns")
async def get_session_turns(session_id: str):
    """Get all turns for a session."""
    return services["db"].get_recent_turns(session_id, k=1000)


# ─── Main ───

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
