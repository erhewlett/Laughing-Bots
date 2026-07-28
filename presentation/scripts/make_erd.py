"""Render the JobHopper ERD straight from the schema in backend/app/models.py.

Produces two images used by the final presentation deck:

  diagrams/erd_overview.png  - the three subject areas and how they meet
  diagrams/erd_full.png      - all 14 tables with every column, keys and edges

Run:  python presentation/scripts/make_erd.py
"""
from __future__ import annotations

from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "diagrams"

# ---------------------------------------------------------------- palette --
# Subject-area hues. Distinct in both hue and lightness so the grouping still
# reads on a projector and in grayscale.
IDENTITY = "#3F5C99"   # people and what they did
MARKET = "#1F7A6B"     # the job-market data the cloud is built from
QUIZ = "#9A4F70"       # the Q&A game
SYSTEM = "#5B6472"     # app bookkeeping

INK = "#1B2430"
MUTED = "#6B7787"
LINE = "#C9D2DE"
PAPER = "#FFFFFF"
BG = "#F4F7FB"

FONT = "DejaVu Sans"

# ------------------------------------------------------------------ model --
# (name, subject-area colour, [(column, type, key)]) - key is "PK", "FK",
# "PK,FK" or "".
TABLES: dict[str, tuple[str, list[tuple[str, str, str]]]] = {
    "roles": (MARKET, [
        ("role_id", "INTEGER", "PK"),
        ("role_name", "VARCHAR(100)", "U"),
    ]),
    "job_postings": (MARKET, [
        ("job_id", "INTEGER", "PK"),
        ("external_id", "VARCHAR(64)", "U"),
        ("role_id", "INTEGER", "FK"),
        ("title", "VARCHAR(150)", ""),
        ("company_name", "VARCHAR(150)", ""),
        ("location", "VARCHAR(100)", ""),
        ("salary_min", "INTEGER", ""),
        ("salary_max", "INTEGER", ""),
        ("date_posted", "DATETIME", ""),
        ("source_url", "VARCHAR(500)", ""),
    ]),
    "role_skills": (MARKET, [
        ("role_id", "INTEGER", "PK,FK"),
        ("skill_id", "INTEGER", "PK,FK"),
        ("demand_score", "FLOAT", ""),
    ]),
    "job_skills": (MARKET, [
        ("job_id", "INTEGER", "PK,FK"),
        ("skill_id", "INTEGER", "PK,FK"),
        ("frequency", "INTEGER", ""),
    ]),
    "app_meta": (SYSTEM, [
        ("key", "VARCHAR(64)", "PK"),
        ("value", "TEXT", ""),
    ]),
    "skills": (MARKET, [
        ("skill_id", "INTEGER", "PK"),
        ("skill_name", "VARCHAR(100)", "U"),
        ("category", "VARCHAR(100)", ""),
    ]),
    "users": (IDENTITY, [
        ("user_id", "INTEGER", "PK"),
        ("name", "VARCHAR(100)", ""),
        ("email", "VARCHAR(255)", "U"),
        ("username", "VARCHAR(16)", "U"),
        ("password_hash", "VARCHAR(255)", ""),
        ("target_role", "VARCHAR(100)", ""),
        ("target_location", "VARCHAR(100)", ""),
    ]),
    "questions": (QUIZ, [
        ("question_id", "INTEGER", "PK"),
        ("skill_id", "INTEGER", "FK"),
        ("difficulty", "VARCHAR(10)", ""),
        ("question_text", "TEXT", ""),
    ]),
    "answer_options": (QUIZ, [
        ("option_id", "INTEGER", "PK"),
        ("question_id", "INTEGER", "FK"),
        ("option_text", "TEXT", ""),
        ("is_correct", "BOOLEAN", ""),
    ]),
    "roadmaps": (IDENTITY, [
        ("roadmap_id", "INTEGER", "PK"),
        ("user_id", "INTEGER", "FK,U"),
        ("role_id", "INTEGER", "FK"),
        ("created_date", "DATETIME", ""),
    ]),
    "roadmap_steps": (IDENTITY, [
        ("step_id", "INTEGER", "PK"),
        ("roadmap_id", "INTEGER", "FK"),
        ("skill_id", "INTEGER", "FK"),
        ("step_order", "INTEGER", ""),
        ("status", "VARCHAR(20)", ""),
    ]),
    "searches": (IDENTITY, [
        ("search_id", "INTEGER", "PK"),
        ("user_id", "INTEGER", "FK"),
        ("job_title", "VARCHAR(150)", ""),
        ("industry", "VARCHAR(100)", ""),
        ("location", "VARCHAR(100)", ""),
        ("min_salary", "INTEGER", ""),
        ("word_count", "INTEGER", ""),
        ("shape", "VARCHAR(50)", ""),
        ("created_at", "DATETIME", ""),
    ]),
    "quiz_sessions": (QUIZ, [
        ("session_id", "INTEGER", "PK"),
        ("user_id", "INTEGER", "FK"),
        ("skill_id", "INTEGER", "FK"),
        ("difficulty", "VARCHAR(10)", ""),
        ("question_ids", "TEXT", ""),
        ("answers", "TEXT", ""),
        ("completed", "BOOLEAN", ""),
        ("created_at", "DATETIME", ""),
    ]),
    "game_attempts": (QUIZ, [
        ("attempt_id", "INTEGER", "PK"),
        ("user_id", "INTEGER", "FK"),
        ("skill_id", "INTEGER", "FK"),
        ("difficulty", "VARCHAR(10)", ""),
        ("score", "INTEGER", ""),
        ("max_score", "INTEGER", ""),
        ("time_taken_seconds", "INTEGER", ""),
        ("date_taken", "DATETIME", ""),
    ]),
}

