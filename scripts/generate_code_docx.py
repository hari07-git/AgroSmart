from __future__ import annotations

import argparse
import html
import os
import posixpath
import zipfile
from dataclasses import dataclass
from pathlib import Path


DOCX_CONTENT_TYPES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>
  <Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>
</Types>
"""

DOCX_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
  <Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>
  <Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>
</Relationships>
"""

DOCX_WORD_RELS = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>
</Relationships>
"""

# Minimal styles: Title, Heading1, and Code (monospace).
DOCX_STYLES = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:style w:type="paragraph" w:styleId="Title">
    <w:name w:val="Title"/>
    <w:qFormat/>
    <w:rPr>
      <w:rFonts w:ascii="Georgia" w:hAnsi="Georgia"/>
      <w:sz w:val="40"/>
      <w:szCs w:val="40"/>
      <w:b/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Heading1">
    <w:name w:val="heading 1"/>
    <w:basedOn w:val="Normal"/>
    <w:next w:val="Normal"/>
    <w:uiPriority w:val="9"/>
    <w:qFormat/>
    <w:pPr>
      <w:keepNext/>
      <w:spacing w:before="240" w:after="120"/>
      <w:outlineLvl w:val="0"/>
    </w:pPr>
    <w:rPr>
      <w:rFonts w:ascii="Georgia" w:hAnsi="Georgia"/>
      <w:sz w:val="28"/>
      <w:szCs w:val="28"/>
      <w:b/>
    </w:rPr>
  </w:style>
  <w:style w:type="paragraph" w:styleId="Code">
    <w:name w:val="Code"/>
    <w:basedOn w:val="Normal"/>
    <w:uiPriority w:val="99"/>
    <w:qFormat/>
    <w:pPr>
      <w:spacing w:before="0" w:after="0"/>
      <w:ind w:left="360"/>
    </w:pPr>
    <w:rPr>
      <w:rFonts w:ascii="Consolas" w:hAnsi="Consolas" w:cs="Consolas"/>
      <w:sz w:val="18"/>
      <w:szCs w:val="18"/>
    </w:rPr>
  </w:style>
</w:styles>
"""


def _core_xml(title: str) -> str:
    # Keep timestamps out; Word accepts this.
    esc = html.escape(title)
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties"
  xmlns:dc="http://purl.org/dc/elements/1.1/"
  xmlns:dcterms="http://purl.org/dc/terms/"
  xmlns:dcmitype="http://purl.org/dc/dcmitype/"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">
  <dc:title>{esc}</dc:title>
  <dc:creator>AgroSmart</dc:creator>
  <cp:lastModifiedBy>AgroSmart</cp:lastModifiedBy>
</cp:coreProperties>
"""


DOCX_APP_XML = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
  xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">
  <Application>AgroSmart</Application>
</Properties>
"""


def _p(text: str, style: str | None = None) -> str:
    # Single paragraph; preserve spaces.
    t = html.escape(text)
    ppr = f"<w:pPr><w:pStyle w:val=\"{style}\"/></w:pPr>" if style else ""
    return f"<w:p>{ppr}<w:r><w:t xml:space=\"preserve\">{t}</w:t></w:r></w:p>"


def _code_paragraphs(code: str) -> str:
    # Word docx wants paragraphs; split on lines.
    out = []
    for line in code.splitlines():
        out.append(_p(line, style="Code"))
    if not code.endswith("\n"):
        # Keep exact final line; nothing extra needed.
        pass
    # Add a small spacer after each file.
    out.append(_p("", style="Code"))
    return "".join(out)


@dataclass(frozen=True)
class FileItem:
    rel: str
    abs: Path


def _is_probably_text(path: Path) -> bool:
    try:
        data = path.read_bytes()
    except Exception:
        return False
    if b"\x00" in data:
        return False
    # Very small files are fine.
    if len(data) < 8:
        return True
    # Heuristic: if it decodes as utf-8, treat as text.
    try:
        data.decode("utf-8")
        return True
    except Exception:
        return False


