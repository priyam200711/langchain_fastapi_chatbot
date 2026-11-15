# 🚀 LangChain + FastAPI + Local Ollama Chatbot

A production-ready conversational AI chatbot backend built with **FastAPI**, **LangChain (LCEL)**, and **Local Ollama Models**. It runs 100% offline, privately on your PC, with **zero API keys, zero rate limits, and zero costs**.

It also features multi-turn session memory, real-time Server-Sent Events (SSE) streaming, and a responsive web chat UI.

---

## 🌟 Key Features

- **🌐 Live Web Search Retrieval (Web RAG)**: Automatically searches the live web using DuckDuckGo to inject real-time, fact-checked context into the prompt, citing sources and links!
- **🦙 100% Local & Free (Ollama)**: Runs directly on your PC using `langchain-ollama`. No Hugging Face tokens, credit cards, or external API permissions needed!
- **⚡ FastAPI Framework**: High-performance asynchronous REST API with automatic Swagger docs (`/docs`).
- **🦜️🔗 LangChain (LCEL)**: Modern LangChain pipeline utilizing `ChatOllama`, prompt templates, and persistent SQLite memory.
- **💾 Persistent Chat History**: Stores conversations in local SQLite database with sidebar session switcher.
- **🌊 Real-Time SSE Streaming**: Supports token streaming via Server-Sent Events (`/api/chat/stream`).
- **💻 Built-in Modern Web UI**: Instant interactive chat interface with Web Search and Streaming toggles at `http://127.0.0.1:8000`.

---

## 📁 Project Structure

```text
new_anti/
├── app/
│   ├── __init__.py
│   ├── config.py           # Configuration management (.env loader)
│   ├── schemas.py          # Pydantic request/response schemas
│   ├── chatbot.py          # LangChain LCEL pipeline & memory (Ollama / HF)
│   ├── main.py             # FastAPI routes & static file mounting
│   └── static/             # Modern Web Chat UI
│       ├── index.html      # Frontend HTML
│       ├── css/style.css   # Dark-mode styling
│       └── js/app.js       # Real-time SSE streaming & chat client
├── .env.example            # Environment variables template
├── .env                    # Active environment settings
├── requirements.txt        # Python package dependencies
├── run.py                  # Server launcher script
├── test_app.py             # In-memory ASGI unit tests
├── test_api.py             # Live HTTP endpoint test script
└── README.md               # Documentation
```

---

## 🛠️ Quick Start with Local Ollama

### 1. Make Sure Ollama is Running
Ensure the Ollama application is running on your PC (or start it in a terminal):
```powershell
ollama serve
```

### 2. Pull Your Model in Ollama
Open PowerShell or Command Prompt and download any free model:
```powershell
# Recommended default (Fast and smart)
ollama pull llama3.2

# Other great models:
ollama pull qwen2.5
ollama pull mistral
ollama pull phi3
ollama pull deepseek-r1:1.5b
```

### 3. Configure Your `.env`
Your [.env](file:///c:/Users/kumar/OneDrive/Desktop/new_anti/.env) is already configured for Ollama:
```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
```

*(If you pulled a different model, simply update `OLLAMA_MODEL` to match).*

---

## 🚀 Running the Chatbot

Start the server using the launcher script:

```powershell
python run.py
```

Or using `uvicorn` directly:

```powershell
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

## 🌐 How to Use

### 1. Web Chat Interface
Open your browser and navigate to:
👉 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

You will see the full-featured ChatGPT-style interface with real-time streaming output, markdown formatting, session switcher, and prompt suggestions.

### 2. Interactive API Documentation (Swagger)
Navigate to:
👉 **[http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)**

---

## 🔌 API Reference

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/` | Serves the interactive web chat UI |
| `GET` | `/health` | Healthcheck & provider verification |
| `GET` | `/api/models` | List recommended Ollama models |
| `POST` | `/api/chat` | Send a message and get a JSON response |
| `POST` | `/api/chat/stream` | Send a message and get a real-time SSE stream |
| `GET` | `/api/history/{session_id}` | Retrieve chat history for a session |
| `DELETE` | `/api/history/{session_id}`| Clear conversation memory for a session |

### Sample `POST /api/chat` Request

```bash
curl -X POST "http://127.0.0.1:8000/api/chat" \
     -H "Content-Type: application/json" \
     -d '{
       "message": "What is LangChain in 2 sentences?",
       "session_id": "session-1"
     }'
```
