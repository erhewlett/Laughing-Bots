"""Build the JobHopper final-presentation deck.

Every slide is laid out against the grading rubric, and speaker notes carry the
narration plus the running clock.

Layout is measurement-driven: text is wrapped with real Carlito metrics (the
metric-compatible twin of Calibri) so a card is exactly as tall as the words
inside it and nothing silently overflows. build() prints a warning for any
slide whose content runs past the footer line.

Regenerate with:  python presentation/scripts/make_deck.py
"""
from __future__ import annotations

from pathlib import Path

from PIL import ImageFont
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

ROOT = Path(__file__).resolve().parent.parent
DIAGRAMS = ROOT / "diagrams"
OUT = ROOT / "JobHopper_Final_Presentation.pptx"

# ------------------------------------------------------------------ design --
SLIDE_W, SLIDE_H = Inches(13.333), Inches(7.5)
MARGIN = Inches(0.72)
CONTENT_W = SLIDE_W - 2 * MARGIN
FOOTER_Y = SLIDE_H - Inches(0.62)

INK = RGBColor(0x1B, 0x24, 0x30)
MUTED = RGBColor(0x5E, 0x6B, 0x7C)
PAPER = RGBColor(0xFF, 0xFF, 0xFF)
CANVAS = RGBColor(0xF4, 0xF7, 0xFB)
HAIRLINE = RGBColor(0xC9, 0xD2, 0xDE)

BLUE = RGBColor(0x3F, 0x5C, 0x99)
TEAL = RGBColor(0x1F, 0x7A, 0x6B)
PLUM = RGBColor(0x9A, 0x4F, 0x70)
AMBER = RGBColor(0xB0, 0x74, 0x2C)
SLATE = RGBColor(0x5B, 0x64, 0x72)

FONT = "Calibri"
LINE = 1.22        # single-spaced line height, as a multiple of font size
EMU_PT = 12700

_TTF = {
    False: "/usr/share/fonts/truetype/crosextra/Carlito-Regular.ttf",
    True: "/usr/share/fonts/truetype/crosextra/Carlito-Bold.ttf",
}
_CACHE: dict = {}
_WARN: list[str] = []


# ------------------------------------------------------------ measurement --
def _face(size_pt: float, bold: bool):
    key = (round(size_pt * 4), bold)
    if key not in _CACHE:
        _CACHE[key] = ImageFont.truetype(_TTF[bold], int(round(size_pt * 4)))
    return _CACHE[key]


def width_pt(text: str, size_pt: float, bold: bool = False) -> float:
    return _face(size_pt, bold).getlength(text) / 4.0


def wrap(text: str, avail_pt: float, size_pt: float, bold: bool = False
         ) -> list[str]:
    """Greedy wrap using real glyph advances. '\\n' forces a break."""
    out: list[str] = []
    for para in text.split("\n"):
        if not para.strip():
            out.append("")
            continue
        cur = ""
        for word in para.split():
            cand = f"{cur} {word}".strip()
            if cur and width_pt(cand, size_pt, bold) > avail_pt:
                out.append(cur)
                cur = word
            else:
                cur = cand
        if cur:
            out.append(cur)
    return out


def pt(length) -> float:
    return length / EMU_PT


# Renderers round differently than we measure, so a line measured at exactly the
# box width can wrap again and push a card over. Measure narrow, draw wide.
SLOP = Pt(7)


# ------------------------------------------------------------- primitives --
def rect(slide, x, y, w, h, fill=None, line=None, line_w=1.25, rounded=False,
         radius=0.05):
    shp = slide.shapes.add_shape(
        MSO_SHAPE.ROUNDED_RECTANGLE if rounded else MSO_SHAPE.RECTANGLE,
        int(x), int(y), int(w), int(h),
    )
    shp.shadow.inherit = False
    # Drop the theme style reference; otherwise LibreOffice and Google Slides
    # re-apply the default shadow and outline even with an empty effect list.
    el = shp._element
    style = el.find("{http://schemas.openxmlformats.org/presentationml/2006/main}style")
    if style is not None:
        el.remove(style)
    if fill is None:
        shp.fill.background()
    else:
        shp.fill.solid()
        shp.fill.fore_color.rgb = fill
    if line is None:
        shp.line.fill.background()
    else:
        shp.line.color.rgb = line
        shp.line.width = Pt(line_w)
    if rounded:
        try:
            shp.adjustments[0] = radius
        except (IndexError, KeyError):
            pass
    tf = shp.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    return shp


