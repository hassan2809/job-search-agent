# Client Outreach Agent

An agent that helps me reach out on LinkedIn to people/companies who need full-stack or AI project work done. It checks fit against my resume, drafts a connection note and follow-up messages, and tracks the conversation — with a human-approval step before anything is ever sent. Built as a hands-on learning project while transitioning from full-stack development into Agentic AI. Leads are sourced by hand (a weekly Excel export, or one-off pastes).

## Stack

- **Python 3.14**
- **FastAPI** — web framework / API layer
- **SQLAlchemy** — ORM for the SQLite database
- **openpyxl** — parsing the weekly Excel lead sheet
- **pydantic-settings** — configuration management
- **pypdf** — parsing the resume used for fit-checks and drafting
- **uv** — dependency management and running the project

## Running it

```
uv run fastapi dev app/main.py
```

Then open `http://127.0.0.1:8000/docs` for the interactive API docs.
