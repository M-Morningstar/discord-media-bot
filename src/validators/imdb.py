from __future__ import annotations

import re

_IMDB_ID_RE = re.compile(r"\btt\d{7,8}\b", re.IGNORECASE)


def extract_imdb_id(text: str) -> str | None:
    """Return the first IMDB ID found in *text*, or ``None``.

    Searches for a pattern matching ``tt`` followed by 7 or 8 digits
    (case-insensitive).  Returns the lowercase IMDB ID string.

    Args:
        text: The message content to search.

    Returns:
        The IMDB ID string like ``"tt1234567"``, or ``None``.
    """
    match = _IMDB_ID_RE.search(text)
    if match is None:
        return None
    return match.group(0).lower()


def _find_all_imdb_ids(text: str) -> list[str]:
    """Return all unique, lowercase IMDB IDs found in *text*."""
    return list({m.group(0).lower() for m in _IMDB_ID_RE.finditer(text)})
