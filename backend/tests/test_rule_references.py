from __future__ import annotations

from app.services.rules.references import build_reference_pattern, find_cited_codes


def test_bare_code_matches() -> None:
    pattern = build_reference_pattern("CLO1")
    assert pattern is not None
    assert pattern.search("Explain ACID properties. CLO1 is relevant.")


def test_hyphenated_variant_matches() -> None:
    pattern = build_reference_pattern("CLO1")
    assert pattern is not None
    assert pattern.search("Explain ACID properties. CLO-1 is relevant.")


def test_bracketed_variant_matches() -> None:
    pattern = build_reference_pattern("CLO1")
    assert pattern is not None
    assert pattern.search("Explain ACID properties. [CLO1]")


def test_case_insensitive() -> None:
    pattern = build_reference_pattern("CLO1")
    assert pattern is not None
    assert pattern.search("clo1 lowercase citation")


def test_does_not_match_inside_longer_code() -> None:
    pattern = build_reference_pattern("CLO1")
    assert pattern is not None
    assert not pattern.search("This relates to CLO10.")
    assert not pattern.search("This relates to CLO12.")


def test_no_citation_does_not_match() -> None:
    pattern = build_reference_pattern("CLO1")
    assert pattern is not None
    assert not pattern.search("No citation here at all.")


def test_topic_code_pattern() -> None:
    pattern = build_reference_pattern("T1")
    assert pattern is not None
    assert pattern.search("T1: intro material")
    assert not pattern.search("T10: advanced material")


def test_find_cited_codes_returns_matched_subset() -> None:
    cited = find_cited_codes("Discuss [CLO1] and CLO-2 together.", ["CLO1", "CLO2", "CLO3"])
    assert cited == {"CLO1", "CLO2"}


def test_find_cited_codes_empty_when_nothing_matches() -> None:
    cited = find_cited_codes("No references at all.", ["CLO1", "CLO2"])
    assert cited == set()


def test_build_reference_pattern_returns_none_for_unshaped_code() -> None:
    assert build_reference_pattern("not-a-code-shape!!") is None
