"""ＡＵＲＯＲＡ design-doc PDF builder — light/serif journal style.

Visual identity: white background, deep-green primary + gold accent,
serif body, minimal tables, thin section dividers. Deliberately different
from the SnowFold (dark navy + dark code blocks) report.
"""
from __future__ import annotations
import re
import sys
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm, mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, Image, KeepTogether, NextPageTemplate, PageBreak,
    PageTemplate, Paragraph, Spacer, Table, TableStyle,
)

# ---------- Palette (light journal) ----------
TEAL_DEEP   = HexColor('#17322b')   # primary heading color
TEAL_MID    = HexColor('#1f5c4d')   # secondary
TEAL_LIGHT  = HexColor('#d8e8e1')   # table header tint
GOLD        = HexColor('#c8961f')   # accent
GOLD_SOFT   = HexColor('#e6c873')   # softer accent
INK         = HexColor('#1a1a1a')   # body text
MUTED       = HexColor('#5b6b64')   # captions
RULE        = HexColor('#cfd9d3')   # hairline rules
PAGE_BG     = HexColor('#fafaf6')   # warm paper white
CODE_BG     = HexColor('#f3f1ea')   # warm code block bg
CODE_BORDER = HexColor('#d6d2c4')   # code block border
QUOTE_BAR   = HexColor('#c8961f')   # left rule of pull quote

# ---------- Page geometry (A4, generous margins for journal feel) ----------
PAGE_W, PAGE_H = A4
MARGIN_X = 22 * mm
MARGIN_TOP = 22 * mm
MARGIN_BOTTOM = 22 * mm

# ---------- Fonts ----------
CJK_REG = 'CJKSans'
CJK_BOLD = 'CJKSans-Bold'
CJK_ITALIC = 'CJKSans-Italic'
CJK_BOLDITALIC = 'CJKSans-BoldItalic'
SERIF_REG = 'CJKSans'        # use CJK sans for both CJK + ASCII to keep weights consistent
SERIF_BOLD = 'CJKSans-Bold'
MONO = 'CJKSans'             # keep mono=base so it doesn't break on missing font

def _try_register_cjk():
    """Register any CJK-capable font found on the system. Fall back to Helvetica."""
    candidates = [
        ('CJKSans', r'C:\Windows\Fonts\msyh.ttc'),
        ('CJKSans', r'C:\Windows\Fonts\msyh.ttf'),
        ('CJKSans', r'C:\Windows\Fonts\simhei.ttf'),
        ('CJKSans', r'C:\Windows\Fonts\simsun.ttc'),
        ('CJKSans-Bold', r'C:\Windows\Fonts\msyhbd.ttc'),
        ('CJKSans-Bold', r'C:\Windows\Fonts\simhei.ttf'),
        ('CJKSans-Italic', r'C:\Windows\Fonts\msyhl.ttc'),
        ('CJKSans-BoldItalic', r'C:\Windows\Fonts\msyhbd.ttc'),
    ]
    seen = set()
    for name, path in candidates:
        if name in seen:
            continue
        if Path(path).exists():
            try:
                pdfmetrics.registerFont(TTFont(name, path))
                seen.add(name)
            except Exception:
                pass

_try_register_cjk()


# ---------- Styles ----------
H1 = ParagraphStyle('H1', fontName=CJK_BOLD, fontSize=22, leading=28,
                    textColor=TEAL_DEEP, spaceBefore=8, spaceAfter=8,
                    alignment=TA_LEFT)
H2 = ParagraphStyle('H2', fontName=CJK_BOLD, fontSize=15, leading=20,
                    textColor=TEAL_DEEP, spaceBefore=18, spaceAfter=6,
                    alignment=TA_LEFT)
H3 = ParagraphStyle('H3', fontName=CJK_BOLD, fontSize=12, leading=16,
                    textColor=TEAL_MID, spaceBefore=12, spaceAfter=4,
                    alignment=TA_LEFT)
BODY = ParagraphStyle('Body', fontName=CJK_REG, fontSize=10.5, leading=16,
                      textColor=INK, alignment=TA_LEFT,
                      spaceBefore=2, spaceAfter=6)
