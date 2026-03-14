"""Handle document fidelity logic so saved, exported, or converted output preserves expected formatting.

This module belongs to the document authoring, fidelity, and review UI layer. It helps explain how `pypad.ui.document` is structured and where this file fits into the runtime workflow.
"""

from __future__ import annotations

from html import escape as html_escape
from pathlib import Path
import re
from typing import Any
import zipfile
import xml.etree.ElementTree as ET

from PySide6.QtGui import QTextDocument


class DocumentFidelityError(RuntimeError):
    """Raised when a document import or export format cannot be processed safely."""
    pass


def _local_name(tag: Any) -> str:
    """Return the namespace-stripped local XML tag name."""
    text = str(tag or "")
    if "}" in text:
        return text.split("}", 1)[1]
    return text


def render_text_to_html(text: str, *, markdown_mode: bool) -> str:
    """Render plain text or Markdown into HTML using Qt's document engine."""
    doc = QTextDocument()
    if markdown_mode or _looks_like_markdown(text):
        doc.setMarkdown(text)
    else:
        doc.setPlainText(text)
    return doc.toHtml()


def _looks_like_markdown(text: str) -> bool:
    """Heuristically detect whether text should be treated as Markdown."""
    if not text.strip():
        return False
    patterns = (
        r"(?m)^\s{0,3}#{1,6}\s+\S",                  # headings
        r"(?m)^\s{0,3}[-*+]\s+\S",                   # unordered lists
        r"(?m)^\s{0,3}\d+[.)]\s+\S",                 # ordered lists
        r"(?m)^\s{0,3}>\s+\S",                       # blockquotes
        r"(?m)^\s{0,3}([-*_]\s*){3,}$",              # horizontal rules
        r"(?s)```.+?```",                            # fenced code
        r"`[^`\n]+`",                                # inline code
        r"\[[^\]\n]+\]\([^)]+\)",                    # links
        r"!\[[^\]\n]*\]\([^)]+\)",                   # images
        r"(?<!\*)\*\*[^*\n]+\*\*(?!\*)",             # bold
        r"(?<!\*)\*[^*\n]+\*(?!\*)",                 # italic
    )
    return any(re.search(pattern, text) for pattern in patterns)


def render_markdown_to_mathjax_html(text: str, *, dark_mode: bool = False) -> str:
    """Render Markdown into standalone HTML that includes MathJax support."""
    doc = QTextDocument()
    doc.setMarkdown(text)
    body_html = doc.toHtml()
    bg = "#1f1f1f" if dark_mode else "#ffffff"
    fg = "#f2f2f2" if dark_mode else "#1f1f1f"
    border = "#3b3b3b" if dark_mode else "#e0e0e0"
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    body {{
      background: {bg};
      color: {fg};
      margin: 0;
      padding: 14px;
      font-family: "Segoe UI", Arial, sans-serif;
      line-height: 1.45;
    }}
    hr {{ border: 0; border-top: 1px solid {border}; }}
    code, pre {{ font-family: "Consolas", "Courier New", monospace; }}
    img {{ max-width: 100%; }}
  </style>
  <script>
    window.MathJax = {{
      tex: {{
        inlineMath: [['$', '$'], ['\\\\(', '\\\\)']],
        displayMath: [['$$', '$$'], ['\\\\[', '\\\\]']]
      }},
      options: {{
        skipHtmlTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code']
      }}
    }};
  </script>
  <script async src="https://cdn.jsdelivr.net/npm/mathjax@3/es5/tex-chtml.js"></script>
