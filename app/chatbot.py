import asyncio
import logging
from typing import AsyncGenerator, Dict, List, Optional
from datetime import datetime

from app.config import settings
from app import db
from app.search import web_search_service

# Setup logger
logger = logging.getLogger("langchain_chatbot")
logging.basicConfig(level=logging.INFO)

# LangChain Core Imports
try:
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
    from langchain_core.output_parsers import StrOutputParser
except ImportError as e:
    logger.warning(f"LangChain core not installed: {e}")
    HumanMessage = AIMessage = SystemMessage = BaseMessage = None
    ChatPromptTemplate = MessagesPlaceholder = StrOutputParser = None

try:
    from langchain_core.chat_history import InMemoryChatMessageHistory
except ImportError:
    try:
        from langchain_community.chat_message_histories import ChatMessageHistory as InMemoryChatMessageHistory
    except ImportError:
        InMemoryChatMessageHistory = None

# Ollama integration
try:
    from langchain_ollama import ChatOllama
except ImportError:
    ChatOllama = None

# Hugging Face integration
try:
    from langchain_huggingface import HuggingFaceEndpoint, ChatHuggingFace
except ImportError:
    HuggingFaceEndpoint = ChatHuggingFace = None


def _format_error(e: Exception) -> str:
    """Provide user-friendly explanations and actionable instructions for common errors."""
    err_str = str(e)

    # Ollama Connection Errors
    if "Connection refused" in err_str or "connectex" in err_str or "Failed to connect" in err_str or "11434" in err_str:
        return (
            "🔌 **Ollama Service is Not Running (Connection Refused)**\n\n"
            f"The application cannot reach Ollama at `{settings.OLLAMA_BASE_URL}`.\n\n"
            "### 🛠️ Quick Solution:\n"
            "1. **Start Ollama**:\n"
            "   - Open the **Ollama** app on your Windows PC (from the Start Menu / System Tray), OR\n"
            "   - Open a terminal and run:\n"
            "     ```powershell\n"
            "     ollama serve\n"
            "     ```\n"
            f"2. **Ensure your model is pulled**:\n"
            "   ```powershell\n"
            f"   ollama pull {settings.OLLAMA_MODEL}\n"
            "   ```\n"
            "3. Refresh this page and send your message again!"
        )

    # Ollama Model Not Found
    if "not found" in err_str.lower() and "model" in err_str.lower():
        return (
            f"📦 **Model '{settings.OLLAMA_MODEL}' not found in your Ollama library**\n\n"
            "To download and run this model, open PowerShell and run:\n"
            "```powershell\n"
            f"ollama pull {settings.OLLAMA_MODEL}\n"
            "```\n"
            "*(Or run `ollama list` to see what models you already downloaded, then set `OLLAMA_MODEL` in `.env`).*"
        )

    # Hugging Face 403 Forbidden
    if "403" in err_str or "sufficient permissions" in err_str or "Inference Providers" in err_str:
        return (
            "🔒 **Hugging Face Token Permission Error (403 Forbidden)**\n\n"
            "Your Hugging Face token does not have permission to call **Inference Providers**.\n\n"
            "### 🛠️ How to Fix:\n"
            "1. Open [huggingface.co/settings/tokens](https://huggingface.co/settings/tokens)\n"
            "2. Under **Inference Permissions**, check **'Make calls to Inference Providers'**\n"
            "3. Or simply switch to local Ollama by setting `LLM_PROVIDER=ollama` in `.env` (No API key needed!)."
        )

    # Hugging Face 503 Warming Up
    if "503" in err_str or "loading" in err_str:
        return (
            "⏳ **Model is Warming Up (503 Service Unavailable)**\n\n"
            "Hugging Face free serverless models spin down when idle. It takes ~10-20s to load.\n"
            "Please wait a moment and try again."
        )

    return f"⚠️ **Execution Error:** {err_str}"


