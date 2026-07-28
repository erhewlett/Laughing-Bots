# JobHopper — live demo runbook

Everything the demo needs, in the order it happens. Total demo budget: **4:55**
inside a 15-minute video — 1:30 for the visitor, 2:15 for the registered user,
1:10 for the database.

Two rules, both from the assignment and the rubric:

- **No code segments on screen.** Browser, database browser and diagrams are
  fine. An editor, a terminal, or a source file is not. Close them before you
  start recording.
- **Do not debug on camera.** If something breaks, say what should have
  happened, finish the thought, and cut a fresh take.

---

> Every step below was run against the real app before this was written, so
> the click path, the field names and the redirects are what actually happens.

## Before you record

### 1. Start the backend

Do this **before** recording starts, in a terminal window you then move to
another desktop or minimise.

```bash
cd backend
python -m venv venv && source venv/bin/activate   # first time only
pip install -r requirements.txt                   # first time only
uvicorn app.main:app
```

**No `--reload`.** It restarts the server on any file change, and a restart in
the middle of a take is a restart. Nothing needs it here.

The database builds itself on first start. Confirm it is up by opening
`http://localhost:8000/health` once — you should get `{"status":"ok"}` — then
close that tab.

### 2. Serve the frontend on port 5500

The API only accepts requests from `http://localhost:5500` and
`http://127.0.0.1:5500`. If you serve the pages from any other port, or open
them straight off disk, the browser blocks every API call and the demo fails
silently.

Either open `frontend/html/main.html` with VS Code's **Live Server**, which
defaults to 5500, or run this from the repo root, which needs nothing installed:

```bash
python3 -m http.server 5500 --directory frontend
```

Then go to `http://localhost:5500/html/main.html`.

### 3. Load each page once before you record

The word cloud library is committed in `frontend/js/vendor/`, so the cloud
renders with no internet connection. Bootstrap and the Cascadia Code font still
come from a CDN, so without a connection the pages work but look plain.

Click through the whole demo path once anyway. A page that has been loaded once
is a page that will not surprise you.

### 4. Open the database in a GUI

Download **DB Browser for SQLite** (free, all platforms) and open
`backend/jobhopper.db`. Leave it open on a second desktop with the *Browse Data*
tab already selected. This is what you switch to for Part 3 — it shows the
database without a terminal, which keeps you inside the no-code rule.

### 5. Clear browser state

Sign out, or open a private window. Part 1 depends on starting signed out.

### 6. Pre-flight checklist

- [ ] Backend running **without `--reload`**, `/health` returns ok
- [ ] Frontend on port 5500
- [ ] Word cloud renders as a picture, and the postings table under it has rows
- [ ] DB Browser open on `jobhopper.db`, Browse Data tab
- [ ] Signed out / private window
- [ ] Editor, terminal and file explorer closed or on another desktop
- [ ] Notifications silenced, screen at 1080p or better
- [ ] A backup account already registered, in case live registration fails
- [ ] Deck open on slide 11

---

## Part 1 — Role 1: the visitor  ·  1:30  ·  Slide 11

| # | Do | Say |
|---|----|-----|
| 1 | Home page (`main.html`) | "This is what a visitor sees. Rules, stack, creators — all public." |
| 2 | Open **Game Rules** briefly | "Three difficulties, three timers — three minutes, two, and a minute and a half." |
| 3 | Try to open the word cloud page while signed out | "It sends me to sign-in. And it isn't just the page hiding a button — the API refuses that request too." |
| 4 | Go to **Sign Up**. Type a 3-character username so the validation message appears, then fix it | "Validation is inline, next to the field it belongs to." |
| 5 | Finish the form — it also collects your first word-cloud search. Job title and location are type-ahead fields; start typing and real options appear | "The same form takes your first search. These suggestions are the job titles and locations we actually have postings for — nothing here is typed in by hand." |
| 6 | Submit | You land signed in, on your first word cloud. Hand over. |

**If registration fails on camera:** say "we already have an account set up for
this," sign in with the backup account, and carry on. Do not investigate.

---

## Part 2 — Role 2: the registered user  ·  3:00  ·  Slide 12

> **You must finish all ten questions.** The score is only written to the
> database when the quiz is submitted, and submission happens on the tenth
> answer or when the timer runs out — nothing else. Answering four questions
> and clicking away to the profile leaves *Recent Game History* saying
> "No available data yet", on camera, during the nine-point database item.
> Verified against the running app.

