# Deployment

Live deployment (Railway): https://faculty-finder-backend-production.up.railway.app

## Layout

- `db/faculty_finder_dump.sql` — read-only faculty dataset (611 profiles,
  precomputed embeddings, corrected emails). Used to seed a fresh MySQL
  instance without recomputing embeddings via the HF Inference API. Does
  **not** include student accounts/sessions/posts — those tables are
  created empty by `student_db.setup_student_db()` on backend startup, and
  `phd_students` is seeded automatically by the same function.
- `railway/` — single combined-service image (nginx + FastAPI backend in
  one container) for Railway. Kept as one service because the target
  project's free-plan service count was capped. Run `railway/stage.sh`
  first to populate `railway/backend/` and `railway/frontend/` from the
  real source (not committed — regenerated each time to avoid drift), then
  deploy that directory as the build context.

## Railway setup (for reference / redeploying)

Project: `expense-tracker` (Railway account's free-plan project slot),
environment `production`. Services:
- `MySQL` — official Railway MySQL template.
- `faculty-finder-backend` — the combined image above. Env vars:
  `MYSQL_HOST/PORT/USER/PASSWORD/DATABASE` as reference variables pointing
  at the `MySQL` service, plus `HF_TOKEN`, `DEEPSEEK_API_KEY`,
  `USE_DEEPSEEK`, `DEEPSEEK_MODEL`, `LLM_MODEL`, `HF_PROVIDER` as plain
  secrets/variables (not committed anywhere).

Note: the MySQL data volume persists across restarts (unlike the earlier
Hugging Face Space attempt, which re-seeded from scratch every cold start),
so student signups/posts/saved items are not lost on redeploy.

## Hugging Face Spaces — not used

A single-container Docker Space build was prepared but Hugging Face now
requires a PRO subscription to run Docker Spaces on free `cpu-basic`
hardware (static Spaces only are free). The user chose Railway instead.