</head>
<body>{body_html}</body>
</html>"""


def _read_text_file(path: Path, encoding: str) -> str:
    """Read a text file with fallback decoding for import workflows."""
    try:
        return path.read_text(encoding=encoding)
    except Exception:
        return path.read_text(encoding="utf-8", errors="replace")


def _docx_to_text(path: Path) -> str:
    """Extract plain text content from a DOCX archive."""
    with zipfile.ZipFile(path, "r") as zf:
        try:
            xml_data = zf.read("word/document.xml")
        except KeyError as exc:
            raise DocumentFidelityError("DOCX file is missing word/document.xml.") from exc
    try:
        root = ET.fromstring(xml_data)
    except Exception as exc:
        raise DocumentFidelityError(f"Could not parse DOCX XML: {exc}") from exc
    lines: list[str] = []
    for para in root.iter():
        if _local_name(para.tag) != "p":
            continue
        parts: list[str] = []
        for node in para.iter():
            lname = _local_name(node.tag)
            if lname == "t" and node.text:
                parts.append(node.text)
            elif lname == "tab":
                parts.append("\t")
            elif lname in {"br", "cr"}:
                parts.append("\n")
        lines.append("".join(parts))
    return "\n".join(lines).strip("\n")


def _odt_to_text(path: Path) -> str:
    """Extract plain text content from an ODT archive."""
    with zipfile.ZipFile(path, "r") as zf:
        try:
            xml_data = zf.read("content.xml")
        except KeyError as exc:
            raise DocumentFidelityError("ODT file is missing content.xml.") from exc
    try:
        root = ET.fromstring(xml_data)
    except Exception as exc:
        raise DocumentFidelityError(f"Could not parse ODT XML: {exc}") from exc
    lines: list[str] = []
    for elem in root.iter():
        lname = _local_name(elem.tag)
        if lname not in {"p", "h"}:
            continue
        text = "".join(elem.itertext()).strip("\n")
        lines.append(text)
    return "\n".join(lines).strip("\n")


def _pdf_to_text(path: Path) -> str:
    """Extract plain text from a PDF using the optional `pypdf` dependency."""
    try:
        from pypdf import PdfReader  # type: ignore[import-not-found]
    except Exception as exc:
        raise DocumentFidelityError(
            "PDF import requires the optional 'pypdf' package."
        ) from exc
    try:
        reader = PdfReader(str(path))
        pages = [(page.extract_text() or "") for page in reader.pages]
    except Exception as exc:
        raise DocumentFidelityError(f"Could not read PDF: {exc}") from exc
    return "\n\n".join(pages).strip()


def import_document_text(path: str, *, encoding: str = "utf-8") -> tuple[str, bool]:
    """Import a supported document format and return its text plus Markdown-mode hint."""
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    if suffix in {".md", ".markdown", ".mdown", ".txt"}:
        return _read_text_file(file_path, encoding), suffix != ".txt"
    if suffix in {".html", ".htm"}:
        html = _read_text_file(file_path, encoding)
        doc = QTextDocument()
        doc.setHtml(html)
        return doc.toMarkdown().strip(), True
    if suffix == ".docx":
        return _docx_to_text(file_path), False
    if suffix == ".odt":
        return _odt_to_text(file_path), False
    if suffix == ".pdf":
        return _pdf_to_text(file_path), False
    raise DocumentFidelityError(f"Unsupported import format: {suffix or '(none)'}")


def _docx_document_xml_from_text(text: str) -> str:
    """Build a minimal DOCX `document.xml` payload from plain text lines."""
    lines = text.splitlines() or [""]
    xml_lines: list[str] = [
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>',
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">',
        "  <w:body>",
    ]
    for line in lines:
        escaped = html_escape(line, quote=False)
        if not escaped:
            xml_lines.append("    <w:p/>")
            continue
        xml_lines.append('    <w:p><w:r><w:t xml:space="preserve">' + escaped + "</w:t></w:r></w:p>")
    xml_lines.extend(["  </w:body>", "</w:document>"])
    return "\n".join(xml_lines)


def _write_docx_from_text(path: Path, text: str) -> None:
    """Write a minimal DOCX archive containing the supplied plain text content."""
    content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
</Types>
"""
    rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
  <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
</Relationships>
"""
    document_xml = _docx_document_xml_from_text(text)
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("[Content_Types].xml", content_types)
        zf.writestr("_rels/.rels", rels)
        zf.writestr("word/document.xml", document_xml)


def _odt_content_xml_from_text(text: str) -> str:
    """Build a minimal ODT `content.xml` payload from plain text lines."""
    lines = text.splitlines() or [""]
    body = "\n".join(f"      <text:p>{html_escape(line, quote=False)}</text:p>" for line in lines)
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<office:document-content
    xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
    xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0"
    office:version="1.2">
  <office:body>
    <office:text>
{body}
    </office:text>
  </office:body>
</office:document-content>
"""


