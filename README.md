# ResolveAI

> **Personal repair-resolution agent** being developed for the Amazon Developer Hackathon.
> ResolveAI helps consumers manage recurring product-repair problems, starting with a laptop that develops the same fault again after two repair attempts.

---

## Backend — Phases 1 to 5: Case Management, Timeline, Evidence, Reasoning & Actions

This repository contains the backend for ResolveAI, built with **Python**, **FastAPI**, **SQLAlchemy**, and **SQLite**.

### Technology Stack
- **Python**: 3.14+ (compatible with Python 3.10+)
- **FastAPI**: 0.115+
- **Uvicorn**: 0.30+
- **SQLAlchemy**: 2.0+
- **Pydantic**: 2.7+
- **pypdf**: 5.0+ (selectable text extraction from PDFs)
- **python-multipart**: 0.0.9+ (multipart/form-data support)
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
| `POST` | `/api/cases` | Create a new repair case (initial status: `NEW`, logs `CASE_CREATED`) |
| `GET` | `/api/cases` | List all existing repair cases (ordered newest first) |
| `GET` | `/api/cases/{case_id}` | Retrieve a specific case by its UUID (returns 404 if not found) |
| `PATCH` | `/api/cases/{case_id}` | Partially update case details (`title`, `product_name`, `issue_description`) |
| `PATCH` | `/api/cases/{case_id}/status` | Transition case workflow status (returns 409 on disallowed transitions) |
| `POST` | `/api/cases/{case_id}/events` | Add a manual user note (`event_type: NOTE_ADDED`) to the timeline |
| `GET` | `/api/cases/{case_id}/timeline` | Retrieve chronological timeline events (`skip` & `limit` query parameters supported) |
| `POST` | `/api/cases/{case_id}/evidence` | Upload evidence document/image via `multipart/form-data`, extracts text, logs timeline event |
| `GET` | `/api/cases/{case_id}/evidence` | List all evidence metadata attached to a case (omits heavy text bodies) |
| `GET` | `/api/cases/{case_id}/evidence/{evidence_id}` | Retrieve single evidence metadata with complete extracted text and suggestions |
| `DELETE` | `/api/cases/{case_id}/evidence/{evidence_id}` | Safely remove stored disk file and database metadata; records `EVIDENCE_DELETED` |
| `GET` | `/api/cases/{case_id}/evidence-checklist` | Heuristic checklist comparing existing vs missing document categories |
| `GET` | `/api/policies` | List available policy sources and references without complete text |
| `GET` | `/api/policies/{policy_id}` | Retrieve full policy source text and provenance metadata |
| `POST` | `/api/policies/search` | Search policy library for passages matching query tokens |
| `POST` | `/api/cases/{case_id}/analysis` | Generate structured case-aware analysis and next-step recommendations |
| `POST` | `/api/cases/{case_id}/chat` | Ask questions about a case; returns grounded answers citing case context and policy |
| `POST` | `/api/cases/{case_id}/actions` | Propose an action for a case (initial status: `PENDING_APPROVAL`, requires user approval) |
| `GET` | `/api/cases/{case_id}/actions` | List all proposed, approved, and executed actions for a case |
| `GET` | `/api/cases/{case_id}/follow-ups` | List scheduled follow-ups for a case with real-time `is_overdue` status |
| `GET` | `/api/actions/{action_id}` | Retrieve single action record |
| `PATCH` | `/api/actions/{action_id}` | Edit an action in `DRAFT` or `PENDING_APPROVAL` (invalidates prior approval) |
| `POST` | `/api/actions/{action_id}/approve` | Explicitly approve an action (transitions from `PENDING_APPROVAL` to `APPROVED`) |
| `POST` | `/api/actions/{action_id}/reject` | Explicitly reject an action (transitions to `REJECTED`, permanently blocks execution) |
| `POST` | `/api/actions/{action_id}/execute` | Execute an approved action in a safe simulated environment (idempotent) |

---

## Agent Actions & Approval Workflow (Phase 5)

ResolveAI enforces human-in-the-loop control for any consequential action. The AI or system may only propose actions; execution is strictly blocked until explicit user approval is recorded.

### 1. Action Lifecycle State Machine
```
[DRAFT] / [PENDING_APPROVAL] ──(Approve)──► [APPROVED] ──(Execute)──► [EXECUTED]
       │             ▲                          │
       │             └──(Edit invalidates)──────┘
       ▼
   [REJECTED] (permanently blocked)
```

- **Supported Action Types**:
  - `SEND_MESSAGE`: Generates a proposed communication (e.g. escalation notice). Must include `recipient`, `message_body`, and `is_simulated: true`.
  - `SCHEDULE_FOLLOW_UP`: Establishes a reminder. Must include `due_at` (UTC timestamp) and `purpose`.
- **Supported Statuses**: `DRAFT`, `PENDING_APPROVAL`, `APPROVED`, `REJECTED`, `EXECUTED`, `FAILED`, `CANCELLED`.
- **Approval Invalidation**: If an action is edited via `PATCH /api/actions/{action_id}`, any existing approval is automatically revoked and the status returns to `PENDING_APPROVAL`.
- **Execution Guardrails**:
  - Unapproved or rejected actions return `HTTP 409 Conflict` upon execution attempts.
  - The AI model is strictly prohibited from approving actions on the user's behalf.
  - Idempotent execution: Calling execute on an already executed action returns the existing record without duplicating effects.

