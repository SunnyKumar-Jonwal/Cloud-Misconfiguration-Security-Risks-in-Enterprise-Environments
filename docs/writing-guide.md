# Writing Guide for the Report Sources

The report lives in `report/` as plain Markdown so that every change can be
reviewed line by line in a pull request. `tools/build_report.py` turns it into
the formatted Word/PDF report.

## Where things go

| Path | Content |
| --- | --- |
| `report/metadata.yaml` | Title, student, guide, institute, and the order of the preliminary pages |
| `report/front-matter/` | Certificate, declaration, acknowledgement, abstract, abbreviations |
| `report/chapters/NN-name.md` | One file per chapter. Chapters are numbered in file-name order |
| `report/references.md` | IEEE-style reference list |
| `report/appendices/` | Appendices, in file-name order |
| `report/figures/` | Images used by the chapters |

The cover page, table of contents, list of tables and list of figures are
generated. Do not write them by hand.

## Conventions

- Start each file with exactly one `# Title`. Chapter numbers are added by the
  build script, so write `# Introduction`, not `# Chapter 1 Introduction`.
- Number sections by hand: `## 3.2 Indirect Prompt Injection`,
  `### 3.2.1 Email-borne Payloads`. The CI check verifies that the numbering
  matches the chapter.
- Cite sources as `[n]`, where `n` is the entry number in `references.md`.
- Put a table caption on the line directly above the table:
  `Table 3.1: Mapping of threats to OWASP categories`.
- Insert a figure with `![Figure 2.1: Caption text](figures/file.png)`.
- Use `{{student.name}}`-style placeholders for anything defined in
  `metadata.yaml`.
- `<!-- pagebreak -->` forces a new page. A `:::center` … `:::` block centres
  each line, and a `:::signatures` block lays out `Left || Right` signature
  lines.

## Building locally

```bash
pip install -r requirements.txt
python tools/build_report.py --pdf
```

PDF output and the page numbers in the table of contents need LibreOffice
(`soffice`) on the `PATH`. Without it, only the `.docx` is produced.
