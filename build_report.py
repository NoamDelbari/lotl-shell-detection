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
#
# These are the CONDENSED body sections (report/body_*.md), not the long
# per-topic working drafts they were written from. The drafts stay in report/ as
# the source material and are deliberately not rendered.
#
# Chapters deliberately RUN ON rather than starting a new page. Ten body files at
# one page break each would strand up to several pages of whitespace inside a
# 15-page allowance; the 14 pt coloured Heading 1 is enough of a break. The only
# page break in the document is the one before Appendix A.
#
# No entry carries a stop_before. The previous list truncated Ch6 at
# "## 6.3 Explicit", which silently dropped a graded rubric item from the output.
BODY_FILES = [
    ("exec_summary.md",  None, None),
    ("body_ch1.md",      None, None),
    ("body_ch2.md",      None, None),
    ("body_ch3.md",      None, None),
    ("body_ch4.md",      None, None),
    ("body_ch5.md",      None, None),
    ("body_ch6.md",      None, None),
    ("body_ch7.md",      None, None),
    ("body_ch8.md",      None, None),
    ("body_bonus.md",    None, None),
]

# Appendix B runs on directly after A -- that is what makes the two fit inside
# the professor's 5-page appendix allowance. Both files carry their own
# `# Appendix A/B` H1, so no synthetic appendix heading is added here.
APPENDIX_FILES = [
    ("appendix_a_execution.md", "PAGE", None),
    ("appendix_b_tables.md",    None,   None),
]

# Figures are sized in inches. ch7_pipeline.png is near-square (1873x1785), so
# width is height here: 3.0 in of width costs ~2.9 in of page.
DEFAULT_FIG_WIDTH = 3.0
MAX_FIG_WIDTH = 6.5          # usable text width between the 1 in margins

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

def set_col_widths(tbl, widths):
    """Pin column widths, in inches, instead of letting Word autofit.

    Word's autofit gives every column a broadly similar width, so a row's
    height is set by its longest cell while the short cells sit half empty.
    On a five-column mapping table that wastes most of the page. Fixed layout
    needs the width written onto every cell, not just the column.
    """
    tbl.autofit = False
    layout = OxmlElement("w:tblLayout")
    layout.set(qn("w:type"), "fixed")
    tbl._tbl.tblPr.append(layout)
    for ci, w in enumerate(widths):
        if ci >= len(tbl.columns): break
        tbl.columns[ci].width = Inches(w)
        for cell in tbl.columns[ci].cells:
            cell.width = Inches(w)

def add_table(doc, rows, col_widths=None):
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
    if col_widths: set_col_widths(tbl, col_widths)
    # Word needs a paragraph after a table (two adjacent tables would merge),
    # but a default 1.5-spaced one wastes ~26pt per table. A 6pt spacer keeps
    # the separation without the gap.
    spacer = doc.add_paragraph()
    spacer.paragraph_format.space_before = Pt(0)
    spacer.paragraph_format.space_after  = Pt(0)
    spacer.paragraph_format.line_spacing_rule = WD_LINE_SPACING.EXACTLY
    spacer.paragraph_format.line_spacing = Pt(6)

def add_figure(doc, rel_path, width=None):
    """Render `![alt](figures/x.png)` as a centred, sized picture.

    The builder had no image support of any kind before this, so every figure in
    report/figures/ was shipping only inside the ZIP. Width is capped at the
    usable text width; height follows from the aspect ratio, which is why a
    near-square diagram is expensive and the default is deliberately small.

    A missing image is fatal rather than skipped -- a silently absent figure
    leaves a dangling "Figure N.M" caption in a graded document.
    """
    path = (REPORT / rel_path).resolve()
    if not path.exists():
        raise SystemExit(f"ERROR: figure not found: {rel_path} (looked in {path})")
    w = min(width or DEFAULT_FIG_WIDTH, MAX_FIG_WIDTH)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(path), width=Inches(w))
    # 1.5 spacing on a picture paragraph pads the image top and bottom for no
    # reason; single spacing keeps the figure tight against its caption.
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after  = Pt(2)
    p.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE

def page_break(doc):
    pb = doc.add_paragraph()
    br = OxmlElement("w:br"); br.set(qn("w:type"), "page")
    pb._p.append(br)

