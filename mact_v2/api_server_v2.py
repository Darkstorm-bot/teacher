"""
MACT v2.0 API Server
Integrates Phase 1/2 Agents with Phase 3 Quizzes, Analytics, TTS
"""
from fastapi import FastAPI, WebSocket, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import asyncio
import json
from datetime import datetime

# Import v2.0 Modules
from database_schema import db_manager, User, LearningStyleProfile, SpacedRepetitionCard, QuizResult
from comprehension_engine import ComprehensionEngine
from analytics_dashboard import AnalyticsDashboard
from personalization_v2 import PersonalizationEngine
from multimodal_interface import MultiModalInterface

app = FastAPI(title="MACT v2.0 API")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Engines
comprehension = ComprehensionEngine()
analytics = AnalyticsDashboard()
personalization = PersonalizationEngine()
multimodal = MultiModalInterface()

# === DATA MODELS ===
class QuizRequest(BaseModel):
    user_id: int
    concept_id: int
    difficulty: Optional[float] = 0.5
    question_count: int = 5

class QuizSubmission(BaseModel):
    quiz_id: int
    user_id: int
    answers: Dict[int, str]  # question_id -> answer

class ReviewRequest(BaseModel):
    user_id: int
    count: int = 10

class TTSRequest(BaseModel):
    text: str
    voice: Optional[str] = "default"

class DiagramRequest(BaseModel):
    concept_id: int
    style: Optional[str] = "mermaid"

# === QUIZ & SPACED REPETITION ENDPOINTS ===
@app.post("/quiz/generate")
async def generate_quiz(request: QuizRequest):
    """Generate adaptive quiz based on ZPD"""
    try:
        # Get user style for personalization
        style = personalization.get_user_profile(request.user_id)
        
        # Generate questions
        quiz = comprehension.generate_quiz(
            concept_id=request.concept_id,
            difficulty=request.difficulty,
            count=request.question_count,
            user_style=style
        )
        
        return {"status": "success", "quiz": quiz}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/quiz/submit")
async def submit_quiz(request: QuizSubmission, background_tasks: BackgroundTasks):
    """Grade quiz and update spaced repetition"""
    try:
        result = comprehension.grade_quiz(request.quiz_id, request.answers)
        
        # Update SM-2 cards
        background_tasks.add_task(
            comprehension.update_spaced_repetition,
            user_id=request.user_id,
            quiz_result=result
        )
        
        # Update analytics
        background_tasks.add_task(
            analytics.record_quiz_result,
            user_id=request.user_id,
            result=result
        )
        
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/review/queue")
async def get_review_queue(request: ReviewRequest):
    """Get spaced repetition cards due for review"""
    try:
        queue = comprehension.get_review_queue(request.user_id, request.count)
        return {"status": "success", "cards": queue}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/review/submit")
async def submit_review(user_id: int, card_id: int, rating: int):
    """Submit SM-2 review rating (0-5)"""
    try:
        updated_card = comprehension.process_review(user_id, card_id, rating)
        return {"status": "success", "card": updated_card}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# === ANALYTICS ENDPOINTS ===
@app.get("/analytics/dashboard/{user_id}")
async def get_dashboard(user_id: int):
    """Get complete analytics dashboard data"""
    try:
        dashboard = analytics.generate_dashboard(user_id)
        return {"status": "success", "data": dashboard}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/knowledge-radar/{user_id}")
async def get_knowledge_radar(user_id: int):
    """Get knowledge radar for visualization"""
    try:
        radar = analytics.get_knowledge_radar(user_id)
        return {"status": "success", "radar": radar}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/analytics/forecast/{user_id}")
async def get_mastery_forecast(user_id: int):
    """Predict mastery dates for concepts"""
    try:
        forecast = analytics.predict_mastery(user_id)
        return {"status": "success", "forecast": forecast}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# === PERSONALIZATION ENDPOINTS ===
@app.get("/profile/{user_id}")
async def get_profile(user_id: int):
    """Get user learning profile"""
    try:
        profile = personalization.get_user_profile(user_id)
        return {"status": "success", "profile": profile}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/profile/update")
async def update_profile(user_id: int, preferences: Dict[str, float]):
    """Update learning style preferences"""
    try:
        profile = personalization.update_profile(user_id, preferences)
        return {"status": "success", "profile": profile}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/cognitive-load/report")
async def report_cognitive_load(user_id: int, load_score: float):
    """Report cognitive load during session"""
    try:
        personalization.track_cognitive_load(user_id, load_score)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# === MULTI-MODAL ENDPOINTS ===
@app.post("/tts/generate")
async def generate_tts(request: TTSRequest):
    """Generate TTS audio stream"""
    try:
        audio_data = multimodal.generate_speech(request.text, request.voice)
        return {"status": "success", "audio": audio_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/diagram/generate")
async def generate_diagram(request: DiagramRequest):
    """Generate diagram DSL code"""
    try:
        diagram = multimodal.generate_diagram(request.concept_id, request.style)
        return {"status": "success", "diagram": diagram}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/video/script")
async def generate_video_script(concept_id: int):
    """Generate video script for content"""
    try:
        script = multimodal.prepare_video_script(concept_id)
        return {"status": "success", "script": script}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# === WEBSOCKET FOR REAL-TIME UPDATES ===
@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: int):
    await websocket.accept()
    
    # Send initial state
    await websocket.send_json({
        "type": "connected",
        "user_id": user_id
    })
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Handle real-time events
            if message["type"] == "start_session":
                # Start learning session tracking
                pass
            elif message["type"] == "quiz_complete":
                # Push analytics update
                dashboard = analytics.generate_dashboard(user_id)
                await websocket.send_json({
                    "type": "analytics_update",
                    "data": dashboard
                })
            elif message["type"] == "review_complete":
                # Push SR card update
                pass
                
    except Exception as e:
        print(f"WebSocket error: {e}")

# === HEALTH CHECK ===
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "version": "2.0",
        "modules": {
            "comprehension": "active",
            "analytics": "active",
            "personalization": "active",
            "multimodal": "active",
            "database": "connected"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
