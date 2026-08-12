"""
build_report.py  —  Group 10 final report (15-page body + 5-page appendix)
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

ROOT   = Path(__file__).resolve().parent
REPORT = ROOT / "report"
OUT    = ROOT / "Group_10_Report.docx"

# each entry: (filename, page_break_before, stop_before_heading)
# stop_before: stop rendering the file when a line starting with this text is hit

BODY_FILES = [
    ("exec_summary.md",              None,    None),
    ("ch1_threat_mapping.md",        "PAGE",  None),
    ("ch1_2_mapping_rows_noam.md",   None,    "### Row N3"),
    ("ch2_literature_review.md",     "PAGE",  "## Comparative essay"),
    ("ch4_ranking_findings.md",      "PAGE",  None),
    ("ch6_model_justification.md",   "PAGE",  "## 6.3 Explicit"),
    ("ch7_sensitivity_findings.md",  "PAGE",  "## Headline answers"),
    ("ch8_3_tops_comparison.md",     "PAGE",  "## What Trizna"),
    ("bonus_b3_findings.md",         "PAGE",  None),
]

APPENDIX_FILES = [
    ("ch2_literature_review.md",         "PAGE",  None),
    ("ch5_1_unified_schema.md",          None,    "## The selection protocol"),
    ("ch8_4_cascade_analysis.md",        None,    "## Attributing every error"),
    ("ch1_2_mapping_rows_noam.md",       None,    None),
]

def set_spacing(para, space_before=0, space_after=6, line_spacing=1.5):
    pf = para.paragraph_format
    pf.space_before = Pt(space_before)
    pf.space_after  = Pt(space_after)
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    pf.line_spacing = line_spacing

def add_run_with_fmt(para, text):
    pattern = re.compile(r'(\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`)')
    last = 0
    for m in pattern.finditer(text):
        if m.start() > last:
            para.add_run(text[last:m.start()])
        raw = m.group(0)
        if raw.startswith("**"):
            r = para.add_run(m.group(2)); r.bold = True
        elif raw.startswith("*"):
            r = para.add_run(m.group(3)); r.italic = True
        else:
            r = para.add_run(m.group(4))
            r.font.name = "Courier New"; r.font.size = Pt(9)
        last = m.end()
    if last < len(text):
        para.add_run(text[last:])

def add_heading(doc, text, level):
    p = doc.add_heading(text, level=level)
    set_spacing(p, space_before=10 if level == 1 else 6, space_after=4, line_spacing=1.15)

def add_para(doc, text):
    p = doc.add_paragraph()
    add_run_with_fmt(p, text)
    set_spacing(p)

def add_code_block(doc, lines):
    p = doc.add_paragraph()
    r = p.add_run("\n".join(lines))
    r.font.name = "Courier New"; r.font.size = Pt(8)
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after  = Pt(4)
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), "F2F2F2")
    p._p.get_or_add_pPr().append(shd)

def add_list_item(doc, text, level=0):
    p = doc.add_paragraph(style="List Bullet")
    add_run_with_fmt(p, text)
    p.paragraph_format.left_indent  = Inches(0.25 + level * 0.2)
    p.paragraph_format.space_before = Pt(1)
    p.paragraph_format.space_after  = Pt(1)
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.MULTIPLE
    p.paragraph_format.line_spacing = 1.5

def parse_table_row(line):
    line = line.strip()
    if line.startswith("|"): line = line[1:]
    if line.endswith("|"):   line = line[:-1]
    return [c for c in line.split("|")]

def add_table(doc, rows):
    data = [r for r in rows if not all(re.match(r"^[-: ]+$", c) for c in r)]
    if not data: return
    ncols = max(len(r) for r in data)
    tbl = doc.add_table(rows=len(data), cols=ncols)
    tbl.style = "Table Grid"
    for ri, row in enumerate(data):
        for ci, cell_text in enumerate(row[:ncols]):
            cell = tbl.cell(ri, ci); cell.text = ""
            p = cell.paragraphs[0]
            add_run_with_fmt(p, cell_text.strip())
            p.paragraph_format.space_before = Pt(1)
            p.paragraph_format.space_after  = Pt(1)
            if ri == 0:
                for run in p.runs: run.bold = True
    for row in tbl.rows:
        for cell in row.cells:
            for p in cell.paragraphs:
                for run in p.runs: run.font.size = Pt(8.5)
    doc.add_paragraph()

def page_break(doc):
    pb = doc.add_paragraph()
    br = OxmlElement("w:br"); br.set(qn("w:type"), "page")
    pb._p.append(br)

def render_md(doc, md_text, stop_before=None):
    lines = md_text.split("\n")
    table_rows, code_lines = [], []
    in_code = False

    def flush_table():
        nonlocal table_rows
        if table_rows: add_table(doc, table_rows); table_rows = []

    def flush_code():
        nonlocal code_lines, in_code
        if code_lines: add_code_block(doc, code_lines); code_lines = []
        in_code = False

    for line in lines:
        stripped = line.strip()

        if stop_before and stripped.startswith(stop_before):
            flush_table()
            if in_code: flush_code()
            return

        if stripped.startswith("```"):
            if not in_code: flush_table(); in_code = True
            else:           flush_code()
            continue
        if in_code: code_lines.append(line); continue

        if stripped.startswith("|"):
            table_rows.append(parse_table_row(stripped)); continue
        else:
            flush_table()

        hm = re.match(r"^(#{1,4})\s+(.*)", stripped)
        if hm:
            add_heading(doc, hm.group(2), len(hm.group(1))); continue

        if stripped.startswith("> "):
            p = doc.add_paragraph(); add_run_with_fmt(p, stripped[2:])
            p.paragraph_format.left_indent = Inches(0.3)
            for run in p.runs: run.italic = True
            set_spacing(p, space_before=2, space_after=2); continue

        lm = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)", line)
        if lm:
            add_list_item(doc, lm.group(3), len(lm.group(1)) // 2); continue

        if re.match(r"^---+\s*$", stripped): continue

        if stripped: add_para(doc, stripped)

    flush_table()
    if in_code: flush_code()

def setup_doc():
    doc = Document()
    for section in doc.sections:
        section.top_margin    = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin   = Inches(1.1)
        section.right_margin  = Inches(1.1)
    style = doc.styles["Normal"]
    style.font.name = "Calibri"; style.font.size = Pt(10.5)
    for lvl, sz in [(1, 14), (2, 12), (3, 11), (4, 10.5)]:
        hs = doc.styles[f"Heading {lvl}"]
        hs.font.size = Pt(sz); hs.font.bold = True; hs.font.name = "Calibri"
        hs.font.color.rgb = RGBColor(0x1F, 0x3B, 0x4D)
    return doc

def add_title_page(doc):
    doc.add_paragraph(); doc.add_paragraph()
    title = doc.add_paragraph(); title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = title.add_run("LotL Shell Attack Detection\nBinary Classifier")
    r.font.size = Pt(20); r.font.bold = True; r.font.name = "Calibri"
    set_spacing(title, space_before=48, space_after=12, line_spacing=1.3)
    sub = doc.add_paragraph(); sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r2 = sub.add_run("MITRE ATT&CK T1059.004  |  Course 3917\nReichman University — Final Project")
    r2.font.size = Pt(12); r2.font.name = "Calibri"
    set_spacing(sub, space_before=6, space_after=6)
    meta = doc.add_paragraph(); meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r3 = meta.add_run("Group 10  |  Ben Volovelsky & Noam Delbari  |  August 2026")
    r3.font.size = Pt(11); r3.font.name = "Calibri"
    set_spacing(meta, space_before=24, space_after=0)
    page_break(doc)

def main():
    doc = setup_doc()
    add_title_page(doc)

    first = True
    for filename, brk, stop_before in BODY_FILES:
        path = REPORT / filename
        if not path.exists():
            print(f"  SKIP: {filename}"); continue
        if brk == "PAGE" and not first:
            page_break(doc)
        render_md(doc, path.read_text(encoding="utf-8"), stop_before=stop_before)
        print(f"  BODY: {filename}" + (f" [stop before '{stop_before}']" if stop_before else ""))
        first = False

    page_break(doc)
    ah = doc.add_heading("Appendix — Supplementary Analysis", level=1)
    set_spacing(ah, space_before=10, space_after=6, line_spacing=1.15)

    for filename, brk, stop_before in APPENDIX_FILES:
        path = REPORT / filename
        if not path.exists():
            print(f"  SKIP: {filename}"); continue
        if brk == "PAGE":
            page_break(doc)
        render_md(doc, path.read_text(encoding="utf-8"), stop_before=stop_before)
        print(f"  APPENDIX: {filename}" + (f" [stop before '{stop_before}']" if stop_before else ""))

    doc.save(OUT)
    print(f"\nSaved: {OUT}")

if __name__ == "__main__":
    main()
