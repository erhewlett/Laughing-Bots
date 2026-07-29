"""Render ANGEL_SCRIPT.md as a printable rehearsal PDF.

This is a presenter's script, not a document, so it is laid out for reading at a
glance while talking:

  * every slide starts on a fresh page, so there is never a mid-sentence turn
  * the clock sits in the top corner of each slide, where a glance can find it
  * SAY lines are set large with a coloured rule beside them; DO lines are
    smaller and grey. Those two being instantly distinguishable is the whole
    point of the format, and it is what a plain markdown render loses.

Requires reportlab. Regenerate with:

    python presentation/scripts/make_angel_pdf.py
"""
from __future__ import annotations

import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    KeepTogether,
    PageBreak,
    PageTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "ANGEL_SCRIPT.md"
OUT = ROOT / "ANGEL_SCRIPT.pdf"

INK = colors.HexColor("#1B2430")
MUTED = colors.HexColor("#5E6B7C")
BLUE = colors.HexColor("#3F5C99")
TEAL = colors.HexColor("#1F7A6B")
PLUM = colors.HexColor("#9A4F70")
HAIRLINE = colors.HexColor("#C9D2DE")
WASH = colors.HexColor("#F4F7FB")

MARGIN = 0.75 * inch


def style(name, **kw):
    base = dict(fontName="Helvetica", fontSize=11, leading=15, textColor=INK,
                alignment=TA_LEFT, spaceAfter=6)
    base.update(kw)
    return ParagraphStyle(name, **base)


S = {
    "title": style("title", fontName="Helvetica-Bold", fontSize=26, leading=30,
                   spaceAfter=4),
    "slide": style("slide", fontName="Helvetica-Bold", fontSize=19, leading=23,
                   textColor=BLUE, spaceBefore=0, spaceAfter=2),
    "clock": style("clock", fontName="Helvetica-Bold", fontSize=10.5, leading=13,
                   textColor=TEAL, spaceAfter=10),
    "h3": style("h3", fontName="Helvetica-Bold", fontSize=12, leading=15,
                textColor=MUTED, spaceBefore=8, spaceAfter=4),
    "body": style("body", fontSize=11, leading=15),
    # The line Angel actually reads out. Deliberately the biggest thing on the
    # page after the slide title.
    "say": style("say", fontSize=13.5, leading=18.5, spaceAfter=9),
    # What he does with his hands. Present but visually secondary.
    "do": style("do", fontSize=10.5, leading=14, textColor=MUTED, spaceAfter=4),
    "note": style("note", fontSize=10, leading=13.5, textColor=PLUM, spaceAfter=6),
    "quote": style("quote", fontSize=10.5, leading=14.5, textColor=MUTED,
                   leftIndent=10, spaceAfter=6),
    "cell": style("cell", fontSize=9.5, leading=12.5, spaceAfter=0),
    "cellb": style("cellb", fontName="Helvetica-Bold", fontSize=9.5, leading=12.5,
                   textColor=colors.white, spaceAfter=0),
}


