# OpportunIQ Backend

FastAPI backend foundation for OpportunIQ, including application startup, SQLite initialization, and shared Pydantic schemas for later agent and API work.

## Requirements

Use Python 3.11 or newer.

## Environment Setup

Create a virtual environment and install dependencies:

```bash
cd opportuniq-backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and fill in local values. Do not commit `.env`, OAuth credentials, tokens, or database files.

## Run

```bash
uvicorn app.main:app --reload
```

Health check:

```text
http://localhost:8000/health
```

Interactive API documentation:

```text
http://localhost:8000/docs
```
