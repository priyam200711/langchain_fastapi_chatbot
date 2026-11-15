import os
from pathlib import Path
from dotenv import load_dotenv

# Locate base directory and .env file
BASE_DIR = Path(__file__).resolve().parent.parent
ENV_FILE = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_FILE)

class Settings:
    # Provider Selection: "ollama" (local, free, offline) or "huggingface"
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "ollama").strip().lower()

    # Ollama Local Configuration
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434").strip()
    OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "qwen3:8b").strip()

    # Hugging Face Configuration (Fallback / Alternative)
    HF_TOKEN: str = os.getenv("HUGGINGFACEHUB_API_TOKEN", "").strip()
    MODEL_REPO_ID: str = os.getenv("MODEL_REPO_ID", "Qwen/Qwen2.5-7B-Instruct").strip()
    
    # Model Generation Parameters
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.7"))
    MAX_NEW_TOKENS: int = int(os.getenv("MAX_NEW_TOKENS", "512"))
    TOP_P: float = float(os.getenv("TOP_P", "0.95"))
    
    # Server Configuration
    HOST: str = os.getenv("HOST", "127.0.0.1")
    PORT: int = int(os.getenv("PORT", "8000"))
    DEBUG: bool = os.getenv("DEBUG", "true").lower() in ("true", "1", "yes")

    # Default system prompt
    DEFAULT_SYSTEM_PROMPT: str = (
        "You are a helpful, respectful, and intelligent AI assistant running locally on Ollama. "
        "Provide clear, accurate, and concise answers."
    )

    @property
    def is_hf_token_set(self) -> bool:
        return bool(self.HF_TOKEN and not self.HF_TOKEN.startswith("your_"))

    @property
    def active_model_name(self) -> str:
        if self.LLM_PROVIDER == "ollama":
            return f"Ollama ({self.OLLAMA_MODEL})"
        return f"HuggingFace ({self.MODEL_REPO_ID})"

settings = Settings()
