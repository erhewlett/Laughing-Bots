# JobHopper — final presentation speaker script

> Generated from the speaker notes inside `JobHopper_Final_Presentation.pptx`.
> Edit the notes in `scripts/make_deck.py`, rebuild the deck, then re-run `scripts/make_script.py`.

**Estimated total: 14:44**  (target 14:00, hard ceiling 15:00 — the assignment caps the video at 15 minutes; the rubric penalises going over 20.)

Speaking estimate assumes 140 words per minute, which is an unhurried presenting pace. The three demo slides are timed from the runbook rather than from word count.

## Running order

| # | Slide | Length | Ends at |
|---|-------|--------|---------|
| 1 | Title | 0:16 | 0:16 |
| 2 | The goal | 0:50 | 1:06 |
| 3 | Functional requirements 1 of 2 | 0:45 | 1:51 |
| 4 | Functional requirements 2 of 2 | 0:52 | 2:44 |
| 5 | Non-functional requirements | 0:48 | 3:33 |
| 6 | Technology stack diagram | 0:48 | 4:21 |
| 7 | Why this stack | 0:54 | 5:16 |
| 8 | ERD — subject areas | 0:40 | 5:56 |
| 9 | ERD — full schema | 1:14 | 7:11 |
| 10 | User roles | 0:36 | 7:47 |
| 11 | Demo 1 — the visitor | 1:30 | 9:17 |
| 12 | Demo 2 — the registered user | 3:00 | 12:17 |
| 13 | Demo 3 — it really is a database | 1:10 | 13:27 |
| 14 | Summary — achieved vs changed | 0:44 | 14:12 |
| 15 | Close | 0:32 | 14:44 |

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
- **Say the numbers.** 14 tables, 1,260 questions, 40 postings, 250 tests. Specifics are what make a claim land.
- **Do not narrate the mouse.** Say what a thing means, not where you are clicking.
- **If something breaks on camera**, say what should have happened and move on. Do not debug live; stop the recording and re-take instead.

---

## Slide 1 — Title

**Clock:** `0:00 - 0:16`  ·  **Speaker:** SPEAKER 1  ·  **Est. length:** 0:16

Hi, we're the Laughing Bots - Rose, Elijah, Angel and Terrell. This is JobHopper:
it reads real job postings, shows you which skills those postings are actually
asking for, and lets you quiz yourself on any of them.

## Slide 2 — The goal

**Clock:** `0:16 - 1:06`  ·  **Speaker:** SPEAKER 1  ·  **Est. length:** 0:50

The problem isn't that this information is secret - job postings are public.
It's volume. Search one title and you get forty postings, each with its own wall
of requirements. The signal is which tools keep repeating, and nobody reads
forty postings to find it.

So our goal: analyse the postings for a target role, identify the most in-demand
skills, show them as a word cloud - then help people build those skills through
interactive Q&A games.

That second half is what we care about. Every skill in the picture is clickable.
Click Python, and you're in a timed quiz on Python. It doesn't just tell you
what to learn - it gives you somewhere to start.

## Slide 3 — Functional requirements 1 of 2

**Clock:** `1:06 - 1:51`  ·  **Speaker:** SPEAKER 2  ·  **Est. length:** 0:45

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

**Clock:** `1:52 - 2:44`  ·  **Speaker:** SPEAKER 2  ·  **Est. length:** 0:52

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

**Clock:** `2:45 - 3:33`  ·  **Speaker:** SPEAKER 2  ·  **Est. length:** 0:48

Non-functional requirements - not features, but the app is wrong without them.

The top row is what we committed to in our spec: the cloud back within ten
seconds, the game open within ten and scored within seven, and all user input
validated and sanitised against injection. We get that last one structurally -
every query goes through the ORM, parameterised, never built by string.

The bottom row we held ourselves to as we built. Passwords bcrypt-hashed and
never returned, and a failed login gives the same generic message whether the
account exists or not. The server decides every score, never the browser. And
250 tests, with nothing merging until both suites pass.

## Slide 6 — Technology stack diagram

**Clock:** `3:33 - 4:21`  ·  **Speaker:** SPEAKER 3  ·  **Est. length:** 0:48

The whole system on one page.

Top: the browser. Eleven HTML pages, Bootstrap, Sass, plain JavaScript modules -
no framework, no build step. It talks to exactly one thing, our API, and
anything tied to an account carries a signed token.

