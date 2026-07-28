"""Render the JobHopper architecture / technology-stack diagram.

Produces diagrams/tech_stack.png for the final presentation deck.

Run:  python presentation/scripts/make_stack.py
"""
from __future__ import annotations

from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "diagrams"

CLIENT = "#3F5C99"
API = "#1F7A6B"
DATA = "#9A4F70"
EXTERNAL = "#B0742C"
QUALITY = "#5B6472"

INK = "#1B2430"
MUTED = "#6B7787"
LINE = "#C9D2DE"
PAPER = "#FFFFFF"
BG = "#F4F7FB"
FONT = "DejaVu Sans"

W, H = 2420, 1460

MAIN_X, MAIN_W = 70, 1620
SIDE_X, SIDE_W = 1750, 600


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def text_w(s: str, size: int) -> float:
    """Rough advance width for DejaVu Sans - good enough to size a chip."""
    return len(s) * size * 0.60


def chip(x: float, y: float, label: str, colour: str, size: int = 25,
         sub: str | None = None) -> tuple[str, float]:
    """A rounded pill. Returns the svg and the width consumed."""
    pad = 24
    w = max(text_w(label, size), text_w(sub or "", 18)) + pad * 2
    h = 74 if sub else 56
    out = [
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h / 2}" '
        f'fill="{PAPER}" stroke="{colour}" stroke-width="2.5"/>',
        f'<text x="{x + pad}" y="{y + (36 if sub else 37)}" font-family="{FONT}" '
        f'font-size="{size}" font-weight="bold" fill="{INK}">{esc(label)}</text>',
    ]
    if sub:
        out.append(
            f'<text x="{x + pad}" y="{y + 60}" font-family="{FONT}" font-size="18" '
            f'fill="{MUTED}">{esc(sub)}</text>'
        )
    return "\n".join(out), w


def chip_row(x: float, y: float, items: list, colour: str, gap: int = 18,
             size: int = 25) -> str:
    out = []
    cx = x
    for it in items:
        label, sub = (it, None) if isinstance(it, str) else it
        svg, w = chip(cx, y, label, colour, size=size, sub=sub)
        out.append(svg)
        cx += w + gap
    return "\n".join(out)


def band(x: float, y: float, w: float, h: float, colour: str, title: str,
         subtitle: str) -> str:
    return "\n".join([
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="20" fill="{PAPER}" '
        f'stroke="{LINE}" stroke-width="2"/>',
        f'<path d="M{x},{y + h - 20} L{x},{y + 20} Q{x},{y} {x + 20},{y} '
        f'L{x + 14},{y} L{x + 14},{y + h} L{x + 20},{y + h} Q{x},{y + h} '
        f'{x},{y + h - 20} Z" fill="{colour}"/>',
        f'<rect x="{x}" y="{y}" width="14" height="{h}" fill="{colour}"/>',
        f'<text x="{x + 42}" y="{y + 50}" font-family="{FONT}" font-size="34" '
        f'font-weight="bold" fill="{colour}">{title}</text>',
        f'<text x="{x + 42}" y="{y + 84}" font-family="{FONT}" font-size="22" '
        f'fill="{MUTED}">{subtitle}</text>',
    ])


def arrow(cx: float, y0: float, y1: float, label: str, colour: str) -> str:
    return "\n".join([
        f'<line x1="{cx}" y1="{y0}" x2="{cx}" y2="{y1 - 16}" stroke="{colour}" '
        f'stroke-width="4"/>',
        f'<path d="M{cx - 13},{y1 - 18} L{cx},{y1} L{cx + 13},{y1 - 18} Z" '
        f'fill="{colour}"/>',
        f'<line x1="{cx - 13}" y1="{y0}" x2="{cx + 13}" y2="{y0}" '
        f'stroke="{colour}" stroke-width="4" stroke-linecap="round"/>',
        f'<text x="{cx + 34}" y="{(y0 + y1) / 2 + 8}" font-family="{FONT}" '
        f'font-size="23" fill="{MUTED}">{esc(label)}</text>',
    ])


