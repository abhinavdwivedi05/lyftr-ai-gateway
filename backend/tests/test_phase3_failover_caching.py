import os
import tempfile
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.database import Base, get_db
from app.config import settings
from app.models import Message
from app.services.cache_service import cache_service

@pytest.fixture
def client_with_db():
    orig_mock = settings.MOCK_LLM
    settings.MOCK_LLM = True

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

    yield client

    app.dependency_overrides.clear()
    settings.MOCK_LLM = orig_mock
    engine.dispose()
    if os.path.exists(temp_db_path):
        try:
            os.remove(temp_db_path)
        except Exception:
            pass

def test_1_live_inference_success(client_with_db):
    resp = client_with_db.post("/chat", json={
        "session_id": "sess-live-1",
        "message": "Unique prompt 1"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == "sess-live-1"
    assert data["reply"]
    meta = data["metadata"]
    assert meta["resolution_source"] == "LIVE_INFERENCE"
    assert meta["key_id"] == "key_1"
    assert meta["fallback_attempts"] == 0

def test_2_first_request_cache_miss(client_with_db):
    resp = client_with_db.post("/chat", json={
        "session_id": "sess-miss-1",
        "message": "Unique prompt for miss test"
    })
    assert resp.status_code == 200
    meta = resp.json()["metadata"]
    assert meta["resolution_source"] == "LIVE_INFERENCE"

def test_3_identical_request_cache_hit(client_with_db):
    # First request in session A
    resp1 = client_with_db.post("/chat", json={
        "session_id": "sess-cache-a",
        "message": "Cache candidate prompt 123"
    })
    assert resp1.status_code == 200
    assert resp1.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"

    # Same first message in session B
    resp2 = client_with_db.post("/chat", json={
        "session_id": "sess-cache-b",
        "message": "Cache candidate prompt 123"
    })
    assert resp2.status_code == 200
    meta2 = resp2.json()["metadata"]
    assert meta2["resolution_source"] == "LLM_CACHE"

def test_4_identical_response_text(client_with_db):
    msg = "Text identity verification prompt"
    resp1 = client_with_db.post("/chat", json={"session_id": "s-ident-1", "message": msg})
    resp2 = client_with_db.post("/chat", json={"session_id": "s-ident-2", "message": msg})
    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json()["reply"] == resp2.json()["reply"]

def test_5_cache_hit_key_id_is_null(client_with_db):
    msg = "Key null check prompt"
    client_with_db.post("/chat", json={"session_id": "s-null-1", "message": msg})
    resp2 = client_with_db.post("/chat", json={"session_id": "s-null-2", "message": msg})
    assert resp2.status_code == 200
    meta = resp2.json()["metadata"]
    assert meta["resolution_source"] == "LLM_CACHE"
    assert meta["key_id"] is None

def test_6_cache_hit_fallback_attempts_equals_zero(client_with_db):
    msg = "Fallback zero check prompt"
    client_with_db.post("/chat", json={"session_id": "s-fb-1", "message": msg})
    resp2 = client_with_db.post("/chat", json={"session_id": "s-fb-2", "message": msg})
    assert resp2.status_code == 200
    meta = resp2.json()["metadata"]
    assert meta["resolution_source"] == "LLM_CACHE"
    assert meta["fallback_attempts"] == 0

def test_7_correct_input_token_tracking(client_with_db):
    resp = client_with_db.post("/chat", json={
        "session_id": "s-tok-1",
        "message": "Count these input tokens accurately"
    })
    assert resp.status_code == 200
    meta = resp.json()["metadata"]
    assert isinstance(meta["input_tokens"], int)
    assert meta["input_tokens"] > 0

def test_8_correct_output_token_tracking(client_with_db):
    resp = client_with_db.post("/chat", json={
        "session_id": "s-tok-2",
        "message": "Output token test"
    })
    assert resp.status_code == 200
    meta = resp.json()["metadata"]
    assert isinstance(meta["output_tokens"], int)
    assert meta["output_tokens"] > 0

def test_9_key_1_429_falls_back_to_key_2(client_with_db):
    resp = client_with_db.post(
        "/chat",
        json={"session_id": "s-sim-429", "message": "Trigger 429 failover"},
        headers={"X-Simulate-Failure": "key_1=429"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["reply"]
    meta = data["metadata"]
    assert meta["resolution_source"] == "LIVE_INFERENCE"
    assert meta["key_id"] == "key_2"
    assert meta["fallback_attempts"] == 1

def test_10_key_1_500_falls_back_to_key_2(client_with_db):
    resp = client_with_db.post(
        "/chat",
        json={"session_id": "s-sim-500", "message": "Trigger 500 failover"},
        headers={"X-Simulate-Failure": "key_1=500"}
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["reply"]
    meta = data["metadata"]
    assert meta["resolution_source"] == "LIVE_INFERENCE"
    assert meta["key_id"] == "key_2"
    assert meta["fallback_attempts"] == 1

def test_11_key1_429_key2_500_returns_503(client_with_db):
    resp = client_with_db.post(
        "/chat",
        json={"session_id": "s-sim-all-fail", "message": "Both fail"},
        headers={"X-Simulate-Failure": "key_1=429,key_2=500"}
    )
    assert resp.status_code == 503
    assert resp.json()["detail"] == "all providers unavailable"

def test_12_wildcard_429_returns_503(client_with_db):
    resp = client_with_db.post(
        "/chat",
        json={"session_id": "s-sim-wildcard", "message": "Wildcard fail"},
        headers={"X-Simulate-Failure": "*=429"}
    )
    assert resp.status_code == 503
    assert resp.json()["detail"] == "all providers unavailable"

def test_13_failed_requests_do_not_enter_history(client_with_db):
    session_id = "s-no-history-fail"
    # Execute a failing request
    resp = client_with_db.post(
        "/chat",
        json={"session_id": session_id, "message": "This message must not be saved"},
        headers={"X-Simulate-Failure": "*=429"}
    )
    assert resp.status_code == 503

    # Attempt to fetch history: should return 404 because session was never created
    hist_resp = client_with_db.get(f"/sessions/{session_id}/messages")
    assert hist_resp.status_code == 404
    assert hist_resp.json()["detail"] == "session not found"

def test_14_cache_is_bypassed_for_simulated_failure_requests(client_with_db):
    msg = "Simulated failure cache bypass test prompt"
    # First: establish a clean cached response
    resp1 = client_with_db.post("/chat", json={"session_id": "s-byp-1", "message": msg})
    assert resp1.status_code == 200
    assert resp1.json()["metadata"]["key_id"] == "key_1"
    assert resp1.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"

    # Second: run with key_1 simulated 429 on the exact same message!
    # If caching took over, it would return key_1/LLM_CACHE.
    # Because simulation is active, it MUST bypass cache and fallback to key_2!
    resp2 = client_with_db.post(
        "/chat",
        json={"session_id": "s-byp-2", "message": msg},
        headers={"X-Simulate-Failure": "key_1=429"}
    )
    assert resp2.status_code == 200
    meta2 = resp2.json()["metadata"]
    assert meta2["resolution_source"] == "LIVE_INFERENCE"
    assert meta2["key_id"] == "key_2"
    assert meta2["fallback_attempts"] == 1

def test_15_simulation_is_disabled_when_configured_false(client_with_db):
    msg = "Simulation toggle test message"
    orig_setting = settings.ENABLE_FAILURE_SIMULATION
    try:
        settings.ENABLE_FAILURE_SIMULATION = False
        # Send simulation header, but it should be ignored since simulation is disabled
        resp = client_with_db.post(
            "/chat",
            json={"session_id": "s-disabled-sim", "message": msg},
            headers={"X-Simulate-Failure": "key_1=429"}
        )
        assert resp.status_code == 200
        meta = resp.json()["metadata"]
        assert meta["key_id"] == "key_1"
        assert meta["fallback_attempts"] == 0
    finally:
        settings.ENABLE_FAILURE_SIMULATION = orig_setting

def test_16_different_messages_do_not_incorrectly_share_cache(client_with_db):
    resp1 = client_with_db.post("/chat", json={"session_id": "s-diff-1", "message": "Message Alpha"})
    resp2 = client_with_db.post("/chat", json={"session_id": "s-diff-2", "message": "Message Beta"})
    assert resp1.status_code == 200
    assert resp2.status_code == 200
    assert resp1.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"
    assert resp2.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"
    assert resp1.json()["reply"] != resp2.json()["reply"]

def test_17_normal_cache_behavior_works_after_failure_simulation(client_with_db):
    msg = "Post-simulation cache recovery test"
    # 1. First live call
    resp1 = client_with_db.post("/chat", json={"session_id": "s-recov-1", "message": msg})
    assert resp1.status_code == 200
    assert resp1.json()["metadata"]["resolution_source"] == "LIVE_INFERENCE"

    # 2. Simulated failure call on same prompt (bypasses cache and uses key_2)
    resp_sim = client_with_db.post(
        "/chat",
        json={"session_id": "s-recov-sim", "message": msg},
        headers={"X-Simulate-Failure": "key_1=429"}
    )
    assert resp_sim.status_code == 200
    assert resp_sim.json()["metadata"]["key_id"] == "key_2"

    # 3. Third call without simulation header: should hit original cache again!
    resp3 = client_with_db.post("/chat", json={"session_id": "s-recov-3", "message": msg})
    assert resp3.status_code == 200
    meta3 = resp3.json()["metadata"]
    assert meta3["resolution_source"] == "LLM_CACHE"
    assert meta3["key_id"] is None
    assert meta3["fallback_attempts"] == 0
