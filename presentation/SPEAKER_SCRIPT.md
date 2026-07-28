# JobHopper — final presentation speaker script

> Generated from the speaker notes inside `JobHopper_Final_Presentation.pptx`.
> Edit the notes in `scripts/make_deck.py`, rebuild the deck, then re-run `scripts/make_script.py`.

**Estimated total: 13:54**  (target 14:00, hard ceiling 15:00 — the assignment caps the video at 15 minutes; the rubric penalises going over 20.)

Speaking estimate assumes 140 words per minute, which is an unhurried presenting pace. The three demo slides are timed from the runbook rather than from word count.

## Running order

| # | Slide | Length | Ends at |
|---|-------|--------|---------|
| 1 | Title | 0:16 | 0:16 |
| 2 | The goal | 0:55 | 1:12 |
| 3 | Functional requirements 1 of 2 | 0:45 | 1:57 |
| 4 | Functional requirements 2 of 2 | 0:52 | 2:50 |
| 5 | Non-functional requirements | 0:48 | 3:38 |
| 6 | Technology stack diagram | 1:00 | 4:39 |
| 7 | Why this stack | 1:04 | 5:44 |
| 8 | ERD — subject areas | 0:40 | 6:24 |
| 9 | ERD — full schema | 1:23 | 7:47 |
| 10 | User roles | 0:36 | 8:23 |
| 11 | Demo 1 — the visitor | 1:00 | 9:24 |
| 12 | Demo 2 — the registered user | 2:00 | 11:24 |
| 13 | Demo 3 — it really is a database | 1:00 | 12:24 |
| 14 | Summary — achieved vs changed | 0:59 | 13:23 |
| 15 | Close | 0:30 | 13:54 |

## Who speaks

The assignment does not require everyone to speak, but the rubric rewards a presentation that looks rehearsed. Suggested split — swap names to suit, and put whoever is most comfortable driving the app on the demo:

| Speaker | Slides | Roughly |
|---------|--------|---------|
| Speaker 1 | 1, 2, 10, 14, 15 | open, goal, roles, summary, close |
| Speaker 2 | 3, 4, 5 | functional and non-functional requirements |
| Speaker 3 | 6, 7, 11, 12 | architecture, stack rationale, demo 1–2 |
| Speaker 4 | 8, 9, 12, 13 | the database — ERD and the live data |

## Delivery notes

- **Look up.** Five rubric points ride on looking at the audience rather than reading. Learn the first and last sentence of each slide by heart; improvise the middle.
- **No code on screen.** The assignment forbids showing code segments. The ERD, the architecture diagram and the database browser are all fine — an editor, a terminal or a source file is not.
- **Say the numbers.** 14 tables, 1,260 questions, 40 postings, 237 tests. Specifics are what make a claim land.
- **Do not narrate the mouse.** Say what a thing means, not where you are clicking.
- **If something breaks on camera**, say what should have happened and move on. Do not debug live; stop the recording and re-take instead.

---

## Slide 1 — Title

**Clock:** `0:00 - 0:15`  ·  **Speaker:** SPEAKER 1  ·  **Est. length:** 0:16

Hi, we're the Laughing Bots - Rose, Elijah, Angel and Terrell. This is JobHopper:
it reads real job postings, shows you which skills those postings are actually
asking for, and lets you quiz yourself on any of them.

## Slide 2 — The goal

**Clock:** `0:15 - 1:00`  ·  **Speaker:** SPEAKER 1  ·  **Est. length:** 0:55

The problem isn't that this information is secret - job postings are public.
It's volume. Search one title and you get forty postings, each with its own wall
of requirements. The signal is which tools keep repeating, and nobody reads
forty postings to find it. So people guess at what to learn next.

So our goal was this: analyse the job postings for a target role, identify the
most in-demand skills, and show them as a word cloud - then help people actually
build those skills through interactive Q&A games.

That second half is what we care about. Every skill in the picture is clickable.
Click Python, and you're in a timed quiz on Python. It doesn't just tell you
what to learn - it gives you somewhere to start.

## Slide 3 — Functional requirements 1 of 2

**Clock:** `1:00 - 1:50`  ·  **Speaker:** SPEAKER 2  ·  **Est. length:** 0:45

These are our functional requirements, written the way we specified them. I
won't read them all - two things to point at.

In registration and login, it's the last pair: showing you your most recent game
score, and your three most recent searches. Those are the requirements that
forced everything to be stored against a real account rather than sitting in the
browser.

And in word cloud creation, it's the last line. The size of each word is based
on how often that skill appears across the postings we pulled. Size equals
frequency - a count, not an opinion. That one sentence is the whole product.

## Slide 4 — Functional requirements 2 of 2

**Clock:** `1:50 - 2:40`  ·  **Speaker:** SPEAKER 2  ·  **Est. length:** 0:52

