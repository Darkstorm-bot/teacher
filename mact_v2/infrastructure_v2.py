"""
MACT v2.0 - Infrastructure Upgrades
Memory Schema v2, Scalable API Server with WebSocket, Async Tasks, Multi-User Auth
"""

import json
import asyncio
import jwt
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import hashlib


# ==================== MEMORY SCHEMA V2 ====================

@dataclass
class TemporalPattern:
    """Track when user learns best"""
    hour_of_day: int
    day_of_week: int
    avg_performance: float
    session_duration_minutes: int
    frequency: int  # Number of sessions at this time


@dataclass
class MetacognitionRecord:
    """User's self-reflection on learning"""
    timestamp: str
    concept_id: str
    self_reported_confidence: float  # 0.0-1.0
    actual_performance: float  # Quiz score
    calibration_error: float  # Difference between confidence and performance
    reflection_notes: str


@dataclass
class AdvancedMemorySchema:
    """Enhanced memory structure for v2.0"""
    user_id: str
    
    # Core learning data
    mastery_matrix: Dict[str, float]  # concept_id -> mastery score
    
    # Temporal patterns (when user learns best)
    temporal_patterns: List[TemporalPattern]
    
    # Metacognition tracking
    metacognition_log: List[MetacognitionRecord]
    
    # Style evolution over time
    style_history: List[Dict]  # Timestamped style preferences
    
    # Social learning (for collaborative features)
    study_groups: List[str]  # Group IDs
    peer_interactions: List[Dict]
    
    # System metadata
    created_at: str
    updated_at: str
    version: str = "2.0"


