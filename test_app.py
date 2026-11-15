"""Direct ASGI test script using TestClient."""
from fastapi.testclient import TestClient
from app.main import app

def run_tests():
    client = TestClient(app)
    
    print("Testing GET /health...")
    res = client.get("/health")
    print(f"Status: {res.status_code}, Response: {res.json()}")
    assert res.status_code == 200

    print("\nTesting GET /api/models...")
    res = client.get("/api/models")
    print(f"Status: {res.status_code}, Models count: {len(res.json()['ollama_models'])}")
    assert res.status_code == 200

    print("\nTesting GET / (Frontend HTML)...")
    res = client.get("/")
    print(f"Status: {res.status_code}, HTML length: {len(res.text)} bytes")
    assert res.status_code == 200
    assert "LangChain" in res.text

    print("\nTesting POST /api/chat (Demo / Fallback mode)...")
    res = client.post("/api/chat", json={
        "message": "Hello from unit test!",
        "session_id": "test_1",
        "use_web_search": False
    })
    print(f"Status: {res.status_code}, Reply preview: {res.json()['reply'][:60]}...")
    assert res.status_code == 200
    assert "test_1" == res.json()["session_id"]

    print("\nTesting GET /api/sessions...")
    sessions_res = client.get("/api/sessions")
    print(f"Status: {sessions_res.status_code}, Saved sessions: {len(sessions_res.json()['sessions'])}")
    assert sessions_res.status_code == 200

    print("\nTesting GET /api/history/test_1...")
    res = client.get("/api/history/test_1")
    print(f"Status: {res.status_code}, History count: {len(res.json()['messages'])}")
    assert res.status_code == 200
    assert len(res.json()["messages"]) >= 2

    print("\nTesting DELETE /api/history/test_1...")
    res = client.delete("/api/history/test_1")
    print(f"Status: {res.status_code}, Cleared: {res.json()['cleared']}")
    assert res.status_code == 200

    print("\nAll ASGI tests passed successfully! 🎉")

if __name__ == "__main__":
    run_tests()
