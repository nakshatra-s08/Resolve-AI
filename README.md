# ResolveAI

> **Personal repair-resolution agent** being developed for the Amazon Developer Hackathon.
> ResolveAI helps consumers manage recurring product-repair problems, starting with a laptop that develops the same fault again after two repair attempts.

---

## Backend — Phases 1 & 2: Case Management & Persistent Timeline

This repository contains the backend for ResolveAI, built with **Python**, **FastAPI**, **SQLAlchemy**, and **SQLite**.

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

## API Endpoints Overview

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/health` | Confirm backend operational status (`{"status": "ok"}`) |
| `POST` | `/api/cases` | Create a new repair case (initial status: `NEW`, automatically logs `CASE_CREATED`) |
| `GET` | `/api/cases` | List all existing repair cases (ordered newest first) |
| `GET` | `/api/cases/{case_id}` | Retrieve a specific case by its UUID (returns 404 if not found) |
| `PATCH` | `/api/cases/{case_id}` | Partially update case details (`title`, `product_name`, `issue_description`) |
| `PATCH` | `/api/cases/{case_id}/status` | Transition case workflow status (returns 409 on disallowed transitions) |
| `POST` | `/api/cases/{case_id}/events` | Add a manual user note (`event_type: NOTE_ADDED`) to the timeline |
| `GET` | `/api/cases/{case_id}/timeline` | Retrieve chronological timeline events (supports `skip` & `limit` query parameters) |

---

## Case Workflow Status Transitions

ResolveAI implements a controlled state machine. Invalid transitions return `HTTP 409 Conflict`.

```
NEW ───────────────► COLLECTING_EVIDENCE ───► UNDER_REVIEW ───► ACTION_READY ───► AWAITING_RESPONSE ───► RESOLVED
 │                          ▲                     │   ▲               ▲                     │              ▲
 │                          │                     │   │               │                     │              │
 └──────────────────────────┴─────────────────────┘   └───────────────┴─────────────────────┼──────────────┤
                                                      (additional evidence needed)          ▼              │
                                                                                      FOLLOW_UP_DUE ───────┘
```

### Transition Rules:
- **`NEW`** ➔ `COLLECTING_EVIDENCE`, `UNDER_REVIEW`, `CLOSED`
- **`COLLECTING_EVIDENCE`** ➔ `UNDER_REVIEW`, `ACTION_READY`, `CLOSED`
- **`UNDER_REVIEW`** ➔ `COLLECTING_EVIDENCE`, `ACTION_READY`, `RESOLVED`, `CLOSED`
- **`ACTION_READY`** ➔ `COLLECTING_EVIDENCE`, `AWAITING_RESPONSE`, `CLOSED`
- **`AWAITING_RESPONSE`** ➔ `FOLLOW_UP_DUE`, `UNDER_REVIEW`, `RESOLVED`, `CLOSED`
- **`FOLLOW_UP_DUE`** ➔ `UNDER_REVIEW`, `AWAITING_RESPONSE`, `RESOLVED`, `CLOSED`
- **`RESOLVED`** ➔ `UNDER_REVIEW` (reopened if issue returns), `CLOSED`
- **`CLOSED`** ➔ `UNDER_REVIEW` (reopened if further work required)

---

## Timeline & Events Model

Events are stored in the `case_events` table and maintain an immutable chronological history:

- **`CASE_CREATED`**: Automatically emitted when a case is created.
- **`CASE_UPDATED`**: Emitted when case details (`title`, `product_name`, `issue_description`) are modified. Contains `changed_fields`, `old_values`, and `new_values` in `metadata_json`.
- **`STATUS_CHANGED`**: Emitted on status changes. Contains `previous_status` and `new_status`. Identical status updates are no-ops.
- **`NOTE_ADDED`**: Added explicitly by users via `POST /api/cases/{case_id}/events`.
- **`SYSTEM_EVENT`**: Reserved for automated system actions.

---

## Database Storage & Migration Safety

- **Default Location**: `backend/data/resolveai.db` (auto-created on startup).
- **Persistent**: Survives backend restarts.
- **Migration Policy**: `init_db()` runs via the FastAPI lifespan event and uses `Base.metadata.create_all(bind=engine)`. If `cases` already exists from Phase 1, `create_all()` will safely create the new `case_events` table without dropping or mutating existing case records.

---

## Running Automated Tests

Run the full pytest suite from the `backend/` directory:

```bash
python3 -m pytest -v
```

All 31 unit and integration tests run against an **isolated in-memory SQLite database** (`sqlite:///:memory:`) using clean transactional fixtures, guaranteeing zero alteration or deletion of your local development database.
