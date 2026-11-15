import json
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.schemas import (
    ChatRequest,
    ChatResponse,
    ClearHistoryResponse,
    HealthResponse,
    HistoryResponse,
    MessageItem,
)
from app.chatbot import chatbot_service

# Create FastAPI app
app = FastAPI(
    title="LangChain Hugging Face Chatbot API",
    description="Conversational AI chatbot backend built with FastAPI, LangChain, and free Hugging Face models.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for local testing and web clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files setup
STATIC_DIR = Path(__file__).resolve().parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse, tags=["Frontend"])
async def get_index():
    """Serve the interactive web chat interface."""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>LangChain FastAPI Chatbot Backend is running! Visit /docs for API documentation.</h1>")


@app.get("/health", response_model=HealthResponse, tags=["System"])
@app.get("/api/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    """Health check endpoint showing active provider and model status."""
    provider = settings.LLM_PROVIDER
    if provider == "ollama":
        msg = f"Local Ollama mode active (Model: {settings.OLLAMA_MODEL}, Base URL: {settings.OLLAMA_BASE_URL})"
    else:
        is_set = settings.is_hf_token_set
        msg = "Hugging Face token is configured and active." if is_set else "HF Token not set in .env."

    return HealthResponse(
        status="healthy",
        provider=provider,
        model=settings.active_model_name,
        hf_token_configured=settings.is_hf_token_set,
        message=msg,
    )


@app.get("/api/models", tags=["System"])
async def list_recommended_models():
    """Return a curated list of free Ollama and Hugging Face models."""
    return {
        "current_provider": settings.LLM_PROVIDER,
        "active_model": settings.active_model_name,
        "ollama_models": [
            {
                "id": "llama3.2",
                "name": "Llama 3.2 (3B / 1B)",
                "command": "ollama pull llama3.2",
                "description": "Meta's latest ultra-efficient model. Fast and intelligent.",
            },
            {
                "id": "qwen2.5",
                "name": "Qwen 2.5 (7B / 3B)",
                "command": "ollama pull qwen2.5",
                "description": "Top-tier coding, multilingual, and general chat quality.",
            },
            {
                "id": "mistral",
                "name": "Mistral 7B",
                "command": "ollama pull mistral",
                "description": "Popular open-source reasoning model.",
            },
            {
                "id": "phi3",
                "name": "Microsoft Phi-3 Mini (3.8B)",
                "command": "ollama pull phi3",
                "description": "Compact and powerful lightweight reasoning model.",
            },
            {
                "id": "deepseek-r1:1.5b",
                "name": "DeepSeek R1 (1.5B)",
                "command": "ollama pull deepseek-r1:1.5b",
                "description": "State-of-the-art chain-of-thought reasoning model.",
            },
        ],
    }


@app.post("/api/chat", response_model=ChatResponse, tags=["Chat"])
async def chat_endpoint(request: ChatRequest):
    """
    Standard synchronous chat endpoint.
    Maintains multi-turn conversation memory for the provided session_id.
    """
    try:
        reply = await chatbot_service.generate_response(
            message=request.message,
            session_id=request.session_id,
            system_prompt=request.system_prompt,
            use_web_search=request.use_web_search,
        )
        return ChatResponse(
            reply=reply,
            session_id=request.session_id,
            model=settings.active_model_name,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat/stream", tags=["Chat"])
async def chat_stream_endpoint(request: ChatRequest):
    """
    Real-time streaming chat endpoint using Server-Sent Events (SSE).
    """
    async def event_generator():
        try:
            async for chunk in chatbot_service.stream_response(
                message=request.message,
                session_id=request.session_id,
                system_prompt=request.system_prompt,
                use_web_search=request.use_web_search,
            ):
                payload = json.dumps({"chunk": chunk, "session_id": request.session_id})
                yield f"data: {payload}\n\n"
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            err_payload = json.dumps({"error": str(e)})
            yield f"data: {err_payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/sessions", tags=["Memory"])
async def list_chat_sessions():
    """Retrieve all saved chat sessions."""
    return {"sessions": chatbot_service.get_sessions()}


@app.get("/api/history/{session_id}", response_model=HistoryResponse, tags=["Memory"])
async def get_chat_history(session_id: str):
    """Retrieve message history for a specific conversation session."""
    raw_messages = chatbot_service.get_messages(session_id)
    items = [MessageItem(role=m.get("role", "user"), content=m.get("content", "")) for m in raw_messages]
    return HistoryResponse(session_id=session_id, messages=items)


@app.delete("/api/history/{session_id}", response_model=ClearHistoryResponse, tags=["Memory"])
async def clear_chat_history(session_id: str):
    """Clear conversation history for a specific conversation session."""
    cleared = chatbot_service.clear_history(session_id)
    return ClearHistoryResponse(
        session_id=session_id,
        cleared=cleared,
        message=f"Conversation history for session '{session_id}' cleared successfully.",
    )
