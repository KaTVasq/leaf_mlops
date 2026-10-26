"""Scientific name parsing and normalization.

Names for the same taxon are written in many ways (case, underscores, hyphens, quoted
cultivars, typos). These helpers make the differences explicit; they never decide a
taxonomic question. Synonyms and spelling must be checked against a taxonomic source.
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from dataclasses import dataclass

_QUOTED = re.compile(r"[\'\u2018\u2019\"\u201c\u201d]([^\'\u2018\u2019\"\u201c\u201d]+)[\'\u2018\u2019\"\u201c\u201d]")
_SEPARATORS = re.compile(r"[_\-\s]+")


@dataclass(frozen=True)
class ParsedName:
    """A Latin name split into its parts. Intended for binomials, not common names."""

    original: str
    genus: str | None
    epithet: str | None
    infraspecific: str | None
    cultivar: str | None
    is_hybrid: bool

    @property
    def canonical(self) -> str:
        """'Genus epithet', 'Genus' (genus-only name) or '' (empty input)."""
        if self.genus and self.epithet:
            return f"{self.genus} {self.epithet}"
        return self.genus or ""


def parse_name(raw: str) -> ParsedName:
    """Split a Latin name: capitalization, quoted cultivar, hybrid sign, variety."""
    text = unicodedata.normalize("NFC", raw).strip()

    cultivar = None
    match = _QUOTED.search(text)
    if match:
        cultivar = match.group(1).strip()
        text = f"{text[: match.start()]} {text[match.end():]}"

    tokens = text.replace("_", " ").replace("\u00d7", " x ").split()

    is_hybrid = False
    if tokens and tokens[0].lower() == "x":
        is_hybrid = True
        tokens = tokens[1:]
    elif len(tokens) > 1 and tokens[1].lower() == "x":
        is_hybrid = True
        tokens = [tokens[0]] + tokens[2:]

    genus = tokens[0].capitalize() if tokens else None
    epithet = tokens[1].lower() if len(tokens) > 1 else None
    rest = " ".join(tokens[2:]).lower() if len(tokens) > 2 else None
    return ParsedName(raw, genus, epithet, rest or None, cultivar, is_hybrid)


def normalize_key(text: str) -> str:
    """Comparison key: no accents, lower case, underscores/hyphens/spaces collapsed."""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    stripped = re.sub(r"[\'\u2018\u2019\"\u201c\u201d]", "", stripped)
    return _SEPARATORS.sub(" ", stripped).strip().lower()


def suggest_names(name: str, reference: list[str], cutoff: float = 0.85, limit: int = 3) -> list[str]:
    """Reference names that look like ``name`` (typos, spelling variants)."""
    by_key = {normalize_key(ref): ref for ref in reference}
    keys = difflib.get_close_matches(normalize_key(name), list(by_key), n=limit, cutoff=cutoff)
    return [by_key[key] for key in keys]