BODY_TIGHT = ParagraphStyle('BodyTight', parent=BODY, spaceAfter=2, leading=15)
LEAD = ParagraphStyle('Lead', parent=BODY, fontSize=12, leading=20,
                      textColor=TEAL_MID, fontName=CJK_BOLD, alignment=TA_LEFT)
SMALL = ParagraphStyle('Small', parent=BODY, fontSize=9, leading=13,
                       textColor=MUTED)
CAPTION = ParagraphStyle('Caption', parent=BODY, fontSize=9.5, leading=13.5,
                         textColor=MUTED, fontName=CJK_REG, alignment=TA_CENTER,
                         spaceBefore=4, spaceAfter=14)
PULLQ = ParagraphStyle('PullQ', parent=BODY, fontSize=12.5, leading=19,
                       textColor=TEAL_DEEP, fontName=CJK_BOLD, leftIndent=10,
                       rightIndent=10, alignment=TA_LEFT)
KBD = ParagraphStyle('Kbd', fontName=MONO, fontSize=8.6, leading=12,
                     textColor=INK, leftIndent=0, rightIndent=0,
                     alignment=TA_LEFT, spaceBefore=2, spaceAfter=4)


# ---------- Helpers ----------

def _esc(s: str) -> str:
    """Escape for reportlab Paragraph (limited XML subset)."""
    return (s.replace('&', '&amp;')
             .replace('<', '&lt;')
             .replace('>', '&gt;'))


def _inline_md(s: str) -> str:
    """Minimal inline markdown: **bold**, *italic*, `code`."""
    s = _esc(s)
    s = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', s)
    s = re.sub(r'\*([^*]+)\*',     r'<i>\1</i>', s)
    s = re.sub(r'`([^`]+)`',       r'<font face="Helvetica" color="#17322b">\1</font>', s)
    return s


def hr_line(color=RULE, thickness=0.4):
    t = Table([['']], colWidths=[PAGE_W - 2 * MARGIN_X])
    t.setStyle(TableStyle([('LINEBELOW', (0, 0), (-1, -1), thickness, color)]))
    return t


def h1(text):  return Paragraph(_inline_md(text), H1)
def h2(text):  return Paragraph(_inline_md(text), H2)
def h3(text):  return Paragraph(_inline_md(text), H3)
def p(text, style=BODY): return Paragraph(_inline_md(text), style)
def small(text): return Paragraph(_inline_md(text), SMALL)
def caption(text): return Paragraph(_inline_md(text), CAPTION)
def lead(text): return Paragraph(_inline_md(text), LEAD)


def _cell(text, bold=False, size=9.5, color=None):
    """Wrap a cell string in a Paragraph so it auto-wraps within the column width."""
    color = color or INK
    weight = '<b>' if bold else ''
    weight_end = '</b>' if bold else ''
    return Paragraph(f'{weight}{_inline_md(str(text))}{weight_end}',
                     ParagraphStyle('cell', fontName=CJK_REG, fontSize=size,
                                    textColor=color, leading=size + 4,
                                    alignment=TA_LEFT, spaceBefore=0, spaceAfter=0))


