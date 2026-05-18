# Marketing Content Generation

An end-to-end pipeline that turns recorded audio or video into a reviewed marketing draft.

```
Producer uploads media → Whisper transcribes → Gemini / Claude drafts → Reviewer approves
```

## Architecture

```
┌─────────────┐   POST /events        ┌─────────────────────────────────────────┐
│  Producer   │ ──────────────────▶   │              FastAPI Backend             │
│  (browser)  │ ◀── pre-signed URL ── │                                         │
└─────────────┘                       │  /events      – create & list events    │
       │                              │  /webhooks    – GCS Pub/Sub handler     │
       │ PUT (direct to GCS)          │  /drafts      – read generated drafts   │
       ▼                              │  /reviews     – comments & decisions    │
┌─────────────┐  Pub/Sub notify       └────────────────────┬────────────────────┘
│    GCS      │ ──────────────────────────────────────────▶│
└─────────────┘                                            │ background task
                                                           ▼
                                               ┌───────────────────────┐
                                               │  Whisper (transcribe) │
                                               │  Gemini / Claude (LLM)│
                                               └───────────┬───────────┘
                                                           │
                                                           ▼
                                                     PostgreSQL
                                                           │
                                               ┌───────────┴───────────┐
                                               │       Reviewer         │
                                               │  view · comment ·     │
                                               │  approve / reject      │
                                               └───────────────────────┘
```

**GCP services:** Cloud Run · Cloud SQL (Postgres) · GCS · Pub/Sub · Secret Manager · Artifact Registry

## Project Structure

```
marketing-content-generation/
├── backend/
│   ├── app/
│   │   ├── config.py          – all settings (env-driven)
│   │   ├── database.py        – async SQLAlchemy engine + session
│   │   ├── main.py            – FastAPI app, CORS, lifespan
│   │   ├── models/            – SQLAlchemy ORM models
│   │   │   ├── event.py
│   │   │   ├── media.py
│   │   │   ├── draft.py
│   │   │   └── review.py
│   │   ├── schemas/           – Pydantic request/response models
│   │   ├── routers/
│   │   │   ├── events.py      – create event, get status
│   │   │   ├── webhooks.py    – Pub/Sub push + /simulate endpoint
│   │   │   ├── drafts.py      – read draft
│   │   │   └── reviews.py     – comments, approve/reject
│   │   └── services/
│   │       ├── gcs.py         – signed URLs, download (emulator-aware)
│   │       ├── transcription.py – Whisper via ffmpeg
│   │       └── draft_generation.py – Gemini or Claude (config-driven)
│   ├── alembic/               – DB migrations
│   ├── tests/
│   │   └── test_pipeline.py   – full flow integration test
│   ├── Dockerfile
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── ProducerPage.tsx  – create event, upload media, list events
│       │   ├── StatusPage.tsx    – pipeline progress (auto-polls)
│       │   └── ReviewPage.tsx    – read draft, comment, approve/reject
│       ├── api/                  – typed API client (axios + React Query)
│       └── types/                – shared TypeScript types
├── infra/
│   ├── setup_gcp.sh           – one-time GCP resource bootstrap
│   └── deploy.sh              – Cloud Run build + deploy
└── docker-compose.yml
```

## Event Pipeline States

```
pending_upload → transcribing → drafting → draft_ready → approved
                                                       └→ rejected
```

Any step can transition to `failed` on error.

---

## Local Development

### Prerequisites