def inline(text: str) -> str:
    """Markdown emphasis -> reportlab markup, with XML escaped first."""
    text = (text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<i>\1</i>", text)
    text = re.sub(r"`(.+?)`", r'<font face="Courier" size="9.5">\1</font>', text)
    return text


def table_block(rows: list[list[str]]) -> Table:
    header, *body = rows
    data = [[Paragraph(inline(c), S["cellb"]) for c in header]]
    data += [[Paragraph(inline(c), S["cell"]) for c in r] for r in body]
    avail = LETTER[0] - 2 * MARGIN
    # The running order is #/slide/length/ends-at; give the name the slack.
    widths = ([0.07, 0.55, 0.19, 0.19] if len(header) == 4
              else [1 / len(header)] * len(header))
    t = Table(data, colWidths=[w * avail for w in widths], repeatRows=1)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BLUE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, WASH]),
        ("GRID", (0, 0), (-1, -1), 0.5, HAIRLINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return t


def say_block(text: str) -> Table:
    """A spoken line, with a teal rule down its left edge."""
    p = Paragraph(inline(text), S["say"])
    t = Table([[p]], colWidths=[LETTER[0] - 2 * MARGIN - 14])
    t.setStyle(TableStyle([
        ("LINEBEFORE", (0, 0), (0, -1), 2.5, TEAL),
        ("LEFTPADDING", (0, 0), (-1, -1), 11),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


def build_story(md: str) -> list:
    story: list = []
    lines = md.split("\n")
    i = 0
    para: list[str] = []
    first_slide = True

    def flush(kind="body"):
        nonlocal para
        if para:
            story.append(Paragraph(inline(" ".join(para).strip()), S[kind]))
            para = []

    while i < len(lines):
        raw = lines[i]
        line = raw.rstrip()

        # table
        if line.startswith("|") and i + 1 < len(lines) and set(
            lines[i + 1].replace("|", "").replace(" ", "")
        ) <= {"-", ":"}:
            flush()
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not set("".join(cells).replace(" ", "")) <= {"-", ":"}:
                    rows.append(cells)
                i += 1
            story.append(table_block(rows))
            story.append(Spacer(1, 10))
            continue

        if line.startswith("# "):
            flush()
            story.append(Paragraph(inline(line[2:]), S["title"]))
        elif line.startswith("## "):
            flush()
            # One slide per page keeps a slide's words together on camera.
            if not first_slide:
                story.append(PageBreak())
            first_slide = False
            story.append(Paragraph(inline(line[3:]), S["slide"]))
        elif line.startswith("### "):
            flush()
            story.append(Paragraph(inline(line[4:]).upper(), S["h3"]))
        elif line.startswith("**Clock:**"):
            flush()
            story.append(Paragraph(
                inline(line.replace("**Clock:**", "").replace("·", "  ·  ").strip()),
                S["clock"]))
        elif line.startswith("**Say:**"):
            flush()
            body = [line[len("**Say:**"):].strip()]
            i += 1
            while i < len(lines) and lines[i].strip() and not lines[i].startswith("**"):
                body.append(lines[i].strip()); i += 1
            story.append(say_block(" ".join(body)))
            continue
        elif re.match(r"^\*\*\d+\. Do:\*\*", line) or line.startswith("**Do:**"):
            flush()
            body = [line]
            i += 1
            while i < len(lines) and lines[i].strip() and not lines[i].startswith("**"):
                body.append(lines[i].strip()); i += 1
            story.append(Paragraph(inline(" ".join(body)), S["do"]))
            continue
        elif line.startswith(">"):
            # Gather the whole quote. A bare ">" is a paragraph break inside it,
            # not a line of its own - rendering each line separately left the
            # intro block double-spaced with a stray chevron above it.
            flush()
            chunks, current = [], []
            while i < len(lines) and lines[i].startswith(">"):
                stripped = lines[i].lstrip(">").strip()
                if stripped:
                    current.append(stripped)
                elif current:
                    chunks.append(" ".join(current)); current = []
                i += 1
            if current:
                chunks.append(" ".join(current))
            for chunk in chunks:
                story.append(Paragraph(inline(chunk), S["quote"]))
            continue
        elif line.startswith("*") and line.endswith("*") and len(line) > 2 \
                and not line.startswith("**"):
            flush()
            body = [line]
            i += 1
            while i < len(lines) and lines[i].strip():
                body.append(lines[i].strip()); i += 1
            story.append(Paragraph(inline(" ".join(body)), S["note"]))
            continue
        elif line.startswith("- ") or re.match(r"^\d+\. ", line):
            flush()
            txt = re.sub(r"^(- |\d+\. )", "", line)
            story.append(Paragraph("&bull;&nbsp;&nbsp;" + inline(txt),
                                   S["body"]))
        elif line.startswith("---"):
            flush()
        elif not line.strip():
            flush()
        else:
            para.append(line.strip())
        i += 1

    flush()
    return story


def main() -> None:
    if not SRC.exists():
        raise SystemExit(f"{SRC} not found.")

    doc = BaseDocTemplate(
        str(OUT), pagesize=LETTER,
        leftMargin=MARGIN, rightMargin=MARGIN,
        topMargin=MARGIN, bottomMargin=0.85 * inch,
        title="JobHopper - Angel's presentation script",
        author="The Laughing Bots",
    )
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height,
                  id="body", leftPadding=0, rightPadding=0,
                  topPadding=0, bottomPadding=0)

    def furniture(canvas, doc_):
        canvas.saveState()
        canvas.setFont("Helvetica", 8.5)
        canvas.setFillColor(MUTED)
        canvas.drawString(MARGIN, 0.5 * inch,
                          "JobHopper  ·  Angel's script  ·  15:00 hard cap")
        canvas.drawRightString(LETTER[0] - MARGIN, 0.5 * inch, str(doc_.page))
        canvas.setStrokeColor(HAIRLINE)
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN, 0.68 * inch, LETTER[0] - MARGIN, 0.68 * inch)
        canvas.restoreState()

    doc.addPageTemplates([PageTemplate(id="all", frames=[frame],
                                       onPage=furniture)])
    doc.build(build_story(SRC.read_text(encoding="utf-8")))
    print(f"wrote {OUT}  ({OUT.stat().st_size / 1024:.0f} KB)")


if __name__ == "__main__":
    main()