def make_table(headers, rows, col_widths=None, header_bg=TEAL_LIGHT,
               header_color=TEAL_DEEP, stripe=True, full_width=True):
    """Light-style table: tinted header, hairline borders, optional zebra rows.
    Cell content is wrapped in Paragraphs so long Chinese strings auto-wrap
    inside the column instead of overflowing."""
    if full_width:
        avail = PAGE_W - 2 * MARGIN_X
        if col_widths is None:
            col_widths = [avail / len(headers)] * len(headers)
    head_row = [_cell(h, bold=True, size=10, color=header_color) for h in headers]
    body_rows = [[_cell(c, size=9.5) for c in row] for row in rows]
    data = [head_row] + body_rows
    t = Table(data, colWidths=col_widths, repeatRows=1)
    style = [
        ('BACKGROUND', (0, 0), (-1, 0), header_bg),
        ('VALIGN',     (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING',  (0, 0), (-1, -1), 7),
        ('RIGHTPADDING', (0, 0), (-1, -1), 7),
        ('TOPPADDING',   (0, 0), (-1, 0), 7),
        ('BOTTOMPADDING',(0, 0), (-1, 0), 7),
        ('TOPPADDING',   (0, 1), (-1, -1), 5),
        ('BOTTOMPADDING',(0, 1), (-1, -1), 5),
        ('LINEBELOW', (0, 0), (-1, 0), 0.7, TEAL_DEEP),
        ('LINEBELOW', (0, -1), (-1, -1), 0.4, RULE),
        ('LINEBEFORE', (0, 0), (0, -1), 0, colors.white),
        ('LINEAFTER',  (-1, 0), (-1, -1), 0, colors.white),
    ]
    if stripe:
        for i in range(1, len(data)):
            if i % 2 == 0:
                style.append(('BACKGROUND', (0, i), (-1, i), HexColor('#f6f3ea')))
    t.setStyle(TableStyle(style))
    return t


def make_codeblock(text, language='text'):
    """Light, paper-style code block. Quiet background, CJK-safe font (Helvetica
    falls back to tofu for non-ASCII)."""
    text = text.rstrip('\n')
    body = _esc(text).replace('\n', '<br/>')
    para = Paragraph(
        f'<font size="8.5" color="#2a2a2a">{body}</font>',
        ParagraphStyle('codebody', fontName=CJK_REG, fontSize=8.5, leading=12,
                       textColor=HexColor('#2a2a2a'), alignment=TA_LEFT,
                       spaceBefore=0, spaceAfter=0))
    inner = Table([[para]], colWidths=[PAGE_W - 2 * MARGIN_X - 14])
    inner.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), CODE_BG),
        ('LEFTPADDING',  (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING',   (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 7),
        ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
        ('BOX',          (0, 0), (-1, -1), 0.5, CODE_BORDER),
        ('LINEBEFORE',   (0, 0), (0, -1), 2.0, GOLD),
    ]))
    return inner


def make_pullquote(text):
    body = _inline_md(text)
    para = Paragraph(body, PULLQ)
    inner = Table([[para]], colWidths=[PAGE_W - 2 * MARGIN_X - 16])
    inner.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HexColor('#f7f3e6')),
        ('LEFTPADDING',  (0, 0), (-1, -1), 14),
        ('RIGHTPADDING', (0, 0), (-1, -1), 14),
        ('TOPPADDING',   (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING',(0, 0), (-1, -1), 10),
        ('VALIGN',       (0, 0), (-1, -1), 'MIDDLE'),
        ('LINEBEFORE',   (0, 0), (0, -1), 3.0, QUOTE_BAR),
    ]))
    return inner


def make_image(path, caption_text=None, width_ratio=0.95, align='center'):
    """Image with optional caption. Sized to page width by ratio."""
    avail_w = PAGE_W - 2 * MARGIN_X
    img = Image(str(path))
    iw, ih = img.imageWidth, img.imageHeight
    target_w = avail_w * width_ratio
    scale = target_w / iw
    img.drawWidth = target_w
    img.drawHeight = ih * scale
    img.hAlign = align.upper()
    elements = [img]
    if caption_text:
        elements.append(Spacer(1, 3))
        elements.append(caption(caption_text))
    return elements


def callout(title, body, color=TEAL_MID):
    """Subtle callout box — like a journal side-note."""
    title_para = Paragraph(f'<b>{_esc(title)}</b>', ParagraphStyle('cT',
                            fontName=CJK_BOLD, fontSize=10.5, leading=14,
                            textColor=color))
    body_para = Paragraph(_inline_md(body), ParagraphStyle('cB',
                           fontName=CJK_REG, fontSize=9.5, leading=14,
                           textColor=INK, alignment=TA_LEFT))
    inner = Table([[title_para], [body_para]], colWidths=[PAGE_W - 2 * MARGIN_X - 18])
    inner.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HexColor('#f0f5f1')),
        ('LEFTPADDING',  (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING',   (0, 0), (-1, 0), 8),
        ('BOTTOMPADDING',(0, 0), (-1, 0), 2),
        ('TOPPADDING',   (0, 1), (-1, 1), 4),
        ('BOTTOMPADDING',(0, 1), (-1, 1), 8),
        ('VALIGN',       (0, 0), (-1, -1), 'TOP'),
        ('LINEBEFORE',   (0, 0), (0, -1), 2.5, TEAL_MID),
    ]))
    return inner


