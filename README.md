# ScholarLink — Faculty Finder

AI-powered research matchmaking for Shahjalal University of Science and Technology (SUST). Describe a research interest in plain language and get matched with the professors and PhD researchers most relevant to it — semantic search over 611 scraped faculty profiles, not keyword search.

**Live app:** https://faculty-finder-phi.vercel.app/

## Features

- **Natural-language faculty search** — ask things like *"Who works on flood prediction at SUST?"* and get a ranked, structured answer (overview, top matches with reasoning, contact emails, a save button per match) instead of a list of keyword hits.
- **PhD student / researcher search** — same semantic matching over a directory of PhD researchers, filterable by topic, method, or collaboration tag.
- **Student accounts** — sign up, edit a profile (bio, research interests, research summary, certifications, CV), publish posts (work/project or research interest), and set collaboration tags that show up as chips when others search.
- **Saved lists** — bookmark faculty, PhD researchers, or other students from search results and manage them from *My Profile → Saved*.
- **Streaming responses** — chat-style answers stream token-by-token via server-sent events instead of waiting for the full response.
- Monochrome, "liquid glass" UI — translucent blurred panels, light/dark theme toggle, no color anywhere by design.

## Tech stack

| Layer | Tech |
|---|---|
| Frontend | React 18 + Vite, React Router, `react-markdown` |
| Backend | FastAPI (Python), streaming responses via `StreamingResponse` |
| Database | MySQL (`mysql-connector-python`) |
| Embeddings | Hugging Face Inference API (`sentence-transformers/all-MiniLM-L6-v2`), cosine similarity over precomputed vectors |
| LLM | DeepSeek API by default (`USE_DEEPSEEK=true`); can switch to an HF-hosted model instead |
| Deployment | Docker; live on Railway (nginx + FastAPI in one container, MySQL as a managed Railway service) |

## Architecture

```
Browser
  │  same-origin (nginx proxies /ask*, /auth/*, /student/*, /phd-students* to the backend)
  ▼
nginx  ──serves──▶  React static build (frontend/dist)
  │
  └──proxy──▶  FastAPI (uvicorn, 127.0.0.1:8000)
                  │
                  ├─▶ MySQL — faculty data, embeddings, student accounts/posts/tags/saved items
                  └─▶ Hugging Face Inference API (embeddings) + DeepSeek API (chat)
```

In local dev, the frontend (`vite dev`, port 5173) and backend (`uvicorn`, port 8000) run as separate processes/origins instead, talking over CORS (`BACKEND_URL` in `frontend/public/config.js`).

## Project structure

```
backend/
  main.py              FastAPI app — all HTTP routes
  rag.py                RAG core: embeddings, retrieval, LLM prompting (faculty + PhD)
  student_db.py         Student accounts, posts, tags, saved items, PhD student seed data
  db.py                 Thin MySQL connection wrapper (sqlite3-style .execute().fetchall())
  fix_faculty_emails.py One-time data-repair script (see "Data notes" below)
  migrate_to_mysql.py   One-time SQLite → MySQL migration script
frontend/
  src/
    pages/              Home, SearchFaculty, SearchPhd, Profile
    components/         Avatar, Sidebar, ChatMarkdown, TagChips, MeshBackground, SectionLabel
    context/             AuthContext, ThemeContext, ToastContext
    api.js               fetch wrapper (BACKEND_URL resolution, SSE stream consumer)
    styles/               variables.css (theme tokens) + one stylesheet per concern
data/
  Faculty_database.db   Original scraped SQLite source (611 faculty profiles)
deploy/
  db/faculty_finder_dump.sql   Read-only faculty dataset dump, for seeding a fresh MySQL instance
  railway/                     Single-container Docker build used for the live Railway deployment
  README.md                    Deployment notes (Railway setup, redeploy gotchas)
```

## Getting started (local dev)

### Prerequisites

- Python 3.11+
- Node 20+
- A MySQL server reachable at `localhost:3306` (or adjust `MYSQL_*` env vars)
- A Hugging Face access token (embeddings) and a DeepSeek API key (chat), or set `USE_DEEPSEEK=false` and supply an HF-hosted chat model instead

### Environment variables

Create a `.env` file at the repo root:

```env
HF_TOKEN=hf_...
HF_PROVIDER=auto
LLM_MODEL=google/gemma-4-26B-A4B-it        # used only if USE_DEEPSEEK=false
DEEPSEEK_API_KEY=sk-...
USE_DEEPSEEK=true
DEEPSEEK_MODEL=deepseek-v4-flash

MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=faculty_finder

# Only used by backend/migrate_to_mysql.py
SQLITE_PATH=./data/Faculty_database.db
```

### Backend

```bash
cd backend
pip install -r ../requirements.txt
python migrate_to_mysql.py   # first time only — seeds MySQL from data/Faculty_database.db
uvicorn main:app --reload --port 8000
```

On startup the backend also computes any missing embeddings automatically (`rag.ensure_embeddings()` / `rag.ensure_phd_embeddings()`), so a fresh database only pays that cost once.

### Frontend

```bash
cd frontend
npm install
npm run dev   # http://localhost:5173, calls http://localhost:8000 by default (frontend/public/config.js)
```

### Docker Compose (all services)

```bash
docker compose up --build
```

Runs MySQL, the backend (root `Dockerfile`), and the frontend (`frontend/Dockerfile`, nginx-served) together. See `docker-compose.yml` for the exact wiring — the frontend needs `BACKEND_URL` set to whatever's reachable from the *browser*, not the Docker network.

## API overview

All endpoints are on the FastAPI backend. Student-scoped routes take an `x-token` header (session token returned by login/signup).

| Method | Path | Purpose |
|---|---|---|
| GET | `/health` | Liveness check, faculty count |
| POST | `/ask`, `/ask-stream` | Faculty search (buffered / SSE streaming) |
| POST | `/ask-phd`, `/ask-phd-stream` | PhD researcher search (buffered / SSE streaming) |
| GET | `/phd-students`, `/phd-students/{id}` | List / fetch PhD student directory entries |
| POST | `/auth/signup`, `/auth/login`, `/auth/logout` | Account auth |
| GET / PUT | `/student/{id}` | Fetch / update a student profile |
| POST / DELETE | `/student/{id}/posts[/…]` | Publish / remove posts |
| POST / DELETE | `/student/{id}/tags[/…]` | Add / remove collaboration tags |
| POST / DELETE / GET | `/student/{id}/save-faculty[/…]`, `save-phd`, `save-student` | Bookmark management |

## Data notes

Faculty data was scraped from SUST department pages. The scraper captured Cloudflare's email-obfuscation placeholder text instead of real addresses for every row; `backend/fix_faculty_emails.py` recovers the real email from the last path segment of each faculty's `profile_url` (the source site keys profile pages by email). 603 of 611 faculty have a recoverable email this way; the remaining 8 have a plain-username `profile_url` slug with no email to recover.

## Deployment

The live instance runs on Railway: a single container (nginx + FastAPI) alongside a managed MySQL service, built from `deploy/railway/Dockerfile`. See `deploy/README.md` for the full setup (env vars, reference variables, the `railway up --no-gitignore` requirement for redeploys) and why it isn't on Hugging Face Spaces (Docker Spaces there require a paid PRO plan on free hardware).
