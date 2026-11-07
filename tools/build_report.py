#!/usr/bin/env python3
"""Build the project report from the Markdown sources in ``report/``.

The report is written as plain Markdown (one file per chapter) so that every
change can be reviewed in a pull request. This script turns those files into a
Word document laid out like a typical HCL / university project report:

* generated cover page, table of contents, list of tables and list of figures
* Times New Roman 12 pt body text, 1.5 line spacing, justified paragraphs
* page border, running header and page numbers (roman for the preliminary
  pages, arabic from Chapter 1 onwards)

When LibreOffice is available the document is also converted to PDF. In that
case the script builds the document twice: the first PDF is only used to find
out on which page every heading landed, so that the table of contents in the
final document carries real page numbers.

Usage::

    python tools/build_report.py            # build/report.docx
    python tools/build_report.py --pdf      # build/report.docx + build/report.pdf
"""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import yaml
from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
REPORT_DIR = ROOT / "report"
BODY_FONT = "Times New Roman"
CODE_FONT = "Courier New"


# --------------------------------------------------------------------------
# Markdown parsing
# --------------------------------------------------------------------------

@dataclass
class Block:
    kind: str  # heading, para, bullets, numbers, table, code, quote, image, align, signatures, pagebreak
    text: str = ""
    level: int = 0
    items: list = field(default_factory=list)
    caption: str = ""
    align: str = ""


HEADING_RE = re.compile(r"^(#{1,4})\s+(.*?)\s*#*\s*$")
BULLET_RE = re.compile(r"^\s*[-*]\s+(.*)$")
NUMBER_RE = re.compile(r"^\s*(\d+)[.)]\s+(.*)$")
IMAGE_RE = re.compile(r"^!\[(.*?)\]\((.*?)\)\s*$")
TABLE_CAPTION_RE = re.compile(r"^Table\s+[A-Z0-9]+\.\d+:\s+.+$")
COMMENT_RE = re.compile(r"<!--.*?-->", re.S)


def substitute(text: str, meta: dict) -> str:
    """Replace ``{{ key.sub }}`` placeholders with values from metadata.yaml."""

    def lookup(match: re.Match) -> str:
        value = meta
        for part in match.group(1).strip().split("."):
            if not isinstance(value, dict) or part not in value:
                raise KeyError(f"unknown placeholder {{{{{match.group(1)}}}}}")
            value = value[part]
        return str(value)

    return re.sub(r"\{\{(.*?)\}\}", lookup, text)