| # | Do | Say |
|---|----|-----|
| 1 | You are on the word cloud registration just generated. Point at the two or three biggest words | "The big words are the ones in the most postings. That's a count, not an opinion." |
| 2 | Scroll down to **The Postings Behind This Cloud** and rest on it for a beat | "And here's what it counted. Real listings, with the company, the location and a link out. The cloud isn't our opinion about the market, it's arithmetic on these rows." |
| 3 | Scroll back up. Hover a skill so the cursor changes | "Any skill we have questions for is clickable." |
| 4 | Click a big skill → difficulty screen → choose **Easy** | "Three difficulties, three timers. Easy gives us three minutes — enough to finish." |
| 5 | Answer question 1 **correctly** | "It tells me immediately — and it can, because my answer was already locked in on the server before I was told, so knowing it now can't change it." |
| 6 | Answer question 2 **wrong on purpose** | "And there's the other case. It shows the right answer, and the clock pauses while I read it." |
| 7 | Say you'll speed up, then click through questions 3–10 without narrating each one | "I'll speed through the rest." |
| 8 | The Submit button is replaced by a return button. Click it | "That's the quiz graded and saved." |
| 9 | Profile: *Recent Game History* now has the score, *Recent Word Clouds* has the search | "We didn't refresh anything. That's the database answering." |
| 10 | Click **My Skill Roadmap** | "Same data, asked a different way. These are the eight skills most in demand for that role, in order." |
| 11 | Set one step to **In progress**, then go back and forward to show it stuck | "Progress is per user and it's saved. Nothing here is in the browser." |
| 12 | Point at **Practise** on any row | "And each one drops straight into the quiz for that skill." |
| 13 | Back to the profile, click **Search Again** on a saved cloud | "Every search is saved, and re-runnable." |

Timing: steps 5–7 are where takes run long. Answering ten on Easy takes about
sixty seconds if you don't read the questions aloud. Practise it once.

Steps 10–12 are the roadmap and they are quick, but if the whole video is
running long they are the safest thing to drop — the roadmap also appears on
the summary slide, so cutting them costs a demonstration and not a
requirement.

Note: you cannot open `word_cloud_view_page.html` directly — it needs a search
first and will send you to the creation page. Reach it by registering, by
submitting the creation form, or via **Search Again** on the profile.

---

## Part 3 — It really is a database  ·  1:10  ·  Slide 13

Switch to the **DB Browser for SQLite** window. This part is worth 9 rubric
points on its own — do not rush it, and do not narrate the mouse.

| # | Do | Say |
|---|----|-----|
| 1 | Show the table list in the sidebar | "There are our fourteen tables — the same fourteen you just saw in the ERD. That diagram isn't a drawing of what we planned; it's what's actually in the file." |
| 2 | Browse Data → **searches**. Scroll to the last row | "There's the search from ninety seconds ago — the role, the salary, the shape, the timestamp, and a user_id pointing at the account we made on camera." |
| 3 | Browse Data → **game_attempts** | "And the quiz: skill, difficulty, score, seconds taken. Every attempt, not just the last one — that's what the history table on the profile was reading." |
| 4 | Browse Data → **users**, `password_hash` column | "That's a bcrypt hash. We couldn't tell you that user's password if we wanted to — we never stored it." |
| 5 | Browse Data → **job_postings** | "And these are the listings you saw under the cloud, sitting in the file." |
| 6 | Browse Data → **job_skills** or **skills** | "And this is where the cloud comes from — a count per skill, not a list we typed." |
| 7 | Browse Data → **roadmap_steps** | "The roadmap too. One row per step, with the progress we set on camera." |
| 8 | Close | "Everything you saw on screen came out of this file." |

DB Browser will list **fifteen** tables, not fourteen. The extra one is
`sqlite_stat1`, which SQLite creates for its own query statistics — it is not
one of ours. Say "our fourteen tables" rather than "fourteen tables", or
point at it and explain it; either is fine, but do not get caught out by it
mid-sentence.

**Fallback if DB Browser is not available:** open
`http://localhost:8000/docs`, expand `POST /wordcloud`, and use *Try it out* to
show the response. It is weaker evidence — it shows the API, not the storage —
so install DB Browser if you possibly can.

---

## Recording

- **Tool:** Zoom (record to computer), OBS, or QuickTime. Zoom is easiest for a
  group — each person speaks on their own mic, and you get one file.
- **Resolution:** 1080p. Anything less and the ERD slide stops being legible,
  which costs slide-legibility points.
- **Share the whole screen**, not a single window — you switch between the deck,
  the browser and the database.
- **Camera on** if you can. The rubric gives 5 points for looking at the
  audience, and a grader can only award that if they can see you.
- **Do one full take** before the real one. The first take always runs long.
- **Check the length before submitting.** Hard cap 15:00.

## Submitting

1. Upload to YouTube as **Unlisted**, or to Google Drive with link sharing on
   for anyone at the school.
2. **Test the link in a private window.** A link that asks the grader for
   permission is the single most common way to lose points on a video
   submission.
3. Submit one video for the group.
