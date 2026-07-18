"""Premium commercial proposal PDF generator for Independent Projects.

Generates a branded, sales-quality PDF that a representative can share with
their customer as a formal proposal document from Independent Media Network.

Design language mirrors the platform UI:
    - Deep executive navy #0033A0 for accent
    - Ink #0A0A0A for primary type
    - Cream/paper #F9F9F6 for sectional shading
    - Playfair-style serif substitute (Times/Bold) for headlines
    - IBM Plex Mono substitute (Courier) for figures & references

The document is intentionally more than an approval receipt — it opens with a
network introduction, presents the selected inventory / TV project, details
network coverage, states the approved commercial terms, and closes with an
official approval block.
"""
from datetime import datetime
from io import BytesIO
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfgen.canvas import Canvas
from reportlab.platypus import Paragraph, Table, TableStyle

# ---- Palette ------------------------------------------------------------
INK        = colors.HexColor("#0A0A0A")
INK_SOFT   = colors.HexColor("#52525B")
INK_MUTE   = colors.HexColor("#A1A1AA")
PAPER      = colors.HexColor("#F9F9F6")
PAPER_DEEP = colors.HexColor("#EFEEEA")
LINE       = colors.HexColor("#E4E4E1")
NAVY       = colors.HexColor("#0033A0")
GOLD       = colors.HexColor("#B45309")
GREEN      = colors.HexColor("#166534")

PAGE_W, PAGE_H = A4
MARGIN_X = 20 * mm
MARGIN_Y = 22 * mm
CONTENT_W = PAGE_W - 2 * MARGIN_X

# ---- Text styles --------------------------------------------------------
EYEBROW = ParagraphStyle("eyebrow", fontName="Helvetica-Bold", fontSize=8,
                          leading=10, textColor=INK_SOFT, spaceAfter=4)
H1 = ParagraphStyle("h1", fontName="Times-Bold", fontSize=32, leading=36,
                     textColor=INK, spaceAfter=6)
H2 = ParagraphStyle("h2", fontName="Times-Bold", fontSize=18, leading=22,
                     textColor=INK, spaceAfter=6)
H3 = ParagraphStyle("h3", fontName="Times-Bold", fontSize=13, leading=17,
                     textColor=INK, spaceAfter=3)
BODY = ParagraphStyle("body", fontName="Helvetica", fontSize=10, leading=14,
                       textColor=INK, spaceAfter=6)
BODY_SOFT = ParagraphStyle("body_s", parent=BODY, textColor=INK_SOFT)
LABEL = ParagraphStyle("label", fontName="Helvetica-Bold", fontSize=7.5,
                        leading=10, textColor=INK_SOFT, spaceAfter=2)
FIGURE = ParagraphStyle("fig", fontName="Times-Bold", fontSize=22, leading=26,
                         textColor=INK, spaceAfter=2)
MONO = ParagraphStyle("mono", fontName="Courier", fontSize=8.5, leading=11,
                       textColor=INK_SOFT)


# ------------------------------------------------------------------------
# Low-level helpers
# ------------------------------------------------------------------------
def _draw_wordmark(c: Canvas, x: float, y: float):
    """Independent Media Network editorial wordmark."""
    c.setFont("Times-Bold", 11)
    c.setFillColor(INK)
    c.drawString(x, y, "Independent Media Network")
    c.setFont("Helvetica", 7)
    c.setFillColor(INK_SOFT)
    c.drawString(x, y - 10, "COMMERCIAL PROPOSAL · CONFIDENTIAL")


