# JobHopper App Project

JobHopper helps users explore skills requested in current job postings. The
backend stores scraped/seeded postings, generates skill word-cloud data, and
supports login, recent activity, quizzes, and prep roadmaps.

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
uvicorn app.main:app --reload
```

Leave `--reload` off when you are demonstrating the app. It restarts the server
on any file change, and while that no longer signs anyone out, a restart in the
middle of a recording is still a restart.

The database is built locally and is not committed. On startup the app creates
`backend/jobhopper.db`, upgrades its schema, and loads any seed data it is
missing, so a fresh clone works with no extra steps. It also reloads the quiz
bank whenever `app/seed_data/questions_seed.json` changes and refreshes the job
postings once they age past a week, which keeps them inside the 30-day window
the word cloud requires. Set `AUTO_SEED=false` in `backend/.env` to turn that
off.

You can still run the loaders by hand, for example after editing a fixture:

```bash
python -m app.seed             # load the shared job postings
python -m app.seed_questions   # load the quiz question bank
```

To start over, delete the database and restart the server:

```bash
rm -f jobhopper.db jobhopper.db-wal jobhopper.db-shm
```

API docs are available at `http://localhost:8000/docs`.

## Frontend Quick Start

The API only accepts requests from `http://localhost:5500` and
`http://127.0.0.1:5500` (see `FRONTEND_ORIGINS` in `backend/.env.example`), so
the pages have to be served from port 5500. Opening the HTML files straight off
disk makes every API call fail.

Either open `frontend/html/main.html` with VS Code's **Live Server**, which
defaults to 5500, or serve the folder with no extra tooling:

```bash
python3 -m http.server 5500 --directory frontend
```

Then go to `http://localhost:5500/html/main.html`.

Nothing on the pages is fetched from a CDN except Bootstrap and the font. The
word cloud library is committed in `frontend/js/vendor/`, so the word cloud
still renders with no internet connection.

Edit the styles through Sass, never `frontend/css/style.css` directly:

```bash
npm run sass          # watches frontend/scss and rebuilds style.css
```

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
- `GET /postings` (the postings a cloud was built from, same filters)
- `GET /roles` (dropdown source: roles with fresh postings)
- `GET /locations` (dropdown source: locations with fresh postings)
- `POST /auth/register`, `POST /auth/login`, `GET /auth/me` (JWT bearer auth)
- `GET /game/skills` (which skills have quizzes, and at which difficulties)
- `GET /game/{skill}?difficulty=easy|medium|hard` and `POST /game/{skill}/submit`
- `POST /roadmap`, `GET /roadmap`, `PATCH /roadmap/steps/{id}`
- `GET /me/recent` (last game plus last 5 searches)
- `GET /me/games` (full quiz history plus per-skill bests)
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
- `GET /postings` takes the same search fields as `/wordcloud` and resolves the
  role the same way, so the listings it returns are the ones a given cloud was
  counted from. `frontend/js/postings_table.js` renders them; both the word
  cloud page and the roadmap page use it.
- Registration passwords must be 8-20 characters; usernames are 4-16 letters
  and digits. Login returns a JWT; send it as an `Authorization: Bearer` header.
- Anyone can play quizzes; attempts are saved to the account only when logged in.
- The backend currently supports `min_salary`; the team still needs to either
  implement `max_salary` backend support or remove the max salary field from the
  frontend.