Job scraping is two requirements. Count how often each keyword appears - and
display an error when there isn't enough job information to build a cloud. A
thin, misleading picture is worse than saying we can't build one, so we made
that a requirement rather than an edge case.

The Q&A game block is the exact path you'll see in the demo: click any word, get
sent to that word's game, get questions matching the keyword and difficulty you
chose, on a timer, with your score at the end.

One thing that isn't on the slide - every answer is locked in on the server
before you're told whether it was right, so the running score and the final
score can never disagree.

## Slide 5 — Non-functional requirements

**Clock:** `2:40 - 3:30`  ·  **Speaker:** SPEAKER 2  ·  **Est. length:** 0:48

Non-functional requirements - not features, but the app is wrong without them.

The top row is what we committed to in our spec: the cloud back within ten
seconds, the game open within ten and scored within seven, and all user input
validated and sanitised against injection. We get that last one structurally -
every query goes through the ORM, parameterised, never built by string.

The bottom row we held ourselves to as we built. Passwords bcrypt-hashed and
never returned, and a failed login gives the same generic message whether the
account exists or not. The server decides every score, never the browser. And
237 tests, with nothing merging until both suites pass.

## Slide 6 — Technology stack diagram

**Clock:** `3:45 - 4:40`  ·  **Speaker:** SPEAKER 3  ·  **Est. length:** 1:00

The whole system on one page.

Top: the browser. Eleven HTML pages, Bootstrap for the grid, Sass compiled to one
stylesheet, plain JavaScript modules. No framework, no build step.

The browser talks to exactly one thing - our API. JSON over HTTP, and anything
tied to an account carries a signed token.

The middle band is where every rule lives: FastAPI, sixteen endpoints across six
routers, Pydantic validating every request and response. Underneath sit the
services - hashing and tokens, skill extraction, and the ingest that keeps our
data current. On the right, note that our postings are real, pulled from a live
job-search API.

The bottom is one SQLite file, reached only through SQLAlchemy.

That line along the bottom is the rule that shaped everything: the browser never
touches the database, and never decides anything it could be lied to about.

## Slide 7 — Why this stack

**Clock:** `4:40 - 5:35`  ·  **Speaker:** SPEAKER 3  ·  **Est. length:** 1:04

Why these choices.

Python and FastAPI: Python is the strongest shared language on this team, and
FastAPI gave us validation for free plus live API docs - so the front end could
build against a written contract instead of waiting for the backend.

SQLite: one file, no server to install, so four laptops and the CI runner run an
identical database with zero setup. That removed a whole category of "works on
my machine". And SQLAlchemy keeps every query parameterised, so we're
injection-safe by construction.

On the front end - Figma first. We designed every screen before anyone built it,
which kept four people from producing four different-looking pages. Bootstrap's
components sped the build up and gave us a responsive grid immediately, and Sass
let us generate custom CSS from one shared palette across eleven pages.

And GitHub Actions - the cheapest way to stop four people breaking each other's
work.

## Slide 8 — ERD — subject areas

**Clock:** `5:50 - 6:30`  ·  **Speaker:** SPEAKER 4  ·  **Est. length:** 0:40

Before the full diagram, the shape of it. Fourteen tables in three groups.

Left: the job-market data - roles, postings, skills, and the junctions between
them. That's where a cloud comes from. Middle: identity and activity. Right: the
quiz engine.

What makes this one system rather than three is two shared tables. Skills is
shared left to right - the same row that sizes a word in the cloud owns that
word's question bank, which is why clicking a word can start a quiz. And users
ties everything on the right to one account.

## Slide 9 — ERD — full schema

**Clock:** `6:15 - 7:35`  ·  **Speaker:** SPEAKER 4   -   Trace each table with the cursor as you name it.  ·  **Est. length:** 1:23

Let me trace the one path that touches most of it.

Start at ROLES. One role has many JOB_POSTINGS - title, company, location, salary
range, date posted.

Now the interesting part. A posting mentions many skills, and a skill appears in
many postings. That's many-to-many, which a relational database can't store
directly - so JOB_SKILLS resolves it. Its primary key is the pair, job plus
skill, and that's what guarantees one posting can only count once toward any
given skill.

So the word cloud is one query: take the postings for this role inside the date
window, join through job_skills, count distinct postings per skill, sort
descending. That count is the word size.

Follow SKILLS right and it becomes the quiz. One skill has many QUESTIONS split
by difficulty; each has its ANSWER_OPTIONS, one flagged correct - and that flag
never leaves the server.

Starting a quiz creates a QUIZ_SESSION recording which questions went out and
what you picked - that is what makes live scoring trustworthy, and what stops a
finished quiz being replayed. Submitting lands the result in GAME_ATTEMPTS.

And down the middle, USERS - every search and every attempt hangs off it.

## Slide 10 — User roles

**Clock:** `7:55 - 8:30`  ·  **Speaker:** SPEAKER 1   -   sets up the demo  ·  **Est. length:** 0:36

One note before the demo, because it shapes what you'll see.