class ChatBotService:
    """
    LangChain Chatbot Service supporting both local Ollama models and cloud Hugging Face models.
    """

    def __init__(self):
        self._histories: Dict[str, InMemoryChatMessageHistory] = {}
        self._model = None
        self._chain = None
        self._init_langchain()

    def _init_langchain(self):
        """Initialize the selected provider (Ollama or Hugging Face) and LangChain pipeline."""
        if ChatPromptTemplate is None:
            logger.error("LangChain core is not available.")
            return

        provider = settings.LLM_PROVIDER
        logger.info(f"Initializing LangChain pipeline using provider: {provider.upper()}")

        try:
            if provider == "ollama":
                if ChatOllama is None:
                    logger.error("langchain-ollama is not installed. Run `pip install langchain-ollama`.")
                    return

                logger.info(f"Configuring local Ollama model: {settings.OLLAMA_MODEL} at {settings.OLLAMA_BASE_URL}")
                self._model = ChatOllama(
                    base_url=settings.OLLAMA_BASE_URL,
                    model=settings.OLLAMA_MODEL,
                    temperature=settings.TEMPERATURE,
                )
            else:
                # Hugging Face cloud provider
                if not settings.is_hf_token_set:
                    logger.warning("HUGGINGFACEHUB_API_TOKEN is not set in .env.")
                    return

                if HuggingFaceEndpoint is None:
                    logger.error("langchain-huggingface is not installed.")
                    return

                logger.info(f"Connecting to Hugging Face model: {settings.MODEL_REPO_ID}")
                endpoint = HuggingFaceEndpoint(
                    repo_id=settings.MODEL_REPO_ID,
                    huggingfacehub_api_token=settings.HF_TOKEN,
                    max_new_tokens=settings.MAX_NEW_TOKENS,
                    temperature=settings.TEMPERATURE,
                    top_p=settings.TOP_P,
                    repetition_penalty=1.03,
                    timeout=120,
                )
                self._model = ChatHuggingFace(llm=endpoint)

            # Build LCEL conversational chain
            self._prompt_template = ChatPromptTemplate.from_messages([
                ("system", "{system_prompt}"),
                MessagesPlaceholder(variable_name="history"),
                ("human", "{input}"),
            ])

            self._chain = self._prompt_template | self._model | StrOutputParser()
            logger.info("LangChain pipeline created successfully.")

        except Exception as e:
            logger.error(f"Error initializing LangChain model pipeline: {e}", exc_info=True)
            self._model = None
            self._chain = None

    def get_history(self, session_id: str) -> InMemoryChatMessageHistory:
        """Retrieve or create a chat message history for a given session, preloaded from SQLite."""
        if session_id not in self._histories:
            if InMemoryChatMessageHistory is not None:
                history = InMemoryChatMessageHistory()
                # Preload existing messages from database
                db_msgs = db.get_messages(session_id)
                for m in db_msgs:
                    if m["role"] == "user":
                        history.add_user_message(m["content"])
                    elif m["role"] == "assistant":
                        history.add_ai_message(m["content"])
                self._histories[session_id] = history
            else:
                class SimpleHistory:
                    def __init__(self):
                        self.messages = db.get_messages(session_id)
                    def add_user_message(self, text: str):
                        self.messages.append({"role": "user", "content": text})
                    def add_ai_message(self, text: str):
                        self.messages.append({"role": "assistant", "content": text})
                    def clear(self):
                        self.messages.clear()
                self._histories[session_id] = SimpleHistory()
        return self._histories[session_id]

    def clear_history(self, session_id: str) -> bool:
        """Clear conversation history from both memory and SQLite storage."""
        db.delete_session(session_id)
        if session_id in self._histories:
            self._histories[session_id].clear()
            del self._histories[session_id]
        return True

    def get_messages(self, session_id: str) -> List[dict]:
        """Return persistent list of messages for a session from SQLite."""
        return db.get_messages(session_id)

    def get_sessions(self) -> List[dict]:
        """Return all historical chat sessions from SQLite."""
        return db.get_all_sessions()

    async def generate_response(
        self,
        message: str,
        session_id: str = "default",
        system_prompt: Optional[str] = None,
        use_web_search: bool = True,
    ) -> str:
        """Generate a complete chat response using LangChain and optional web retrieval."""
        sys_prompt = system_prompt or settings.DEFAULT_SYSTEM_PROMPT
        history = self.get_history(session_id)
        search_sources_md = ""

        if use_web_search:
            try:
                search_results = await asyncio.to_thread(web_search_service.search, message, 5)
                if search_results:
                    search_context = web_search_service.format_search_context(search_results)
                    search_sources_md = web_search_service.format_sources_markdown(search_results)
                    sys_prompt = (
                        "You are an intelligent, accurate, and up-to-date AI assistant.\n"
                        "Answer the user's question clearly, thoroughly, and factually using the real-time search context below.\n"
                        "- Ground your answer in the provided search facts.\n"
                        "- Cite sources with [1], [2], etc., where helpful.\n"
                        "- If the search results do not cover the answer, state that and use your general knowledge.\n\n"
                        "=== REAL-TIME WEB SEARCH CONTEXT ===\n"
                        f"{search_context}\n"
                        "===================================="
                    )
            except Exception as e:
                logger.warning(f"Web search failed: {e}")

        if self._chain is None:
            self._init_langchain()

        if self._chain is None:
            demo_reply = (
                "🤖 **[Local Ollama Setup Notice]**\n\n"
                "FastAPI and LangChain are ready! To connect to your local Ollama:\n\n"
                "1. Make sure Ollama is running (`ollama serve` or open Ollama app)\n"
                f"2. Pull your model: `ollama pull {settings.OLLAMA_MODEL}`\n"
                "3. Send your message again!\n\n"
                f"*Echo message received:* \"{message}\""
            )
            if hasattr(history, "add_user_message"):
                history.add_user_message(message)
                history.add_ai_message(demo_reply)
            return demo_reply

        try:
            history_messages = history.messages if hasattr(history, "messages") else []
            result = await self._chain.ainvoke({
                "system_prompt": sys_prompt,
                "history": history_messages,
                "input": message,
            })

            reply_text = str(result).strip()
            if search_sources_md:
                reply_text += search_sources_md

            # Save to SQLite
            db.save_message(session_id, "user", message)
            db.save_message(session_id, "assistant", reply_text)

            if hasattr(history, "add_user_message"):
                history.add_user_message(message)
                history.add_ai_message(reply_text)

            return reply_text
        except Exception as e:
            logger.error(f"Error during LangChain chat generation: {e}", exc_info=True)
            error_msg = _format_error(e)
            db.save_message(session_id, "user", message)
            db.save_message(session_id, "assistant", error_msg)
            if hasattr(history, "add_user_message"):
                history.add_user_message(message)
                history.add_ai_message(error_msg)
            return error_msg

    async def stream_response(
        self,
        message: str,
        session_id: str = "default",
        system_prompt: Optional[str] = None,
        use_web_search: bool = True,
    ) -> AsyncGenerator[str, None]:
        """Stream chunks of response in real-time with optional web retrieval."""
        sys_prompt = system_prompt or settings.DEFAULT_SYSTEM_PROMPT
        history = self.get_history(session_id)
        search_sources_md = ""

        if use_web_search:
            yield "🌐 *Searching the web for latest information...*\n\n"
            try:
                search_results = await asyncio.to_thread(web_search_service.search, message, 5)
                if search_results:
                    search_context = web_search_service.format_search_context(search_results)
                    search_sources_md = web_search_service.format_sources_markdown(search_results)
                    sys_prompt = (
                        "You are an intelligent, accurate, and up-to-date AI assistant.\n"
                        "Answer the user's question clearly, thoroughly, and factually using the real-time search context below.\n"
                        "- Ground your answer in the provided search facts.\n"
                        "- Cite sources with [1], [2], etc., where helpful.\n"
                        "- If the search results do not cover the answer, state that and use your general knowledge.\n\n"
                        "=== REAL-TIME WEB SEARCH CONTEXT ===\n"
                        f"{search_context}\n"
                        "===================================="
                    )
            except Exception as e:
                logger.warning(f"Web search failed: {e}")

        if self._chain is None:
            self._init_langchain()

        if self._chain is None:
            full_reply = await self.generate_response(message, session_id, system_prompt, use_web_search=False)
            words = full_reply.split(" ")
            for i, word in enumerate(words):
                yield word + (" " if i < len(words) - 1 else "")
            return

        try:
            history_messages = history.messages if hasattr(history, "messages") else []
            accumulated_chunks = []

            async for chunk in self._chain.astream({
                "system_prompt": sys_prompt,
                "history": history_messages,
                "input": message,
            }):
                text_chunk = str(chunk)
                accumulated_chunks.append(text_chunk)
                yield text_chunk

            if search_sources_md:
                yield search_sources_md
                accumulated_chunks.append(search_sources_md)

            full_reply = "".join(accumulated_chunks).strip()

            # Save to SQLite
            db.save_message(session_id, "user", message)
            db.save_message(session_id, "assistant", full_reply)

            if hasattr(history, "add_user_message"):
                history.add_user_message(message)
                history.add_ai_message(full_reply)
        except Exception as e:
            logger.error(f"Error streaming from model: {e}", exc_info=True)
            err_msg = _format_error(e)
            db.save_message(session_id, "user", message)
            db.save_message(session_id, "assistant", err_msg)
            yield f"\n\n{err_msg}"


# Singleton instance
chatbot_service = ChatBotService()
