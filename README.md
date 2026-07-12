# JobHopper App Project

JobHopper helps users explore skills requested in current job postings. The
backend stores scraped/seeded postings, generates skill word-cloud data, and
will support login, recent activity, quizzes, and prep roadmaps.

## Stack

- Frontend: HTML, Bootstrap, Sass
- Backend: FastAPI, SQLAlchemy
- Database: SQLite

## Backend Quick Start

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python -m app.seed
uvicorn app.main:app --reload
```

API docs are available at `http://localhost:8000/docs`.

## Tests

```bash
cd backend
source venv/bin/activate
python -m pytest
```

## Current Backend Status

Implemented:
- `GET /health`
- `POST /wordcloud`
- `GET /roles`
- local seed loader: `python -m app.seed`

Scaffolded, not implemented yet:
- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`
- game endpoints
- roadmap endpoints
- `GET /me/recent`

## Frontend Integration Notes

- Populate the industry/role dropdown from `GET /roles`.
- Submit the selected role name as the `industry` value for `/wordcloud`.
- Registration passwords must be 8-20 characters. Login requires a non-empty
  password and will use the generic auth failure path once auth is implemented.
- The backend currently supports `min_salary`; the team still needs to either
  implement `max_salary` backend support or remove the max salary field from the
  frontend.