def parse_markdown(source: str) -> list[Block]:
    source = source.replace("<!-- pagebreak -->", "\n@@PAGEBREAK@@\n")
    source = COMMENT_RE.sub("", source)
    lines = source.splitlines()
    blocks: list[Block] = []
    i = 0
    pending_caption = ""

    def is_block_start(line: str) -> bool:
        return bool(
            HEADING_RE.match(line)
            or BULLET_RE.match(line)
            or NUMBER_RE.match(line)
            or line.startswith(("|", ">", "```", ":::", "@@PAGEBREAK@@"))
            or IMAGE_RE.match(line)
            or TABLE_CAPTION_RE.match(line)
        )

    while i < len(lines):
        line = lines[i].rstrip()
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        if stripped == "@@PAGEBREAK@@":
            blocks.append(Block("pagebreak"))
            i += 1
            continue

        if stripped.startswith("```"):
            code = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i].rstrip("\n"))
                i += 1
            i += 1
            blocks.append(Block("code", text="\n".join(code)))
            continue

        if stripped.startswith(":::"):
            directive = stripped[3:].strip()
            body = []
            i += 1
            while i < len(lines) and lines[i].strip() != ":::":
                body.append(lines[i].strip())
                i += 1
            i += 1
            if directive == "signatures":
                rows = [tuple(c.strip() for c in row.split("||")) for row in body]
                blocks.append(Block("signatures", items=rows))
            else:
                blocks.append(Block("align", items=body, align=directive or "center"))
            continue

        match = HEADING_RE.match(stripped)
        if match:
            blocks.append(Block("heading", text=match.group(2), level=len(match.group(1))))
            i += 1
            continue

        if TABLE_CAPTION_RE.match(stripped):
            pending_caption = stripped
            i += 1
            continue

        if stripped.startswith("|"):
            rows = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                row = lines[i].strip().strip("|")
                cells = [c.strip() for c in re.split(r"(?<!\\)\|", row)]
                if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                    rows.append([c.replace("\\|", "|") for c in cells])
                i += 1
            blocks.append(Block("table", items=rows, caption=pending_caption))
            pending_caption = ""
            continue

        match = IMAGE_RE.match(stripped)
        if match:
            blocks.append(Block("image", caption=match.group(1), text=match.group(2)))
            i += 1
            continue

        if stripped.startswith(">"):
            quote = []
            while i < len(lines) and lines[i].strip().startswith(">"):
                quote.append(lines[i].strip()[1:].strip())
                i += 1
            blocks.append(Block("quote", text=" ".join(quote)))
            continue

        for kind, regex in (("bullets", BULLET_RE), ("numbers", NUMBER_RE)):
            if regex.match(line):
                items: list[str] = []
                while i < len(lines):
                    current = lines[i].rstrip()
                    item_match = regex.match(current)
                    if item_match:
                        items.append(item_match.group(item_match.lastindex))
                    elif current.startswith(("  ", "\t")) and current.strip() and items:
                        items[-1] += " " + current.strip()
                    else:
                        break
                    i += 1
                blocks.append(Block(kind, items=items))
                break
        else:
            para = [stripped]
            i += 1
            while i < len(lines) and lines[i].strip() and not is_block_start(lines[i].strip()):
                para.append(lines[i].strip())
                i += 1
            blocks.append(Block("para", text=" ".join(para)))
    return blocks


INLINE_RE = re.compile(r"(\*\*.+?\*\*|`[^`]+`|\*[^*\s][^*]*?\*|\[[^\]]+\]\([^)]+\)|<https?://[^>\s]+>)")


def add_inline(paragraph, text: str, size: float | None = None, bold: bool = False, italic: bool = False):
    """Add Markdown-formatted text (bold, italic, code, links) to a paragraph."""
    for token in INLINE_RE.split(text):
        if not token:
            continue
        run_bold, run_italic, font = bold, italic, None
        if token.startswith("**") and token.endswith("**"):
            token, run_bold = token[2:-2], True
        elif token.startswith("`") and token.endswith("`"):
            token, font = token[1:-1], CODE_FONT
        elif token.startswith("*") and token.endswith("*") and len(token) > 2:
            token, run_italic = token[1:-1], True
        elif token.startswith("[") and "](" in token:
            token = token[1 : token.index("](")]
        elif token.startswith("<http") and token.endswith(">"):
            token = token[1:-1]
        run = paragraph.add_run(token)
        run.bold = run_bold or None
        run.italic = run_italic or None
        if font:
            set_run_font(run, font)
            run.font.size = Pt((size or 12) - 1.5)
        elif size:
            run.font.size = Pt(size)
    return paragraph


# --------------------------------------------------------------------------
# Low level python-docx helpers
# --------------------------------------------------------------------------