BOX_W = 330
HEAD_H = 46
ROW_H = 28
PAD_B = 10

COLS = {1: 55, 2: 495, 3: 935, 4: 1375, 5: 1815}

# table -> (column, top y)
POS = {
    "roles": (1, 120), "job_postings": (1, 280),
    "role_skills": (2, 120), "job_skills": (2, 300), "app_meta": (2, 480),
    "skills": (3, 200), "users": (3, 700),
    "questions": (4, 120), "answer_options": (4, 310), "roadmaps": (4, 560),
    "roadmap_steps": (4, 750), "searches": (4, 980),
    "quiz_sessions": (5, 560), "game_attempts": (5, 870),
}

CANVAS_W, CANVAS_H = 2420, 1580


def box_h(name: str) -> int:
    return HEAD_H + len(TABLES[name][1]) * ROW_H + PAD_B


def geom(name: str) -> tuple[int, int, int, int]:
    col, y = POS[name]
    x = COLS[col]
    return x, y, BOX_W, box_h(name)


def row_y(name: str, field: str) -> float:
    """Vertical centre of a named column's row inside its box."""
    _, y, _, _ = geom(name)
    for i, (fname, _t, _k) in enumerate(TABLES[name][1]):
        if fname == field:
            return y + HEAD_H + i * ROW_H + ROW_H / 2
    return y + HEAD_H / 2


# parent, child, parent-side field, child-side field, cardinality label
EDGES = [
    ("roles", "job_postings", "role_id", "role_id", "1:N"),
    ("roles", "role_skills", "role_id", "role_id", "1:N"),
    ("roles", "roadmaps", "role_id", "role_id", "1:N"),
    ("job_postings", "job_skills", "job_id", "job_id", "1:N"),
    ("skills", "role_skills", "skill_id", "skill_id", "1:N"),
    ("skills", "job_skills", "skill_id", "skill_id", "1:N"),
    ("skills", "questions", "skill_id", "skill_id", "1:N"),
    ("skills", "roadmap_steps", "skill_id", "skill_id", "1:N"),
    ("skills", "quiz_sessions", "skill_id", "skill_id", "1:N"),
    ("skills", "game_attempts", "skill_id", "skill_id", "1:N"),
    ("questions", "answer_options", "question_id", "question_id", "1:N"),
    ("roadmaps", "roadmap_steps", "roadmap_id", "roadmap_id", "1:N"),
    ("users", "searches", "user_id", "user_id", "1:N"),
    ("users", "roadmaps", "user_id", "user_id", "1:1"),
    ("users", "quiz_sessions", "user_id", "user_id", "1:N"),
    ("users", "game_attempts", "user_id", "user_id", "1:N"),
]

