"""Repository ingestion: sample dir or public GitHub zipball -> bounded list of text files."""
import io, os, re, urllib.request, urllib.error, zipfile
from pathlib import Path

MAX_FILES, MAX_FILE_BYTES, MAX_TOTAL_BYTES, MAX_ZIP_BYTES = 120, 60_000, 800_000, 25_000_000
SKIP_DIRS = {".git", "node_modules", "dist", "build", "__pycache__", "venv", ".venv", "vendor", "target", ".next", "coverage"}
SKIP_NAMES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock", "Cargo.lock"}
SECRET_RE = re.compile(r"(^\.env($|\.)|\.pem$|\.key$|\.p12$|id_rsa|credentials|secrets?\.)", re.I)
TEXT_EXT = {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".rb", ".php", ".c", ".h", ".cpp", ".cs", ".md", ".txt",
            ".toml", ".yaml", ".yml", ".json", ".html", ".css", ".sh", ".sql", ".cfg", ".ini", ".kt", ".swift"}
GH_RE = re.compile(r"^https?://(?:www\.)?github\.com/([\w.-]+)/([\w.-]+?)(?:\.git)?/?$")

class RepoError(Exception):
    pass

def parse_github_url(url: str):
    m = GH_RE.match((url or "").strip())
    if not m:
        raise RepoError("Enter a public repository URL like https://github.com/owner/repo.")
    return m.group(1), m.group(2)

def _keep(path: str, size: int) -> bool:
    p = Path(path)
    if any(part in SKIP_DIRS for part in p.parts) or p.name in SKIP_NAMES or SECRET_RE.search(p.name):
        return False
    if size > MAX_FILE_BYTES or size == 0:
        return False
    return (p.suffix.lower() in TEXT_EXT or p.name in {"Dockerfile", "Makefile", "LICENSE"}
            or p.name.lower().startswith("readme"))

def _priority(path: str):
    low = path.lower()
    return (0 if low.split("/")[-1].startswith("readme") else 1, low.count("/"), low)

def _finish(name: str, raw: dict) -> dict:
    files, total = {}, 0
    for path in sorted(raw, key=_priority)[:MAX_FILES]:
        text = raw[path]
        if total + len(text) > MAX_TOTAL_BYTES:
            break
        files[path] = text
        total += len(text)
    if not files:
        raise RepoError("No usable text or code files were found in this repository.")
    return {"name": name, "files": files, "skipped": len(raw) - len(files)}

def load_sample(sample_dir: Path) -> dict:
    raw = {}
    for f in sample_dir.rglob("*"):
        rel = f.relative_to(sample_dir).as_posix()
        if f.is_file() and _keep(rel, f.stat().st_size):
            raw[rel] = f.read_text("utf-8", errors="ignore")
    return _finish("sample/tasktracker", raw)

def load_github(url: str) -> dict:
    owner, repo = parse_github_url(url)
    req = urllib.request.Request(f"https://api.github.com/repos/{owner}/{repo}/zipball",
                                 headers={"User-Agent": "RepoLens", "Accept": "application/vnd.github+json"})
    if os.getenv("GITHUB_TOKEN"):  # optional: raises GitHub's rate limit
        req.add_header("Authorization", f"Bearer {os.getenv('GITHUB_TOKEN')}")
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            data = r.read(MAX_ZIP_BYTES + 1)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            raise RepoError("Repository not found. RepoLens can only read public repositories.")
        if e.code in (403, 429):
            raise RepoError("GitHub rate limit reached. Try again in a few minutes or use the sample repository.")
        raise RepoError(f"GitHub returned an error ({e.code}).")
    except Exception:
        raise RepoError("Could not reach GitHub. Check your connection or use the sample repository.")
    if len(data) > MAX_ZIP_BYTES:
        raise RepoError("This repository is too large to analyze (over 25 MB).")
    raw = {}
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        for info in z.infolist():
            if info.is_dir():
                continue
            rel = info.filename.split("/", 1)[-1]
            if rel and _keep(rel, info.file_size):
                raw[rel] = z.read(info).decode("utf-8", errors="ignore")
    return _finish(f"{owner}/{repo}", raw)
