from pypad.ui.document.document_fidelity import render_text_to_html


def test_render_text_to_html_auto_detects_markdown_when_mode_off() -> None:
    source = "# Heading\n\n- item one\n- item two\n\nA [link](https://example.com)"
    html = render_text_to_html(source, markdown_mode=False)
    assert "Heading" in html
    assert "<ul" in html
    assert "href=\"https://example.com\"" in html


def test_render_text_to_html_plain_text_without_markdown_syntax() -> None:
    source = "Just plain text line 1.\nline 2."
    html = render_text_to_html(source, markdown_mode=False)
    assert "Just plain text line 1." in html
    assert "<ul" not in html
    assert "<h1" not in html