def _write_odt_from_text(path: Path, text: str) -> None:
    """Write a minimal ODT archive containing the supplied plain text content."""
    manifest = """<?xml version="1.0" encoding="UTF-8"?>
<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.2">
  <manifest:file-entry manifest:full-path="/" manifest:media-type="application/vnd.oasis.opendocument.text"/>
  <manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>
  <manifest:file-entry manifest:full-path="styles.xml" manifest:media-type="text/xml"/>
</manifest:manifest>
"""
    styles = """<?xml version="1.0" encoding="UTF-8"?>
<office:document-styles
    xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"
    office:version="1.2"/>
"""
    meta = """<?xml version="1.0" encoding="UTF-8"?>
<office:document-meta xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" office:version="1.2"/>
"""
    settings = """<?xml version="1.0" encoding="UTF-8"?>
<office:document-settings xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" office:version="1.2"/>
"""
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("mimetype", "application/vnd.oasis.opendocument.text", compress_type=zipfile.ZIP_STORED)
        zf.writestr("content.xml", _odt_content_xml_from_text(text), compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr("styles.xml", styles, compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr("meta.xml", meta, compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr("settings.xml", settings, compress_type=zipfile.ZIP_DEFLATED)
        zf.writestr("META-INF/manifest.xml", manifest, compress_type=zipfile.ZIP_DEFLATED)


def export_document_text(path: str, text: str, *, markdown_mode: bool) -> None:
    """Export text to a supported document format, raising when fidelity support is unavailable."""
    file_path = Path(path)
    suffix = file_path.suffix.lower()
    if suffix in {".md", ".markdown", ".mdown", ".txt"}:
        file_path.write_text(text, encoding="utf-8")
        return
    if suffix in {".html", ".htm"}:
        file_path.write_text(render_text_to_html(text, markdown_mode=markdown_mode), encoding="utf-8")
        return
    if suffix == ".docx":
        _write_docx_from_text(file_path, text)
        return
    if suffix == ".odt":
        _write_odt_from_text(file_path, text)
        return
    raise DocumentFidelityError(f"Unsupported export format: {suffix or '(none)'}")


def clipboard_paste_special_options(mime: Any) -> list[str]:
    """Return the paste-special choices supported by the available clipboard MIME data."""
    options = ["Keep Formatting", "Text Only"]
    if mime is None:
        return options
    has_html = bool(getattr(mime, "hasHtml", lambda: False)())
    has_text = bool(getattr(mime, "hasText", lambda: False)())
    if has_html:
        options.extend(["Markdown (from HTML)", "HTML Source", "HTML to Text"])
    if has_text:
        options.extend(["Markdown to HTML", "Quote as Markdown Block", "Wrap in Markdown Code Fence"])
    return options


def convert_clipboard_for_paste(mime: Any, choice: str) -> str:
    """Convert clipboard MIME content into the representation requested by Paste Special."""
    if mime is None:
        return ""
    has_html = bool(getattr(mime, "hasHtml", lambda: False)())
    has_text = bool(getattr(mime, "hasText", lambda: False)())
    text_value = mime.text() if has_text else ""
    html_value = mime.html() if has_html else ""

    if choice == "Text Only":
        if text_value:
            return text_value
        if not html_value:
            return ""
        doc = QTextDocument()
        doc.setHtml(html_value)
        return doc.toPlainText()
    if choice == "Markdown (from HTML)":
        if not html_value:
            return text_value
        doc = QTextDocument()
        doc.setHtml(html_value)
        return doc.toMarkdown().strip()
    if choice == "HTML Source":
        return html_value or text_value
    if choice == "HTML to Text":
        if not html_value:
            return text_value
        doc = QTextDocument()
        doc.setHtml(html_value)
        return doc.toPlainText()
    if choice == "Markdown to HTML":
        if not text_value:
            return ""
        return render_text_to_html(text_value.strip(), markdown_mode=True).strip()
    if choice == "Quote as Markdown Block":
        source = text_value or (html_value.strip() if html_value else "")
        if not source:
            return ""
        return "\n".join(f"> {line}" if line.strip() else ">" for line in source.splitlines())
    if choice == "Wrap in Markdown Code Fence":
        source = text_value or html_value
        if not source:
            return ""
        normalized = source.rstrip("\n")
        return f"```\n{normalized}\n```"
    return ""