def _draw_header(c: Canvas, proposal_id: str, page_num: int, total: Optional[int] = None):
    _draw_wordmark(c, MARGIN_X, PAGE_H - MARGIN_Y + 8)
    # Right-side proposal ref
    c.setFont("Courier", 7)
    c.setFillColor(INK_SOFT)
    label = f"REF · {proposal_id.upper()}"
    c.drawRightString(PAGE_W - MARGIN_X, PAGE_H - MARGIN_Y + 8, label)
    c.drawRightString(PAGE_W - MARGIN_X, PAGE_H - MARGIN_Y - 2,
                       f"PAGE {page_num:02d}" + (f" / {total:02d}" if total else ""))
    # Divider
    c.setStrokeColor(LINE)
    c.setLineWidth(0.4)
    c.line(MARGIN_X, PAGE_H - MARGIN_Y - 10, PAGE_W - MARGIN_X, PAGE_H - MARGIN_Y - 10)


def _draw_footer(c: Canvas):
    c.setStrokeColor(LINE); c.setLineWidth(0.4)
    c.line(MARGIN_X, MARGIN_Y - 6, PAGE_W - MARGIN_X, MARGIN_Y - 6)
    c.setFont("Helvetica", 7); c.setFillColor(INK_SOFT)
    c.drawString(MARGIN_X, MARGIN_Y - 14, "Independent Media Network · Global publishing & television group")
    c.drawRightString(PAGE_W - MARGIN_X, MARGIN_Y - 14, "www.independentmedianetwork.com")


def _paragraph_height(p: Paragraph, width: float) -> float:
    p.wrapOn(None, width, 10_000)
    return p.height


def _draw_paragraph(c: Canvas, p: Paragraph, x: float, y: float, width: float) -> float:
    """Draw a paragraph anchored to (x, y=top) and return the new y (below)."""
    h = _paragraph_height(p, width)
    p.drawOn(c, x, y - h)
    return y - h


def _draw_eyebrow(c: Canvas, text: str, x: float, y: float, color=INK_SOFT) -> float:
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(color)
    c.drawString(x, y, text.upper())
    return y - 12


def _draw_section_title(c: Canvas, section_num: str, title: str, y: float) -> float:
    c.setFont("Courier", 7); c.setFillColor(NAVY)
    c.drawString(MARGIN_X, y, section_num)
    c.setFont("Times-Bold", 22); c.setFillColor(INK)
    c.drawString(MARGIN_X, y - 22, title)
    # Accent underline
    c.setStrokeColor(NAVY); c.setLineWidth(1)
    c.line(MARGIN_X, y - 30, MARGIN_X + 40, y - 30)
    return y - 46


def _draw_kv(c: Canvas, x: float, y: float, label: str, value: str,
              value_font=("Times-Bold", 12), width: float = 80) -> float:
    c.setFont("Helvetica-Bold", 7); c.setFillColor(INK_SOFT)
    c.drawString(x, y, label.upper())
    c.setFont(*value_font); c.setFillColor(INK)
    c.drawString(x, y - 15, value)
    return y - 30


def _money(n) -> str:
    try:
        return f"${int(round(float(n))):,}"
    except Exception:
        return str(n)


def _fmt_date(iso: str) -> str:
    if not iso:
        return "—"
    try:
        d = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        return d.strftime("%d %B %Y")
    except Exception:
        return str(iso)[:10]


def _fmt_datetime(iso: str) -> str:
    if not iso:
        return "—"
    try:
        d = datetime.fromisoformat(str(iso).replace("Z", "+00:00"))
        return d.strftime("%d %B %Y · %H:%M UTC")
    except Exception:
        return str(iso)


# ------------------------------------------------------------------------
# Sections
# ------------------------------------------------------------------------
INTRO_PARAGRAPHS = [
    ("Independent Media Network is a worldwide publishing and television group "
     "operating across dozens of countries. Its editorial infrastructure combines "
     "national news properties, thematic verticals and Independent TV — an "
     "international video platform producing original documentaries, interview "
     "series and long-form programs."),
    ("This proposal has been prepared exclusively for the client of a licensed "
     "commercial representative of the network. It presents the selected "
     "inventory, the network coverage it will reach and the approved commercial "
     "terms under which the campaign will run."),
]

