"""Explicit deterministic reference-citation detection (M8's approved
decision 2). A question-to-CLO or question-to-topic mapping may only be
created from an explicit, literal citation of the CLO/topic's official code
somewhere in the question's extracted text - never from keyword overlap,
similarity, or any other invented signal.

Allowed variants (decision 2's own examples): "CLO1", "CLO-1", "[CLO1]" -
implemented as one letter-prefix + optional-hyphen + digits pattern with
word-boundary lookaround, which accepts any non-alphanumeric surrounding
character (bracket, paren, punctuation, whitespace) without needing to
special-case brackets specifically, while still rejecting a longer code
that merely starts with the same digits (e.g. "CLO1" must not match inside
"CLO10" or "CLO12").
"""

from __future__ import annotations

import re
from collections.abc import Sequence

_CODE_PATTERN = re.compile(r"^([A-Za-z]+)-?(\d+)$")


def build_reference_pattern(code: str) -> re.Pattern[str] | None:
    """None if `code` isn't in the expected letter-prefix + digits shape
    (defensive - every Clo/Topic code produced by the current extractors
    matches it, but this never raises on unexpected input)."""
    match = _CODE_PATTERN.match(code.strip())
    if match is None:
        return None
    prefix, number = match.group(1), match.group(2)
    return re.compile(
        rf"(?<![A-Za-z0-9]){re.escape(prefix)}-?{re.escape(number)}(?![0-9])",
        re.IGNORECASE,
    )


def find_cited_codes(text: str, codes: Sequence[str]) -> set[str]:
    """Returns the subset of `codes` explicitly cited somewhere in `text`."""
    cited: set[str] = set()
    for code in codes:
        pattern = build_reference_pattern(code)
        if pattern is not None and pattern.search(text):
            cited.add(code)
    return cited
