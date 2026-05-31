# api_server.py
import os
import logging
from typing import Optional
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime
import uvicorn
from dotenv import load_dotenv

from sid_agent import SIDAgent, config

load_dotenv()

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(
    title="SID Agent API",
    description="Savage Intelligent Dialogue API - Your unhinged AI best friend",
    version="1.0.0"
)

# Add CORS middleware for web access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize SID agent
sid_agent = SIDAgent()

# Request/Response models
class ChatRequest(BaseModel):
    user_id: str
    message: str
    mode: Optional[str] = "chaos"  # chaos or care

class ChatResponse(BaseModel):
    user_id: str
    response: str
    mode: str
    timestamp: datetime

class HealthResponse(BaseModel):
    status: str
    version: str
    timestamp: datetime
    memory_count: int

@app.get("/")
async def root():
    """Health check endpoint."""
    # Get memory count safely (works with both ChromaDB and SimpleMemoryStore)
    try:
        memory_count = sid_agent.memory.collection.count()
    except AttributeError:
        # For SimpleMemoryStore fallback
        memory_count = len(sid_agent.memory.memories) if hasattr(sid_agent.memory, 'memories') else 0
    
    return {
        "status": "healthy",
        "version": "1.0.0",
        "timestamp": datetime.now(),
        "memory_count": memory_count
    }

@app.get("/health")
async def health_check():
    """Simple health check."""
    return {"status": "alive", "timestamp": datetime.now()}

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Send a message to SID.
    
    - **user_id**: Unique identifier for the user
    - **message**: The message to send to SID
    - **mode**: "chaos" for savage roasts, "care" for supportive responses
    """
    try:
        # Validate input
        if not request.user_id or not request.message:
            raise HTTPException(status_code=400, detail="user_id and message are required")
        
        if len(request.message) > config.MAX_INPUT_LENGTH:
            raise HTTPException(
                status_code=400, 
                detail=f"Message too long. Maximum {config.MAX_INPUT_LENGTH} characters"
            )
        
        # Get response from SID
        response = sid_agent.chat(
            request.user_id, 
            request.message, 
            request.mode
        )
        
        return ChatResponse(
            user_id=request.user_id,
            response=response,
            mode=request.mode,
            timestamp=datetime.now()
        )
        
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    """Webhook endpoint for Telegram bot."""
    try:
        update_data = await request.json()
        # This would be handled by your Telegram bot
        # For now, just acknowledge
        return {"status": "ok"}
    except Exception as e:
        logger.error(f"Telegram webhook error: {e}")
        return {"status": "error", "message": str(e)}

@app.get("/stats/{user_id}")
async def get_user_stats(user_id: str):
    """Get conversation stats for a user."""
    try:
        session_history = sid_agent._sessions.get(user_id, [])
        message_count = len(session_history) // 2
        
        return {
            "user_id": user_id,
            "total_messages": message_count,
            "total_turns": len(session_history),
            "mode": "chaos"  # This would need to be stored
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/memory/{user_id}")
async def clear_user_memory(user_id: str):
    """Clear conversation memory for a user."""
    try:
        # Clear session memory
        if user_id in sid_agent._sessions:
            sid_agent._sessions[user_id] = []
        
        return {
            "status": "success",
            "message": f"Cleared memory for user {user_id}"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        workers=4
    )