BANNER_COVERAGE = {
    "global":        "Every country site across every editorial vertical of the Independent Media Network.",
    "tourism":       "Every travel, tourism and destination property in the network — reaching intent-driven leisure and business audiences.",
    "health":        "Every health & wellness property in the network — reaching decision-making readers focused on medical, fitness and lifestyle content.",
    "real_estate":   "Every real-estate property in the network — reaching high-intent buyers, investors and developers.",
    "education":     "Every education & learning property in the network — reaching students, families and academic decision-makers.",
    "economy":       "Every economy & business property in the network — reaching executives, investors and financial professionals.",
    "sports":        "Every sports property in the network — reaching passionate national and international audiences across major disciplines.",
    "technology":    "Every technology property in the network — reaching early adopters, engineers and IT decision-makers.",
    "entertainment": "Every entertainment property in the network — reaching mass-market audiences across film, music, culture and lifestyle.",
}


def _cover_page(c: Canvas, proposal: dict, kind: str):
    """Full-bleed cover page: massive title + proposal reference + subtle branding."""
    # Left column vertical rule
    c.setStrokeColor(NAVY); c.setLineWidth(1.4)
    c.line(MARGIN_X, MARGIN_Y, MARGIN_X, PAGE_H - MARGIN_Y)

    # Top: eyebrow
    top_y = PAGE_H - MARGIN_Y - 4
    c.setFont("Courier", 8); c.setFillColor(NAVY)
    c.drawString(MARGIN_X + 8, top_y, "INDEPENDENT MEDIA NETWORK")
    c.setFont("Helvetica-Bold", 7); c.setFillColor(INK_SOFT)
    c.drawString(MARGIN_X + 8, top_y - 12, "COMMERCIAL PROPOSAL")

    # Center block: kind label + title
    center_y = PAGE_H * 0.60
    c.setFont("Courier", 9); c.setFillColor(GOLD)
    kind_label = "BANNER CAMPAIGN" if kind == "banner" else "TV SPONSORSHIP"
    c.drawString(MARGIN_X + 8, center_y + 56, kind_label)

    title = proposal.get("campaign_name") or proposal.get("proposal_name") or "Commercial Proposal"
    # Wrap title at ~26 chars for large type
    _draw_wrapped_title(c, title, MARGIN_X + 8, center_y, max_width=CONTENT_W - 8)

    # Subtitle: for banner → network · position, for TV → project title
    subtitle = (f"{proposal.get('network_name', '')} · {proposal.get('position_name', '')}"
                if kind == "banner" else proposal.get("tv_project_title", ""))
    c.setFont("Times-Italic", 14); c.setFillColor(INK_SOFT)
    c.drawString(MARGIN_X + 8, center_y - 60, subtitle)

    # Bottom block: prepared for / approved on / reference
    bottom_y = MARGIN_Y + 90
    c.setFont("Helvetica-Bold", 7); c.setFillColor(INK_SOFT)
    c.drawString(MARGIN_X + 8, bottom_y, "PREPARED BY")
    c.setFont("Times-Bold", 12); c.setFillColor(INK)
    c.drawString(MARGIN_X + 8, bottom_y - 16, proposal.get("agency_name") or proposal.get("rep_name") or "Independent Media Network")

    c.setFont("Helvetica-Bold", 7); c.setFillColor(INK_SOFT)
    c.drawString(MARGIN_X + 8, bottom_y - 40, "APPROVED ON")
    c.setFont("Times-Bold", 12); c.setFillColor(INK)
    c.drawString(MARGIN_X + 8, bottom_y - 56, _fmt_date(proposal.get("decided_at") or proposal.get("created_at", "")))

    c.setFont("Courier", 7); c.setFillColor(INK_MUTE)
    c.drawString(MARGIN_X + 8, MARGIN_Y - 4,
                  f"REF · {proposal.get('id', '')[:8].upper()}   ·   "
                  f"GENERATED {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")

    c.showPage()


