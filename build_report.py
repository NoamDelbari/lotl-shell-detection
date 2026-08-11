"""
build_report.py  —  assemble report/*.md files into Group_10_Report.docx
Run:  python build_report.py
"""
from __future__ import annotations
import re
from pathlib import Path
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_LINE_SPACING, WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

ROOT = Path(__file__).resolve().parent
REPORT = ROOT / "report"
OUT = ROOT / "Group_10_Report.docx"

# ── file list (order = final document order) ──────────────────────────────── #
FILES = [
    ("exec_summary.md",                    None),           # no chapter break before first

    ("ch1_threat_mapping.md",              "CHAPTER BREAK"),
    ("ch1_1_threat_analysis.md",           None),
    ("ch1_2_mapping_rows_noam.md",         None),
    ("ch1_3_feature_rationale.md",         None),

    ("ch2_literature_review.md",           "CHAPTER BREAK"),
    ("ch2_1_shellcore_extraction.md",      None),
    ("ch2_2_adopt_modify_reject.md",       None),
    ("ch2_3_comparative_contribution_noam.md", None),

    ("ch3_eda_findings.md",                "CHAPTER BREAK"),
    ("ch3_d2_eda_findings.md",             None),

    ("ch4_ranking_findings.md",            "CHAPTER BREAK"),

    ("ch5_1_unified_schema.md",            "CHAPTER BREAK"),
    ("ch5_2_distribution_shift.md",        None),
    ("ch5_3_scaling_normalisation.md",     None),

    ("ch6_model_justification.md",         "CHAPTER BREAK"),
    ("ch6_rf_if_justification.md",         None),

    ("ch7_sensitivity_findings.md",        "CHAPTER BREAK"),
    ("ch7_rf_if_sensitivity_findings.md",  None),

    ("ch8_1_error_forensics_ben.md",       "CHAPTER BREAK"),
    ("ch8_1_rf_if_forensics.md",           None),
    ("ch8_2_cross_dataset_table.md",       None),
    ("ch8_3_tops_comparison.md",           None),
    ("ch8_3_shellcore_comparison.md",      None),
    ("ch8_4_cascade_analysis.md",          None),

    ("bonus_b3_findings.md",               "CHAPTER BREAK"),
]

# ── docx helpers ──────────────────────────────────────────────────────────── #
def set_spacing(para, space_before=0, space_after=6, line_spacing=1.5):
    pf = para.paragraph_format
    pf.space_before = Pt(space_before)
    pf.space_after  = Pt(space_after)
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    pf.line_spacing = line_spacing


def add_run_with_fmt(para, text: str):
    """Parse **bold**, *italic*, `code` and add runs to para."""
    pattern = re.compile(r'(\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`)')
    last = 0
    for m in pattern.finditer(text):
        if m.start() > last:
            para.add_run(text[last:m.start()])
        raw = m.group(0)
        if raw.startswith("**"):
            r = para.add_run(m.group(2))
            r.bold = True
        elif raw.startswith("*"):
            r = para.add_run(m.group(3))
            r.italic = True
        else:  # backtick code
            r = para.add_run(m.group(4))
            r.font.name = "Courier New"
            r.font.size = Pt(9)
        last = m.end()
    if last < len(text):
        para.add_run(text[last:])


def add_heading(doc: Document, text: str, level: int):
    style = {1: "Heading 1", 2: "Heading 2", 3: "Heading 3", 4: "Heading 4"}.get(level, "Heading 4")
    p = doc.add_heading(text, level=level)
    set_spacing(p, space_before=10 if level == 1 else 6, space_after=4, line_spacing=1.15)
    return p


def add_para(doc: Document, text: str, style: str = "Normal"):
    p = doc.add_paragraph(style=style)
    add_run_with_fmt(p, text)
    set_spacing(p)
    return p


