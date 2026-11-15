from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User message text")
    session_id: str = Field(default="default", description="Conversation session ID for memory tracking")
    system_prompt: Optional[str] = Field(default=None, description="Custom system instruction for this conversation")
    use_web_search: bool = Field(default=True, description="Whether to retrieve real-time web search results before answering")

class ChatResponse(BaseModel):
    reply: str
    session_id: str
    model: str
    sources: Optional[List[dict]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class MessageItem(BaseModel):
    role: str
    content: str
    timestamp: Optional[datetime] = None

class HistoryResponse(BaseModel):
    session_id: str
    messages: List[MessageItem]

class ClearHistoryResponse(BaseModel):
    session_id: str
    cleared: bool
    message: str

class HealthResponse(BaseModel):
    status: str
    provider: str
    model: str
    hf_token_configured: bool = False
    message: str
