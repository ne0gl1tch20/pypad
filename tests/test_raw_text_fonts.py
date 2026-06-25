from pypad.ui.document.raw_text_fonts import (
    RAW_FONT_BEGIN,
    RAW_FONT_END,
    decode_raw_text_with_font,
    encode_raw_text_with_font,
)


def test_raw_text_font_round_trip_preserves_body():
    body = "Hello\nraw text\n"
    encoded = encode_raw_text_with_font(
        body,
        {"family": "Segoe UI", "point_size": 12, "display": "document"},
    )

    assert encoded.startswith(RAW_FONT_BEGIN)
    assert RAW_FONT_END in encoded

    decoded, metadata = decode_raw_text_with_font(encoded)

    assert decoded == body
    assert metadata["family"] == "Segoe UI"
    assert metadata["point_size"] == 12
    assert metadata["display"] == "document"
    assert "PyPad" in metadata["reminder"]


def test_raw_text_font_decode_ignores_normal_text():
    text = "plain text\nwithout pypad metadata"

    decoded, metadata = decode_raw_text_with_font(text)

    assert decoded == text
    assert metadata is None


def test_raw_text_font_decode_keeps_malformed_header_as_text():
    text = f"{RAW_FONT_BEGIN}\nnot json\n{RAW_FONT_END}\nBody"

    decoded, metadata = decode_raw_text_with_font(text)

    assert decoded == text
    assert metadata is None