The middle band is where every rule lives: FastAPI, seventeen endpoints, Pydantic
validating every request and response, and underneath it the services - hashing
and tokens, skill extraction, and the ingest that keeps our postings current.

The bottom is one SQLite file, reached only through SQLAlchemy.

That line along the bottom is the rule that shaped everything: the browser never
touches the database, and never decides anything it could be lied to about.

## Slide 7 — Why this stack

**Clock:** `4:22 - 5:16`  ·  **Speaker:** SPEAKER 3  ·  **Est. length:** 0:54

Why these choices.

Python and FastAPI: the strongest shared language on this team, and FastAPI gave
us validation for free plus live API docs - so the front end could build against
a written contract instead of waiting for the backend.

SQLite: one file, no server to install, so four laptops and the CI runner run an
identical database with zero setup. SQLAlchemy keeps every query parameterised,
so we're injection-safe by construction.

On the front end, Figma first - we designed every screen before anyone built it,
which kept four people from producing four different-looking pages. Bootstrap
gave us a responsive grid on day one, Sass one shared palette across twelve
pages.

And GitHub Actions, so a regression is caught by the robot, not by whoever pulls
next.

## Slide 8 — ERD — subject areas

**Clock:** `5:16 - 5:56`  ·  **Speaker:** SPEAKER 4  ·  **Est. length:** 0:40

Before the full diagram, the shape of it. Fourteen tables in three groups.

Left: the job-market data - roles, postings, skills, and the junctions between
them. That's where a cloud comes from. Middle: identity and activity. Right: the
quiz engine.

What makes this one system rather than three is two shared tables. Skills is
shared left to right - the same row that sizes a word in the cloud owns that
word's question bank, which is why clicking a word can start a quiz. And users
ties everything on the right to one account.

## Slide 9 — ERD — full schema

**Clock:** `5:57 - 7:11`  ·  **Speaker:** SPEAKER 4   -   Trace each table with the cursor as you name it.  ·  **Est. length:** 1:14

Let me trace the one path that touches most of it.

Start at ROLES. One role has many JOB_POSTINGS - title, company, location, salary
range, date posted.

Now the interesting part. A posting mentions many skills, and a skill appears in
many postings. That's many-to-many, which a relational database can't store
directly - so JOB_SKILLS resolves it. Its primary key is the pair, job plus
skill, which guarantees one posting can only count once toward a skill.

So the word cloud is one query: the postings for this role inside the date
window, joined through job_skills, counted per skill, sorted descending. That
count is the word size.

Follow SKILLS right and it becomes the quiz - QUESTIONS split by difficulty, each
with its ANSWER_OPTIONS, one flagged correct. That flag never leaves the server.

Starting a quiz creates a QUIZ_SESSION recording what was served and what you
picked, which is what makes live scoring trustworthy. Submitting lands the result
in GAME_ATTEMPTS.

And down the middle, USERS - every search and every attempt hangs off it.

## Slide 10 — User roles

**Clock:** `7:11 - 7:47`  ·  **Speaker:** SPEAKER 1   -   sets up the demo  ·  **Est. length:** 0:36

One note before the demo, because it shapes what you'll see.

JobHopper has two roles, and the difference is whether the request carries a
valid token. A visitor can read the public pages and register - nothing else. A
signed-in user gets word clouds, quizzes that save their result, and a profile.

And there's deliberately no admin role. Postings come in through the ingest
pipeline and questions load from a fixture, so there was never a job an admin
would log in to do.

## Slide 11 — Demo 1 — the visitor

**Clock:** `7:47 - 9:17`  ·  **Speaker:** SPEAKER 3   -   LIVE DEMO, PART 1.  Share your screen now.  ·  **Est. length:** 1:30

Lines in quotes are what you say. Lines starting with > are what you do.

> Home page already open.

"This is JobHopper the way anyone arrives at it - not signed in. Rules, stack
and creators are open to everybody."

> Click Game Rules. Don't scroll far.

"Ten questions, three difficulties, each with its own clock."

> Try to open the word cloud page directly.

"Now watch what happens if I go straight for a word cloud with no account. It
sends me to sign-in - and that's not the page hiding a button. The API refuses
the request too, so there's no way around it."

> Click Sign Up. Type a 3-character username so the validation fires.

"So let's make one. Validation is inline, right where the problem is."