def render() -> str:
    p: list[str] = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" '
        f'viewBox="0 0 {W} {H}"><rect width="{W}" height="{H}" fill="{BG}"/>',
        f'<text x="{MAIN_X}" y="80" font-family="{FONT}" font-size="52" '
        f'font-weight="bold" fill="{INK}">JobHopper technology stack</text>',
        f'<text x="{MAIN_X}" y="128" font-family="{FONT}" font-size="28" '
        f'fill="{MUTED}">A browser talking to one Python API, which owns the only '
        f'connection to the database.</text>',
    ]

    # ---------------------------------------------------------- client layer
    y = 190
    p.append(band(MAIN_X, y, MAIN_W, 300, CLIENT, "Presentation layer",
                  "Runs in the browser - no framework, no build step"))
    p.append(chip_row(MAIN_X + 42, y + 110, [
        ("HTML5", "12 pages, semantic markup"),
        ("Bootstrap 5.3", "grid, navbar, forms"),
        ("Sass", "compiled to one stylesheet"),
    ], CLIENT))
    p.append(chip_row(MAIN_X + 42, y + 204, [
        ("JavaScript (ES modules)", "page controllers, no framework"),
        ("wordcloud.js", "canvas rendering"),
        ("Figma", "every screen designed first"),
    ], CLIENT))

    p.append(arrow(MAIN_X + MAIN_W / 2 - 300, 490, 570,
                   "HTTP + JSON  ·  Authorization: Bearer <JWT>  ·  "
                   "CORS allow-list  ·  gzip", CLIENT))

    # ------------------------------------------------------------- api layer
    y = 570
    p.append(band(MAIN_X, y, MAIN_W, 400, API, "Application layer",
                  "FastAPI on Uvicorn - every rule lives here, never in the browser"))
    p.append(chip_row(MAIN_X + 42, y + 108, [
        ("FastAPI + Uvicorn", "17 endpoints, auto OpenAPI docs"),
        ("Pydantic v2", "validates every request and response"),
    ], API))
    p.append(
        f'<text x="{MAIN_X + 42}" y="{y + 224}" font-family="{FONT}" font-size="21" '
        f'font-weight="bold" fill="{MUTED}">ROUTERS</text>'
    )
    p.append(chip_row(MAIN_X + 200, y + 200, [
        "auth", "wordcloud", "game", "roadmap", "history", "meta",
    ], API, size=24))
    p.append(
        f'<text x="{MAIN_X + 42}" y="{y + 314}" font-family="{FONT}" font-size="21" '
        f'font-weight="bold" fill="{MUTED}">SERVICES</text>'
    )
    p.append(chip_row(MAIN_X + 200, y + 290, [
        ("security", "bcrypt hashing + PyJWT tokens"),
        ("keywords", "skill extraction from postings"),
        ("ingest / autoseed", "keeps the data fresh"),
    ], API, size=24))

    p.append(arrow(MAIN_X + MAIN_W / 2 - 300, 970, 1050,
                   "SQLAlchemy session per request  ·  parameterised queries "
                   "only", API))

    # ------------------------------------------------------------ data layer
    y = 1050
    p.append(band(MAIN_X, y, MAIN_W, 250, DATA, "Data layer",
                  "One SQLite file, created and migrated by the app itself"))
    p.append(chip_row(MAIN_X + 42, y + 116, [
        ("SQLAlchemy 2.0 ORM", "typed models, no raw SQL strings"),
        ("SQLite", "backend/jobhopper.db"),
        ("14 tables", "with composite indexes"),
    ], DATA))

    # ------------------------------------------------------------- side rail
    y = 190
    p.append(band(SIDE_X, y, SIDE_W, 300, EXTERNAL, "Where the data comes from",
                  "Real postings, not invented rows"))
    for i, (head, sub) in enumerate([
        ("JSearch API (RapidAPI)", "live job-posting search"),
        ("ingest pipeline", "extracts skills, de-dupes on external_id"),
        ("seed fixture (JSON)", "40 postings shared by all four of us"),
    ]):
        yy = y + 118 + i * 60
        p.append(
            f'<circle cx="{SIDE_X + 56}" cy="{yy - 8}" r="9" fill="{EXTERNAL}"/>'
        )
        p.append(
            f'<text x="{SIDE_X + 84}" y="{yy}" font-family="{FONT}" font-size="24" '
            f'font-weight="bold" fill="{INK}">{esc(head)}</text>'
        )
        p.append(
            f'<text x="{SIDE_X + 84}" y="{yy + 27}" font-family="{FONT}" '
            f'font-size="19" fill="{MUTED}">{esc(sub)}</text>'
        )
        if i < 2:
            p.append(
                f'<line x1="{SIDE_X + 56}" y1="{yy + 2}" x2="{SIDE_X + 56}" '
                f'y2="{yy + 42}" stroke="{EXTERNAL}" stroke-width="3" '
                f'stroke-dasharray="5 6"/>'
            )

    y = 570
    p.append(band(SIDE_X, y, SIDE_W, 400, QUALITY, "How we kept it working",
                  "Every merge had to pass this"))
    for i, (head, sub) in enumerate([
        ("pytest", "209 backend tests"),
        ("Jest + jsdom", "28 frontend tests"),
        ("GitHub Actions", "both suites run on every pull request"),
        ("Pull requests", "44 merged into main, reviewed first"),
    ]):
        yy = y + 122 + i * 70
        p.append(
            f'<rect x="{SIDE_X + 42}" y="{yy - 30}" width="10" height="46" rx="5" '
            f'fill="{QUALITY}"/>'
        )
        p.append(
            f'<text x="{SIDE_X + 70}" y="{yy - 4}" font-family="{FONT}" '
            f'font-size="25" font-weight="bold" fill="{INK}">{esc(head)}</text>'
        )
        p.append(
            f'<text x="{SIDE_X + 70}" y="{yy + 24}" font-family="{FONT}" '
            f'font-size="20" fill="{MUTED}">{esc(sub)}</text>'
        )

    y = 1050
    p.append(band(SIDE_X, y, SIDE_W, 250, CLIENT, "How we worked",
                  "Four people, one main branch"))
    for i, (head, sub) in enumerate([
        ("Figma", "designs agreed before anyone implemented them"),
        ("189 commits, 44 pull requests", "one feature branch per task"),
        ("Pinned dependency versions", "all four machines resolve the same set"),
    ]):
        yy = y + 108 + i * 52
        p.append(
            f'<circle cx="{SIDE_X + 52}" cy="{yy - 8}" r="8" fill="{CLIENT}"/>'
        )
        p.append(
            f'<text x="{SIDE_X + 78}" y="{yy}" font-family="{FONT}" font-size="22" '
            f'font-weight="bold" fill="{INK}">{esc(head)}</text>'
        )
        p.append(
            f'<text x="{SIDE_X + 78}" y="{yy + 24}" font-family="{FONT}" '
            f'font-size="18" fill="{MUTED}">{esc(sub)}</text>'
        )

    # ------------------------------------------------------------- footnote
    p.append(
        f'<rect x="{MAIN_X}" y="1340" width="{W - 2 * MAIN_X + 30}" height="86" '
        f'rx="16" fill="{PAPER}" stroke="{LINE}" stroke-width="2"/>'
    )
    p.append(
        f'<text x="{MAIN_X + 34}" y="1376" font-family="{FONT}" font-size="24" '
        f'font-weight="bold" fill="{INK}">The rule that shaped the whole design:</text>'
    )
    p.append(
        f'<text x="{MAIN_X + 34}" y="1408" font-family="{FONT}" font-size="23" '
        f'fill="{MUTED}">the browser never touches the database, and it never '
        f'decides anything it could be lied to about — scoring, ownership and '
        f'validation all happen in the API.</text>'
    )

    p.append("</svg>")
    return "\n".join(p)


def main() -> None:
    import cairosvg

    OUT.mkdir(parents=True, exist_ok=True)
    svg = render()
    (OUT / "tech_stack.svg").write_text(svg, encoding="utf-8")
    cairosvg.svg2png(bytestring=svg.encode("utf-8"),
                     write_to=str(OUT / "tech_stack.png"), output_width=W)
    print(f"wrote {OUT / 'tech_stack.png'}")


if __name__ == "__main__":
    main()
