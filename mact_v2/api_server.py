"""
MACT v2.0 - Integrated API Server
Connects Comprehension, Analytics, Personalization, and MultiModal features.
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import jwt
import datetime
import asyncio
import json

# Import v2.0 Modules
from database import init_db, get_engine, User, QuizResult, SpacedRepetitionCard, LearningStyleProfile
from comprehension_engine import ComprehensionEngine
from analytics_dashboard import AnalyticsDashboard
from personalization_v2 import PersonalizationEngine
from multimodal_interface import MultiModalInterface

app = FastAPI(title="MACT v2.0 API")

# CORS for Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Components
db_session_local = init_db()
comprehension = ComprehensionEngine()
analytics = AnalyticsDashboard()
personalization = PersonalizationEngine()
multimodal = MultiModalInterface()

# --- Auth Helper ---
SECRET_KEY = "mact_v2_secret_key_change_in_prod"

def create_token(user_id: int):
    return jwt.encode(
        {"user_id": user_id, "exp": datetime.datetime.utcnow() + datetime.timedelta(days=7)},
        SECRET_KEY, algorithm="HS256"
    )

def verify_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

# --- Pydantic Models ---
class QuizRequest(BaseModel):
    user_id: int
    concept_id: str
    question_type: str = "MCQ"
    difficulty: float = 0.5

class QuizSubmission(BaseModel):
    quiz_id: int
    user_answer: str
    time_taken: float

class ReviewRequest(BaseModel):
    user_id: int
    limit: int = 10

class TTSRequest(BaseModel):
    text: str
    voice: str = "default"

class DiagramRequest(BaseModel):
    concept_ids: List[str]
    style: str = "mermaid"

# --- API Routes ---

@app.get("/health")
def health_check():
    return {"status": "ok", "version": "2.0"}

@app.post("/auth/login")
def login(username: str):
    # Simplified auth for demo (create user if not exists)
    db = db_session_local()
    user = db.query(User).filter(User.username == username).first()
    if not user:
        user = User(username=username)
        db.add(user)
        db.commit()
        db.refresh(user)
    token = create_token(user.id)
    return {"access_token": token, "user_id": user.id}

@app.post("/quiz/generate")
def generate_quiz(req: QuizRequest):
    """Generate adaptive quiz based on ZPD"""
    style = personalization.get_user_style(req.user_id)
    quiz = comprehension.generate_quiz(
        concept_id=req.concept_id,
        question_type=req.question_type,
        difficulty=req.difficulty,
        user_style=style
    )
    return quiz

@app.post("/quiz/submit")
def submit_quiz(req: QuizSubmission, background_tasks: BackgroundTasks):
    """Submit answer, update spaced repetition, trigger analytics"""
    result = comprehension.submit_answer(
        quiz_id=req.quiz_id,
        user_answer=req.user_answer,
        time_taken=req.time_taken
    )
    
    # Update spaced repetition card
    background_tasks.add_task(
        comprehension.update_spaced_repetition,
        quiz_id=req.quiz_id,
        is_correct=result["is_correct"]
    )
    
    # Log to analytics
    background_tasks.add_task(
        analytics.log_quiz_result,
        user_id=result["user_id"],
        data=result
    )
    
    return result

@app.get("/review/queue")
def get_review_queue(req: ReviewRequest):
    """Get cards due for review today"""
    return comprehension.get_due_cards(req.user_id, limit=req.limit)

@app.post("/review/grade")
def grade_review(card_id: int, quality: int):
    """Grade review card (0-5 scale) for SM-2"""
    return comprehension.process_review(card_id, quality)

@app.get("/analytics/dashboard/{user_id}")
def get_dashboard(user_id: int):
    """Full analytics dashboard data"""
    return analytics.get_full_dashboard(user_id)

@app.get("/analytics/forecast/{user_id}")
def get_forecast(user_id: int):
    """Predict mastery dates"""
    return analytics.predict_mastery(user_id)

@app.get("/personalization/profile/{user_id}")
def get_profile(user_id: int):
    """Get current learning style profile"""
    return personalization.get_user_style(user_id)

@app.post("/personalization/update")
def update_profile(user_id: int, metrics: Dict[str, float]):
    """Update style based on recent session"""
    return personalization.update_style(user_id, metrics)

@app.post("/tts/generate")
def generate_tts(req: TTSRequest):
    """Prepare text for TTS engine"""
    return multimodal.prepare_tts(req.text, req.voice)

@app.post("/diagram/generate")
def generate_diagram(req: DiagramRequest):
    """Generate Mermaid/Graphviz diagram code"""
    return multimodal.generate_diagram(req.concept_ids, req.style)

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data)
            
            # Handle real-time events
            if msg["type"] == "cognitive_load_update":
                personalization.track_cognitive_load(user_id, msg["score"])
                await websocket.send_json({"status": "load_updated"})
                
            elif msg["type"] == "request_hint":
                hint = comprehension.get_hint(msg["quiz_id"])
                await websocket.send_json({"hint": hint})
                
    except WebSocketDisconnect:
        print(f"User {user_id} disconnected")

if __name__ == "__main__":
    import uvicorn
    print("Starting MACT v2.0 API Server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
