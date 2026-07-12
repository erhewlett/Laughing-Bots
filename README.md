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
python -m app.seed             # load the shared job postings
python -m app.seed_questions   # load the quiz question bank
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
- `POST /wordcloud` (saves search history for logged-in users)
- `GET /roles` (dropdown source: roles with fresh postings)
- `POST /auth/register`, `POST /auth/login`, `GET /auth/me` (JWT bearer auth)
- `GET /game/skills` (which skills have quizzes, and at which difficulties)
- `GET /game/{skill}?difficulty=easy|medium|hard` and `POST /game/{skill}/submit`
- `POST /roadmap`, `GET /roadmap`, `PATCH /roadmap/steps/{id}`
- `GET /me/recent` (last game plus last 5 searches)
- seed loaders: `python -m app.seed` (job postings), `python -m app.seed_questions`
  (quiz bank)

Remaining work:
- expand the quiz question bank in `app/seed_data/questions_seed.json`
  (aim for 10+ questions per skill and difficulty)
- team decision on max salary support

## Frontend Integration Notes

- Populate the industry/role dropdown from `GET /roles`.
- Submit the selected role name as the `industry` value for `/wordcloud`.
- Use `GET /game/skills` to decide which word-cloud words are clickable.
- Registration passwords must be 8-20 characters; usernames are 4-16 letters
  and digits. Login returns a JWT; send it as an `Authorization: Bearer` header.
- Anyone can play quizzes; attempts are saved to the account only when logged in.
- The backend currently supports `min_salary`; the team still needs to either
  implement `max_salary` backend support or remove the max salary field from the
  frontend.
