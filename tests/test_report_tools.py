"""Tests for the report build and check scripts."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))

import build_report  # noqa: E402
import check_report  # noqa: E402


def kinds(blocks):
    return [b.kind for b in blocks]


def test_parse_markdown_recognises_block_types():
    source = """# Title

## 1.1 Section

A paragraph that
continues here.

- one
- two
  continued

1. first
2. second

Table 1.1: Caption

| A | B |
|---|---|
| x | y |

> quoted

```
code
```
"""
    blocks = build_report.parse_markdown(source)
    assert kinds(blocks) == ["heading", "heading", "para", "bullets", "numbers", "table", "quote", "code"]
    assert blocks[2].text == "A paragraph that continues here."
    assert blocks[3].items == ["one", "two continued"]
    assert blocks[5].caption == "Table 1.1: Caption"
    assert blocks[5].items == [["A", "B"], ["x", "y"]]


def test_parse_markdown_handles_directives_and_page_breaks():
    source = """:::signatures
Left || Right
:::

<!-- pagebreak -->

:::right
Signed
:::
"""
    blocks = build_report.parse_markdown(source)
    assert kinds(blocks) == ["signatures", "pagebreak", "align"]
    assert blocks[0].items == [("Left", "Right")]
    assert blocks[2].align == "right"


def test_substitute_placeholders():
    meta = {"student": {"name": "A. Student"}}
    assert build_report.substitute("By {{student.name}}.", meta) == "By A. Student."
    with pytest.raises(KeyError):
        build_report.substitute("{{guide.name}}", meta)


def test_roman_numerals():
    assert [build_report.to_roman(n) for n in (1, 4, 9, 14)] == ["i", "iv", "ix", "xiv"]


@pytest.mark.parametrize(
    "group, expected",
    [("3", [3]), ("1, 4", [1, 4]), ("5-7", [5, 6, 7]), ("2–3, 9", [2, 3, 9])],
)
def test_expand_citation(group, expected):
    assert check_report.expand_citation(group) == expected


def test_inline_autolinks_render_as_plain_urls():
    from docx import Document

    paragraph = Document().add_paragraph()
    build_report.add_inline(paragraph, "Available: <https://example.com/a?b=1> and **bold**.")
    assert paragraph.text == "Available: https://example.com/a?b=1 and bold."


def test_task_list_items_render_as_checkboxes():
    builder = build_report.ReportBuilder({"title": "t", "organisation": "o"}, None, markers=False)
    builder.render_blocks(build_report.parse_markdown("- [ ] open item\n- [x] done item\n"), None)
    texts = [p.text for p in builder.doc.paragraphs if p.text]
    assert texts == ["☐  open item", "☑  done item"]
