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
OUT    = ROOT / "Group_209361864_315005066_Report.docx"

# each entry: (filename, page_break_before, stop_before_heading)
# stop_before: stop rendering the file when a line starting with this text is hit

# Every graded chapter is represented (Exec + Ch1-8 + Bonus). stop_before trims
# each source file to its headline deliverable so all chapters fit the page budget;
# full versions live in report/*.md (and the *_Report_FULL.docx) in the ZIP.
# Chapters flow continuously (no per-chapter page break) so headings — not blank
# half-pages — separate them; this reclaims ~4-5 pages vs one-chapter-per-page.
# stop_before trims each file to its headline deliverable.
BODY_FILES = [
    ("exec_summary.md",                None, None),
    ("ch1_threat_mapping.md",          None, None),
    ("ch2_literature_review.md",       None, "## Comparative essay"),
    ("ch2_4_comparative_essay.md",     None, None),   # 2 papers + 3 essay questions
    ("ch3_eda_findings.md",            None, "Variance gap is a measure"),
    ("ch4_ranking_findings.md",        None, "## Surprises versus intuition"),
    ("ch5_1_unified_schema.md",        None, "## One column, one contract"),
    ("ch5_2_distribution_shift.md",    None, "## Effect shift I"),
    ("ch5_3_scaling_normalisation.md", None, "## Why a scaler"),
    ("ch6_model_justification.md",     None, "## 6.3 Explicit"),
    ("ch6_2_rf_if.md",                 None, None),   # RF + IF (models 3 & 4), concise
    ("ch7_sensitivity_findings.md",    None, "## Headline answers"),
    ("ch7_2_class_imbalance.md",       None, None),   # 7.2 class-imbalance defense
    ("ch8_1_error_forensics_ben.md",   None, "## cnn1d/dataset1"),   # trimmed to rebalance
    ("ch8_2_cross_dataset_table.md",   None, None),
    ("ch8_3_tops_comparison.md",       None, "## What Trizna"),
    ("ch8_4_cascade_analysis.md",      None, "## Attributing every error"),
    ("bonus_b3_findings.md",           None, None),
]

APPENDIX_FILES = [
    ("appendix_a_code_execution.md",   None,   None),
    ("appendix_b_environment.md",      "PAGE", None),
]

# Descriptive caption for every rendered table, in document order (spec: all
# tables must be captioned). Kept here rather than in the .md sources so the
# stop_before truncations do not have to be caption-aware.
TABLE_CAPTIONS = [
    "In-domain F1, false-positive rate, and D2->D1 transfer F1 for the five detectors and the character n-gram baseline on both datasets.",
    "Telemetry and feature mapping for three T1059.004-adjacent sub-techniques: shell-log signature, capturing source, engineered features, and whether provenance labelling detects them.",
    "Feature-and-model extraction matrix comparing Trizna's SLP work with this project across six dimensions.",
    "Per-feature benign vs. attack variance and variance gap on Dataset 1, ranked by gap.",
    "Top five Dataset 1 features by XGBoost gain, with what each measures and its MITRE ATT&CK mapping.",
    "Covariate-shift probe: ROC-AUC of a classifier trained to separate Dataset 1 from Dataset 2 rows using the 43 features alone.",
    "Cross-dataset performance of all five models (in-domain and both transfer directions) across Accuracy, Precision, Recall/DR, FPR, F1, and ROC-AUC.",
    "Error-profile comparison of failure modes: a Trizna-style anomaly detector vs. our XGBoost-hybrid and 1D-CNN.",
    "Dataset 1 - cascade configurations vs. the single best model: F1, precision, recall, FPR, and confusion counts.",
    "Dataset 2 - cascade configurations vs. the single best model: F1, precision, recall, FPR, and confusion counts.",
    "Local Llama-3.1-8B arbitration on high-uncertainty edge cases: accuracy, agreement with the model vote, mean latency, and call count per dataset.",
    "Software frameworks and versions used across the pipeline.",
]
_TABLE_I = 0

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
    # split on UNescaped pipes only, so a literal shell pipe written as \| inside
    # a cell (e.g. `cat /tmp/f\|/bin/sh`) stays in the cell instead of creating a
    # spurious column; then unescape \| -> | for display.
    cells = re.split(r'(?<!\\)\|', line)
    return [c.replace('\\|', '|') for c in cells]

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
    add_table_caption(doc)