# ---------- Page templates ----------

def cover_page(canvas, doc):
    """Minimal cover: thin teal band on top, big title, gold rule, key stat."""
    canvas.saveState()
    # Top band
    canvas.setFillColor(TEAL_DEEP)
    canvas.rect(0, PAGE_H - 8 * mm, PAGE_W, 8 * mm, stroke=0, fill=1)
    canvas.setFillColor(GOLD)
    canvas.rect(0, PAGE_H - 9 * mm, PAGE_W, 1 * mm, stroke=0, fill=1)
    # Bottom band
    canvas.setFillColor(TEAL_DEEP)
    canvas.rect(0, 0, PAGE_W, 6 * mm, stroke=0, fill=1)
    # Footer text
    canvas.setFillColor(HexColor('#ffffff'))
    canvas.setFont(CJK_REG, 8)
    canvas.drawString(MARGIN_X, 2 * mm, 'ＡＵＲＯＲＡ GFP Design 2026  ·  参赛设计文档')
    canvas.drawRightString(PAGE_W - MARGIN_X, 2 * mm, 'Competition Design Document')
    canvas.restoreState()


def body_page(canvas, doc):
    """Standard body page: warm paper bg, page number, running header."""
    canvas.saveState()
    canvas.setFillColor(PAGE_BG)
    canvas.rect(0, 0, PAGE_W, PAGE_H, stroke=0, fill=1)
    # Top hairline rule
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.4)
    canvas.line(MARGIN_X, PAGE_H - 14 * mm, PAGE_W - MARGIN_X, PAGE_H - 14 * mm)
    # Running header
    canvas.setFillColor(MUTED)
    canvas.setFont(CJK_REG, 8.5)
    canvas.drawString(MARGIN_X, PAGE_H - 12 * mm, 'ＡＵＲＯＲＡ GFP Design 2026')
    canvas.drawRightString(PAGE_W - MARGIN_X, PAGE_H - 12 * mm, '参赛设计文档 · Competition Report')
    # Page number
    canvas.setFillColor(TEAL_DEEP)
    canvas.setFont(CJK_BOLD, 8.5)
    canvas.drawCentredString(PAGE_W / 2, 10 * mm, f'— {doc.page} —')
    # Bottom rule
    canvas.setStrokeColor(RULE)
    canvas.setLineWidth(0.4)
    canvas.line(MARGIN_X, 14 * mm, PAGE_W - MARGIN_X, 14 * mm)
    canvas.restoreState()


# ---------- Markdown parser (intentionally small) ----------