# Edges that skip a column are routed through a channel under the diagram and
# brought back up in a gutter, so no connector is ever drawn across a table.
# (lane y, riser x, gutter x on the way down, drop below parent, exit fraction)
HIGHWAY = {
    ("roles", "roadmaps"): (1500, 1760, 880, 50, 0.72),
    ("skills", "quiz_sessions"): (1332, 2200, 1285, 26, 0.55),
    ("users", "quiz_sessions"): (1374, 2250, 1325, 26, 0.55),
    ("skills", "game_attempts"): (1416, 2300, 1305, 58, 0.78),
    ("users", "game_attempts"): (1458, 2350, 1345, 58, 0.78),
}


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def crow(x: float, y: float, facing: str, colour: str) -> str:
    """Crow's foot on the many side."""
    d = 15 if facing == "right" else -15
    s = 9
    return (
        f'<path d="M{x + d},{y} L{x},{y - s} M{x + d},{y} L{x},{y} '
        f'M{x + d},{y} L{x},{y + s}" stroke="{colour}" stroke-width="2.6" '
        f'fill="none" stroke-linecap="round"/>'
    )


def one_bar(x: float, y: float, facing: str, colour: str) -> str:
    """Tick on the one side."""
    d = 13 if facing == "right" else -13
    return (
        f'<line x1="{x + d}" y1="{y - 8}" x2="{x + d}" y2="{y + 8}" '
        f'stroke="{colour}" stroke-width="2.6" stroke-linecap="round"/>'
    )


