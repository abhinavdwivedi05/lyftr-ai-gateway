import os
import json
import tempfile
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.config import settings

from app.main import app
from app.database import Base, get_db
from app.models import Message

@pytest.fixture
def test_db_session():
    # Ensure automated tests run in deterministic test mode
    orig_mock = settings.MOCK_LLM
    settings.MOCK_LLM = True

    # Create a temporary file for SQLite to test real file persistence & reconnection
    temp_db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    temp_db_path = temp_db_file.name
    temp_db_file.close()

    db_url = f"sqlite:///{temp_db_path}"
    engine = create_engine(db_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)

    yield {
        "client": client,
        "engine": engine,
        "db_path": temp_db_path,
        "SessionLocal": TestingSessionLocal
    }

    app.dependency_overrides.clear()
    settings.MOCK_LLM = orig_mock
    engine.dispose()
    if os.path.exists(temp_db_path):
        try:
            os.remove(temp_db_path)
        except Exception:
            pass

def test_1_health_endpoint(test_db_session):
    client = test_db_session["client"]
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "keys_configured" in data
    assert data["keys_configured"] >= 2
    assert data["cache_enabled"] is True

def test_2_successful_chat(test_db_session):
    client = test_db_session["client"]
    payload = {
        "session_id": "test-session-1",
        "message": "Hello world"
    }
    resp = client.post("/chat", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == "test-session-1"
    assert data["reply"]
    meta = data["metadata"]
    assert meta["resolution_source"] in ["LIVE_INFERENCE", "LLM_CACHE"]
    assert meta["model"]
    assert isinstance(meta["latency_ms"], int)
    assert isinstance(meta["input_tokens"], int)
    assert isinstance(meta["output_tokens"], int)
    assert "fallback_attempts" in meta

def test_3_empty_message_returns_422(test_db_session):
    client = test_db_session["client"]
    
    # Empty string
    resp1 = client.post("/chat", json={"session_id": "s1", "message": ""})
    assert resp1.status_code == 422
    assert "detail" in resp1.json()

    # Whitespace only
    resp2 = client.post("/chat", json={"session_id": "s1", "message": "    \n\t  "})
    assert resp2.status_code == 422
    assert "detail" in resp2.json()

def test_4_message_exceeding_4000_chars_returns_422(test_db_session):
    client = test_db_session["client"]
    long_msg = "a" * 4001
    resp = client.post("/chat", json={"session_id": "s1", "message": long_msg})
    assert resp.status_code == 422
    assert "detail" in resp.json()

def test_5_session_history_retrieval(test_db_session):
    client = test_db_session["client"]
    session_id = "s-hist-test"
    
    # Post with a system prompt
    resp = client.post("/chat", json={
        "session_id": session_id,
        "message": "What is the capital of France?",
        "system_prompt": "You are a geography expert."
    })
    assert resp.status_code == 200

    # Retrieve history
    hist_resp = client.get(f"/sessions/{session_id}/messages")
    assert hist_resp.status_code == 200
    data = hist_resp.json()
    assert data["session_id"] == session_id
    messages = data["messages"]
    
    # Must have user and assistant messages
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "What is the capital of France?"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["content"]

    # System prompt must NOT be in the history
    roles = [m["role"] for m in messages]
    assert "system" not in roles

def test_6_history_ordering(test_db_session):
    client = test_db_session["client"]
    session_id = "s-order-test"

    for i in range(3):
        resp = client.post("/chat", json={
            "session_id": session_id,
            "message": f"Message number {i}"
        })
        assert resp.status_code == 200

    hist_resp = client.get(f"/sessions/{session_id}/messages")
    assert hist_resp.status_code == 200
    messages = hist_resp.json()["messages"]
    assert len(messages) == 6 # 3 user + 3 assistant

    # Check chronological ordering (oldest first)
    assert messages[0]["content"] == "Message number 0"
    assert messages[2]["content"] == "Message number 1"
    assert messages[4]["content"] == "Message number 2"

def test_7_unknown_session_returns_404(test_db_session):
    client = test_db_session["client"]
    resp = client.get("/sessions/totally-unknown-id/messages")
    assert resp.status_code == 404
    data = resp.json()
    assert data["detail"] == "session not found"

def test_8_assistant_metadata_persistence(test_db_session):
    client = test_db_session["client"]
    session_id = "s-meta-test"
    
    resp = client.post("/chat", json={
        "session_id": session_id,
        "message": "Tell me a fact."
    })
    assert resp.status_code == 200

    hist_resp = client.get(f"/sessions/{session_id}/messages")
    assert hist_resp.status_code == 200
    messages = hist_resp.json()["messages"]
    
    assistant_msg = [m for m in messages if m["role"] == "assistant"][0]
    assert "metadata" in assistant_msg
    meta = assistant_msg["metadata"]
    assert "resolution_source" in meta
    assert "input_tokens" in meta
    assert "output_tokens" in meta

def test_9_session_isolation(test_db_session):
    client = test_db_session["client"]
    
    # Session A
    client.post("/chat", json={"session_id": "session_A", "message": "Secret A"})
    
    # Session B
    client.post("/chat", json={"session_id": "session_B", "message": "Secret B"})

    hist_A = client.get("/sessions/session_A/messages").json()["messages"]
    hist_B = client.get("/sessions/session_B/messages").json()["messages"]

    contents_A = [m["content"] for m in hist_A]
    contents_B = [m["content"] for m in hist_B]

    assert "Secret A" in contents_A
    assert "Secret A" not in contents_B
    assert "Secret B" in contents_B
    assert "Secret B" not in contents_A

def test_10_database_persistence_after_reopening_connection(test_db_session):
    client = test_db_session["client"]
    session_id = "s-persist-test"
    db_path = test_db_session["db_path"]

    # Write data through client
    resp = client.post("/chat", json={
        "session_id": session_id,
        "message": "Persistent data check"
    })
    assert resp.status_code == 200

    # Close existing connection/engine and reopen from disk file
    test_db_session["engine"].dispose()
    new_engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    NewSession = sessionmaker(autocommit=False, autoflush=False, bind=new_engine)

    db = NewSession()
    try:
        saved_messages = db.query(Message).filter(Message.session_id == session_id).all()
        assert len(saved_messages) == 2 # 1 user, 1 assistant
        assert saved_messages[0].content == "Persistent data check"
        assert saved_messages[1].role == "assistant"
        assert saved_messages[1].parsed_metadata["resolution_source"] in ["LIVE_INFERENCE", "LLM_CACHE"]
    finally:
        db.close()
        new_engine.dispose()
