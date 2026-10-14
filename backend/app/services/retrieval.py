"""Simple lexical retrieval over line-based chunks."""
import math, re
from collections import Counter

STOP = set("the a an and or of to in is are what how do does where which this that it for on with from i me my can be by as at".split())
CHUNK_LINES = 40
# Generic "tell me about this repo" words: when they match nothing, the README is still the best source.
OVERVIEW_Q = {"project", "repo", "repository", "app", "application", "tool", "technologies", "stack",
              "purpose", "overview", "language", "languages", "framework", "summary", "about"}

def tokens(text):
    return [t for t in re.findall(r"[a-z0-9_]+", text.lower()) if t not in STOP and len(t) > 1]

def chunk_files(files: dict):
    chunks = []
    for path, text in files.items():
        lines = text.splitlines()
        for i in range(0, len(lines), CHUNK_LINES):
            body = "\n".join(lines[i:i + CHUNK_LINES])
            if body.strip():
                chunks.append({"path": path, "start": i + 1, "end": min(i + CHUNK_LINES, len(lines)), "text": body})
    return chunks

def search(chunks, question, k=5):
    q = set(tokens(question))
    if not q:
        return []
    docs = [Counter(tokens(c["path"] + " " + c["text"])) for c in chunks]
    df = Counter(t for d in docs for t in d)
    n, scored = len(chunks), []
    wants_entry = bool(q & {"entry", "start", "main", "run", "starts", "launch", "install", "setup", "locally"})
    for c, d in zip(chunks, docs):
        s = sum((1 + math.log(d[t])) * math.log(1 + n / df[t]) for t in q if t in d)
        if s <= 0:
            continue
        name = c["path"].lower().split("/")[-1]
        if name.startswith("readme"):
            s *= 1.3
        if wants_entry and re.match(r"(main|app|index|server|cli|__main__)\.", name):
            s *= 1.5
        scored.append((s, c))
    scored.sort(key=lambda x: -x[0])
    if not scored and q & OVERVIEW_Q:
        readmes = [c for c in chunks if c["path"].lower().split("/")[-1].startswith("readme")]
        return [{**c, "score": 0} for c in (readmes[:2] or chunks[:1])]
    return [{**c, "score": round(s, 2)} for s, c in scored[:k]]