def render_full() -> str:
    parts: list[str] = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{CANVAS_W}" '
        f'height="{CANVAS_H}" viewBox="0 0 {CANVAS_W} {CANVAS_H}">'
    )
    parts.append(f'<rect width="{CANVAS_W}" height="{CANVAS_H}" fill="{BG}"/>')

    # -- connectors, drawn first so the tables sit cleanly on top ------------
    halos: list[str] = []
    strokes: list[str] = []
    caps: list[str] = []

    for parent, child, pfield, cfield, card in EDGES:
        colour = TABLES[parent][0]
        px, py, pw, ph = geom(parent)
        cx, cy, cw, ch = geom(child)
        p_y = row_y(parent, pfield)
        c_y = row_y(child, cfield)

        key = (parent, child)
        if key in HIGHWAY:
            lane, riser, gutter, drop, frac = HIGHWAY[key]
            start_x = px + pw * frac
            start_y = py + ph
            end_x = cx + cw
            d = (
                f"M{start_x},{start_y} L{start_x},{start_y + drop} "
                f"L{gutter},{start_y + drop} L{gutter},{lane} "
                f"L{riser},{lane} L{riser},{c_y} L{end_x + 16},{c_y}"
            )
            halos.append(
                f'<path d="{d}" stroke="{BG}" stroke-width="11" fill="none" '
                f'stroke-linejoin="round" stroke-linecap="round"/>'
            )
            strokes.append(
                f'<path d="{d}" stroke="{colour}" stroke-width="2.6" fill="none" '
                f'stroke-linejoin="round" stroke-linecap="round" opacity="0.95"/>'
            )
            caps.append(
                f'<line x1="{start_x - 8}" y1="{start_y + 12}" x2="{start_x + 8}" '
                f'y2="{start_y + 12}" stroke="{colour}" stroke-width="2.6" '
                f'stroke-linecap="round"/>'
            )
            caps.append(crow(end_x, c_y, "right", colour))
            mid_x = (gutter + riser) / 2
            caps.append(
                f'<text x="{mid_x}" y="{lane - 12}" font-family="{FONT}" '
                f'font-size="19" fill="{MUTED}" text-anchor="middle">'
                f'{parent} &#8594; {child} ({card})</text>'
            )
            continue

        p_col, c_col = POS[parent][0], POS[child][0]

        if p_col == c_col:
            # stacked in the same column: leave the bottom, re-enter the top
            sx = px + pw * 0.5
            sy = py + ph
            ex = cx + cw * 0.5
            ey = cy
            d = (f"M{sx},{sy} C{sx},{sy + 40} {ex},{ey - 40} {ex},{ey - 16}")
            halos.append(f'<path d="{d}" stroke="{BG}" stroke-width="11" fill="none"/>')
            strokes.append(
                f'<path d="{d}" stroke="{colour}" stroke-width="2.6" fill="none"/>'
            )
            caps.append(
                f'<line x1="{sx - 8}" y1="{sy + 12}" x2="{sx + 8}" y2="{sy + 12}" '
                f'stroke="{colour}" stroke-width="2.6" stroke-linecap="round"/>'
            )
            caps.append(
                f'<path d="M{ex},{ey - 15} L{ex - 9},{ey} M{ex},{ey - 15} L{ex},{ey} '
                f'M{ex},{ey - 15} L{ex + 9},{ey}" stroke="{colour}" '
                f'stroke-width="2.6" fill="none" stroke-linecap="round"/>'
            )
            caps.append(
                f'<text x="{ex + 16}" y="{(sy + ey) / 2 + 6}" font-family="{FONT}" '
                f'font-size="19" fill="{MUTED}">{card}</text>'
            )
            continue

        # neighbouring columns: exit the near side, enter the facing side
        if c_col > p_col:
            sx, ex = px + pw, cx
            s_face, e_face = "right", "left"
            ctrl = 90
        else:
            sx, ex = px, cx + cw
            s_face, e_face = "left", "right"
            ctrl = -90
        d = f"M{sx},{p_y} C{sx + ctrl},{p_y} {ex - ctrl},{c_y} {ex},{c_y}"
        halos.append(f'<path d="{d}" stroke="{BG}" stroke-width="11" fill="none"/>')
        strokes.append(
            f'<path d="{d}" stroke="{colour}" stroke-width="2.6" fill="none"/>'
        )
        caps.append(one_bar(sx, p_y, s_face, colour))
        caps.append(crow(ex, c_y, e_face, colour))
        caps.append(
            f'<text x="{(sx + ex) / 2}" y="{(p_y + c_y) / 2 - 12}" '
            f'font-family="{FONT}" font-size="19" fill="{MUTED}" '
            f'text-anchor="middle">{card}</text>'
        )

    parts.extend(halos)
    parts.extend(strokes)
    parts.extend(caps)

    # -- tables --------------------------------------------------------------
    for name, (colour, fields) in TABLES.items():
        x, y, w, h = geom(name)
        parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" '
            f'fill="{PAPER}" stroke="{colour}" stroke-width="2.5"/>'
        )
        parts.append(
            f'<path d="M{x},{y + HEAD_H} L{x},{y + 12} Q{x},{y} {x + 12},{y} '
            f'L{x + w - 12},{y} Q{x + w},{y} {x + w},{y + 12} '
            f'L{x + w},{y + HEAD_H} Z" fill="{colour}"/>'
        )
        parts.append(
            f'<text x="{x + 16}" y="{y + 31}" font-family="{FONT}" font-size="23" '
            f'font-weight="bold" fill="#FFFFFF">{esc(name)}</text>'
        )
        for i, (fname, ftype, key) in enumerate(fields):
            fy = y + HEAD_H + i * ROW_H + 19
            if i:
                ly = y + HEAD_H + i * ROW_H
                parts.append(
                    f'<line x1="{x + 10}" y1="{ly}" x2="{x + w - 10}" y2="{ly}" '
                    f'stroke="{LINE}" stroke-width="1"/>'
                )
            bold = "bold" if "PK" in key else "normal"
            ink = INK if key else MUTED
            parts.append(
                f'<text x="{x + 16}" y="{fy}" font-family="{FONT}" font-size="18" '
                f'font-weight="{bold}" fill="{ink}">{esc(fname)}</text>'
            )
            label = key if key else ftype.split("(")[0].lower()
            fill = colour if key else MUTED
            weight = "bold" if key else "normal"
            parts.append(
                f'<text x="{x + w - 14}" y="{fy}" font-family="{FONT}" '
                f'font-size="15" font-weight="{weight}" fill="{fill}" '
                f'text-anchor="end">{esc(label)}</text>'
            )

    # -- title and key -------------------------------------------------------
    parts.append(
        f'<text x="55" y="66" font-family="{FONT}" font-size="42" '
        f'font-weight="bold" fill="{INK}">JobHopper &#8212; Entity Relationship '
        f'Diagram</text>'
    )
    parts.append(
        f'<text x="{CANVAS_W - 60}" y="64" font-family="{FONT}" font-size="24" '
        f'fill="{MUTED}" text-anchor="end">14 tables &#183; SQLite &#183; mapped '
        f'with SQLAlchemy ORM</text>'
    )

    # callout in the open space bottom-left
    cbx, cby, cbw = 55, 680, 740
    parts.append(
        f'<rect x="{cbx}" y="{cby}" width="{cbw}" height="300" rx="14" '
        f'fill="{PAPER}" stroke="{LINE}" stroke-width="2"/>'
    )
    parts.append(
        f'<rect x="{cbx}" y="{cby}" width="{cbw}" height="7" rx="3.5" fill="{MARKET}"/>'
    )
    parts.append(
        f'<text x="{cbx + 26}" y="{cby + 56}" font-family="{FONT}" font-size="28" '
        f'font-weight="bold" fill="{INK}">Three things to notice</text>'
    )
    for i, (head, body) in enumerate([
        ("Two junction tables",
         "job_skills and role_skills resolve the many-to-many"),
        ("skills is the hinge",
         "the same row sizes a cloud word and owns its quiz bank"),
        ("Nothing is hard-coded",
         "every screen is a query; no lists live in the frontend"),
    ]):
        yy = cby + 104 + i * 66
        parts.append(
            f'<rect x="{cbx + 26}" y="{yy - 20}" width="9" height="46" rx="4.5" '
            f'fill="{MARKET}"/>'
        )
        parts.append(
            f'<text x="{cbx + 52}" y="{yy}" font-family="{FONT}" font-size="23" '
            f'font-weight="bold" fill="{INK}">{head}</text>'
        )
        parts.append(
            f'<text x="{cbx + 52}" y="{yy + 26}" font-family="{FONT}" font-size="20" '
            f'fill="{MUTED}">{esc(body)}</text>'
        )

    lx, ly = 1815, 120
    parts.append(
        f'<rect x="{lx}" y="{ly}" width="{BOX_W + 200}" height="200" rx="12" '
        f'fill="{PAPER}" stroke="{LINE}" stroke-width="2"/>'
    )
    parts.append(
        f'<text x="{lx + 18}" y="{ly + 34}" font-family="{FONT}" font-size="21" '
        f'font-weight="bold" fill="{INK}">Subject areas</text>'
    )
    for i, (colour, label) in enumerate([
        (IDENTITY, "Identity &amp; user activity"),
        (MARKET, "Job-market data (word cloud)"),
        (QUIZ, "Q&amp;A game engine"),
        (SYSTEM, "Application bookkeeping"),
    ]):
        yy = ly + 62 + i * 33
        parts.append(
            f'<rect x="{lx + 18}" y="{yy - 14}" width="20" height="20" rx="4" '
            f'fill="{colour}"/>'
        )
        parts.append(
            f'<text x="{lx + 48}" y="{yy + 2}" font-family="{FONT}" font-size="19" '
            f'fill="{INK}">{label}</text>'
        )

    kx, ky = 1815, 345
    parts.append(
        f'<rect x="{kx}" y="{ky}" width="{BOX_W + 200}" height="140" rx="12" '
        f'fill="{PAPER}" stroke="{LINE}" stroke-width="2"/>'
    )
    parts.append(
        f'<text x="{kx + 18}" y="{ky + 32}" font-family="{FONT}" font-size="21" '
        f'font-weight="bold" fill="{INK}">Key</text>'
    )
    for i, txt in enumerate([
        "PK primary key   FK foreign key   U unique",
        "&#8212;| one side          &#8212;&#60; many side",
        "PK,FK composite key on a junction table",
    ]):
        parts.append(
            f'<text x="{kx + 18}" y="{ky + 62 + i * 28}" font-family="{FONT}" '
            f'font-size="18" fill="{MUTED}">{txt}</text>'
        )

    parts.append("</svg>")
    return "\n".join(parts)