def _draw_wrapped_title(c: Canvas, text: str, x: float, y: float, max_width: float):
    """Manually wrap a large serif title to avoid Paragraph overflow."""
    c.setFont("Times-Bold", 40); c.setFillColor(INK)
    words = text.split()
    lines = []
    line = ""
    for w in words:
        candidate = (line + " " + w).strip()
        if c.stringWidth(candidate, "Times-Bold", 40) > max_width and line:
            lines.append(line)
            line = w
        else:
            line = candidate
    if line:
        lines.append(line)
    for i, ln in enumerate(lines[:3]):
        c.drawString(x, y - i * 42, ln)


def _section_intro(c: Canvas, y: float) -> float:
    y = _draw_section_title(c, "01 · About", "Independent Media Network", y)
    for text in INTRO_PARAGRAPHS:
        p = Paragraph(text, BODY)
        y = _draw_paragraph(c, p, MARGIN_X, y - 6, CONTENT_W) - 4

    # Stat strip
    y -= 8
    c.setFillColor(PAPER); c.rect(MARGIN_X, y - 60, CONTENT_W, 60, stroke=0, fill=1)
    facts = [
        ("Countries covered",  "40+"),
        ("Editorial verticals", "9"),
        ("Independent TV",     "Original"),
        ("Model",              "Licensed"),
    ]
    col_w = CONTENT_W / len(facts)
    for i, (label, value) in enumerate(facts):
        fx = MARGIN_X + i * col_w + 10
        c.setFont("Helvetica-Bold", 7); c.setFillColor(INK_SOFT)
        c.drawString(fx, y - 22, label.upper())
        c.setFont("Times-Bold", 13); c.setFillColor(INK)
        c.drawString(fx, y - 42, value)
    return y - 76


def _section_banner_inventory(c: Canvas, proposal: dict, y: float) -> float:
    y = _draw_section_title(c, "02 · Inventory", "Selected placement", y)

    # Big inventory card
    c.setFillColor(PAPER); c.rect(MARGIN_X, y - 108, CONTENT_W, 108, stroke=0, fill=1)
    c.setStrokeColor(NAVY); c.setLineWidth(2)
    c.line(MARGIN_X, y - 108, MARGIN_X, y)  # left accent
    inner_x = MARGIN_X + 14
    c.setFont("Helvetica-Bold", 7); c.setFillColor(NAVY)
    c.drawString(inner_x, y - 20, "NETWORK PRODUCT")
    c.setFont("Times-Bold", 20); c.setFillColor(INK)
    c.drawString(inner_x, y - 42, f"{proposal.get('network_name', '')} · {proposal.get('position_name', '')}")

    # Coverage line
    coverage = BANNER_COVERAGE.get(proposal.get("network_key", ""),
                                    "Every property in the selected sub-network.")
    p = Paragraph(coverage, BODY_SOFT)
    _draw_paragraph(c, p, inner_x, y - 58, CONTENT_W - 28)

    y -= 122

    # Flight + impressions row
    row = [
        ("Campaign name",   proposal.get("campaign_name") or "—"),
        ("Client reference", proposal.get("client_reference") or "—"),
        ("Flight window",   f"{_fmt_date(proposal.get('start_date'))} → {_fmt_date(proposal.get('end_date'))}"
                             if proposal.get("end_date") else _fmt_date(proposal.get("start_date"))),
        ("Requested impressions", f"{int(proposal['impressions']):,}" if proposal.get("impressions") else "Negotiated volume"),
    ]
    y = _kv_grid(c, y, row, cols=2)
    return y