def parse(md_path):
    """Parse the markdown into flowables. Supports:
       - `#`, `##`, `###` headings
       - paragraphs
       - `![alt](path)` images
       - ` ``` ` fenced code blocks
       - markdown tables (`| col | col |`)
       - blockquote (`> ...`)
       - horizontal rule (`---`)
       - bullet list (`- item` or `* item`)
    """
    text = Path(md_path).read_text(encoding='utf-8')
    base = Path(md_path).parent
    lines = text.splitlines()

    out = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        stripped = ln.strip()

        # blank
        if not stripped:
            i += 1
            continue

        # horizontal rule
        if stripped == '---':
            out.append(Spacer(1, 6))
            out.append(hr_line())
            out.append(Spacer(1, 6))
            i += 1
            continue

        # heading
        m = re.match(r'^(#{1,3})\s+(.*)$', stripped)
        if m:
            level, txt = m.group(1), m.group(2)
            if level == '#':   out.append(Spacer(1, 4))
            if level == '##':
                out.append(Spacer(1, 4))
                out.append(hr_line(GOLD, 0.6))
            if   level == '#':  out.append(h1(txt))
            elif level == '##': out.append(h2(txt))
            else:               out.append(h3(txt))
            i += 1
            continue

        # fenced code block
        if stripped.startswith('```'):
            lang = stripped[3:].strip() or 'text'
            i += 1
            buf = []
            while i < len(lines) and not lines[i].strip().startswith('```'):
                buf.append(lines[i])
                i += 1
            i += 1  # skip closing fence
            out.append(Spacer(1, 4))
            out.append(make_codeblock('\n'.join(buf), lang))
            out.append(Spacer(1, 4))
            continue

        # image (single-line)
        m = re.match(r'^!\[([^\]]*)\]\(([^)]+)\)\s*$', stripped)
        if m:
            alt, path = m.group(1), m.group(2)
            full = (base / path).resolve()
            out.append(Spacer(1, 4))
            out.extend(make_image(full, alt))
            i += 1
            continue

        # table — detect contiguous `|` rows
        if stripped.startswith('|') and i + 1 < len(lines) and re.match(r'^\|[\s|:-]+\|\s*$', lines[i + 1].strip()):
            tbl = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                tbl.append(lines[i])
                i += 1
            headers = [c.strip() for c in tbl[0].strip('|').split('|')]
            rows = []
            for row in tbl[2:]:
                cells = [c.strip() for c in row.strip('|').split('|')]
                rows.append(cells)
            out.append(Spacer(1, 4))
            out.append(make_table(headers, rows))
            out.append(Spacer(1, 6))
            continue

        # blockquote (lines starting with '> ')
        if stripped.startswith('> '):
            qbuf = []
            while i < len(lines) and lines[i].strip().startswith('>'):
                qbuf.append(lines[i].strip()[1:].strip())
                i += 1
            out.append(Spacer(1, 6))
            out.append(make_pullquote(' '.join(qbuf)))
            out.append(Spacer(1, 6))
            continue

        # bullet list
        if re.match(r'^[-*]\s+', stripped):
            items = []
            while i < len(lines) and re.match(r'^\s*[-*]\s+', lines[i]):
                items.append(re.sub(r'^\s*[-*]\s+', '', lines[i]))
                i += 1
            for it in items:
                out.append(Paragraph('•  ' + _inline_md(it),
                                     ParagraphStyle('li', parent=BODY,
                                                    leftIndent=14,
                                                    bulletIndent=2,
                                                    alignment=TA_LEFT)))
            out.append(Spacer(1, 4))
            continue

        # paragraph (gather contiguous non-empty, non-special lines)
        buf = [stripped]
        i += 1
        while i < len(lines):
            nxt = lines[i].strip()
            if (not nxt) or nxt.startswith('#') or nxt.startswith('```') \
               or nxt.startswith('![') or nxt.startswith('|') \
               or nxt.startswith('> ') or nxt == '---' \
               or re.match(r'^[-*]\s+', nxt) \
               or re.match(r'^!\[([^\]]*)\]\(([^)]+)\)\s*$', nxt):
                break
            buf.append(nxt)
            i += 1
        out.append(p(' '.join(buf), BODY))
        out.append(Spacer(1, 2))

    return out


# ---------- Main ----------

def build(md_path, pdf_path):
    flowables = parse(md_path)
    doc = BaseDocTemplate(
        str(pdf_path), pagesize=A4,
        leftMargin=MARGIN_X, rightMargin=MARGIN_X,
        topMargin=MARGIN_TOP, bottomMargin=MARGIN_BOTTOM,
        title='ＡＵＲＯＲＡ GFP Design 2026 — Competition Report',
        author='ＡＵＲＯＲＡ Team',
    )
    frame = Frame(MARGIN_X, MARGIN_BOTTOM,
                  PAGE_W - 2 * MARGIN_X,
                  PAGE_H - MARGIN_TOP - MARGIN_BOTTOM,
                  id='body', showBoundary=0)
    cover_frame = Frame(MARGIN_X, MARGIN_BOTTOM,
                        PAGE_W - 2 * MARGIN_X,
                        PAGE_H - MARGIN_TOP - MARGIN_BOTTOM,
                        id='cover', showBoundary=0)
    doc.addPageTemplates([
        PageTemplate(id='cover', frames=[cover_frame], onPage=cover_page),
        PageTemplate(id='body',  frames=[frame],      onPage=body_page),
    ])
    story = [NextPageTemplate('body')]
    story.extend(flowables)
    doc.build(story)


if __name__ == '__main__':
    md = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / 'biofluor_report.md'
    out = md.with_suffix('.pdf')
    build(md, out)
    print(f'PDF written: {out}')