# RepoLens

Understand any public GitHub repository in minutes, with AI answers grounded in the actual source files.

RepoLens reads a repository's README and a bounded set of text/code files, shows an overview (purpose, stack, key files), and answers questions using retrieved excerpts. Every answer lists the files and line ranges it drew from, with expandable excerpts. If the files don't contain the answer, it says so.

## Run it

Prerequisites: Python 3.10+.

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # add Snowflake credentials for live AI (optional for a first look)
uvicorn backend.app.main:app --reload
```

Open http://127.0.0.1:8000, click **Load sample repository**, then use a suggested question. Run tests with `python -m pytest`.

## Modes

- **Snowflake mode** (when `SNOWFLAKE_ACCOUNT` and `SNOWFLAKE_TOKEN` are set): the overview summary and answers are generated through the Snowflake Cortex REST API (`/api/v2/cortex/inference:complete`) in `backend/app/services/llm.py`.
- **Offline mode** (no credentials): no model is called. The overview shows the opening of the README and answers point to the best matching excerpts. The UI labels this clearly.

## Status of requirements (honest)

- Snowflake integration: request shape verified against the current Cortex REST API documentation (`POST /api/v2/cortex/inference:complete`, `Authorization: Bearer` + `X-Snowflake-Authorization-Token-Type` header, `choices[0].message.content` response). **Not yet tested against a live account** — pending credentials.
- GitHub ingestion: **verified live** — `octocat/Hello-World` and `octocat/Spoon-Knife` were downloaded and analyzed; a nonexistent repo returns a readable "not found" error. Set `GITHUB_TOKEN` if you hit GitHub's unauthenticated rate limit.
- Open-weight model: default `SNOWFLAKE_MODEL=mistral-7b` (Mistral 7B Instruct, **Apache 2.0**, confirmed on the official Mistral AI Hugging Face page). `mistral-7b` is in the Snowflake Cortex model catalog, but availability varies by region; if yours lacks it, enable cross-region inference or set another open-weight model via `SNOWFLAKE_MODEL`. **Not yet confirmed**: whether the event accepts a hosted open-weight model accessed through Snowflake for the Best Open-Source AI category — confirm with the organizers. The provider is isolated in `llm.py`, so an eligible model can replace it without touching the rest of the app. Inference is hosted (Snowflake), not local.

## How it works

`ingest.py` loads the sample or a public repo's zipball (limits: 120 files, 60 KB per file, 800 KB total; skips dependencies, build output, binaries, lockfiles, and secret-like files). `retrieval.py` splits files into 40-line chunks and ranks them with TF-IDF-style keyword scoring. `answer.py` sends the top excerpts to the model, fenced as untrusted data, with instructions to answer only from them. Repository code is never executed.

## Limits

Public repositories only; sessions are in memory and cleared on restart; retrieval is lexical (generic overview questions fall back to the README; other questions that share no words with the code can miss).

## Demo script (60-90 seconds)

1. Load the sample repository; point out the overview and skipped-file count.
2. Ask: "What does this project do, and what technologies does it use?"
3. Ask: "Where is the main application entry point, and what happens when the app starts?"
4. Ask: "How do I run this project locally?"; expand a source excerpt.
5. Ask something unrelated to show it declines to guess.

## Submission blurb

RepoLens helps developers understand unfamiliar codebases. Paste a public GitHub URL and get an overview plus answers backed by retrieved files and line ranges. Built with FastAPI and a dependency-free HTML frontend; generation runs through Snowflake Cortex with an open-weight model (Mistral 7B, Apache 2.0). Code is MIT licensed.

## License

MIT. See `LICENSE`.