- Docker & Docker Compose
- A free Gemini API key from [aistudio.google.com/apikey](https://aistudio.google.com/apikey)

### 1. Configure environment

```bash
cd backend
cp .env.example .env
```

Edit `.env` and set at minimum:

```env
GEMINI_API_KEY=your-key-here
```

### 2. Start all services

```bash
docker compose up --build
```

This starts:
| Service | URL |
|---------|-----|
| Frontend (React) | http://localhost:3000 |
| Backend (FastAPI) | http://localhost:8000 |
| API docs (Swagger) | http://localhost:8000/docs |
| Postgres | localhost:5432 |
| fake-gcs-server | http://localhost:4443 |

> **Note:** The first build downloads the Whisper `base` model (~150 MB) and caches it in a Docker volume — subsequent starts are fast.

### 3. Test the pipeline locally (without real GCS)

After creating an event via the UI or API, trigger the pipeline directly:

```bash
curl -X POST http://localhost:8000/webhooks/gcs/simulate \
  -H "Content-Type: application/json" \
  -d '{"event_id": "<uuid-from-create-event>"}'
```

This skips the actual GCS upload and drives the full transcription → draft flow.

### Running tests

```bash
# Start Postgres only
docker compose up db -d

cd backend
pip install -r requirements-dev.txt
pytest tests/ -v
```

Tests mock Whisper and the LLM — no API keys or GCS needed.

---

## LLM Provider

Controlled by `LLM_PROVIDER` in `.env`:

| Value | Model | Notes |
|-------|-------|-------|
| `gemini` (default) | `gemini-2.0-flash` | Free tier, 1,500 req/day |
| `claude` | `claude-opus-4-7` | Requires paid Anthropic key |

Switch at runtime — no code change needed:

```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=...

# or

LLM_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-...
```

On Cloud Run with `LLM_PROVIDER=gemini` you can leave `GEMINI_API_KEY` empty — the library uses Application Default Credentials automatically.

---

## API Reference

### Events

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/events` | Create event — returns pre-signed GCS upload URL |
| `GET` | `/events` | List events (filter by `?producer_id=`) |
| `GET` | `/events/{id}` | Get event |
| `GET` | `/events/{id}/status` | Full pipeline status (poll this) |

### Webhooks

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/webhooks/gcs?token=` | GCS Pub/Sub push endpoint |
| `POST` | `/webhooks/gcs/simulate` | **Dev only** — trigger pipeline without a real upload |

### Drafts

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/drafts/by-event/{event_id}` | Get draft for an event |
| `GET` | `/drafts/{draft_id}` | Get draft by ID |

### Reviews

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/reviews/by-draft/{draft_id}` | Get review (auto-created on first view) |
| `POST` | `/reviews/by-draft/{draft_id}/comments` | Add comment |
| `POST` | `/reviews/by-draft/{draft_id}/decision` | Submit `approved` or `rejected` |

---

## GCP Deployment

### 1. Bootstrap GCP resources (once)

```bash
export PROJECT_ID=your-gcp-project-id
export REGION=us-central1
./infra/setup_gcp.sh
```

Creates: GCS bucket, Pub/Sub topic + GCS notification, service account with required roles, Artifact Registry repo. Prints Cloud SQL setup commands to run next.

### 2. Store secrets in Secret Manager

```bash
echo -n "your-gemini-key"    | gcloud secrets create gemini-api-key    --data-file=-
echo -n "your-webhook-token" | gcloud secrets create pubsub-webhook-token --data-file=-
echo -n "your-secret-key"    | gcloud secrets create app-secret-key    --data-file=-
```

### 3. Deploy

```bash
export PROJECT_ID=your-gcp-project-id
./infra/deploy.sh
```

Builds and pushes Docker images to Artifact Registry, deploys backend and frontend as separate Cloud Run services.

### 4. Wire Pub/Sub → Cloud Run

After the first deploy, re-run setup with the backend URL to create the push subscription:

```bash
export BACKEND_URL=$(gcloud run services describe marketing-content-backend \
  --region=us-central1 --format="value(status.url)")
./infra/setup_gcp.sh
```

---

## Database Migrations

```bash
cd backend

# Apply all migrations
alembic upgrade head

# Generate a new migration after model changes
alembic revision --autogenerate -m "describe change"
```

In development, tables are auto-created on startup (`APP_ENV=development`). Use Alembic for production.