def textbox(slide, x, y, w, h, anchor=MSO_ANCHOR.TOP):
    tb = slide.shapes.add_textbox(int(x), int(y), int(w), int(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    return tf


def put(tf, text, size, *, bold=False, color=INK, first=False, space_before=0,
        space_after=0, align=PP_ALIGN.LEFT):
    p = tf.paragraphs[0] if first else tf.add_paragraph()
    p.alignment = align
    p.space_before = Pt(space_before)
    p.space_after = Pt(space_after)
    r = p.add_run()
    r.text = text
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.color.rgb = color
    r.font.name = FONT
    return p


def canvas(slide):
    rect(slide, 0, 0, SLIDE_W, SLIDE_H, fill=CANVAS)


def footer(slide, number: str):
    tf = textbox(slide, MARGIN, FOOTER_Y + Inches(0.12), CONTENT_W, Inches(0.3))
    put(tf, "JobHopper   ·   The Laughing Bots", 11, color=MUTED, first=True)
    tf = textbox(slide, SLIDE_W - MARGIN - Inches(1.2), FOOTER_Y + Inches(0.12),
                 Inches(1.2), Inches(0.3))
    put(tf, number, 11, color=MUTED, first=True, align=PP_ALIGN.RIGHT)


def heading(slide, kicker, title, accent=BLUE, sub=None, title_size=34):
    y = Inches(0.5)
    tf = textbox(slide, MARGIN, y, CONTENT_W, Inches(0.24))
    put(tf, kicker.upper(), 13, bold=True, color=accent, first=True)

    lines = wrap(title, pt(CONTENT_W - SLOP), title_size, bold=True)
    th = Pt(len(lines) * title_size * LINE)
    tf = textbox(slide, MARGIN, y + Inches(0.28), CONTENT_W, th)
    for i, ln in enumerate(lines):
        put(tf, ln, title_size, bold=True, color=INK, first=(i == 0))

    bottom = y + Inches(0.28) + th + Pt(6)
    if sub:
        slines = wrap(sub, pt(CONTENT_W - SLOP), 17)
        sh = Pt(len(slines) * 17 * LINE)
        tf = textbox(slide, MARGIN, bottom, CONTENT_W, sh)
        for i, ln in enumerate(slines):
            put(tf, ln, 17, color=MUTED, first=(i == 0))
        bottom += sh + Pt(8)
    rect(slide, MARGIN, bottom, Inches(1.45), Pt(3.5), fill=accent)
    return bottom + Inches(0.3)


# ----------------------------------------------------------------- cards --
CARD_PAD_X = Inches(0.26)
CARD_PAD_T = Pt(13)
CARD_PAD_B = Pt(15)
CARD_GAP = Pt(8)
RAIL = Inches(0.055)


def card_metrics(w, title, body, title_size, body_size, tag=None):
    """Wrapped lines and the exact height a card needs."""
    inner = pt(w - RAIL - CARD_PAD_X - Inches(0.24) - SLOP)
    t_avail = inner - (58 if tag else 0)
    tl = wrap(title, t_avail, title_size, bold=True)
    bl = wrap(body, inner, body_size)
    h = (pt(CARD_PAD_T) + len(tl) * title_size * LINE + pt(CARD_GAP)
         + len(bl) * body_size * LINE + pt(CARD_PAD_B))
    return tl, bl, Pt(h)


def card(slide, x, y, w, h, accent, title, body, *, title_size=18,
         body_size=14, tag=None):
    tl, bl, _ = card_metrics(w, title, body, title_size, body_size, tag)
    rect(slide, x, y, w, h, fill=PAPER, line=HAIRLINE, rounded=True, radius=0.055)
    rect(slide, x, y, RAIL, h, fill=accent)

    tx = x + RAIL + CARD_PAD_X
    tw = w - RAIL - CARD_PAD_X - Inches(0.18)
    ty = y + CARD_PAD_T
    th = Pt(len(tl) * title_size * LINE)
    tf = textbox(slide, tx, ty, tw, th)
    for i, ln in enumerate(tl):
        put(tf, ln, title_size, bold=True, color=INK, first=(i == 0))

    by = ty + th + CARD_GAP
    tf = textbox(slide, tx, by, tw, Pt(len(bl) * body_size * LINE))
    blank_next = False
    for i, ln in enumerate(bl):
        if ln == "":
            blank_next = True
            continue
        put(tf, ln, body_size, color=MUTED, first=(i == 0),
            space_before=(body_size * 0.55 if blank_next else 0))
        blank_next = False

    if tag:
        badge = rect(slide, x + w - Inches(1.18), y + Pt(11), Inches(0.95),
                     Inches(0.25), fill=AMBER, rounded=True, radius=0.4)
        btf = badge.text_frame
        btf.vertical_anchor = MSO_ANCHOR.MIDDLE
        put(btf, tag, 9.5, bold=True, color=PAPER, first=True,
            align=PP_ALIGN.CENTER)


def card_grid(slide, y0, items, cols, *, title_size=19, body_size=14,
              gap_x=Inches(0.3), gap_y=Inches(0.24), uniform_rows=True):
    """Lay cards out in a grid, each row as tall as its tallest card."""
    w = (CONTENT_W - (cols - 1) * gap_x) / cols
    heights = [card_metrics(w, t, b, title_size, body_size, tag)[2]
               for _a, t, b, tag in items]
    y = y0
    for r in range(0, len(items), cols):
        row = items[r:r + cols]
        rh = max(heights[r:r + cols]) if uniform_rows else None
        for c, (accent, title, body, tag) in enumerate(row):
            h = rh if uniform_rows else heights[r + c]
            card(slide, MARGIN + c * (w + gap_x), y, w, h, accent, title, body,
                 title_size=title_size, body_size=body_size, tag=tag)
        y += (rh if uniform_rows else max(heights[r:r + cols])) + gap_y
    return y - gap_y


def banner(slide, y, text, size=17, fill=PAPER, color=INK, accent=None):
    lines = wrap(text, pt(CONTENT_W - Inches(0.72) - SLOP), size, bold=True)
    h = Pt(len(lines) * size * LINE) + Pt(26)
    rect(slide, MARGIN, y, CONTENT_W, h, fill=fill,
         line=(HAIRLINE if fill == PAPER else None), rounded=True, radius=0.14)
    if accent:
        rect(slide, MARGIN, y, RAIL, h, fill=accent)
    tf = textbox(slide, MARGIN + Inches(0.34), y + Pt(13),
                 CONTENT_W - Inches(0.68), Pt(len(lines) * size * LINE))
    for i, ln in enumerate(lines):
        put(tf, ln, size, bold=True, color=color, first=(i == 0))
    return y + h


def bullets(slide, x, y, w, items, size=20, gap=13):
    total = Pt(0)
    for i, item in enumerate(items):
        lines = wrap(item, pt(w) - 22 - pt(SLOP), size)
        h = Pt(len(lines) * size * LINE)
        rect(slide, x + Inches(0.02), y + Pt(size * 0.34), Pt(7), Pt(7),
             fill=TEAL, rounded=True, radius=0.5)
        tf = textbox(slide, x + Inches(0.26), y, w - Inches(0.26), h)
        for j, ln in enumerate(lines):
            put(tf, ln, size, color=INK, first=(j == 0))
        y += h + Pt(gap)
        total += h + Pt(gap)
    return y


def full_bleed(slide, image: Path, pad=Inches(0.16)):
    from PIL import Image

    with Image.open(image) as im:
        iw, ih = im.size
    aw, ah = SLIDE_W - 2 * pad, SLIDE_H - 2 * pad
    if iw / ih > aw / ah:
        w, h = aw, Emu(int(aw * ih / iw))
    else:
        h, w = ah, Emu(int(ah * iw / ih))
    slide.shapes.add_picture(str(image), Emu(int((SLIDE_W - w) / 2)),
                             Emu(int((SLIDE_H - h) / 2)), int(w), int(h))


def check(name: str, bottom):
    if bottom > FOOTER_Y:
        _WARN.append(f"{name}: content overruns footer by "
                     f"{pt(bottom - FOOTER_Y):.0f}pt")


def blank(prs):
    return prs.slides.add_slide(prs.slide_layouts[6])


def notes(slide, text: str):
    slide.notes_slide.notes_text_frame.text = text.strip()


# ------------------------------------------------------------------ build --
def build() -> None:
    prs = Presentation()
    prs.slide_width, prs.slide_height = SLIDE_W, SLIDE_H

    # 1 -------------------------------------------------------------- title
    s = blank(prs)
    canvas(s)
    rect(s, 0, 0, Inches(0.32), SLIDE_H, fill=BLUE)
    rect(s, Inches(0.32), 0, Inches(0.1), SLIDE_H, fill=TEAL)
    rect(s, Inches(0.42), 0, Inches(0.06), SLIDE_H, fill=PLUM)

    tf = textbox(s, Inches(1.25), Inches(1.5), Inches(11.0), Inches(1.3))
    put(tf, "JobHopper", 66, bold=True, color=INK, first=True)
    tf = textbox(s, Inches(1.25), Inches(2.82), Inches(10.2), Inches(0.9))
    put(tf, "Turning a pile of job postings into a picture of what to learn "
            "— and a way to practise it.", 23, color=MUTED, first=True)

    rect(s, Inches(1.28), Inches(4.0), Inches(1.5), Pt(3.5), fill=TEAL)
    tf = textbox(s, Inches(1.25), Inches(4.36), Inches(11.0), Inches(0.3))
    put(tf, "THE LAUGHING BOTS", 14, bold=True, color=TEAL, first=True)
    tf = textbox(s, Inches(1.25), Inches(4.7), Inches(11.3), Inches(0.4))
    put(tf, "Rose Duarte   ·   Elijah Hewlett   ·   Angel Patino   ·   "
            "Terrell Whiting", 21, bold=True, color=INK, first=True)
    tf = textbox(s, Inches(1.25), Inches(5.32), Inches(10.6), Inches(0.9))
    put(tf, "Final project presentation", 17, color=MUTED, first=True)
    put(tf, "A full-stack web application: HTML, Bootstrap and Sass on the "
            "front end; FastAPI, SQLAlchemy and SQLite behind it.", 15,
        color=MUTED, space_before=7)
    footer(s, "1")
    notes(s, """
[0:00 - 0:15]   SPEAKER 1

Hi, we're the Laughing Bots - Rose, Elijah, Angel and Terrell. This is JobHopper:
it reads real job postings, shows you which skills those postings are actually
asking for, and lets you quiz yourself on any of them.
""")

    # 2 --------------------------------------------------------------- goal
    s = blank(prs)
    canvas(s)
    top = heading(s, "The goal",
                  "The information is public. Reading it is the problem.", BLUE)
    col_w = (CONTENT_W - Inches(0.34)) / 2
    y = top
    for para in [
        "Somebody trying to move up in tech opens a job board and finds forty "
        "postings for the same title — each one a different wall of "
        "requirements.",
        "The useful signal is which tools keep coming up. That signal is real, "
        "it is public, and it is completely buried.",
        "Reading forty postings by hand is the thing nobody actually does. So "
        "people guess at what to learn next.",
    ]:
        lines = wrap(para, pt(col_w - SLOP), 19)
        h = Pt(len(lines) * 19 * LINE)
        tf = textbox(s, MARGIN, y, col_w, h)
        for i, ln in enumerate(lines):
            put(tf, ln, 19, color=INK, first=(i == 0))
        y += h + Pt(16)

    x2 = MARGIN + col_w + Inches(0.34)
    cy = top
    for accent, title, body in [
        (TEAL, "What JobHopper does",
         "Reads the current postings for a role and draws the tools and skills "
         "sized by how many of those postings actually mention them."),
        (PLUM, "And then makes it actionable",
         "Every skill in that picture is clickable. Click it and you are in a "
         "timed, multiple-choice quiz on that exact skill."),
    ]:
        _, _, h = card_metrics(col_w, title, body, 19, 15)
        card(s, x2, cy, col_w, h, accent, title, body, title_size=19,
             body_size=15)
        cy += h + Inches(0.22)

    b = banner(s, max(y, cy) + Inches(0.16),
               "In one sentence:  show people what the market is asking for, "
               "and give them a way to practise it.", size=19, fill=INK,
               color=PAPER)
    check("s2", b)
    footer(s, "2")
    notes(s, """
[0:15 - 1:00]   SPEAKER 1

The problem isn't that this information is secret - job postings are public. It's
volume. Search one title and you get forty postings, each with its own wall of
requirements. The signal is which tools keep repeating, and nobody reads forty
postings to find it. So people guess at what to learn next.

JobHopper does the reading. It pulls the current postings for a role, extracts
the tools and skills, and sizes them by how many postings actually mention each
one. The big words are what the market keeps asking for.

Then it does one more thing: every skill in that picture is clickable. Click
Python, and you're in a timed quiz on Python.
""")

    # 3 ------------------------------------------------ functional reqs 1/2
    s = blank(prs)
    canvas(s)
    top = heading(s, "Functional requirements  ·  1 of 2",
                  "What the system has to do", TEAL,
                  sub="Everything below is built and demonstrable unless it "
                      "carries a flag.")
    end = card_grid(s, top, [
        (BLUE, "FR1 · Accounts",
         "Register, sign in, stay signed in, sign out. Usernames are 4–16 "
         "letters and digits; passwords 8–20 characters. A session lasts 24 "
         "hours.", None),
        (TEAL, "FR2 · Generate a skills word cloud",
         "Choose a job title, and optionally a location and a minimum salary. "
         "Pick up to 40 keywords and a shape. Get back the tools and skills "
         "weighted by how many current postings mention each one.", None),
        (BLUE, "FR3 · Remember what you searched",
         "Every cloud a signed-in user generates is saved to their account and "
         "can be re-run from their profile in one click.", None),
        (TEAL, "FR4 · Fail honestly",
         "If the filters match too little posting data to build a cloud, the "
         "app says so. It never draws an empty or misleading picture.", None),
    ], 2)
    b = banner(s, end + Inches(0.26),
               "The word cloud is the front door — everything else in the app "
               "is reached through it.")
    check("s3", b)
    footer(s, "3")
    notes(s, """
[1:00 - 1:55]   SPEAKER 2

These are our functional requirements - what the system has to do.

FR1, accounts: register, sign in, stay signed in, sign out. Usernames four to
sixteen characters, passwords eight to twenty, sessions last twenty-four hours.

FR2 is the core feature. Pick a job title, optionally a location and a minimum
salary, then how many keywords and a shape. What comes back is the tools and
skills for that role, weighted by how many current postings mention each one.

FR3, we remember it - every cloud a signed-in user generates is saved, and can be
re-run in one click.

FR4 is the one people forget to write down. If the filters match too little data
to build an honest picture, the app says so rather than draw a misleading cloud.
""")

    # 4 ------------------------------------------------ functional reqs 2/2
    s = blank(prs)
    canvas(s)
    top = heading(s, "Functional requirements  ·  2 of 2",
                  "From a picture to practice", TEAL)
    end = card_grid(s, top, [
        (PLUM, "FR5 · Play a quiz on any skill",
         "Any skill backed by a question bank is clickable. Ten multiple-choice "
         "questions at easy, medium or hard, each difficulty on its own timer — "
         "3:00, 2:00 or 1:30.", None),
        (PLUM, "FR6 · Live scoring, honestly done",
         "Each answer is locked in on the server as it is chosen, and only then "
         "is the player told whether it was right. Knowing the answer afterwards "
         "cannot change it, so the running score and the final score always "
         "agree.", None),
        (BLUE, "FR7 · Remember how you did",
         "Completed quizzes are saved to the account with the skill, the "
         "difficulty and the score, and shown back on the profile page.", None),
        (SLATE, "FR8 · Personal prep roadmap",
         "An ordered list of skills to learn for a target role, each step "
         "markable as you go. The API is built and covered by tests — it never "
         "got a screen. More on that at the end.", "API ONLY"),
    ], 2)
    b = banner(s, end + Inches(0.26),
               "Behind it: 1,260 questions — 28 skills × 3 difficulties × 15 "
               "questions each.")
    check("s4", b)
    footer(s, "4")
    notes(s, """
[2:00 - 2:55]   SPEAKER 2

The second half turns that picture into practice.

FR5: any skill with a question bank behind it is clickable. Ten multiple-choice
questions at easy, medium or hard, each with its own clock - three minutes, two,
or a minute and a half.

FR6 is the one we're most careful about. Every answer is locked in on the server
the moment it's chosen, and only then are you told whether it was right. Because
the choice is already committed, knowing the answer afterwards can't change it -
so the running score and the final score can never disagree.

FR7: completed quizzes are saved with the skill, the difficulty and the score.

FR8, the prep roadmap. I'll be straight - the API is built and tested, but it
never got a screen. More on that at the end.
""")

    # 5 ------------------------------------------- non-functional reqs
    s = blank(prs)
    canvas(s)
    top = heading(s, "Non-functional requirements", "How well it has to do it",
                  PLUM,
                  sub="Not features — but the app is wrong without them.")
    end = card_grid(s, top, [
        (BLUE, "Security",
         "Passwords are bcrypt-hashed, never stored or returned. Tokens are "
         "signed and expire in 24 hours. A failed login gives one generic "
         "message, so it can't reveal which usernames exist.", None),
        (PLUM, "Integrity",
         "The server decides every score, never the browser. A finished quiz "
         "can't be replayed, and importing the same posting twice can't "
         "duplicate it.", None),
        (TEAL, "Performance",
         "The two hottest queries — building a cloud and pulling a quiz — each "
         "run against a composite index. Responses over 500 bytes are "
         "compressed.", None),
        (SLATE, "Reliability",
         "237 automated tests: 209 on the backend, 28 on the front end. Both "
         "suites run on every pull request before anything can merge.", None),
        (BLUE, "Usability",
         "Responsive at phone and desktop widths. Validation appears next to "
         "the field. Every API error arrives in one shape, so no screen shows a "
         "user a raw error object.", None),
        (TEAL, "Portability",
         "Dependency versions are pinned so four laptops and the CI runner "
         "resolve the same set, and the app builds and migrates its own "
         "database on first run.", None),
    ], 3, title_size=19, body_size=13.5)
    check("s5", end)
    footer(s, "5")
    notes(s, """
[2:50 - 3:45]   SPEAKER 2

Non-functional requirements - not features, but the app is wrong without them.

Security: passwords are bcrypt-hashed, never stored or returned, and a failed
login gives one generic message either way - so you can't use our login form to
find out who has an account.

Integrity: the server decides every score, never the browser, and a finished quiz
can't be replayed.

Performance: the two hottest queries each run against a composite index we added
deliberately for them.

Reliability: 237 automated tests, and nothing merges until both suites pass.

Usability: responsive, validation next to the field, and every API error in one
shape.

Portability: pinned versions, and the app builds its own database on first run.
""")

    # 6 ----------------------------------------------------- stack diagram
    s = blank(prs)
    canvas(s)
    full_bleed(s, DIAGRAMS / "tech_stack.png")
    notes(s, """
[3:45 - 4:40]   SPEAKER 3

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
""")
    footer(s, "6")

    # 7 ------------------------------------------------------ why the stack
    s = blank(prs)
    canvas(s)
    top = heading(s, "Why this stack",
                  "Chosen for a four-person team on a semester timeline", TEAL)
    end = card_grid(s, top, [
        (TEAL, "Python + FastAPI",
         "Python is the strongest shared language on this team. FastAPI gave us "
         "request and response validation for free and generated live API docs — "
         "so the front end could build against a written contract instead of "
         "waiting for the backend to finish.", None),
        (PLUM, "SQLite + SQLAlchemy",
         "SQLite is a single file: no database server to install, so four "
         "laptops and the CI runner all run an identical database with zero "
         "setup. SQLAlchemy keeps every query parameterised — injection-safe by "
         "construction — and moving to PostgreSQL later is one connection "
         "string.", None),
        (BLUE, "Plain JavaScript, Bootstrap, Sass",
         "A framework would have added a build step and a learning curve to a "
         "team of four on a semester clock. Bootstrap gave us a responsive grid "
         "on day one; Sass gave us one shared palette across eleven pages "
         "instead of eleven copies of it.", None),
        (SLATE, "GitHub Actions + pytest + Jest",
         "The cheapest way to stop four people breaking each other's work. Both "
         "suites run on every pull request, so a regression is caught by the "
         "robot rather than by whoever pulls next.", None),
    ], 2, title_size=20)
    check("s7", end)
    footer(s, "7")
    notes(s, """
[4:40 - 5:30]   SPEAKER 3

Why these choices.

Python and FastAPI: Python is the strongest shared language on this team, and
FastAPI gave us validation for free plus live API docs - so the front end could
build against a written contract instead of waiting for the backend.

SQLite: one file, no server to install, so four laptops and the CI runner run an
identical database with zero setup. That removed a whole category of "works on my
machine". And SQLAlchemy keeps every query parameterised, so we're injection-safe
by construction.

Plain JavaScript, Bootstrap and Sass: a framework would have cost us a build step
and a learning curve on a semester clock.

And GitHub Actions - the cheapest way to stop four people breaking each other's
work.
""")

    # 8 ------------------------------------------------------ ERD overview
    s = blank(prs)
    canvas(s)
    full_bleed(s, DIAGRAMS / "erd_overview.png")
    notes(s, """
[5:50 - 6:30]   SPEAKER 4

Before the full diagram, the shape of it. Fourteen tables in three groups.

Left: the job-market data - roles, postings, skills, and the junctions between
them. That's where a cloud comes from. Middle: identity and activity. Right: the
quiz engine.

What makes this one system rather than three is two shared tables. Skills is
shared left to right - the same row that sizes a word in the cloud owns that
word's question bank, which is why clicking a word can start a quiz. And users
ties everything on the right to one account.
""")
    footer(s, "8")

    # 9 ---------------------------------------------------------- full ERD
    s = blank(prs)
    canvas(s)
    full_bleed(s, DIAGRAMS / "erd_full.png")
    notes(s, """
[6:15 - 7:35]   SPEAKER 4   -   Trace each table with the cursor as you name it.

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
what you picked. That is what makes live scoring trustworthy, and what stops a
finished quiz being replayed. Submitting lands the result in GAME_ATTEMPTS.

Down the middle, USERS - every search, every attempt, and one roadmap per user
all hang off it.
""")
    footer(s, "9")

    # 10 -------------------------------------------------------- the roles
    s = blank(prs)
    canvas(s)
    top = heading(s, "User roles",
                  "JobHopper has two roles — and we'll show you both", BLUE,
                  sub="What the app lets you do depends entirely on whether the "
                      "request carries a valid token.")
    cw2 = (CONTENT_W - Inches(0.3)) / 2
    pair = [
        (SLATE, "Visitor  ·  not signed in",
         "Can browse the home page, the game rules, the stack page and the "
         "creators page — and can register an account.\n\n"
         "Cannot generate a word cloud, and has no profile, no saved searches "
         "and no game history. The page sends them to sign-in — and the API "
         "refuses the request as well, so the rule holds even if you skip the "
         "page."),
        (BLUE, "Registered user  ·  signed in",
         "Everything above, plus: generate word clouds, play quizzes with the "
         "result saved, and a profile page showing recent searches and recent "
         "scores — each one re-runnable in a click.\n\n"
         "Identity comes from a signed token, checked on the server for every "
         "single request."),
    ]
    h = max(card_metrics(cw2, t, b, 21, 15)[2] for _a, t, b in pair)
    for i, (accent, title, body) in enumerate(pair):
        card(s, MARGIN + i * (cw2 + Inches(0.3)), top, cw2, h, accent, title,
             body, title_size=21, body_size=15)

    y = top + h + Inches(0.26)
    body = ("Nothing in JobHopper is administered through a screen. Postings "
            "arrive through the ingest pipeline and the question bank is loaded "
            "from a fixture, so there was never a task an admin would log in to "
            "do. Adding an admin login would have been a role with nothing "
            "behind it.")
    _, bl, ch = card_metrics(CONTENT_W, "Why there is no admin role", body, 19,
                             15)
    card(s, MARGIN, y, CONTENT_W, ch, AMBER, "Why there is no admin role", body,
         title_size=19, body_size=15)
    check("s10", y + ch)
    footer(s, "10")
    notes(s, """
[7:55 - 8:30]   SPEAKER 1   -   sets up the demo

One note before the demo, because it shapes what you'll see.

JobHopper has two roles, and the difference is whether the request carries a
valid token. A visitor can read the public pages and register - nothing else. A
signed-in user gets word clouds, quizzes that save their result, and a profile.

And there's deliberately no admin role. Postings come in through the ingest
pipeline and questions load from a fixture, so there was never a job an admin
would log in to do.
""")

    # 11-13 ------------------------------------------------------ demo cues
    demos = [
        ("1 OF 3", SLATE, "Role 1 — the visitor", [
            "Browse the public pages — home, rules, stack, creators",
            "Try to reach a word cloud without signing in → bounced to sign-in",
            "Register a brand-new account live — the form builds your first "
            "cloud with you",
        ], "11", """
[8:00 – 9:00]   SPEAKER 3   —   LIVE DEMO. Screen share on.

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
"""),
        ("2 OF 3", BLUE, "Role 2 — the registered user", [
            "Read the cloud we just generated — then build another from the "
            "profile",
            "Click a skill → pick a difficulty → play the timed quiz",
            "Watch the live score move as each answer locks in",
            "Open the profile: the search and the score are both already there",
        ], "12", """
[9:00 – 11:00]   SPEAKER 3 and SPEAKER 4   —   LIVE DEMO. The main event.

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
"""),
        ("3 OF 3", PLUM, "It really is a database", [
            "Open the database file and list the tables — the same fourteen from "
            "the ERD",
            "Show the rows we just created: the search and the game attempt, "
            "carrying our user_id",
            "Show a stored password — a bcrypt hash, not the password we typed",
            "Show the word-cloud counts matching the picture we just drew",
        ], "13", """
[11:00 – 12:00]   SPEAKER 4   —   LIVE DEMO. This is the 9-point rubric item.

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
"""),
    ]
    for part, accent, title, steps, num, note in demos:
        s = blank(prs)
        canvas(s)
        rect(s, 0, 0, SLIDE_W, Inches(0.13), fill=accent)
        tf = textbox(s, MARGIN, Inches(1.35), CONTENT_W, Inches(0.3))
        put(tf, f"LIVE DEMO  ·  PART {part}", 16, bold=True, color=accent,
            first=True)
        tlines = wrap(title, pt(CONTENT_W - SLOP), 50, bold=True)
        tf = textbox(s, MARGIN, Inches(1.78), CONTENT_W,
                     Pt(len(tlines) * 50 * LINE))
        for i, ln in enumerate(tlines):
            put(tf, ln, 50, bold=True, color=INK, first=(i == 0))
        ry = Inches(1.78) + Pt(len(tlines) * 50 * LINE) + Inches(0.18)
        rect(s, MARGIN, ry, Inches(1.5), Pt(3.5), fill=accent)
        end = bullets(s, MARGIN, ry + Inches(0.4), CONTENT_W - Inches(1.2),
                      steps, size=20)
        check(f"s{num}", end)
        footer(s, num)
        notes(s, note)

    # 14 --------------------------------------------- achieved vs altered
    s = blank(prs)
    canvas(s)
    top = heading(s, "Summary", "What we achieved, and what we changed", TEAL,
                  sub="We planned more than we shipped. Here is the honest "
                      "accounting.")
    pair = [
        (TEAL, "Achieved",
         "▸  Every core feature is live: accounts, word cloud, timed quiz with "
         "live scoring, and saved history.\n\n"
         "▸  Real posting data — ingested from a live job-search API rather "
         "than invented: 40 postings across 4 roles.\n\n"
         "▸  The question bank beat its own target. We aimed for 10 per skill "
         "per difficulty and shipped 15 — 1,260 questions.\n\n"
         "▸  237 automated tests with CI on every pull request. 189 commits, "
         "44 reviewed pull requests."),
        (AMBER, "Altered or cut",
         "▸  The prep roadmap has a finished, tested API and no screen. With "
         "the time left we chose to make the quiz good rather than make the "
         "roadmap merely exist.\n\n"
         "▸  Maximum salary: we removed the field instead of shipping a filter "
         "that quietly did nothing. Minimum salary works.\n\n"
         "▸  Named ranks are described on our rules page, but scoring currently "
         "ends at a normalised number. The docs got ahead of the app.\n\n"
         "▸  Word clouds ended up behind sign-in, so every search could be "
         "saved to a real account and offered back."),
    ]
    h = max(card_metrics(cw2, t, b, 22, 14.5)[2] for _a, t, b in pair)
    for i, (accent, title, body) in enumerate(pair):
        card(s, MARGIN + i * (cw2 + Inches(0.3)), top, cw2, h, accent, title,
             body, title_size=22, body_size=14.5)
    check("s14", top + h)
    footer(s, "14")
    notes(s, """
[11:30 - 12:30]   SPEAKER 1

The honest accounting.

On the left. Every core feature is live. Our postings are real - ingested from a
live job-search API, which meant dealing with genuinely messy description text.
The question bank beat its own target: we aimed for ten per skill per difficulty
and shipped fifteen, which is 1,260 questions. And the process held - 189
commits, 44 reviewed pull requests, 237 tests.

On the right, what changed. The prep roadmap has a finished, tested API and no
screen; with the time left, we chose to make the quiz good rather than make the
roadmap merely exist.

Maximum salary we removed rather than ship a filter that quietly did nothing.

Named ranks are on our rules page but not in the scoring yet - our docs got ahead
of the app, and that's on us.
""")

    # 15 -------------------------------------------------------- close
    s = blank(prs)
    canvas(s)
    rect(s, 0, 0, Inches(0.32), SLIDE_H, fill=BLUE)
    rect(s, Inches(0.32), 0, Inches(0.1), SLIDE_H, fill=TEAL)
    rect(s, Inches(0.42), 0, Inches(0.06), SLIDE_H, fill=PLUM)

    left = Inches(1.25)
    inner_w = SLIDE_W - left - Inches(0.9)
    tf = textbox(s, left, Inches(0.85), inner_w, Inches(0.3))
    put(tf, "WHERE WE'D TAKE IT NEXT", 14, bold=True, color=TEAL, first=True)

    nx = [
        (BLUE, "Ship the roadmap screen",
         "The API is already built and tested. The shortest distance between "
         "where we are and a noticeably more useful app."),
        (TEAL, "Widen the ingest",
         "Four roles was enough to prove the idea. The pipeline isn't the "
         "limit — the vocabulary of skills we match against is."),
        (PLUM, "Close the loop",
         "Feed quiz results back into the cloud, so the skills you keep getting "
         "wrong become the ones it puts in front of you."),
    ]
    cw3 = (inner_w - 2 * Inches(0.26)) / 3
    ch = max(card_metrics(cw3, t, b, 18, 13.5)[2] for _a, t, b in nx)
    for i, (accent, title, body) in enumerate(nx):
        card(s, left + i * (cw3 + Inches(0.26)), Inches(1.25), cw3, ch, accent,
             title, body, title_size=18, body_size=13.5)

    y = Inches(1.25) + ch + Inches(0.45)
    tf = textbox(s, left, y, inner_w, Inches(0.9))
    put(tf, "Thank you", 50, bold=True, color=INK, first=True)
    tf = textbox(s, left, y + Inches(0.86), inner_w - Inches(0.6), Inches(0.5))
    put(tf, "JobHopper reads what the market is asking for, and gives you "
            "somewhere to start.", 21, color=MUTED, first=True)
    rect(s, left + Inches(0.03), y + Inches(1.52), Inches(1.5), Pt(3.5),
         fill=TEAL)
    tf = textbox(s, left, y + Inches(1.85), inner_w, Inches(0.3))
    put(tf, "THE LAUGHING BOTS", 13, bold=True, color=TEAL, first=True)
    tf = textbox(s, left, y + Inches(2.18), inner_w, Inches(0.4))
    put(tf, "Rose Duarte   ·   Elijah Hewlett   ·   Angel Patino   ·   "
            "Terrell Whiting", 18, bold=True, color=INK, first=True)
    check("s15", y + Inches(2.5))
    footer(s, "15")
    notes(s, """
[12:30 - 13:00]   SPEAKER 1   -   close

Three things next. Ship the roadmap screen - the API is already there. Widen the
ingest; the pipeline isn't the limit, the skill vocabulary is. And the one we
actually want: close the loop, so the skills you keep getting wrong become the
ones your cloud puts in front of you.

Right now the two halves of the app share a database. They should share a memory.

That's JobHopper. Thank you.

--- END. Target 13:00. Hard ceiling 15:00. ---
""")

    prs.save(OUT)
    print(f"wrote {OUT}")
    if _WARN:
        print("LAYOUT WARNINGS:")
        for w in _WARN:
            print("  !", w)
    else:
        print("layout: all slides fit")


if __name__ == "__main__":
    build()
