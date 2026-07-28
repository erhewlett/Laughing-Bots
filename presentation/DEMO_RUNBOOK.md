# JobHopper — live demo runbook

Everything the demo needs, in the order it happens. Total demo budget: **4:00**
inside a 15-minute video.

Two rules, both from the assignment and the rubric:

- **No code segments on screen.** Browser, database browser and diagrams are
  fine. An editor, a terminal, or a source file is not. Close them before you
  start recording.
- **Do not debug on camera.** If something breaks, say what should have
  happened, finish the thought, and cut a fresh take.

---

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

### 3. Open the database in a GUI

Download **DB Browser for SQLite** (free, all platforms) and open
`backend/jobhopper.db`. Leave it open on a second desktop with the *Browse Data*
tab already selected. This is what you switch to for Part 3 — it shows the
database without a terminal, which keeps you inside the no-code rule.

### 4. Clear browser state

Sign out, or open a private window. Part 1 depends on starting signed out.

### 5. Pre-flight checklist

- [ ] Backend running, `/health` returns ok
- [ ] Frontend on port 5500
- [ ] DB Browser open on `jobhopper.db`, Browse Data tab
- [ ] Signed out / private window
- [ ] Editor, terminal and file explorer closed or on another desktop
- [ ] Notifications silenced, screen at 1080p or better
- [ ] A backup account already registered, in case live registration fails
- [ ] Deck open on slide 11

---

## Part 1 — Role 1: the visitor  ·  1:00  ·  Slide 11

| # | Do | Say |
|---|----|-----|
| 1 | Home page (`main.html`) | "This is what a visitor sees. Rules, stack, creators — all public." |
| 2 | Open **Game Rules** briefly | "Three difficulties, three timers — three minutes, two, and a minute and a half." |
| 3 | Try to open the word cloud page while signed out | "It sends me to sign-in. And it isn't just the page hiding a button — the API refuses that request too." |
| 4 | Go to **Sign Up**. Type a 3-character username so the validation message appears, then fix it | "Validation is inline, next to the field it belongs to." |
| 5 | Finish the form — it also collects your first word-cloud search (job title, location, minimum salary, keyword count, shape) | "Registration and your first search are one step." |
| 6 | Submit | You land signed in, on your first word cloud. Hand over. |

**If registration fails on camera:** say "we already have an account set up for
this," sign in with the backup account, and carry on. Do not investigate.

---

## Part 2 — Role 2: the registered user  ·  2:00  ·  Slide 12

| # | Do | Say |
|---|----|-----|
| 1 | You are on the word cloud registration just generated. Point at the two or three biggest words | "The big words are the ones in the most postings. That's a count, not an opinion." |
| 2 | Hover a skill so it shows as clickable | "Any skill we have questions for is clickable." |
| 3 | Click a big skill → difficulty screen → choose **Medium** | "Medium gives us two minutes." |
| 4 | Answer 3–4 questions. **Get one wrong deliberately.** Point at the clock and the running score | "It tells me immediately — and it can, because the answer was already locked in on the server before I was told." |
| 5 | **Do not play all ten.** Navigate to the profile page | — |
| 6 | Profile: *Recent Game History* and *Recent Word Clouds* | "We didn't refresh anything. That's the database answering." |
| 7 | Click **Search Again** on a saved cloud | "Every search is saved, and re-runnable." |
| 8 | Optional, only if you are ahead of the clock: **Generate New Word Cloud** with a different role and shape | "Different role, different picture — nothing here is hard-coded." |

Timing note: step 4 is where takes run long. Cap it at four questions.

---

## Part 3 — It really is a database  ·  1:00  ·  Slide 13

Switch to the **DB Browser for SQLite** window. This part is worth 9 rubric
points on its own — do not rush it, and do not narrate the mouse.

| # | Do | Say |
|---|----|-----|
| 1 | Show the table list in the sidebar | "Fourteen tables — the same fourteen you just saw in the ERD. That diagram isn't a drawing of what we planned; it's what's actually in the file." |
| 2 | Browse Data → **searches**. Scroll to the last row | "There's the search from ninety seconds ago — the role, the salary, the shape, the timestamp, and a user_id pointing at the account we made on camera." |
| 3 | Browse Data → **game_attempts** | "And the quiz: skill, difficulty, score, seconds taken." |
| 4 | Browse Data → **users**, `password_hash` column | "That's a bcrypt hash. We couldn't tell you that user's password if we wanted to — we never stored it." |
| 5 | Browse Data → **job_skills** or **skills** | "And this is where the cloud comes from — a count per skill, not a list we typed." |
| 6 | Close | "Everything you saw on screen came out of this file." |

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