def add_code_block(doc: Document, lines: list[str]):
    text = "\n".join(lines)
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.font.name = "Courier New"
    r.font.size = Pt(8)
    pf = p.paragraph_format
    pf.space_before = Pt(4)
    pf.space_after  = Pt(4)
    # light grey shading
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), "F2F2F2")
    p._p.get_or_add_pPr().append(shd)


def add_blockquote(doc: Document, text: str):
    p = doc.add_paragraph()
    add_run_with_fmt(p, text)
    pf = p.paragraph_format
    pf.left_indent = Inches(0.3)
    pf.space_before = Pt(2)
    pf.space_after  = Pt(2)
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    pf.line_spacing = 1.5
    # italic style for blockquote
    for run in p.runs:
        run.italic = True


def add_list_item(doc: Document, text: str, level: int = 0):
    p = doc.add_paragraph(style="List Bullet")
    add_run_with_fmt(p, text)
    p.paragraph_format.left_indent = Inches(0.25 + level * 0.2)
    p.paragraph_format.space_before = Pt(1)
    p.paragraph_format.space_after  = Pt(1)
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    p.paragraph_format.line_spacing = 1.5


def add_table(doc: Document, rows: list[list[str]]):
    if not rows:
        return
    # first row is header, second is separator (skip), rest are data
    data_rows = [r for r in rows if not all(re.match(r"^[-: ]+$", c) for c in r)]
    if not data_rows:
        return
    ncols = max(len(r) for r in data_rows)
    tbl = doc.add_table(rows=len(data_rows), cols=ncols)
    tbl.style = "Table Grid"
    for ri, row in enumerate(data_rows):
        for ci, cell_text in enumerate(row):
            if ci >= ncols:
                break
            cell = tbl.cell(ri, ci)
            cell.text = ""
            p = cell.paragraphs[0]
            add_run_with_fmt(p, cell_text.strip())
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after  = Pt(1)
            # header row bold
            if ri == 0:
                for run in p.runs:
                    run.bold = True
    # small font for tables
    for row in tbl.rows:
        for cell in row.cells:
            for p in cell.paragraphs:
                for run in p.runs:
                    run.font.size = Pt(8.5)
    doc.add_paragraph()   # breathing room after table


def add_page_break(doc: Document):
    p = doc.add_paragraph()
    r = p.add_run()
    r.add_break(docx.oxml.ns.qn and __import__("docx").enum.text.WD_BREAK.PAGE or None)
    # simpler approach:
    from docx.oxml import OxmlElement
    br = OxmlElement("w:br")
    br.set(qn("w:type"), "page")
    p._p.append(br)


def parse_table_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    return [c for c in line.split("|")]


# ── markdown → docx ──────────────────────────────────────────────────────── #
def render_md(doc: Document, md_text: str):
    lines = md_text.split("\n")
    i = 0
    table_rows: list[list[str]] = []
    code_lines: list[str] = []
    in_code = False
    code_lang = ""

    def flush_table():
        nonlocal table_rows
        if table_rows:
            add_table(doc, table_rows)
            table_rows = []

    def flush_code():
        nonlocal code_lines, in_code
        if code_lines:
            add_code_block(doc, code_lines)
            code_lines = []
        in_code = False

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # ── code fence ─────────────────────────────────────────────────── #
        if stripped.startswith("```"):
            if not in_code:
                flush_table()
                in_code = True
                code_lang = stripped[3:].strip()
                i += 1
                continue
            else:
                flush_code()
                i += 1
                continue

        if in_code:
            code_lines.append(line)
            i += 1
            continue

        # ── table row ──────────────────────────────────────────────────── #
        if stripped.startswith("|"):
            table_rows.append(parse_table_row(stripped))
            i += 1
            continue
        else:
            flush_table()

        # ── heading ────────────────────────────────────────────────────── #
        hm = re.match(r"^(#{1,4})\s+(.*)", stripped)
        if hm:
            level = len(hm.group(1))
            text = hm.group(2)
            add_heading(doc, text, level)
            i += 1
            continue

        # ── horizontal rule ────────────────────────────────────────────── #
        if re.match(r"^---+\s*$", stripped) or re.match(r"^\*\*\*+\s*$", stripped):
            p = doc.add_paragraph()
            p.paragraph_format.space_before = Pt(4)
            p.paragraph_format.space_after  = Pt(4)
            i += 1
            continue

        # ── blockquote ─────────────────────────────────────────────────── #
        if stripped.startswith("> "):
            add_blockquote(doc, stripped[2:])
            i += 1
            continue

        # ── list item ──────────────────────────────────────────────────── #
        lm = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)", line)
        if lm:
            level = len(lm.group(1)) // 2
            add_list_item(doc, lm.group(3), level)
            i += 1
            continue

        # ── blank line ─────────────────────────────────────────────────── #
        if not stripped:
            i += 1
            continue

        # ── normal paragraph ───────────────────────────────────────────── #
        add_para(doc, stripped)
        i += 1

    flush_table()
    if in_code:
        flush_code()