> Fix the username, then fill the rest. Job title and location are type-ahead
> fields - start typing and real options drop down. Keep talking while you
> type; don't narrate the typing.

"The same form takes your first search - and those suggestions are the job
titles and locations we actually have postings for."

> Submit.

If registration misbehaves: sign in with the backup account, say "we've already
got one set up", and carry on. Do not debug on camera.

## Slide 12 — Demo 2 — the registered user

**Clock:** `9:17 - 12:17`  ·  **Speaker:** SPEAKER 3 and SPEAKER 4   -   LIVE DEMO, PART 2. The main event.  ·  **Est. length:** 3:00

Lines in quotes are what you say. Lines starting with > are what you do.

> You are on the cloud registration just built.

"Here's what that search produced. The biggest words are the ones that appeared
in the most postings for that role - that's a count, not our opinion. Anything
we have questions for is clickable."

> Click one of the biggest skills.

"So let's take that one."

> Difficulty screen. Choose EASY - three minutes, so you can finish all ten.
> The score is only saved when the quiz is submitted, and that happens on the
> tenth answer or when the clock runs out. Stopping early means an empty game
> history on the profile.

"Three difficulties, three timers. I'll take easy - three minutes."

> Answer one question correctly.

"It tells me straight away whether I got it. It can do that safely because my
answer is already locked in on the server before I'm told - so knowing it now
can't change what I picked."

> Answer the next one wrong, on purpose.

"And there's the other case. It shows me the right answer, and the clock pauses
while I'm reading it."

> Now click through questions 3 to 10 without narrating each one. About
> sixty seconds if you don't read them aloud.

"I'll speed through the rest of these."

> The Submit button is replaced by a return button. Click it.

"That's graded and saved. This is my profile - the search I ran is under recent
word clouds, and the quiz I just played is under game history, score and all.
We didn't refresh anything, and none of this is hard-coded. That's the database
answering."

> Click Search Again on the saved cloud.

"And any saved search re-runs in one click."

## Slide 13 — Demo 3 — it really is a database

**Clock:** `12:17 - 13:27`  ·  **Speaker:** SPEAKER 4   -   LIVE DEMO, PART 3. This is the 9-point item.  ·  **Est. length:** 1:10

Switch to the DB Browser window already open on the second desktop. Do not open
a terminal - that reads as code.

> Show the table list in the sidebar.

"Last thing - proof this is really sitting in a database. There are our fourteen
tables, the same fourteen from the ERD. That diagram isn't what we planned; it's
what's in the file."

> DB Browser lists fifteen. The extra one is sqlite_stat1, which SQLite makes
> for its own query statistics. Say "our fourteen tables", not "fourteen
> tables", so the count on screen doesn't catch you out.

> Browse Data, searches table, scroll to the last row.

"The bottom row is the search from ninety seconds ago - role, salary, shape,
timestamp, and a user_id pointing at the account we made on camera."

> Switch to game_attempts.

"Same for the quiz. Skill, difficulty, score, seconds taken."

> Switch to users. Point at the password_hash column.

"And this is the users table. That's a bcrypt hash. We couldn't tell you that
password if we wanted to - we never stored it."

> Stop sharing, back to the deck.

"Everything you just saw came out of that one file."

## Slide 14 — Summary — achieved vs changed

**Clock:** `13:28 - 14:12`  ·  **Speaker:** SPEAKER 1  ·  **Est. length:** 0:44

The honest accounting.

On the left, what worked. Everything you just saw, plus a question bank that beat
its own target - we aimed for ten per skill per difficulty and shipped fifteen,
so 1,260 questions. And 250 tests on every pull request.

On the right, what changed. The top two are the same story: the external API
limited what we could reliably fetch, so typing any role became four supported
roles, and location became a menu of places that actually have postings behind
them. Both were us refusing to offer a search that comes back empty.

The rest is choosing depth over breadth.

## Slide 15 — Close

**Clock:** `14:12 - 14:44`  ·  **Speaker:** SPEAKER 1   -   close  ·  **Est. length:** 0:32

Three things next. Rank the roadmap by what you're weak at, not just by what the
market wants. Widen the ingest; the pipeline isn't the limit, the skill
vocabulary is. And the one we actually want: close the loop, so the skills you
keep getting wrong become the ones your cloud puts in front of you.

Right now the two halves of the app share a database. They should share a memory.

That's JobHopper. Thank you.

--- END. Target 13:00. Hard ceiling 15:00. ---
