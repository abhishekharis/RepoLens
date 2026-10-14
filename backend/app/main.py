import uuid
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass
from .services import ingest, llm, answer as ans
from .services.retrieval import chunk_files

ROOT = Path(__file__).resolve().parents[2]
app = FastAPI(title="RepoLens")
STORE: dict = {}  # in-memory sessions; a restart clears them

class AnalyzeIn(BaseModel):
    url: str = ""
    sample: bool = False

class AskIn(BaseModel):
    session_id: str
    question: str

def llm_info():
    return {"provider": llm.provider(), "model": llm.model_name()}

@app.get("/api/status")
def status():
    return llm_info()

@app.post("/api/analyze")
def analyze(body: AnalyzeIn):
    try:
        repo = ingest.load_sample(ROOT / "backend" / "sample_repo") if body.sample else ingest.load_github(body.url)
        ov = ans.overview(repo)
    except ingest.RepoError as e:
        raise HTTPException(400, str(e))
    except llm.LLMError as e:
        raise HTTPException(502, str(e))
    sid = uuid.uuid4().hex
    if len(STORE) > 20:
        STORE.pop(next(iter(STORE)))
    STORE[sid] = {"repo": repo, "chunks": chunk_files(repo["files"])}
    return {"session_id": sid, "name": repo["name"], "overview": ov, **llm_info()}

@app.post("/api/ask")
def ask(body: AskIn):
    s = STORE.get(body.session_id)
    q = body.question.strip()
    if not s:
        raise HTTPException(404, "Session expired. Analyze the repository again.")
    if not q or len(q) > 500:
        raise HTTPException(400, "Ask a question between 1 and 500 characters.")
    try:
        return ans.answer(s["repo"], s["chunks"], q)
    except llm.LLMError as e:
        raise HTTPException(502, str(e))

app.mount("/", StaticFiles(directory=ROOT / "frontend", html=True), name="ui")