def set_run_font(run, name: str):
    run.font.name = name
    rpr = run._element.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.append(fonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        fonts.set(qn(attr), name)


def set_style_font(style, name: str, size: float, bold: bool = False):
    style.font.name = name
    style.font.size = Pt(size)
    style.font.bold = bold
    style.font.color.rgb = RGBColor(0, 0, 0)
    rpr = style.element.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.append(fonts)
    for attr in ("w:ascii", "w:hAnsi", "w:cs", "w:eastAsia"):
        fonts.set(qn(attr), name)
    for theme_attr in ("w:asciiTheme", "w:hAnsiTheme", "w:cstheme", "w:eastAsiaTheme"):
        if fonts.get(qn(theme_attr)) is not None:
            del fonts.attrib[qn(theme_attr)]


def add_field(paragraph, instruction: str, size: float | None = None):
    """Insert a simple field such as PAGE; ``size`` sets the result's font size."""
    field = OxmlElement("w:fldSimple")
    field.set(qn("w:instr"), instruction)
    run = OxmlElement("w:r")
    rpr = OxmlElement("w:rPr")
    if size:
        for tag in ("w:sz", "w:szCs"):
            element = OxmlElement(tag)
            element.set(qn("w:val"), str(int(size * 2)))
            rpr.append(element)
    run.append(rpr)
    text = OxmlElement("w:t")
    text.text = "1"
    run.append(text)
    field.append(run)
    paragraph._p.append(field)
    return field


def set_page_border(section):
    sect_pr = section._sectPr
    borders = OxmlElement("w:pgBorders")
    borders.set(qn("w:offsetFrom"), "page")
    for side in ("top", "left", "bottom", "right"):
        element = OxmlElement(f"w:{side}")
        element.set(qn("w:val"), "double")
        element.set(qn("w:sz"), "6")
        element.set(qn("w:space"), "24")
        element.set(qn("w:color"), "000000")
        borders.append(element)
    sect_pr.append(borders)


def set_page_numbering(section, fmt: str, start: int = 1):
    sect_pr = section._sectPr
    pg = sect_pr.find(qn("w:pgNumType"))
    if pg is None:
        pg = OxmlElement("w:pgNumType")
        sect_pr.append(pg)
    pg.set(qn("w:fmt"), fmt)
    pg.set(qn("w:start"), str(start))


def paragraph_border(paragraph, side: str = "bottom"):
    ppr = paragraph._p.get_or_add_pPr()
    borders = OxmlElement("w:pBdr")
    line = OxmlElement(f"w:{side}")
    line.set(qn("w:val"), "single")
    line.set(qn("w:sz"), "6")
    line.set(qn("w:space"), "1")
    line.set(qn("w:color"), "000000")
    borders.append(line)
    ppr.append(borders)


def shade(element, fill: str):
    props = element.get_or_add_tcPr() if element.tag == qn("w:tc") else element.get_or_add_pPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), fill)
    props.append(shd)


def keep_with_next(paragraph):
    paragraph.paragraph_format.keep_with_next = True


def repeat_header_row(row):
    tr_pr = row._tr.get_or_add_trPr()
    element = OxmlElement("w:tblHeader")
    element.set(qn("w:val"), "true")
    tr_pr.append(element)


def remove_table_borders(table):
    tbl_pr = table._tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for side in ("top", "left", "bottom", "right", "insideH", "insideV"):
        element = OxmlElement(f"w:{side}")
        element.set(qn("w:val"), "nil")
        borders.append(element)
    tbl_pr.append(borders)


def to_roman(number: int) -> str:
    numerals = [(10, "x"), (9, "ix"), (5, "v"), (4, "iv"), (1, "i")]
    out = ""
    for value, letters in numerals:
        while number >= value:
            out += letters
            number -= value
    return out


# --------------------------------------------------------------------------
# Report builder
# --------------------------------------------------------------------------

@dataclass
class TocEntry:
    key: str
    level: int  # 1 = chapter / preliminary page, 2 = section, 0 = table / figure
    label: str
    kind: str = "heading"  # heading, table, figure


