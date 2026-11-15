"""Convenience script to run the FastAPI LangChain application."""
import uvicorn
from app.config import settings

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 Starting LangChain Chatbot Server")
    print(f"📡 Provider: {settings.LLM_PROVIDER.upper()}")
    if settings.LLM_PROVIDER == "ollama":
        print(f"🦙 Ollama Model: {settings.OLLAMA_MODEL}")
        print(f"🔗 Ollama URL: {settings.OLLAMA_BASE_URL}")
    else:
        print(f"🤗 Hugging Face Model: {settings.MODEL_REPO_ID}")
        print(f"🔑 HF Token: {'Configured ✅' if settings.is_hf_token_set else 'Missing ⚠️'}")
    print(f"🌐 Web UI: http://{settings.HOST}:{settings.PORT}")
    print(f"📖 Swagger Docs: http://{settings.HOST}:{settings.PORT}/docs")
    print("=" * 60)
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
    )
