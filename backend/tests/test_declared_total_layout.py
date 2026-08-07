from app.services.extraction.declared_total import extract_layout_declared_total
from app.services.extraction.pdf_layout import PdfLayoutLine, PdfLayoutToken
from app.services.extraction.types import Geometry


def _token(text: str, x0: float, x1: float) -> PdfLayoutToken:
    return PdfLayoutToken(
        original_text=text,
        geometry=Geometry(x0=x0, top=10, x1=x1, bottom=20),
    )


def test_compact_bilingual_header_row_extracts_total_not_duration() -> None:
    tokens = (
        _token("Duration", 10, 55),
        _token("/", 58, 62),
        _token("الزمن", 65, 100),
        _token("75", 130, 145),
        _token("minutes", 148, 190),
        _token("Total", 220, 250),
        _token("Marks", 253, 290),
        _token("/", 293, 297),
        _token("الدرجة", 300, 340),
        _token("30", 360, 375),
    )
    line = PdfLayoutLine(
        raw_text="Duration / الزمن 75 minutes Total Marks / الدرجة 30",
        reading_text="30 الدرجة / Marks Total minutes 75 الزمن / Duration",
        page_number=1,
        geometry=Geometry(10, 10, 375, 20),
        source_spans=tuple(token.original_text for token in tokens),
        tokens=tokens,
    )

    result = extract_layout_declared_total([line])

    assert result is not None
    assert result.value == 30
    assert result.reading_text == "Total Marks: 30"
    assert "75" not in result.source_text
    assert result.confidence == 0.95


def test_token_fallback_does_not_scan_through_a_duration_label() -> None:
    tokens = (
        _token("Total", 10, 40),
        _token("Marks", 43, 80),
        _token("Duration", 83, 130),
        _token("75", 133, 148),
    )
    line = PdfLayoutLine(
        raw_text="Total Marks Duration 75",
        reading_text="Total Marks Duration 75",
        page_number=1,
        geometry=Geometry(10, 10, 148, 20),
        source_spans=tuple(token.original_text for token in tokens),
        tokens=tokens,
    )

    assert extract_layout_declared_total([line]) is None