### 2. Simulated Environment Execution
- **`SEND_MESSAGE`**: Simulated delivery dispatches to an internal simulation log. No real external emails, SMS, or manufacturer APIs are invoked.
- **`SCHEDULE_FOLLOW_UP`**: Records the due timestamp in persistent SQLite storage. No external calendar or third-party webhooks are fired.
- **Real-Time Overdue Calculation**: `GET /api/cases/{case_id}/follow-ups` dynamically evaluates current UTC time against `due_at` to mark `is_overdue: true` if the deadline has elapsed.

---

## Policy Retrieval & Case Reasoning (Phase 4)

ResolveAI provides a policy retrieval and case reasoning engine that grounds advice in case facts and reference standards.

### 1. Curated Policy Library & Provenance Rules
The policy library is seeded idempotently on application startup into the `policy_sources` SQLite table. Every source includes its provenance:
- **Illustrative Standards**: Clearly labeled with `DEMO POLICY — NOT AN OFFICIAL MANUFACTURER POLICY` (e.g., replacement escalation thresholds after 2 repair attempts).
- **Reference pointer**: The National Consumer Helpline entry stores a link only. It is classified as general guidance and contains no verified quote or legal rule.
- **Best Practice Evidence Guidelines**: Checklists and guidance for chain-of-custody in repeat repair disputes.
- **Offline Reliability**: Seeding is local and does not require internet connectivity.

### 2. Lexical Policy Retrieval
- The `PolicyRetrievalService` implements lexical keyword matching with frequency weighting and title boost.
- Breaks policy documents into discrete passages and returns passages with relevance scores.
- Rejects empty queries and returns empty lists for irrelevant queries without fabricating citations.

### 3. Demo Mode and Provider Availability
- **Default Engine**: `AI_PROVIDER=demo` (Deterministic Rule-Based Engine).
- **Zero API Key Requirement**: Runs completely locally with no external API subscription needed.
- **Distinction of Facts**: Separates user-reported facts, extracted document snippets, policy passages, and AI inferences.

---

## Evidence Management & Document Processing

### Supported File Formats:
- **PDF** (`.pdf`): Selectable text is extracted using `pypdf`. Image-only/scanned PDFs yield extraction status `NO_TEXT_FOUND`.
- **PNG** (`.png`), **JPG / JPEG** (`.jpg`, `.jpeg`): Supported for document attachments. Returns `UNSUPPORTED` extraction status (OCR is intentionally out of scope).
- **Validation**: Strict file magic header inspection prevents client MIME spoofing (e.g. `.exe` disguised as `.pdf`).

### Maximum File Size:
- Default: **10 MB** (10,485,760 bytes). Configurable via `MAX_UPLOAD_SIZE_BYTES` in `.env`.
- Uploads are streamed in bounded chunks to prevent high memory consumption.

### Local File Storage & Security:
- Files are saved to `./uploads/` (or configured `UPLOAD_DIR`).
- Stored using random server-generated UUID filenames (`<hex>.<ext>`) to prevent directory traversal attacks.
- Absolute filesystem paths are never exposed over API responses.
- Uploaded files are excluded from Git via `.gitignore`.

---

## Case Workflow Status Transitions

ResolveAI implements a controlled state machine. Invalid transitions return `HTTP 409 Conflict`.

- **`NEW`** ➔ `COLLECTING_EVIDENCE`, `UNDER_REVIEW`, `CLOSED`
- **`COLLECTING_EVIDENCE`** ➔ `UNDER_REVIEW`, `ACTION_READY`, `CLOSED`
- **`UNDER_REVIEW`** ➔ `COLLECTING_EVIDENCE`, `ACTION_READY`, `RESOLVED`, `CLOSED`
- **`ACTION_READY`** ➔ `COLLECTING_EVIDENCE`, `AWAITING_RESPONSE`, `CLOSED`
- **`AWAITING_RESPONSE`** ➔ `FOLLOW_UP_DUE`, `UNDER_REVIEW`, `RESOLVED`, `CLOSED`
- **`FOLLOW_UP_DUE`** ➔ `UNDER_REVIEW`, `AWAITING_RESPONSE`, `RESOLVED`, `CLOSED`
- **`RESOLVED`** ➔ `UNDER_REVIEW` (reopened if issue returns), `CLOSED`
- **`CLOSED`** ➔ `UNDER_REVIEW` (reopened if further work required)

---

## Database Storage & Schema Changes

- **Default Location**: `backend/data/resolveai.db` (auto-created on startup).
- **Persistent**: Survives backend restarts.
- **Schema setup**: `init_db()` uses SQLAlchemy `create_all()` to create missing tables. This safely creates the `actions` table and preserves all existing `cases`, `case_events`, `evidence`, and `policy_sources` data without alteration.

---

## Running Automated Tests

Run the full pytest suite from the `backend/` directory:

```bash
python3 -m pytest -v
```

All 67 unit and integration tests run against an **isolated in-memory SQLite database** (`sqlite:///:memory:`) and temporary upload directories.
