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
uvicorn app.main:app --reload
```

The database builds itself on first start. Confirm it is up by opening
`http://localhost:8000/health` once — you should get `{"status":"ok"}` — then
close that tab.

### 2. Serve the frontend on port 5500

The API's allowed origins default to `http://localhost:5500` and
`http://127.0.0.1:5500`, which is VS Code's Live Server default. Open
`frontend/html/main.html` with **Live Server**.

If you serve it from any other port, the browser will block every API call and
the demo will fail silently. Either use 5500 or set `FRONTEND_ORIGINS` in
`backend/.env` to whatever you are actually using.

### 3. Check your internet connection

The word cloud library is loaded from a CDN (`cdn.jsdelivr.net`), not from the
repo. **No internet means no word cloud, and no word cloud means no demo** —
the page renders the words as plain text with a `WordCloud is not defined`
error where the picture should be.

Load the word cloud page once before you record. If you see a real cloud, you
are fine. If you are recording somewhere with a captive portal or flaky wifi,
either fix that first or point the script tag in
`frontend/html/word_cloud_view_page.html` at the copy already in
`node_modules/wordcloud/src/wordcloud2.js` — that is a one-line change to the
app, so it is the team's call, not something to do five minutes before
recording.

### 4. Open the database in a GUI

Download **DB Browser for SQLite** (free, all platforms) and open
`backend/jobhopper.db`. Leave it open on a second desktop with the *Browse Data*
tab already selected. This is what you switch to for Part 3 — it shows the
database without a terminal, which keeps you inside the no-code rule.

### 5. Clear browser state

Sign out, or open a private window. Part 1 depends on starting signed out.

### 6. Pre-flight checklist

- [ ] Backend running, `/health` returns ok
- [ ] Frontend on port 5500
- [ ] Internet up — word cloud renders as a picture, not as an error
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

## Part 2 — Role 2: the registered user  ·  2:15  ·  Slide 12

> **You must finish all ten questions.** The score is only written to the
> database when the quiz is submitted, and submission happens on the tenth
> answer or when the timer runs out — nothing else. Answering four questions
> and clicking away to the profile leaves *Recent Game History* saying
> "No available data yet", on camera, during the nine-point database item.
> Verified against the running app.

| # | Do | Say |
|---|----|-----|
| 1 | You are on the word cloud registration just generated. Point at the two or three biggest words | "The big words are the ones in the most postings. That's a count, not an opinion." |
| 2 | Hover a skill so the cursor changes | "Any skill we have questions for is clickable." |
| 3 | Click a big skill → difficulty screen → choose **Easy** | "Three difficulties, three timers. Easy gives us three minutes — enough to finish." |
| 4 | Answer question 1 **correctly** | "It tells me immediately — and it can, because my answer was already locked in on the server before I was told, so knowing it now can't change it." |
| 5 | Answer question 2 **wrong on purpose** | "And there's the other case. It shows the right answer, and the clock pauses while I read it." |
| 6 | Say you'll speed up, then click through questions 3–10 without narrating each one | "I'll speed through the rest." |
| 7 | The Submit button is replaced by a return button. Click it | "That's the quiz graded and saved." |
| 8 | Profile: *Recent Game History* now has the score, *Recent Word Clouds* has the search | "We didn't refresh anything. That's the database answering." |
| 9 | Click **Search Again** on a saved cloud | "Every search is saved, and re-runnable." |

Timing: steps 4–6 are where takes run long. Answering ten on Easy takes about
sixty seconds if you don't read the questions aloud. Practise it once.

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
| 3 | Browse Data → **game_attempts** | "And the quiz: skill, difficulty, score, seconds taken." |
| 4 | Browse Data → **users**, `password_hash` column | "That's a bcrypt hash. We couldn't tell you that user's password if we wanted to — we never stored it." |
| 5 | Browse Data → **job_skills** or **skills** | "And this is where the cloud comes from — a count per skill, not a list we typed." |
| 6 | Close | "Everything you saw on screen came out of this file." |

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
