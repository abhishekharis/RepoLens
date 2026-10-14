import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services import ingest, llm
from backend.app.services.retrieval import chunk_files, search

c = TestClient(app)

@pytest.fixture(autouse=True)
def no_creds(monkeypatch):
    monkeypatch.delenv("SNOWFLAKE_ACCOUNT", raising=False)
    monkeypatch.delenv("SNOWFLAKE_TOKEN", raising=False)

def sample():
    r = c.post("/api/analyze", json={"sample": True})
    assert r.status_code == 200
    return r.json()

def test_sample_overview():
    d = sample()
    assert "Python" in d["overview"]["stack"] and "README.md" in d["overview"]["key_files"]

def test_demo_questions_have_sources():
    sid = sample()["session_id"]
    for q, path in [("How do I run this project locally?", "README.md"),
                    ("Where is the main application entry point?", "__main__.py")]:
        r = c.post("/api/ask", json={"session_id": sid, "question": q}).json()
        assert any(path in s["path"] for s in r["sources"]), q

def test_unanswerable_says_so():
    sid = sample()["session_id"]
    r = c.post("/api/ask", json={"session_id": sid, "question": "zebra quantum kubernetes"}).json()
    assert r["mode"] == "no_context" and r["sources"] == []

def test_bad_urls():
    for u in ["", "notaurl", "https://example.com/a/b"]:
        r = c.post("/api/analyze", json={"url": u})
        assert r.status_code == 400 and "github.com" in r.json()["detail"]

def test_expired_session():
    assert c.post("/api/ask", json={"session_id": "x", "question": "hi"}).status_code == 404

def test_missing_credentials_message():
    with pytest.raises(llm.LLMError, match=".env.example"):
        llm.complete("s", "u")

def test_secret_and_binary_filtering():
    assert not ingest._keep(".env", 10) and not ingest._keep("keys/server.pem", 10)
    assert not ingest._keep("node_modules/x/index.js", 10) and not ingest._keep("logo.png", 10)
    assert not ingest._keep("big.py", ingest.MAX_FILE_BYTES + 1) and ingest._keep("src/app.py", 10)

def test_snowflake_error_is_readable(monkeypatch):
    monkeypatch.setenv("SNOWFLAKE_ACCOUNT", "a"); monkeypatch.setenv("SNOWFLAKE_TOKEN", "t")
    def boom(*a, **k): raise llm.LLMError("Could not reach the Snowflake API (timeout or network error). Try again.")
    monkeypatch.setattr(llm, "complete", boom)
    assert c.post("/api/analyze", json={"sample": True}).status_code == 502