def _section_tv_project(c: Canvas, proposal: dict, tv: dict, y: float) -> float:
    y = _draw_section_title(c, "02 · Production", "The Independent TV project", y)

    # Project card
    card_h = 128
    c.setFillColor(PAPER); c.rect(MARGIN_X, y - card_h, CONTENT_W, card_h, stroke=0, fill=1)
    c.setStrokeColor(NAVY); c.setLineWidth(2)
    c.line(MARGIN_X, y - card_h, MARGIN_X, y)
    inner_x = MARGIN_X + 14
    c.setFont("Helvetica-Bold", 7); c.setFillColor(NAVY)
    c.drawString(inner_x, y - 20, "PROJECT")
    c.setFont("Times-Bold", 22); c.setFillColor(INK)
    c.drawString(inner_x, y - 44, tv.get("title", ""))
    if tv.get("tagline"):
        c.setFont("Times-Italic", 12); c.setFillColor(INK_SOFT)
        c.drawString(inner_x, y - 62, tv["tagline"])
    if tv.get("synopsis"):
        p = Paragraph(tv["synopsis"], BODY)
        _draw_paragraph(c, p, inner_x, y - 76, CONTENT_W - 28)
    y -= card_h + 12

    # Details grid
    langs = ", ".join(tv.get("languages") or []) or "—"
    details = [
        ("Total episodes", f"{tv.get('total_episodes', '—')}"),
        ("Target audience", tv.get("target_audience") or "—"),
        ("Distribution", tv.get("distribution") or "Independent TV international platform"),
        ("Languages", langs),
    ]
    y = _kv_grid(c, y, details, cols=2)
    y -= 6

    # Sponsorship rights
    if tv.get("sponsorship_rights"):
        y = _draw_eyebrow(c, "SPONSORSHIP RIGHTS", MARGIN_X, y, color=NAVY)
        p = Paragraph(tv["sponsorship_rights"], BODY)
        y = _draw_paragraph(c, p, MARGIN_X, y, CONTENT_W) - 4

    return y


