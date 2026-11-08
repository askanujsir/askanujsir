# askanujsir
AI-powered CBSE Class 12 learning platform: syllabus-grounded AI tutor, PYQ practice, AI sample papers, community chat, leaderboard, and an admin content interface. Modular monolith: FastAPI + SQLAlchemy + Neon Postgres (backend), React + Vite + TypeScript + Tailwind (frontend), Groq `openai/gpt-oss-20b`.

## Features
- Landing page, student auth (bcrypt, JWT access + rotating refresh tokens), teacher login shows "Teacher Portal is currently under development".
- Subjects: only Computer Science enabled; others show Coming Soon and can be enabled in Admin > Subjects.
- Versioned syllabus (upload PDF/DOCX -> review/edit -> publish & activate; history is kept). The tutor loads the active syllabus from PostgreSQL at runtime.
- AI Study Companion: persistent per-student chats, off-topic refusal, recent-message context window, rate limited.
- PYQ practice: years come from published papers; timed (server-enforced) / untimed; single, multiple, assertion-reason; palette, review marks, scoring with per-question negative marking.
- Paper ingestion: CSV -> deterministic MCQ row parsing -> human review/edit -> publish. Required columns are `question, option_a, option_b, option_c, option_d, answer`; optional columns are `marks` and `explanation`. `answer` may be A-D or a zero-based option index. Blank option columns are retained for review, while complete options are required before publishing. Invalid rows are reported as skipped. Originals are stored via the storage adapter.
- AI sample papers: generation uses the uploaded syllabus and a fixed CBSE Class 12 board pattern (18 MCQs, 3 assertion-reasoning, 7 two-mark, 3 three-mark, and 2 five-mark questions) through Groq's `openai/gpt-oss-120b` model. Labelled "AI-Generated Practice Paper — CBSE Pattern".
- Community: one shared room over WebSockets (auth, 500-char limit, rate limit, history, reconnect, report).
- Leaderboard (weekly / all-time): best attempt per PYQ paper (2 pts per correct + 5 completion) + top 5 sample papers (1 pt per correct). Retakes and bulk generation can't farm points.
- Dashboard: all numbers from DB; streaks use Asia/Kolkata and count chat, PYQ and sample-paper activity (not community chat).
- Profile: update name / password.
- Admin UI at `/app/admin` (admin role only): overview, subjects & years, syllabus, papers + review editor, blueprints.

## Setup
Prereqs: Python 3.11+, Node 18+, a Neon Postgres database, a Groq API key.
1. **Neon**: create a project, copy the connection string into `DATABASE_URL` as `postgresql+psycopg2://user:pass@host/db?sslmode=require`.
2. **Storage**: `STORAGE_PROVIDER=local` (default, `./storage`) or `s3` with `S3_ENDPOINT_URL`, `S3_BUCKET`, `S3_ACCESS_KEY`, `S3_SECRET_KEY` (Neon Bucket or any S3-compatible service). If storage is unavailable, uploads fail with a clear 503; everything else keeps working.
3. **AI providers**: set `GROQ_API_KEY` for the AI tutor and sample-paper generation. Set `GEMINI_API_KEY` for question-paper MCQ extraction and answer-key inference. Without the relevant key, that feature returns a 503 message and the rest of the app works.
4. **Backend**
```
cd backend && cp .env.example .env     # edit values, set ADMIN_EMAIL / ADMIN_PASSWORD
pip install -r requirements.txt
alembic upgrade head                   # or leave AUTO_CREATE_TABLES=true for dev
uvicorn app.main:app --reload          # API docs: http://localhost:8000/docs
```
The admin account is created at startup from `ADMIN_EMAIL` / `ADMIN_PASSWORD`. There is no public admin registration. The first Alembic revision snapshots the current models; create later ones with `alembic revision --autogenerate -m "msg"`. If you used `alembic upgrade head`, set `AUTO_CREATE_TABLES=false`.
5. **Frontend**
```
cd frontend && cp .env.example .env && npm i && npm run dev   # http://localhost:5173
```
6. **Tests**: `cd backend && pytest`. Frontend check: `cd frontend && npm run build`.

## Render deployment
The repository includes [render.yaml](./render.yaml) and [backend/Dockerfile](./backend/Dockerfile) for deploying the FastAPI backend as a Render Docker web service. Create the service from the Blueprint, then provide the `DATABASE_URL`, AI keys, admin credentials, `FRONTEND_URL`, and S3 credentials as Render environment variables. The container runs `alembic upgrade head` before starting Uvicorn and listens on Render's `PORT`.

## Content workflow (log in as the admin, open Admin in the sidebar)
1. Subjects & Years: add an academic year; enable subjects.
2. Syllabus: upload PDF/DOCX (lines starting with "Unit"/"Chapter" become units, which you then edit as JSON) -> Save, publish & activate.
3. Papers: upload a CSV with the documented MCQ columns, Extract, fix every question (type, options, correct indices, marks, negative, order), Save & publish. The year then appears for students automatically.
4. Blueprints: open Admin > Blueprints, enter the number of questions for each fixed board section (18 one-mark MCQs, 3 one-mark assertion-reason, 7 two-mark, 3 three-mark, and 2 five-mark questions), create a draft, then click Publish. Marks, sections, question types, and the 180-minute duration are fixed; the active blueprint controls only the counts. Sample paper generation needs both a published blueprint and a published active syllabus.

## Known limitations
- Leaderboard is computed on request (fine for MVP scale). Community uses an in-process hub, so run one backend worker. Rate limits are in-memory per process.
- Syllabus structure detection is heuristic, so review it. OCR needs `pytesseract` plus the Tesseract binary.
- The `assets/` folder is empty: no logo was supplied. Put it in `assets/` and as `frontend/public/logo.png`.
- Not covered by tests: frontend UI flows.
