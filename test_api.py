"""Simple script to test the FastAPI endpoints locally."""
import json
import requests

BASE_URL = "http://127.0.0.1:8000"

def test_endpoints():
    print(f"Testing LangChain FastAPI bot at {BASE_URL}...\n")

    # 1. Test Health
    try:
        res = requests.get(f"{BASE_URL}/health")
        print("1. Healthcheck Response:", res.status_code)
        print(json.dumps(res.json(), indent=2))
    except Exception as e:
        print(f"Server is not running or unreachable at {BASE_URL}. Start it with `python run.py` first.\nError: {e}")
        return

    # 2. Test Model List
    print("\n2. Recommended Models:")
    res = requests.get(f"{BASE_URL}/api/models")
    print(json.dumps(res.json(), indent=2))

    # 3. Test Chat Endpoint
    print("\n3. Testing /api/chat...")
    payload = {
        "message": "Hello! What can you help me with?",
        "session_id": "test_session_1",
        "system_prompt": "You are a helpful coding tutor."
    }
    chat_res = requests.post(f"{BASE_URL}/api/chat", json=payload)
    print("Status:", chat_res.status_code)
    print(json.dumps(chat_res.json(), indent=2))

    # 4. Test Session History
    print("\n4. Testing /api/history/test_session_1...")
    hist_res = requests.get(f"{BASE_URL}/api/history/test_session_1")
    print("History:")
    print(json.dumps(hist_res.json(), indent=2))

if __name__ == "__main__":
    test_endpoints()