def _section_tv_selection(c: Canvas, proposal: dict, tv: dict, y: float) -> float:
    y = _draw_section_title(c, "03 · Selection", "Sponsored episodes", y)

    total = tv.get("total_episodes", 0) or 0
    eps = proposal.get("episode_numbers") or []
    y = _draw_kv(c, MARGIN_X, y, "Sponsored episodes",
                  f"{len(eps)} of {total}",
                  value_font=("Times-Bold", 22))
    y -= 6
    # Episode chip grid
    eps_set = set(eps)
    if total > 0:
        chip_w = 22; chip_h = 22; gap = 5
        per_row = int((CONTENT_W + gap) // (chip_w + gap))
        for i in range(1, total + 1):
            idx = i - 1
            row = idx // per_row
            col = idx % per_row
            cx = MARGIN_X + col * (chip_w + gap)
            cy = y - row * (chip_h + gap) - chip_h
            if i in eps_set:
                c.setFillColor(NAVY); c.setStrokeColor(NAVY)
                c.rect(cx, cy, chip_w, chip_h, stroke=1, fill=1)
                c.setFillColor(colors.white); c.setFont("Courier-Bold", 7)
                c.drawCentredString(cx + chip_w / 2, cy + chip_h / 2 - 2.5, f"{i:03d}")
            else:
                c.setFillColor(colors.white); c.setStrokeColor(LINE)
                c.rect(cx, cy, chip_w, chip_h, stroke=1, fill=1)
                c.setFillColor(INK_MUTE); c.setFont("Courier", 7)
                c.drawCentredString(cx + chip_w / 2, cy + chip_h / 2 - 2.5, f"{i:03d}")
        rows_used = (total + per_row - 1) // per_row
        y -= rows_used * (chip_h + gap) + 4

    # Legend
    c.setFont("Helvetica", 7); c.setFillColor(INK_SOFT)
    c.setFillColor(NAVY); c.rect(MARGIN_X, y - 12, 10, 10, stroke=0, fill=1)
    c.setFillColor(INK)
    c.drawString(MARGIN_X + 14, y - 8, "Sponsored under this proposal")
    c.setStrokeColor(LINE); c.setFillColor(colors.white)
    c.rect(MARGIN_X + 200, y - 12, 10, 10, stroke=1, fill=1)
    c.setFillColor(INK)
    c.drawString(MARGIN_X + 214, y - 8, "Not covered by this proposal")
    return y - 22


def _kv_grid(c: Canvas, y: float, items, cols: int = 2) -> float:
    """Draw a labelled grid of key-value pairs."""
    col_w = CONTENT_W / cols
    row_h = 42
    for i, (label, value) in enumerate(items):
        col = i % cols
        row = i // cols
        x = MARGIN_X + col * col_w
        yy = y - row * row_h
        c.setFont("Helvetica-Bold", 7); c.setFillColor(INK_SOFT)
        c.drawString(x, yy - 4, label.upper())
        c.setFont("Times-Bold", 12); c.setFillColor(INK)
        # Truncate very long values to avoid overflow
        val = str(value)
        while c.stringWidth(val, "Times-Bold", 12) > col_w - 12 and len(val) > 8:
            val = val[:-2]
        if val != str(value):
            val = val.rstrip() + "…"
        c.drawString(x, yy - 22, val)
        # separator line under row
        if col == cols - 1 or i == len(items) - 1:
            c.setStrokeColor(LINE); c.setLineWidth(0.4)
            c.line(MARGIN_X, yy - row_h + 8, PAGE_W - MARGIN_X, yy - row_h + 8)
    rows_used = (len(items) + cols - 1) // cols
    return y - rows_used * row_h - 6


def _section_commercials(c: Canvas, proposal: dict, y: float) -> float:
    y = _draw_section_title(c, "04 · Terms", "Approved commercial terms", y)

    # Big amount block
    block_h = 90
    c.setFillColor(INK); c.rect(MARGIN_X, y - block_h, CONTENT_W, block_h, stroke=0, fill=1)
    inner_x = MARGIN_X + 16
    c.setFont("Helvetica-Bold", 7); c.setFillColor(colors.HexColor("#A1A1AA"))
    c.drawString(inner_x, y - 22, "APPROVED PROPOSAL AMOUNT")
    c.setFont("Times-Bold", 40); c.setFillColor(colors.white)
    c.drawString(inner_x, y - 60, _money(proposal.get("offer_amount_usd", 0)) + " USD")
    c.setFont("Helvetica", 8); c.setFillColor(colors.HexColor("#A1A1AA"))
    c.drawString(inner_x, y - 78, "Terms confirmed by Independent Media Network. Payable per representative agreement.")
    y -= block_h + 10

    # Feedback from the network
    fb = proposal.get("representative_feedback") or ""
    if fb:
        y = _draw_eyebrow(c, "NOTE FROM INDEPENDENT MEDIA NETWORK", MARGIN_X, y, color=NAVY)
        p = Paragraph(fb, BODY)
        y = _draw_paragraph(c, p, MARGIN_X, y, CONTENT_W) - 6
    return y


def _section_approval(c: Canvas, proposal: dict, y: float) -> float:
    y = _draw_section_title(c, "05 · Approval", "Official approval", y)

    # Approval card
    card_h = 130
    c.setFillColor(PAPER); c.rect(MARGIN_X, y - card_h, CONTENT_W, card_h, stroke=0, fill=1)
    c.setStrokeColor(GREEN); c.setLineWidth(2)
    c.line(MARGIN_X, y - card_h, MARGIN_X, y)
    inner_x = MARGIN_X + 14

    # Stamp
    c.setStrokeColor(GREEN); c.setLineWidth(1.4)
    c.circle(PAGE_W - MARGIN_X - 55, y - 55, 42, stroke=1, fill=0)
    c.setFont("Times-Bold", 10); c.setFillColor(GREEN)
    c.drawCentredString(PAGE_W - MARGIN_X - 55, y - 46, "APPROVED")
    c.setFont("Helvetica", 6.5); c.setFillColor(GREEN)
    c.drawCentredString(PAGE_W - MARGIN_X - 55, y - 58, "INDEPENDENT MEDIA")
    c.drawCentredString(PAGE_W - MARGIN_X - 55, y - 66, "NETWORK")
    c.setFont("Courier", 6); c.setFillColor(GREEN)
    c.drawCentredString(PAGE_W - MARGIN_X - 55, y - 78, _fmt_date(proposal.get("decided_at") or "")[:11])

    # Text
    approver = _approver_name(proposal)
    c.setFont("Helvetica-Bold", 7); c.setFillColor(INK_SOFT)
    c.drawString(inner_x, y - 20, "APPROVED BY")
    c.setFont("Times-Bold", 15); c.setFillColor(INK)
    c.drawString(inner_x, y - 40, approver)

    c.setFont("Helvetica-Bold", 7); c.setFillColor(INK_SOFT)
    c.drawString(inner_x, y - 62, "DATE OF DECISION")
    c.setFont("Times-Bold", 12); c.setFillColor(INK)
    c.drawString(inner_x, y - 78, _fmt_datetime(proposal.get("decided_at", "")))

    c.setFont("Helvetica-Bold", 7); c.setFillColor(INK_SOFT)
    c.drawString(inner_x, y - 100, "PROPOSAL REFERENCE")
    c.setFont("Courier-Bold", 11); c.setFillColor(INK)
    c.drawString(inner_x, y - 116, proposal.get("id", "")[:24].upper())

    return y - card_h - 10


def _approver_name(proposal: dict) -> str:
    hist = proposal.get("history") or []
    for h in reversed(hist):
        if h.get("status") == "approved":
            return h.get("actor_name") or "Independent Media Network"
    return "Independent Media Network"


# ------------------------------------------------------------------------
# Public API
# ------------------------------------------------------------------------
def generate_proposal_pdf(proposal: dict, tv_project: Optional[dict] = None) -> bytes:
    """Generate a full commercial proposal PDF.

    `proposal.kind` decides the layout: 'banner' or 'sponsorship'. For
    sponsorships a `tv_project` dict must be supplied.
    """
    buf = BytesIO()
    c = Canvas(buf, pagesize=A4, pageCompression=1)
    kind = proposal.get("kind") or ("sponsorship" if proposal.get("tv_project_id") else "banner")

    # --- Cover page ---
    _cover_page(c, proposal, kind)

    # Track pages for header numbering (we'll re-render header after each page)
    # Page 2 — Intro
    _draw_header(c, proposal.get("id", ""), 2)
    y = PAGE_H - MARGIN_Y - 20
    y = _section_intro(c, y)
    _draw_footer(c)
    c.showPage()

    # Page 3 — Inventory / TV Project
    _draw_header(c, proposal.get("id", ""), 3)
    y = PAGE_H - MARGIN_Y - 20
    if kind == "banner":
        y = _section_banner_inventory(c, proposal, y)
    else:
        y = _section_tv_project(c, proposal, tv_project or {}, y)
    _draw_footer(c)
    c.showPage()

    # Page 4 — For TV, episode selection; for banner, commercial terms
    _draw_header(c, proposal.get("id", ""), 4)
    y = PAGE_H - MARGIN_Y - 20
    if kind == "banner":
        y = _section_commercials(c, proposal, y)
        y -= 10
        y = _section_approval(c, proposal, y)
    else:
        y = _section_tv_selection(c, proposal, tv_project or {}, y)
    _draw_footer(c)
    c.showPage()

    # Page 5 — TV only: commercials + approval
    if kind != "banner":
        _draw_header(c, proposal.get("id", ""), 5)
        y = PAGE_H - MARGIN_Y - 20
        y = _section_commercials(c, proposal, y)
        y -= 10
        y = _section_approval(c, proposal, y)
        _draw_footer(c)
        c.showPage()

    c.save()
    return buf.getvalue()