# ── document setup ───────────────────────────────────────────────────────── #
def setup_doc() -> Document:
    doc = Document()
    # page margins — 1 inch all sides
    for section in doc.sections:
        section.top_margin    = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin   = Inches(1.1)
        section.right_margin  = Inches(1.1)
    # default body font
    style = doc.styles["Normal"]
    font  = style.font
    font.name = "Calibri"
    font.size = Pt(10.5)
    # heading styles
    for lvl, sz, bold in [(1, 14, True), (2, 12, True), (3, 11, True), (4, 10.5, True)]:
        hs = doc.styles[f"Heading {lvl}"]
        hs.font.size = Pt(sz)
        hs.font.bold = bold
        hs.font.name = "Calibri"
        hs.font.color.rgb = RGBColor(0x1F, 0x3B, 0x4D)
    return doc


# ── title page ───────────────────────────────────────────────────────────── #
def add_title_page(doc: Document):
    doc.add_paragraph()
    doc.add_paragraph()
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = title.add_run("LotL Shell Attack Detection\nBinary Classifier")
    r.font.size = Pt(20)
    r.font.bold = True
    r.font.name = "Calibri"
    set_spacing(title, space_before=48, space_after=12, line_spacing=1.3)

    sub = doc.add_paragraph()
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r2 = sub.add_run("MITRE ATT&CK T1059.004 | Course 3917\nReichman University — Final Project")
    r2.font.size = Pt(12)
    r2.font.name = "Calibri"
    set_spacing(sub, space_before=6, space_after=6)

    meta = doc.add_paragraph()
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r3 = meta.add_run("Group 10  |  Ben Volovelsky & Noam Delbari  |  August 2026")
    r3.font.size = Pt(11)
    r3.font.name = "Calibri"
    set_spacing(meta, space_before=24, space_after=0)

    # page break after title
    pb = doc.add_paragraph()
    from docx.oxml import OxmlElement
    br = OxmlElement("w:br")
    br.set(qn("w:type"), "page")
    pb._p.append(br)


# ── main ─────────────────────────────────────────────────────────────────── #
def main():
    doc = setup_doc()
    add_title_page(doc)

    first = True
    for filename, break_type in FILES:
        path = REPORT / filename
        if not path.exists():
            print(f"  SKIP (not found): {filename}")
            continue

        if break_type == "CHAPTER BREAK" and not first:
            pb = doc.add_paragraph()
            from docx.oxml import OxmlElement
            br = OxmlElement("w:br")
            br.set(qn("w:type"), "page")
            pb._p.append(br)

        text = path.read_text(encoding="utf-8")
        render_md(doc, text)
        print(f"  OK: {filename}")
        first = False

    doc.save(OUT)
    print(f"\nSaved: {OUT}")


if __name__ == "__main__":
    import docx  # noqa: ensure import for helpers above
    main()
