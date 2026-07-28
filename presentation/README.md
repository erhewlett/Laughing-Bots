# Final presentation

Everything needed to record the JobHopper final-project video, built against the
grading rubric.

## What is here

| File | What it is |
|---|---|
| **`JobHopper_Final_Presentation.pptx`** | The deck. 15 slides, 16:9, with the full narration in the speaker notes. |
| **`SPEAKER_SCRIPT.md`** | The same narration as a rehearsal document, with a per-slide clock and a suggested speaker split. |
| **`DEMO_RUNBOOK.md`** | Click-by-click demo: what to open, what to click, what to say. Read this before recording. |
| **`RUBRIC_CHECKLIST.md`** | Every rubric line mapped to the slide or demo step that earns it. |
| `diagrams/` | The architecture and ERD images, as PNG and SVG. |
| `scripts/` | The generators. Re-run them to rebuild anything. |

## The short version

1. Read **`DEMO_RUNBOOK.md`** — it has the setup steps and the pre-flight
   checklist.
2. Rehearse from **`SPEAKER_SCRIPT.md`**. Estimated runtime **14:29** against a
   15-minute cap — 9:34 of talking plus a 4:55 demo budget.
3. Record. Two rules: **no code on screen**, and **do not debug live**.
4. Walk **`RUBRIC_CHECKLIST.md`** before you submit.

## Deck outline

| # | Slide | Rubric item |
|---|-------|-------------|
| 1 | Title | — |
| 2 | The goal | Summary: application goal |
| 3–4 | Functional requirements | Requirements (20 pts) |
| 5 | Non-functional requirements | Requirements (5 pts) |
| 6 | Technology stack diagram | Presentation (5 pts, diagram) |
| 7 | Why this stack | Presentation (5 pts, rationale) |
| 8–9 | ERD — subject areas, then full schema | Demo (8 pts, ERD walkthrough) |
| 10 | User roles | Sets up Demo (8 pts, all roles) |
| 11–13 | Live demo cues | Demo (25 pts) |
| 14 | What we achieved, and what we changed | Summary: achieved / altered |
| 15 | What's next, and thank you | — |

## Rebuilding

The diagrams and the deck are generated, so they stay consistent with each other
and with the schema. Requires `python-pptx`, `cairosvg` and `pillow`.

```bash
python presentation/scripts/make_erd.py      # ERD images
python presentation/scripts/make_stack.py    # architecture diagram
python presentation/scripts/make_deck.py     # the deck (warns on any overflow)
python presentation/scripts/make_script.py   # the script (warns if over 15:00)
```

Run them in that order — the deck embeds the diagrams, and the script is read
back out of the deck.

Two safety nets are built in, because both are easy to get wrong by hand:

- `make_deck.py` measures every string with real Carlito metrics (the
  metric-compatible twin of Calibri) and reports any slide whose content would
  run past the footer.
- `make_script.py` estimates the spoken length at 140 words per minute and fails
  loudly if an edit pushes the talk over the 15-minute ceiling.

To change the narration, edit the `notes(...)` blocks in `make_deck.py`, then
re-run `make_deck.py` and `make_script.py`.

## Where the numbers come from

Every figure in the deck was taken from the repository, not estimated:

| Claim | Source |
|---|---|
| 14 tables | `backend/app/models.py` |
| 16 API endpoints | the six routers in `backend/app/routers/` plus `/health` |
| 1,260 quiz questions (28 skills × 3 × 15) | `backend/app/seed_data/questions_seed.json` |
| 40 postings across 4 roles | `backend/app/seed_data/jobhopper_seed.json` |
| 11 HTML pages | `frontend/html/` |
| 237 tests (209 backend, 28 frontend) | `python -m pytest` and `npm test`, both run green |
| The demo click path | driven end to end against the running app |
| 189 commits, 44 merged pull requests | `git log` |