def add_table_caption(doc):
    global _TABLE_I
    cap = TABLE_CAPTIONS[_TABLE_I] if _TABLE_I < len(TABLE_CAPTIONS) else ""
    _TABLE_I += 1
    p = doc.add_paragraph()
    r = p.add_run(f"Table {_TABLE_I}. {cap}")
    r.italic = True; r.font.name = "Calibri"; r.font.size = Pt(9)
    pf = p.paragraph_format
    pf.space_before = Pt(2); pf.space_after = Pt(8)
    pf.line_spacing_rule = WD_LINE_SPACING.MULTIPLE; pf.line_spacing = 1.0

def page_break(doc):
    pb = doc.add_paragraph()
    br = OxmlElement("w:br"); br.set(qn("w:type"), "page")
    pb._p.append(br)

def render_md(doc, md_text, stop_before=None):
    lines = md_text.split("\n")
    table_rows, code_lines, para_buf = [], [], []
    in_code = False

    def flush_table():
        nonlocal table_rows
        if table_rows: add_table(doc, table_rows); table_rows = []

    def flush_code():
        nonlocal code_lines, in_code
        if code_lines: add_code_block(doc, code_lines); code_lines = []
        in_code = False

    def flush_para():
        # join soft-wrapped lines of one paragraph (Markdown treats a single
        # newline inside a paragraph as a space). Without this, a **bold** span
        # that wraps across two source lines renders the literal ** because each
        # physical line is parsed on its own.
        nonlocal para_buf
        if para_buf: add_para(doc, " ".join(para_buf)); para_buf = []

    for line in lines:
        stripped = line.strip()

        if stop_before and stripped.startswith(stop_before):
            flush_para(); flush_table()
            if in_code: flush_code()
            return

        if stripped.startswith("```"):
            flush_para()
            if not in_code: flush_table(); in_code = True
            else:           flush_code()
            continue
        if in_code: code_lines.append(line); continue

        if stripped.startswith("|"):
            flush_para()
            table_rows.append(parse_table_row(stripped)); continue
        else:
            flush_table()

        hm = re.match(r"^(#{1,4})\s+(.*)", stripped)
        if hm:
            flush_para()
            add_heading(doc, hm.group(2), len(hm.group(1))); continue

        if stripped.startswith("> "):
            flush_para()
            p = doc.add_paragraph(); add_run_with_fmt(p, stripped[2:])
            p.paragraph_format.left_indent = Inches(0.3)
            for run in p.runs: run.italic = True
            set_spacing(p, space_before=2, space_after=2); continue

        lm = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)", line)
        if lm:
            flush_para()
            add_list_item(doc, lm.group(3), len(lm.group(1)) // 2); continue

        if re.match(r"^---+\s*$", stripped):
            flush_para(); continue

        if not stripped:
            flush_para(); continue

        para_buf.append(stripped)   # accumulate a wrapped paragraph's lines

    flush_para(); flush_table()
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
    r = title.add_run("AI-Driven Detection of Living-off-the-Land\nUnix Shell Attacks")
    r.font.size = Pt(20); r.font.bold = True; r.font.name = "Calibri"
    set_spacing(title, space_before=42, space_after=10, line_spacing=1.2)

    sub = doc.add_paragraph(); sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r2 = sub.add_run("MITRE ATT&CK T1059.004 — Command & Scripting Interpreter: Unix Shell")
    r2.font.size = Pt(12); r2.font.name = "Calibri"; r2.font.italic = True
    set_spacing(sub, space_before=4, space_after=18)

    course = doc.add_paragraph(); course.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rc = course.add_run("Course: Using AI for Intrusion and Malware Detection (3917)\n"
                        "Reichman University — Efi Arazi School of Computer Science")
    rc.font.size = Pt(12); rc.font.name = "Calibri"
    set_spacing(course, space_before=6, space_after=18)

    team = doc.add_paragraph(); team.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rt = team.add_run("Ben Volovelsky · ID 209361864 · bvolovelsky@nvidia.com\n"
                      "Noam Delbari · ID 315005066 · noam.delbari@post.runi.ac.il")
    rt.font.size = Pt(11); rt.font.name = "Calibri"
    set_spacing(team, space_before=2, space_after=18)

    date = doc.add_paragraph(); date.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rd = date.add_run("Date of Submission: August 15, 2026")
    rd.font.size = Pt(11); rd.font.name = "Calibri"
    set_spacing(date, space_before=6, space_after=0)

    page_break(doc)

def main():
    global _TABLE_I
    _TABLE_I = 0
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

    page_break(doc)   # appendix files carry their own "# Appendix A/B" titles
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