class ReportBuilder:
    def __init__(self, meta: dict, page_numbers: dict[str, str] | None, markers: bool):
        self.meta = meta
        self.page_numbers = page_numbers or {}
        self.markers = markers
        self.entries: list[TocEntry] = []
        self.doc = Document()
        self._setup_styles()
        self._counter = 0
        self._break_before_next_heading = False

    # -- setup ------------------------------------------------------------
    def _setup_styles(self):
        styles = self.doc.styles
        normal = styles["Normal"]
        set_style_font(normal, BODY_FONT, 12)
        fmt = normal.paragraph_format
        fmt.line_spacing = 1.5
        fmt.space_after = Pt(6)
        fmt.space_before = Pt(0)
        for name, size in (("Heading 1", 16), ("Heading 2", 14), ("Heading 3", 12), ("Heading 4", 12)):
            style = styles[name]
            set_style_font(style, BODY_FONT, size, bold=True)
            style.font.italic = name == "Heading 4"
            style.paragraph_format.space_before = Pt(12 if name != "Heading 1" else 0)
            style.paragraph_format.space_after = Pt(6 if name != "Heading 1" else 18)
            style.paragraph_format.keep_with_next = True
            style.paragraph_format.line_spacing = 1.15
        styles["Heading 1"].paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for name in ("List Bullet", "List Number"):
            set_style_font(styles[name], BODY_FONT, 12)

        section = self.doc.sections[0]
        section.page_height, section.page_width = Inches(11.69), Inches(8.27)  # A4
        section.left_margin = Inches(1.4)
        section.right_margin = Inches(1.0)
        section.top_margin = Inches(1.0)
        section.bottom_margin = Inches(1.0)
        section.header_distance = Inches(0.5)
        section.footer_distance = Inches(0.5)
        set_page_border(section)

    # -- small helpers ------------------------------------------------------
    def _key(self) -> str:
        self._counter += 1
        return f"E{self._counter:03d}"

    def _marker(self, paragraph, key: str):
        """Hidden-in-plain-sight marker used only in the measuring pass."""
        if self.markers:
            run = paragraph.add_run(f" QQ{key}QQ")
            run.font.size = Pt(1)
            run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

    def page_break(self):
        self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def new_page(self):
        """Start the next heading on a new page.

        Uses "page break before" on the heading instead of an empty paragraph
        holding a break, which leaves a blank page whenever the previous page
        happens to be exactly full.
        """
        self._break_before_next_heading = True

    def _take_break(self, paragraph):
        if self._break_before_next_heading:
            paragraph.paragraph_format.page_break_before = True
            self._break_before_next_heading = False

    def centered(self, text: str, size: float = 12, bold: bool = False, italic: bool = False, space_after: float = 6):
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after = Pt(space_after)
        p.paragraph_format.line_spacing = 1.15
        add_inline(p, text, size=size, bold=bold, italic=italic)
        return p

    # -- page furniture -----------------------------------------------------
    def configure_front_section(self, section):
        section.footer.is_linked_to_previous = False
        section.header.is_linked_to_previous = False
        section.different_first_page_header_footer = False
        footer = section.footer.paragraphs[0]
        footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
        add_field(footer, "PAGE", size=11)
        set_page_numbering(section, "lowerRoman", 1)

    def configure_body_section(self, section):
        section.header.is_linked_to_previous = False
        section.footer.is_linked_to_previous = False
        header = section.header.paragraphs[0]
        header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        run = header.add_run(self.meta["title"])
        run.italic = True
        run.font.size = Pt(9)
        paragraph_border(header, "bottom")
        footer = section.footer.paragraphs[0]
        footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
        paragraph_border(footer, "top")
        left = footer.add_run(f"{self.meta['organisation']}  |  Page ")
        left.font.size = Pt(9)
        add_field(footer, "PAGE", size=9)
        set_page_numbering(section, "decimal", 1)

    def new_section(self):
        section = self.doc.add_section(WD_SECTION.NEW_PAGE)
        set_page_border(section)
        return section

    # -- cover page ---------------------------------------------------------
    def cover_page(self):
        m = self.meta
        section = self.doc.sections[0]
        section.different_first_page_header_footer = True

        self.centered(m["report_type"].upper(), 14, bold=True, space_after=4).paragraph_format.space_before = Pt(18)
        self.centered("on", 12, italic=True, space_after=14)
        self.centered(f"“{m['title']}”", 22, bold=True, space_after=8)
        self.centered(m["subtitle"], 13, italic=True, space_after=36)
        self.centered(f"Submitted {m['submitted_for']}", 12, space_after=40)
        self.centered("Submitted by", 12, italic=True, space_after=4)
        self.centered(m["student"]["name"], 15, bold=True, space_after=2)
        self.centered(m["student"]["id"], 12, space_after=2)
        self.centered(m["student"]["programme"], 12, space_after=36)
        self.centered("Under the guidance of", 12, italic=True, space_after=4)
        self.centered(m["guide"]["name"], 13, bold=True, space_after=2)
        self.centered(f"{m['guide']['designation']}, {m['guide']['organisation']}", 12, space_after=60)
        self.centered(m["organisation"].upper(), 17, bold=True, space_after=6)
        self.centered("in association with", 11, italic=True, space_after=6)
        self.centered(m["institute"]["department"], 12, space_after=2)
        self.centered(m["institute"]["name"].upper(), 14, bold=True, space_after=2)
        self.centered(m["institute"]["city"], 12, space_after=16)
        self.centered(f"Academic Year {m['academic_year']}", 12, bold=True, space_after=0)

    # -- lists of contents ------------------------------------------------
    def contents_pages(self, planned: list[TocEntry]):
        def line(entry: TocEntry, indent: float, bold: bool):
            p = self.doc.add_paragraph()
            p.paragraph_format.line_spacing = 1.15
            p.paragraph_format.space_after = Pt(4 if entry.level == 1 else 2)
            p.paragraph_format.left_indent = Inches(indent)
            p.paragraph_format.tab_stops.add_tab_stop(Inches(5.85), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
            add_inline(p, entry.label, size=12 if entry.level == 1 else 11.5, bold=bold)
            # "000" keeps the line width identical between the two passes
            run = p.add_run("\t" + self.page_numbers.get(entry.key, "000" if self.markers else ""))
            run.bold = bold or None

        def title(text: str):
            p = self.doc.add_paragraph(style="Heading 1")
            self._take_break(p)
            p.add_run(text)

        def column_heads(left: str):
            p = self.doc.add_paragraph()
            p.paragraph_format.tab_stops.add_tab_stop(Inches(5.85), WD_TAB_ALIGNMENT.RIGHT)
            p.paragraph_format.line_spacing = 1.15
            r = p.add_run(f"{left}\tPage No.")
            r.bold = True
            paragraph_border(p, "bottom")

        title("TABLE OF CONTENTS")
        column_heads("Title")
        for entry in planned:
            if entry.kind == "heading":
                line(entry, 0 if entry.level == 1 else 0.35, entry.level == 1)

        for kind, heading, label in (("table", "LIST OF TABLES", "Table"), ("figure", "LIST OF FIGURES", "Figure")):
            items = [e for e in planned if e.kind == kind]
            if not items:
                continue
            self.new_page()
            title(heading)
            column_heads(label)
            for entry in items:
                line(entry, 0, False)

    # -- block rendering ----------------------------------------------------
    def render_blocks(self, blocks: list[Block], chapter: int | None):
        first_heading = True
        for block in blocks:
            if block.kind == "heading":
                if block.level == 1:
                    if not first_heading:
                        self.new_page()
                    self.chapter_heading(block.text, chapter)
                    first_heading = False
                else:
                    p = self.doc.add_paragraph(style=f"Heading {min(block.level, 4)}")
                    add_inline(p, block.text)
                    if block.level == 2 and chapter is not None:
                        key = self._key()
                        self.entries.append(TocEntry(key, 2, block.text))
                        self._marker(p, key)
            elif block.kind == "para":
                p = self.doc.add_paragraph()
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                add_inline(p, block.text)
            elif block.kind in ("bullets", "numbers"):
                for n, item in enumerate(block.items, 1):
                    if block.kind == "bullets" and re.match(r"\[[ xX]\]\s", item):
                        # task-list item: draw a checkbox instead of a bullet
                        p = self.doc.add_paragraph()
                        p.paragraph_format.left_indent = Inches(0.5)
                        p.paragraph_format.first_line_indent = Inches(-0.3)
                        p.add_run(("\u2611" if item[1] in "xX" else "\u2610") + "\u00a0\u00a0")
                        item = item[4:]
                    elif block.kind == "bullets":
                        p = self.doc.add_paragraph(style="List Bullet")
                    else:
                        p = self.doc.add_paragraph()
                        p.paragraph_format.left_indent = Inches(0.5)
                        p.paragraph_format.first_line_indent = Inches(-0.3)
                        p.add_run(f"{n}.  ")
                    p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                    p.paragraph_format.space_after = Pt(3)
                    add_inline(p, item)
            elif block.kind == "quote":
                p = self.doc.add_paragraph()
                p.paragraph_format.left_indent = Inches(0.5)
                p.paragraph_format.right_indent = Inches(0.5)
                p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
                add_inline(p, block.text, italic=True)
            elif block.kind == "code":
                self.code_block(block.text)
            elif block.kind == "table":
                self.table(block)
            elif block.kind == "image":
                self.image(block)
            elif block.kind == "align":
                for text in block.items:
                    p = self.doc.add_paragraph()
                    p.alignment = {"right": WD_ALIGN_PARAGRAPH.RIGHT, "left": WD_ALIGN_PARAGRAPH.LEFT}.get(
                        block.align, WD_ALIGN_PARAGRAPH.CENTER
                    )
                    p.paragraph_format.space_after = Pt(0)
                    add_inline(p, text)
            elif block.kind == "signatures":
                self.signatures(block.items)
            elif block.kind == "pagebreak":
                self.page_break()

    def chapter_heading(self, text: str, chapter: int | None):
        key = self._key()
        if chapter is not None:
            label = self.doc.add_paragraph()
            self._take_break(label)
            label.alignment = WD_ALIGN_PARAGRAPH.CENTER
            label.paragraph_format.space_after = Pt(4)
            keep_with_next(label)
            r = label.add_run(f"CHAPTER {chapter}")
            r.bold = True
            r.font.size = Pt(14)
            toc_label = f"{chapter}.  {text.upper()}"
        else:
            toc_label = text.upper()
        p = self.doc.add_paragraph(style="Heading 1")
        self._take_break(p)
        add_inline(p, text.upper())
        self._marker(p, key)
        self.entries.append(TocEntry(key, 1, toc_label))

    def code_block(self, text: str):
        for n, line in enumerate(text.split("\n")):
            p = self.doc.add_paragraph()
            p.paragraph_format.line_spacing = 1.0
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.left_indent = Inches(0.15)
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            shade(p._p, "F2F2F2")
            run = p.add_run(line if line else " ")
            set_run_font(run, CODE_FONT)
            run.font.size = Pt(9)
        self.doc.add_paragraph().paragraph_format.space_after = Pt(0)

    def caption(self, text: str, kind: str):
        key = self._key()
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.line_spacing = 1.15
        number, _, rest = text.partition(":")
        r = p.add_run(number + ":")
        r.bold = True
        r.font.size = Pt(11)
        add_inline(p, rest, size=11)
        self._marker(p, key)
        self.entries.append(TocEntry(key, 0, text, kind))
        return p

    def table(self, block: Block):
        if block.caption:
            keep_with_next(self.caption(block.caption, "table"))
        rows = block.items
        columns = max(len(r) for r in rows)
        table = self.doc.add_table(rows=len(rows), cols=columns)
        table.style = "Table Grid"
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        for r, row in enumerate(rows):
            for c in range(columns):
                cell = table.cell(r, c)
                p = cell.paragraphs[0]
                p.paragraph_format.line_spacing = 1.0
                p.paragraph_format.space_after = Pt(2)
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER if r == 0 else WD_ALIGN_PARAGRAPH.LEFT
                add_inline(p, row[c] if c < len(row) else "", size=10, bold=r == 0)
                if r == 0:
                    shade(cell._tc, "D9D9D9")
        repeat_header_row(table.rows[0])
        self._fit_columns(table, rows, columns)
        spacer = self.doc.add_paragraph()
        spacer.paragraph_format.space_after = Pt(4)

    @staticmethod
    def _fit_columns(table, rows, columns, total_inches: float = 5.85):
        """Size columns so the longest word always fits, then share the rest by content."""
        padding, per_char = 0.2, 0.085  # inches, for 10 pt Times
        minimum, desired = [], []
        for c in range(columns):
            cells = [row[c] if c < len(row) else "" for row in rows]
            words = [len(w.strip("*`")) for cell in cells for w in cell.split()] or [1]
            minimum.append(max(words) * per_char + padding)
            desired.append(min(max(len(cell) for cell in cells), 70) * per_char * 0.8 + padding)
        if sum(minimum) >= total_inches:
            widths = [m * total_inches / sum(minimum) for m in minimum]
        else:
            extra = [max(d - m, 0.0) for d, m in zip(desired, minimum)]
            spare = total_inches - sum(minimum)
            if sum(extra) == 0:
                widths = [m + spare / columns for m in minimum]
            else:
                widths = [m + spare * e / sum(extra) for m, e in zip(minimum, extra)]
        table.autofit = False
        for c, width in enumerate(widths):
            table.columns[c].width = Inches(width)
            for cell in table.columns[c].cells:
                cell.width = Inches(width)

    def image(self, block: Block):
        path = (REPORT_DIR / block.text).resolve()
        if not path.exists():
            raise FileNotFoundError(f"figure not found: {block.text}")
        p = self.doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        keep_with_next(p)
        # Fit to the text width, but never taller than most of a page.
        from docx.image.image import Image as DocxImage

        info = DocxImage.from_file(str(path))
        if info.px_height / info.px_width * 5.8 > 7.8:
            p.add_run().add_picture(str(path), height=Inches(7.8))
        else:
            p.add_run().add_picture(str(path), width=Inches(5.8))
        self.caption(block.caption, "figure")

    def signatures(self, rows):
        spacer = self.doc.add_paragraph()
        spacer.paragraph_format.space_before = Pt(36)
        table = self.doc.add_table(rows=len(rows), cols=2)
        remove_table_borders(table)
        for r, row in enumerate(rows):
            for c in range(2):
                p = table.cell(r, c).paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT if c == 0 else WD_ALIGN_PARAGRAPH.RIGHT
                p.paragraph_format.space_after = Pt(0)
                add_inline(p, row[c] if c < len(row) else "")


_warned: set[str] = set()


def warn_once(message: str):
    if message not in _warned:
        _warned.add(message)
        print(f"warning: {message}")


def load_sources(meta: dict):
    """Return (front matter items, chapters, back matter) as parsed blocks."""

    def read(path: Path) -> list[Block]:
        return parse_markdown(substitute(path.read_text(encoding="utf-8"), meta))

    front = []
    for name in meta["front_matter"]:
        path = REPORT_DIR / "front-matter" / name
        if name == "@toc":
            front.append("@toc")
        elif path.exists():
            front.append(read(path))
        else:
            warn_once(f"{path.relative_to(ROOT)} is listed in metadata.yaml but missing, skipped")
    chapters = [read(p) for p in sorted((REPORT_DIR / "chapters").glob("*.md"))]
    back = []
    if (REPORT_DIR / "references.md").exists():
        back.append(read(REPORT_DIR / "references.md"))
    back.extend(read(p) for p in sorted((REPORT_DIR / "appendices").glob("*.md")))
    return front, chapters, back


def build(meta: dict, page_numbers: dict[str, str] | None, markers: bool, planned: list[TocEntry] | None):
    front, chapters, back = load_sources(meta)
    builder = ReportBuilder(meta, page_numbers, markers)
    builder.cover_page()

    section = builder.new_section()
    builder.configure_front_section(section)
    first = True
    for item in front:
        if not first:
            builder.new_page()
        first = False
        if item == "@toc":
            builder.contents_pages(planned or [])
        else:
            builder.render_blocks(item, None)

    for number, blocks in enumerate(chapters, 1):
        if number == 1:
            builder.configure_body_section(builder.new_section())
        else:
            builder.new_page()
        builder.render_blocks(blocks, number)

    for blocks in back:
        builder.new_page()
        builder.render_blocks(blocks, None)
    return builder


def find_soffice() -> str | None:
    return shutil.which("soffice") or shutil.which("libreoffice")


def convert_to_pdf(docx_path: Path, out_dir: Path) -> Path:
    soffice = find_soffice()
    if not soffice:
        raise RuntimeError("LibreOffice (soffice) is required for PDF output")
    with tempfile.TemporaryDirectory() as profile:
        subprocess.run(
            [
                soffice,
                f"-env:UserInstallation=file://{profile}",
                "--headless",
                "--convert-to",
                "pdf",
                "--outdir",
                str(out_dir),
                str(docx_path),
            ],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=300,
        )
    return out_dir / (docx_path.stem + ".pdf")


def measure_pages(pdf_path: Path, entries: list[TocEntry]) -> dict[str, str]:
    """Find on which page each marked heading/caption ended up."""
    from pypdf import PdfReader

    pages = [page.extract_text() or "" for page in PdfReader(str(pdf_path)).pages]
    located: dict[str, int] = {}
    for index, text in enumerate(pages):
        for key in re.findall(r"QQ(E\d{3})QQ", text.replace(" ", "")):
            located.setdefault(key, index)

    first_chapter = next((e.key for e in entries if e.label.startswith("1.  ")), None)
    body_start = located.get(first_chapter, len(pages))
    numbers = {}
    for key, index in located.items():
        numbers[key] = str(index - body_start + 1) if index >= body_start else to_roman(index)
    return numbers


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pdf", action="store_true", help="also produce a PDF (needs LibreOffice)")
    parser.add_argument("--out", default=str(ROOT / "build" / "report.docx"), help="output .docx path")
    args = parser.parse_args(argv)

    meta = yaml.safe_load((REPORT_DIR / "metadata.yaml").read_text(encoding="utf-8"))
    out = Path(args.out).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)

    # Pass 0: collect the headings, tables and figures for the contents pages.
    planned = build(meta, None, markers=False, planned=None).entries
    page_numbers: dict[str, str] = {}

    if find_soffice():
        # Pass 1: build with invisible markers and see where everything lands.
        with tempfile.TemporaryDirectory() as tmp:
            probe = Path(tmp) / "probe.docx"
            build(meta, None, markers=True, planned=planned).doc.save(probe)
            page_numbers = measure_pages(convert_to_pdf(probe, Path(tmp)), planned)
    else:
        print("note: LibreOffice not found, table of contents is built without page numbers")

    final = build(meta, page_numbers, markers=False, planned=planned)
    final.doc.core_properties.title = meta["title"]
    final.doc.core_properties.author = meta["student"]["name"]
    final.doc.core_properties.subject = meta["subtitle"]
    final.doc.save(out)
    print(f"wrote {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out}")

    if args.pdf:
        pdf = convert_to_pdf(out, out.parent)
        print(f"wrote {pdf.relative_to(ROOT) if pdf.is_relative_to(ROOT) else pdf}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