class MemoryManagerV2:
    def __init__(self, storage_backend=None):
        self.storage = storage_backend  # MemPalace or other
        self.user_schemas: Dict[str, AdvancedMemorySchema] = {}
        
    def create_user_schema(self, user_id: str) -> AdvancedMemorySchema:
        """Initialize memory schema for new user"""
        schema = AdvancedMemorySchema(
            user_id=user_id,
            mastery_matrix={},
            temporal_patterns=[],
            metacognition_log=[],
            style_history=[],
            study_groups=[],
            peer_interactions=[],
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        self.user_schemas[user_id] = schema
        
        if self.storage:
            self.storage.store(f"user_schema_{user_id}", asdict(schema))
        
        return schema
    
    def update_mastery(self, user_id: str, concept_id: str, score: float):
        """Update concept mastery with exponential moving average"""
        if user_id not in self.user_schemas:
            self.create_user_schema(user_id)
        
        schema = self.user_schemas[user_id]
        
        # Exponential moving average (alpha=0.3)
        current = schema.mastery_matrix.get(concept_id, 0.0)
        new_mastery = 0.3 * score + 0.7 * current
        
        schema.mastery_matrix[concept_id] = min(1.0, max(0.0, new_mastery))
        schema.updated_at = datetime.now().isoformat()
        
        # Save to storage
        if self.storage:
            self.storage.store(f"user_schema_{user_id}", asdict(schema))
    
    def log_metacognition(
        self,
        user_id: str,
        concept_id: str,
        self_confidence: float,
        actual_score: float,
        notes: str = ""
    ):
        """Log metacognitive reflection"""
        if user_id not in self.user_schemas:
            self.create_user_schema(user_id)
        
        schema = self.user_schemas[user_id]
        
        record = MetacognitionRecord(
            timestamp=datetime.now().isoformat(),
            concept_id=concept_id,
            self_reported_confidence=self_confidence,
            actual_performance=actual_score,
            calibration_error=abs(self_confidence - actual_score),
            reflection_notes=notes
        )
        
        schema.metacognition_log.append(record)
        
        # Keep only last 50 records
        if len(schema.metacognition_log) > 50:
            schema.metacognition_log = schema.metacognition_log[-50:]
        
        schema.updated_at = datetime.now().isoformat()
        
        if self.storage:
            self.storage.store(f"user_schema_{user_id}", asdict(schema))
        
        return record
    
    def analyze_temporal_patterns(self, user_id: str) -> Dict:
        """Analyze when user performs best"""
        if user_id not in self.user_schemas:
            return {"best_hour": 9, "best_day": 2}  # Default: Tuesday 9am
        
        # This would analyze session timestamps vs performance
        # Simplified for demo
        return {
            "best_hour": 10,
            "best_day": 3,
            "recommendation": "Schedule challenging topics in late morning"
        }
    
    def get_calibration_score(self, user_id: str) -> float:
        """How well does user judge their own understanding?"""
        if user_id not in self.user_schemas:
            return 0.5
        
        schema = self.user_schemas[user_id]
        
        if not schema.metacognition_log:
            return 0.5
        
        # Average calibration error (lower is better)
        avg_error = sum(
            r.calibration_error 
            for r in schema.metacognition_log[-20:]  # Last 20 reflections
        ) / len(schema.metacognition_log[-20:])
        
        # Convert to calibration score (1.0 = perfect calibration)
        return max(0.0, 1.0 - avg_error)


# ==================== AUTH SYSTEM ====================

class AuthManager:
    def __init__(self, secret_key: str = "mact_secret_key_v2"):
        self.secret_key = secret_key
        self.users: Dict[str, Dict] = {}
        self.sessions: Dict[str, Dict] = {}
        
    def register_user(self, username: str, password: str, email: str) -> Dict:
        """Register new user"""
        if username in self.users:
            raise ValueError("Username already exists")
        
        # Hash password (in production use bcrypt/argon2)
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        user = {
            "user_id": f"user_{hashlib.md5(username.encode()).hexdigest()[:8]}",
            "username": username,
            "email": email,
            "password_hash": password_hash,
            "created_at": datetime.now().isoformat(),
            "role": "student",
            "is_active": True
        }
        
        self.users[username] = user
        
        return {
            "user_id": user["user_id"],
            "username": username,
            "message": "User registered successfully"
        }
    
    def login(self, username: str, password: str) -> Dict:
        """Authenticate user and return JWT token"""
        if username not in self.users:
            raise ValueError("Invalid credentials")
        
        user = self.users[username]
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        if password_hash != user["password_hash"]:
            raise ValueError("Invalid credentials")
        
        # Generate JWT token
        token_payload = {
            "user_id": user["user_id"],
            "username": username,
            "exp": datetime.now() + timedelta(hours=24),
            "iat": datetime.now()
        }
        
        token = jwt.encode(token_payload, self.secret_key, algorithm="HS256")
        
        # Store session
        session_id = hashlib.md5(token.encode()).hexdigest()
        self.sessions[session_id] = {
            "user_id": user["user_id"],
            "created_at": datetime.now().isoformat(),
            "expires_at": (datetime.now() + timedelta(hours=24)).isoformat()
        }
        
        return {
            "access_token": token,
            "token_type": "bearer",
            "expires_in": 86400,
            "user_id": user["user_id"]
        }
    
    def verify_token(self, token: str) -> Optional[Dict]:
        """Verify JWT token and return payload"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            return None
        except jwt.InvalidTokenError:
            return None


# ==================== WEBSOCKET MANAGER ====================

class WebSocketManager:
    def __init__(self):
        self.active_connections: Dict[str, Any] = {}  # user_id -> connection
        self.pending_messages: Dict[str, List[Dict]] = {}  # user_id -> messages
        
    async def connect(self, user_id: str, websocket):
        """Accept websocket connection"""
        await websocket.accept()
        self.active_connections[user_id] = websocket
        
        # Send any pending messages
        if user_id in self.pending_messages:
            for msg in self.pending_messages[user_id]:
                await self.send_to_user(user_id, msg)
            del self.pending_messages[user_id]
    
    def disconnect(self, user_id: str):
        """Remove websocket connection"""
        if user_id in self.active_connections:
            del self.active_connections[user_id]
    
    async def send_to_user(self, user_id: str, message: Dict):
        """Send message to specific user"""
        if user_id in self.active_connections:
            websocket = self.active_connections[user_id]
            await websocket.send_json(message)
        else:
            # Queue message for later
            if user_id not in self.pending_messages:
                self.pending_messages[user_id] = []
            self.pending_messages[user_id].append(message)
    
    async def broadcast(self, message: Dict, exclude: List[str] = None):
        """Broadcast message to all connected users"""
        exclude = exclude or []
        for user_id in list(self.active_connections.keys()):
            if user_id not in exclude:
                await self.send_to_user(user_id, message)
    
    async def send_agent_update(
        self, 
        user_id: str, 
        agent_name: str, 
        content: str,
        metadata: Dict = None
    ):
        """Send agent turn update to user"""
        message = {
            "type": "agent_turn",
            "agent": agent_name,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        await self.send_to_user(user_id, message)
    
    async def send_progress_update(
        self,
        user_id: str,
        step: str,
        progress: float,
        total_steps: int
    ):
        """Send progress update"""
        message = {
            "type": "progress",
            "step": step,
            "progress": progress,
            "total_steps": total_steps,
            "timestamp": datetime.now().isoformat()
        }
        await self.send_to_user(user_id, message)


# ==================== ASYNC TASK MANAGER ====================

class AsyncTaskManager:
    def __init__(self):
        self.tasks: Dict[str, Dict] = {}
        self.results: Dict[str, Any] = {}
        
    async def create_task(
        self, 
        task_id: str, 
        task_type: str, 
        coroutine
    ) -> str:
        """Create and track async task"""
        self.tasks[task_id] = {
            "type": task_type,
            "status": "pending",
            "created_at": datetime.now().isoformat(),
            "completed_at": None,
            "error": None
        }
        
        # Schedule task
        asyncio.create_task(self._run_task(task_id, coroutine))
        
        return task_id
    
    async def _run_task(self, task_id: str, coroutine):
        """Execute task and store result"""
        try:
            self.tasks[task_id]["status"] = "running"
            result = await coroutine
            self.results[task_id] = result
            self.tasks[task_id]["status"] = "completed"
            self.tasks[task_id]["completed_at"] = datetime.now().isoformat()
        except Exception as e:
            self.tasks[task_id]["status"] = "failed"
            self.tasks[task_id]["error"] = str(e)
    
    def get_task_status(self, task_id: str) -> Dict:
        """Get task status"""
        return self.tasks.get(task_id, {"error": "Task not found"})
    
    def get_task_result(self, task_id: str) -> Any:
        """Get task result if completed"""
        return self.results.get(task_id)


# Example usage
if __name__ == "__main__":
    print("=== MACT v2.0 INFRASTRUCTURE ===\n")
    
    # Test Memory Manager
    print("1. Memory Schema v2:")
    memory = MemoryManagerV2()
    schema = memory.create_user_schema("test_user")
    memory.update_mastery("test_user", "neural_networks", 0.75)
    memory.log_metacognition(
        "test_user", 
        "neural_networks", 
        self_confidence=0.8, 
        actual_score=0.75,
        notes="Felt confident but made some mistakes"
    )
    
    calibration = memory.get_calibration_score("test_user")
    print(f"   Calibration Score: {calibration:.2%}")
    print(f"   Mastery Matrix: {schema.mastery_matrix}")
    
    # Test Auth
    print("\n2. Authentication System:")
    auth = AuthManager()
    
    try:
        reg_result = auth.register_user("alice", "password123", "alice@example.com")
        print(f"   Registration: {reg_result['message']}")
        
        login_result = auth.login("alice", "password123")
        print(f"   Login Success: Token received ({len(login_result['access_token'])} chars)")
        
        # Verify token
        payload = auth.verify_token(login_result['access_token'])
        print(f"   Token Valid: User {payload['username']}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test Task Manager
    print("\n3. Async Task Manager:")
    task_mgr = AsyncTaskManager()
    
    async def sample_task():
        await asyncio.sleep(0.1)
        return {"result": "Task completed"}
    
    async def run_demo():
        task_id = await task_mgr.create_task("task_001", "demo", sample_task())
        
        await asyncio.sleep(0.2)  # Wait for completion
        
        status = task_mgr.get_task_status(task_id)
        result = task_mgr.get_task_result(task_id)
        
        print(f"   Task Status: {status['status']}")
        print(f"   Task Result: {result}")
    
    asyncio.run(run_demo())
    
    print("\n✓ All infrastructure components ready!")
