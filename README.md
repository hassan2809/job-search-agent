# Job Search Agent

An agent that discovers job postings relevant to my resume, drafts tailored outreach, and learns from outcomes over time — with a human-approval step before anything is ever sent. Built as a hands-on learning project while transitioning from full-stack development into Agentic AI.

## Status

**v1 — ingestion pipeline** (current): fetches job postings from RemoteOK and Arbeitnow, dedupes them, and stores them in SQLite. No LLM, matching, or outreach yet — that comes in later phases.

## Stack

- **Python 3.14**
- **FastAPI** — web framework / API layer
- **SQLAlchemy** — ORM for the SQLite database
- **httpx** — calling external job source APIs
- **pydantic-settings** — configuration management
- **uv** — dependency management and running the project

## Running it

```
uv run fastapi dev app/main.py
```