# ------------------------------------------------------------- overview ----
def wrap(text: str, width: int) -> list[str]:
    """Greedy word wrap; keeps SVG entities intact by never splitting a token."""
    lines: list[str] = []
    cur = ""
    for word in text.split():
        candidate = f"{cur} {word}".strip()
        if len(candidate) > width and cur:
            lines.append(cur)
            cur = word
        else:
            cur = candidate
    if cur:
        lines.append(cur)
    return lines


def render_overview() -> str:
    W, H = 2420, 1250
    p: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}">',
        f'<rect width="{W}" height="{H}" fill="{BG}"/>',
        f'<text x="70" y="86" font-family="{FONT}" font-size="52" '
        f'font-weight="bold" fill="{INK}">How the database is organised</text>',
        f'<text x="70" y="140" font-family="{FONT}" font-size="30" fill="{MUTED}">'
        f'Three subject areas, joined by the two tables every feature depends on: '
        f'<tspan font-weight="bold" fill="{IDENTITY}">users</tspan> and '
        f'<tspan font-weight="bold" fill="{MARKET}">skills</tspan>.</text>',
    ]

    panels = [
        (70, MARKET, "Job-market data",
         "Where the word cloud comes from",
         ["roles", "job_postings", "skills", "job_skills", "role_skills"],
         "40 postings across 4 roles, broken down into the skills each one asks for."),
        (840, IDENTITY, "Identity &amp; activity",
         "Who the user is and what they did",
         ["users", "searches", "roadmaps", "roadmap_steps"],
         "Accounts, saved searches and a per-user prep roadmap."),
        (1610, QUIZ, "Q&amp;A game engine",
         "The quiz built on those same skills",
         ["questions", "answer_options", "quiz_sessions", "game_attempts"],
         "1,251 questions; a session records what was served, an attempt records the score."),
    ]

    PANEL_TOP, PANEL_H, HEAD = 210, 730, 112
    for x, colour, title, sub, tables, note in panels:
        p.append(
            f'<rect x="{x}" y="{PANEL_TOP}" width="740" height="{PANEL_H}" rx="20" '
            f'fill="{PAPER}" stroke="{colour}" stroke-width="4"/>'
        )
        p.append(
            f'<path d="M{x},{PANEL_TOP + HEAD} L{x},{PANEL_TOP + 12} '
            f'Q{x},{PANEL_TOP} {x + 12},{PANEL_TOP} L{x + 728},{PANEL_TOP} '
            f'Q{x + 740},{PANEL_TOP} {x + 740},{PANEL_TOP + 12} '
            f'L{x + 740},{PANEL_TOP + HEAD} Z" fill="{colour}"/>'
        )
        p.append(
            f'<text x="{x + 30}" y="{PANEL_TOP + 54}" font-family="{FONT}" '
            f'font-size="36" font-weight="bold" fill="#FFFFFF">{title}</text>'
        )
        p.append(
            f'<text x="{x + 30}" y="{PANEL_TOP + 93}" font-family="{FONT}" '
            f'font-size="23" fill="#FFFFFF" opacity="0.88">{sub}</text>'
        )
        for i, t in enumerate(tables):
            ty = PANEL_TOP + HEAD + 32 + i * 90
            p.append(
                f'<rect x="{x + 34}" y="{ty}" width="672" height="68" rx="10" '
                f'fill="{BG}" stroke="{LINE}" stroke-width="2"/>'
            )
            p.append(
                f'<rect x="{x + 34}" y="{ty}" width="10" height="68" rx="5" '
                f'fill="{colour}"/>'
            )
            p.append(
                f'<text x="{x + 66}" y="{ty + 45}" font-family="{FONT}" '
                f'font-size="31" font-weight="bold" fill="{INK}">{t}</text>'
            )
        for j, line in enumerate(wrap(note, 60)[:2]):
            p.append(
                f'<text x="{x + 34}" y="{PANEL_TOP + PANEL_H - 62 + j * 30}" '
                f'font-family="{FONT}" font-size="22" fill="{MUTED}">{line}</text>'
            )

    box_y = PANEL_TOP + PANEL_H + 60
    p.append(
        f'<rect x="70" y="{box_y}" width="2280" height="188" rx="18" fill="{PAPER}" '
        f'stroke="{LINE}" stroke-width="2"/>'
    )
    p.append(
        f'<text x="106" y="{box_y + 56}" font-family="{FONT}" font-size="31" '
        f'font-weight="bold" fill="{INK}">The two joins that make it one system</text>'
    )
    for i, (colour, txt) in enumerate([
        (MARKET, "skills is shared &#8212; the same row that sizes a word in the cloud "
                 "owns that word&#8217;s question bank, so clicking a word starts a quiz."),
        (IDENTITY, "users is shared &#8212; searches, quiz_sessions, game_attempts and "
                   "roadmaps all hang off one account, which is what the profile page reads back."),
    ]):
        yy = box_y + 106 + i * 46
        p.append(
            f'<rect x="106" y="{yy - 21}" width="12" height="28" rx="6" fill="{colour}"/>'
        )
        p.append(
            f'<text x="136" y="{yy}" font-family="{FONT}" font-size="26" '
            f'fill="{INK}">{txt}</text>'
        )

    p.append("</svg>")
    return "\n".join(p)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    import cairosvg

    for stem, svg in [("erd_full", render_full()), ("erd_overview", render_overview())]:
        svg_path = OUT / f"{stem}.svg"
        svg_path.write_text(svg, encoding="utf-8")
        cairosvg.svg2png(
            bytestring=svg.encode("utf-8"),
            write_to=str(OUT / f"{stem}.png"),
            output_width=2420,
        )
        print(f"wrote {OUT / f'{stem}.png'}")


if __name__ == "__main__":
    main()