JobHopper has two roles, and the difference is whether the request carries a
valid token. A visitor can read the public pages and register - nothing else. A
signed-in user gets word clouds, quizzes that save their result, and a profile.

And there's deliberately no admin role. Postings come in through the ingest
pipeline and questions load from a fixture, so there was never a job an admin
would log in to do.

## Slide 11 — Demo 1 — the visitor

**Clock:** `8:00 – 9:00`  ·  **Speaker:** SPEAKER 3   —   LIVE DEMO. Screen share on.  ·  **Est. length:** 1:00

Runbook: presentation/DEMO_RUNBOOK.md, Part 1.

1. Home page. Point out the nav — rules, stack, creators. All public.
2. Game rules page briefly: three difficulties, three timers.
3. Try to hit the word cloud page while signed out. It bounces you to sign-in.
   Say out loud: "and it isn't just the page hiding a button — the API refuses
   that request too."
4. Register a new account live. Show the inline validation — type a 3-character
   username so the message appears, then fix it. The registration form also
   collects the first word-cloud search, so fill that in as you go.
5. Submitting lands you signed in, on your first word cloud. Hand over.

If registration fails live, fall back to the pre-made account in the runbook and
say so plainly. Do not debug on camera.

## Slide 12 — Demo 2 — the registered user

**Clock:** `9:00 – 11:00`  ·  **Speaker:** SPEAKER 3 and SPEAKER 4   —   LIVE DEMO. The main event.  ·  **Est. length:** 2:00

Runbook: presentation/DEMO_RUNBOOK.md, Part 2.

1. You are already on the cloud that registration generated. Read it out: name
   the two or three biggest words. Say what the sizing means: "the big words are
   in the most postings — that's a count, not an opinion."
2. Optional, if you have the time: profile → Generate New Word Cloud → change the
   role and the shape, and show a second cloud coming back different.
3. Click a big skill. Difficulty screen. Pick Medium — 2:00 is long enough to show
   and short enough to stay inside our slot.
4. Play three or four questions. Deliberately get one wrong so the live feedback
   and the score behaviour are both visible. Point at the clock.
5. Do NOT play all ten on camera. Jump to the profile page.
6. Profile: the search you just ran is under Recent Word Clouds; the attempt you
   just made is under Recent Game History. Say: "we didn't refresh anything —
   that's the database answering."
7. Click Search Again on a saved cloud to show it re-runs.

## Slide 13 — Demo 3 — it really is a database

**Clock:** `11:00 – 12:00`  ·  **Speaker:** SPEAKER 4   —   LIVE DEMO. This is the 9-point rubric item.  ·  **Est. length:** 1:00

Runbook: presentation/DEMO_RUNBOOK.md, Part 3. Use the DB Browser for SQLite
window already open on the second desktop — don't open a terminal and type
commands on camera, it reads as code.

1. Show the table list. Say: "fourteen tables — the same fourteen you just saw in
   the ERD. The diagram isn't a drawing of what we planned, it's what's actually
   in the file."
2. Open SEARCHES. The row from ninety seconds ago is at the bottom — the role, the
   salary, the shape, the timestamp, and a user_id pointing at the account we
   registered on camera.
3. Open GAME_ATTEMPTS. Same story: skill, difficulty, score, seconds taken.
4. Open USERS. Show the password column. It's a bcrypt hash. Say: "we couldn't
   tell you that user's password if we wanted to. We never stored it."
5. Show the word-cloud counts next to the picture: same numbers.

Close with: "everything you saw on screen came out of this file. Nothing on any
page is hard-coded."

## Slide 14 — Summary — achieved vs changed

**Clock:** `11:20 - 12:10`  ·  **Speaker:** SPEAKER 1  ·  **Est. length:** 0:59

The honest accounting.

On the left, what worked. Registration and sign-in, real postings parsed into a
cloud from whatever the user asked for, the timed game with live scoring, every
result saved. The question bank beat its own target - we aimed for ten per skill
per difficulty and shipped fifteen, so 1,260 questions. And 237 tests on every
pull request.

On the right, what changed. The top two are the same story: the external API
limited what we could reliably fetch, so typing any role became four supported
roles, and location became a menu of places that actually have postings behind
them. Both were us refusing to offer a search that comes back empty.

The rest is us choosing depth over breadth - and one place where our
documentation got ahead of the app, which is on us.

## Slide 15 — Close

**Clock:** `12:30 - 13:00`  ·  **Speaker:** SPEAKER 1   -   close  ·  **Est. length:** 0:30

Three things next. Ship the roadmap screen - the API is already there. Widen the
ingest; the pipeline isn't the limit, the skill vocabulary is. And the one we
actually want: close the loop, so the skills you keep getting wrong become the
ones your cloud puts in front of you.

Right now the two halves of the app share a database. They should share a memory.

That's JobHopper. Thank you.

--- END. Target 13:00. Hard ceiling 15:00. ---