def _read_text(path: Path) -> str:
    # Prefer utf-8; replace errors for robustness.
    return path.read_text(encoding="utf-8", errors="replace")


def collect_files(root: Path) -> list[FileItem]:
    include_ext = {".py", ".html", ".css", ".js", ".md", ".txt"}
    # Keep order stable and predictable.
    candidates: list[FileItem] = []

    def add(p: Path):
        rel = p.relative_to(root).as_posix()
        candidates.append(FileItem(rel=rel, abs=p))

    # Top-level important files
    for name in ("app.py", "README.md", "requirements.txt", "requirements-dev.txt", "requirements-ml.txt", "requirements-report.txt"):
        p = root / name
        if p.exists() and p.is_file():
            add(p)

    # Folders
    for base in ("agrosmart", "scripts", "static", "docs", "tests"):
        base_path = root / base
        if not base_path.exists():
            continue
        for p in base_path.rglob("*"):
            if not p.is_file():
                continue
            if p.suffix.lower() not in include_ext:
                continue
            # Skip caches/venv-like
            parts = set(p.parts)
            if ".venv" in parts or "__pycache__" in parts or ".pytest_cache" in parts:
                continue
            add(p)

    # De-dup by rel path
    seen: set[str] = set()
    uniq: list[FileItem] = []
    for it in sorted(candidates, key=lambda x: x.rel):
        if it.rel in seen:
            continue
        seen.add(it.rel)
        uniq.append(it)
    return uniq


def build_document_xml(title: str, items: list[FileItem], max_file_bytes: int) -> str:
    body_parts = [_p(title, style="Title"), _p("", style=None)]

    for it in items:
        # Skip big files
        try:
            size = it.abs.stat().st_size
        except Exception:
            continue
        if size > max_file_bytes:
            body_parts.append(_p(it.rel, style="Heading1"))
            body_parts.append(_p(f"[skipped: file too large: {size} bytes]", style="Code"))
            continue

        if not _is_probably_text(it.abs):
            body_parts.append(_p(it.rel, style="Heading1"))
            body_parts.append(_p("[skipped: non-text/binary file]", style="Code"))
            continue

        body_parts.append(_p(it.rel, style="Heading1"))
        try:
            txt = _read_text(it.abs)
        except Exception as e:
            body_parts.append(_p(f"[error reading file: {e}]", style="Code"))
            continue
        body_parts.append(_code_paragraphs(txt))

    body = "".join(body_parts) + "<w:sectPr/>"
    return f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
  <w:body>{body}</w:body>
</w:document>
"""


def write_docx(out_path: Path, title: str, document_xml: str) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out_path, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", DOCX_CONTENT_TYPES)
        z.writestr("_rels/.rels", DOCX_RELS)
        z.writestr("word/_rels/document.xml.rels", DOCX_WORD_RELS)
        z.writestr("word/styles.xml", DOCX_STYLES)
        z.writestr("word/document.xml", document_xml)
        z.writestr("docProps/core.xml", _core_xml(title))
        z.writestr("docProps/app.xml", DOCX_APP_XML)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate a .docx containing project code with headings per file.")
    parser.add_argument("--root", default=".", help="Project root (default: .)")
    parser.add_argument("--out", default="AgroSmart_Code.docx", help="Output .docx path")
    parser.add_argument("--title", default="AgroSmart Project Code", help="Document title")
    parser.add_argument("--max-bytes", type=int, default=500_000, help="Max bytes per file (default 500k)")
    args = parser.parse_args()

    root = Path(args.root).resolve()
    out = Path(args.out).resolve()

    items = collect_files(root)
    doc_xml = build_document_xml(args.title, items, max_file_bytes=int(args.max_bytes))
    write_docx(out, args.title, doc_xml)

    print(str(out))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