def render_md(doc, md_text, stop_before=None):
    lines = md_text.split("\n")
    table_rows, code_lines = [], []
    in_code = False
    # Markdown sources are hard-wrapped, so a paragraph spans several lines.
    # Buffer consecutive body lines and emit them as ONE Word paragraph --
    # rendering each source line separately would give every wrapped line its
    # own paragraph spacing and break the text flow.
    para_buf, quote_buf, list_buf = [], [], None
    # `<!-- cols: 1.2 0.9 ... -->` on the line before a table pins its column
    # widths in inches; without it Word autofits. Applies to the next table only.
    pending_widths = None
    # `<!-- fig-width: 3.5 -->` before an image line overrides DEFAULT_FIG_WIDTH
    # for that one figure.
    pending_fig_width = None

    def flush_table():
        nonlocal table_rows, pending_widths
        if table_rows:
            add_table(doc, table_rows, col_widths=pending_widths)
            table_rows = []
            # cleared only once the table it belongs to has been emitted, so a
            # blank line between the directive and the table is harmless
            pending_widths = None

    def flush_code():
        nonlocal code_lines, in_code
        if code_lines: add_code_block(doc, code_lines); code_lines = []
        in_code = False

    def flush_para():
        nonlocal para_buf
        if para_buf: add_para(doc, " ".join(para_buf)); para_buf = []

    def flush_quote():
        nonlocal quote_buf
        if quote_buf:
            p = doc.add_paragraph(); add_run_with_fmt(p, " ".join(quote_buf))
            p.paragraph_format.left_indent = Inches(0.3)
            for run in p.runs: run.italic = True
            set_spacing(p, space_before=2, space_after=2)
            quote_buf = []

    def flush_list():
        nonlocal list_buf
        if list_buf:
            text, level = list_buf
            add_list_item(doc, " ".join(text), level)
            list_buf = None

    def flush_text():
        flush_para(); flush_quote(); flush_list()

    for line in lines:
        stripped = line.strip()

        if stop_before and stripped.startswith(stop_before):
            flush_text(); flush_table()
            if in_code: flush_code()
            return

        if stripped.startswith("```"):
            if not in_code: flush_text(); flush_table(); in_code = True
            else:           flush_code()
            continue
        if in_code: code_lines.append(line); continue

        cm = re.match(r"^<!--\s*cols:\s*([\d.\s]+?)\s*-->$", stripped)
        if cm:
            flush_text(); flush_table()
            pending_widths = [float(w) for w in cm.group(1).split()]; continue
        fm = re.match(r"^<!--\s*fig-width:\s*([\d.]+)\s*-->$", stripped)
        if fm:
            pending_fig_width = float(fm.group(1)); continue
        if stripped.startswith("<!--"):       # any other comment is not content
            continue

        im = re.match(r"^!\[[^\]]*\]\(([^)]+)\)$", stripped)
        if im:
            flush_text(); flush_table()
            add_figure(doc, im.group(1), pending_fig_width)
            pending_fig_width = None
            continue

        if stripped.startswith("|"):
            flush_text()
            table_rows.append(parse_table_row(stripped)); continue
        else:
            flush_table()

        if not stripped:                      # blank line ends any text block
            flush_text(); continue

        hm = re.match(r"^(#{1,4})\s+(.*)", stripped)
        if hm:
            flush_text()
            add_heading(doc, hm.group(2), len(hm.group(1))); continue

        if re.match(r"^---+\s*$", stripped):
            flush_text(); continue

        if stripped.startswith("> "):
            flush_para(); flush_list()
            quote_buf.append(stripped[2:]); continue

        lm = re.match(r"^(\s*)([-*]|\d+\.)\s+(.*)", line)
        if lm:
            flush_para(); flush_quote(); flush_list()
            list_buf = ([lm.group(3)], len(lm.group(1)) // 2); continue

        # A plain line: a continuation of whichever block is open, else prose.
        if list_buf is not None and line.startswith(("  ", "\t")):
            list_buf[0].append(stripped); continue
        if quote_buf:
            quote_buf.append(stripped); continue
        flush_list()
        para_buf.append(stripped)

    flush_text(); flush_table()
    if in_code: flush_code()

def setup_doc():
    doc = Document()
    for section in doc.sections:
        section.top_margin    = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.left_margin   = Inches(1.0)
        section.right_margin  = Inches(1.0)
    style = doc.styles["Normal"]
    # Spec: Arial or Calibri, 11 or 12 pt, 1.5 line spacing.
    style.font.name = "Calibri"; style.font.size = Pt(11)
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
    r2.font.size = Pt(12); r2.font.name = "Calibri"; r2.italic = True
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

def check_sources() -> None:
    """Fail before building if any listed section is missing.

    This used to `print("SKIP")` and carry on, which meant a renamed or
    not-yet-written chapter produced a clean-looking .docx with a graded section
    silently absent from it. Same failure class as an unregistered AI-log
    session: cheap to detect, expensive to miss.
    """
    missing = [f for f, _, _ in BODY_FILES + APPENDIX_FILES
               if not (REPORT / f).exists()]
    if missing:
        raise SystemExit(
            "ERROR: these sections are listed in build_report.py but do not "
            f"exist: {', '.join(missing)}. Write them, or remove the entry -- "
            "do not build a report with a section silently missing."
        )

def main():
    check_sources()
    doc = setup_doc()
    add_title_page(doc)

    first = True
    for filename, brk, stop_before in BODY_FILES:
        if brk == "PAGE" and not first:
            page_break(doc)
        render_md(doc, (REPORT / filename).read_text(encoding="utf-8"),
                  stop_before=stop_before)
        print(f"  BODY: {filename}" + (f" [stop before '{stop_before}']" if stop_before else ""))
        first = False

    # Both appendix files carry their own `# Appendix A/B` heading, so the only
    # thing needed here is the page break that starts the appendix -- it is
    # declared on the Appendix A entry.
    for filename, brk, stop_before in APPENDIX_FILES:
        if brk == "PAGE":
            page_break(doc)
        render_md(doc, (REPORT / filename).read_text(encoding="utf-8"),
                  stop_before=stop_before)
        print(f"  APPENDIX: {filename}" + (f" [stop before '{stop_before}']" if stop_before else ""))

    doc.save(OUT)
    print(f"\nSaved: {OUT}")

if __name__ == "__main__":
    main()
