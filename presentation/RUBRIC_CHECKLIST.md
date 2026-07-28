# Rubric traceability — where every point is earned

Each line of the grading rubric mapped to the slide, the demo step, or the
delivery behaviour that satisfies it. Use this as the final pass before
recording: if a row has no tick, that is a point you have not earned yet.

## Timing — 25 points

> Max 20 minutes. Each 10 minutes over loses 5 points.

| Requirement | Where | Status |
|---|---|---|
| Under 20 minutes (rubric) | Script estimates **13:51** | ✅ |
| Under 15 minutes (assignment) | 1:08 of headroom at 140 wpm | ✅ |

`scripts/make_script.py` re-checks the total every time it runs and prints a
warning if an edit pushes the script over the ceiling.

## Demo — 25 points

| Requirement | Points | Where | Status |
|---|---|---|---|
| Demonstrates the system is built on a database | 9 | Slide 13 + **Demo runbook Part 3** — the live rows created during the demo, shown in the database file itself | ✅ |
| Logs in to show the system from the perspective of **all user roles** | 8 | Slide 10 names both roles and explains why there is no third one; **Runbook Parts 1 and 2** show visitor then registered user | ✅ |
| Walks through the ERD | 8 | Slides 8 and 9, with a scripted trace through the schema on slide 9 | ✅ |

**On "all user roles":** JobHopper has exactly two — visitor and registered
user. Slide 10 states that explicitly and explains why an admin role would have
had nothing behind it. Say that out loud; do not let it look like a role you
forgot to demo.

## Presentation — 25 points

| Requirement | Points | Where | Status |
|---|---|---|---|
| Slides are legible | 5 | 16:9, minimum 13.5pt body and 34pt headings; layout is measured against real font metrics so nothing overflows | ✅ |
| Looks up at the audience while speaking | 5 | Delivery — **the one thing this package cannot do for you**. Learn the first and last line of each slide | ⬜ rehearse |
| Summary of the application goal, and how much was achieved and/or altered | 5 | Slide 2 (goal), Slide 14 (achieved vs altered, both columns) | ✅ |
| Tech stack diagram | 5 | Slide 6 — `diagrams/tech_stack.png` | ✅ |
| Why you chose those technologies | 5 | Slide 7 — a reason per choice, not a list of names | ✅ |

## Requirements — 25 points

| Requirement | Points | Where | Status |
|---|---|---|---|
| Functional requirements | 20 | Slides 3 and 4 — FR1 to FR8, each stated as a capability | ✅ |
| Non-functional requirements | 5 | Slide 5 — security, integrity, performance, reliability, usability, portability | ✅ |

---

## Final pass before you hit record

- [ ] Every name on slide 1 is spelled the way that person spells it
- [ ] Deck opens correctly on the machine that will present it (fonts included)
- [ ] Backend running, frontend on port 5500, DB Browser open — see the runbook
- [ ] Editor, terminal and file explorer closed (no code on screen)
- [ ] One full rehearsal done, and it came in under 15:00
- [ ] Everyone knows which slides are theirs (`SPEAKER_SCRIPT.md` → *Who speaks*)

## After recording

- [ ] Video is under 15:00
- [ ] Audio is audible for every speaker
- [ ] The ERD slide is readable in the exported video, not just on your monitor
- [ ] Share link tested in a private window
- [ ] One video submitted for the whole group
