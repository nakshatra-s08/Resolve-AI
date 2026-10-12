# ResolveAI

> **Personal repair-resolution agent** being developed for the Amazon Developer Hackathon.
> ResolveAI helps consumers manage recurring product-repair problems, starting with a laptop that develops the same fault again after two repair attempts.

---

## Backend Foundation — Milestone 1

This repository contains the backend foundation for ResolveAI, built with **Python**, **FastAPI**, **SQLAlchemy**, and **SQLite**.

### Technology Stack
- **Python**: 3.14+ (compatible with Python 3.10+)
- **FastAPI**: 0.115+
- **Uvicorn**: 0.30+
- **SQLAlchemy**: 2.0+
- **Pydantic**: 2.7+
- **SQLite**: Local persistent storage (default: `backend/data/resolveai.db`)
- **Pytest**: 8.0+

---

## macOS Developer Setup Guide

Follow these simple steps in Terminal on macOS:

### 1. Navigate to the project backend
```bash
cd "Desktop/Projects/Amazon-Handling Agentic Workflow/backend"
```

### 2. Create and activate a Python virtual environment (recommended)
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

---

## Running the Application

### 1. Start the FastAPI server
From the `backend/` directory:
```bash
python3 -m uvicorn app.main:app --reload --port 8000
```

The application will start at: `http://127.0.0.1:8000`

### 2. Test the Health Endpoint
In a separate terminal or web browser:
```bash
curl http://127.0.0.1:8000/api/health
```
**Expected Response:**
```json
{"status":"ok"}
```

### 3. Interactive API Documentation
Open your browser to:
- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## API Endpoints (Milestone 1)

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Confirm backend operational status (`{"status": "ok"}`) |
| `POST` | `/api/cases` | Create a new repair case (initial status: `NEW`) |
| `GET` | `/api/cases` | List all existing repair cases (ordered newest first) |
| `GET` | `/api/cases/{case_id}` | Retrieve a specific case by its UUID (returns 404 if not found) |

### Sample `POST /api/cases` Request:
```bash
curl -X POST http://127.0.0.1:8000/api/cases \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Repeated laptop repair failure",
    "product_name": "Dell XPS 15",
    "issue_description": "Motherboard replaced twice; screen flickering returns within 48 hours."
  }'
```

---

## Database Storage & Configuration

- **Default Location**: `backend/data/resolveai.db` (auto-created on startup).
- **Persistent**: Survives backend restarts.
- **Git Ignored**: `.db` files and `data/` directories are excluded in `.gitignore`.
- **Custom Database URL**:
  You can set or override the database URL using the `DATABASE_URL` environment variable:
  ```bash
  export DATABASE_URL="sqlite:///./data/resolveai.db"
  ```
  Or copy `.env.example` to `.env`:
  ```bash
  cp ../.env.example .env
  ```

---

## Running Automated Tests

Run the full pytest suite from the `backend/` directory:

```bash
python3 -m pytest -v
```

All 11 tests run against an **isolated in-memory SQLite database** (`sqlite:///:memory:`) using clean transactional fixtures, ensuring tests never alter or delete your local development database.
