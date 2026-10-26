"""Verification of label mappings against the GBIF Backbone Taxonomy.

The mapping files are first drafted by hand or with an assistant, so every entry starts
as ``proposed_unverified``. This module checks each entry with the GBIF *species match*
API and decides conservatively:

* ``verified`` only when GBIF finds the same accepted name and agrees on genus and family.
* ``needs_review`` for anything else (synonyms, fuzzy matches, family disagreements).

It never rewrites family, genus or species by itself: GBIF's suggestion is stored in the
entry note and in the report so a person decides.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from leaf_mlops.data.mapping import LabelEntry
from leaf_mlops.data.names import parse_name

GBIF_MATCH_URL = "https://api.gbif.org/v1/species/match"
MIN_CONFIDENCE = 90

Fetcher = Callable[[str, str | None], dict]


class GbifError(RuntimeError):
    """Raised when the GBIF API cannot be reached or returns an unusable answer."""


@dataclass(frozen=True)
class GbifMatch:
    query: str
    match_type: str  # EXACT, FUZZY, HIGHERRANK, NONE
    confidence: int
    status: str  # ACCEPTED, SYNONYM, DOUBTFUL, ...
    rank: str
    canonical_name: str
    family: str
    genus: str
    species: str  # accepted species name according to GBIF (may differ from the query)

    @classmethod
    def from_response(cls, query: str, data: dict) -> GbifMatch:
        return cls(
            query=query,
            match_type=data.get("matchType", "NONE"),
            confidence=int(data.get("confidence", 0)),
            status=data.get("status", ""),
            rank=data.get("rank", ""),
            canonical_name=data.get("canonicalName", ""),
            family=data.get("family", ""),
            genus=data.get("genus", ""),
            species=data.get("species", ""),
        )


@dataclass(frozen=True)
class Verdict:
    key: str
    status: str  # verified | needs_review
    findings: tuple[str, ...]
    match: GbifMatch

    @property
    def message(self) -> str:
        return "; ".join(self.findings)


def http_fetch(name: str, rank: str | None = None) -> dict:
    """Query the GBIF species match endpoint (plants only)."""
    params = {"name": name, "kingdom": "Plantae"}
    if rank:
        params["rank"] = rank
    url = f"{GBIF_MATCH_URL}?{urllib.parse.urlencode(params)}"
    try:
        with urllib.request.urlopen(url, timeout=30) as response:
            return json.load(response)
    except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as error:
        raise GbifError(f"GBIF request failed for '{name}': {error}") from error


class CachedMatcher:
    """Calls GBIF once per (name, rank) and optionally persists the answers as JSON.

    The cache makes a verification run reproducible and avoids hammering the API.
    """

    def __init__(self, fetch: Fetcher = http_fetch, cache_path: str | Path | None = None, delay: float = 0.0):
        self._fetch = fetch
        self._delay = delay
        self._cache_path = Path(cache_path) if cache_path else None
        self._cache: dict[str, dict] = {}
        if self._cache_path and self._cache_path.exists():
            self._cache = json.loads(self._cache_path.read_text(encoding="utf-8"))

    def match(self, name: str, rank: str | None = None) -> GbifMatch:
        cache_key = f"{rank or ''}|{name}"
        if cache_key not in self._cache:
            self._cache[cache_key] = self._fetch(name, rank)
            if self._delay:
                time.sleep(self._delay)
        return GbifMatch.from_response(name, self._cache[cache_key])

    def save(self) -> None:
        if self._cache_path:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            self._cache_path.write_text(
                json.dumps(self._cache, indent=1, ensure_ascii=False, sort_keys=True), encoding="utf-8"
            )


def verify_entry(entry: LabelEntry, matcher: CachedMatcher) -> Verdict:
    """Check one mapping entry against GBIF and return a conservative verdict."""
    if entry.species:
        query, rank = parse_name(entry.species).canonical, "SPECIES"
    else:
        query, rank = entry.genus, "GENUS"
    match = matcher.match(query, rank)

    findings: list[str] = []
    if match.match_type == "NONE" or not match.canonical_name:
        findings.append("GBIF found no match")
    else:
        if match.match_type != "EXACT":
            findings.append(f"GBIF match is {match.match_type} ('{match.canonical_name}')")
        if match.confidence < MIN_CONFIDENCE:
            findings.append(f"low confidence ({match.confidence})")
        if match.status != "ACCEPTED":
            findings.append(f"GBIF status is {match.status}; accepted species: '{match.species or '?'}'")
        if match.rank != rank:
            findings.append(f"GBIF rank is {match.rank}, expected {rank}")
        if match.genus and match.genus != entry.genus:
            findings.append(f"GBIF genus is '{match.genus}', mapping has '{entry.genus}'")
        if match.family and match.family != entry.family:
            findings.append(f"GBIF family is '{match.family}', mapping has '{entry.family}'")
        if entry.species and match.canonical_name != query and match.match_type == "EXACT":
            findings.append(f"GBIF canonical name is '{match.canonical_name}'")

    status = "verified" if not findings else "needs_review"
    return Verdict(entry.key, status, tuple(findings), match)


def verify_mapping(entries: dict[str, LabelEntry], matcher: CachedMatcher) -> list[Verdict]:
    """Verify every entry, in numeric key order when possible."""
    ordered = sorted(entries.values(), key=lambda e: (len(e.key), e.key))
    return [verify_entry(entry, matcher) for entry in ordered]


def apply_verdicts(mapping_path: str | Path, verdicts: list[Verdict]) -> int:
    """Write the verdicts back into a mapping JSON; returns how many entries changed.

    Only ``status`` and ``note`` are touched. Previous notes are kept.
    """
    path = Path(mapping_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    changed = 0
    for verdict in verdicts:
        raw = data["classes"][verdict.key]
        note = raw.get("note", "")
        tag = "GBIF: " + verdict.message
        base = note.split(" | GBIF:")[0].strip()
        new_note = base if verdict.status == "verified" else f"{base} | {tag}".strip(" |")
        if raw.get("status") != verdict.status or note != new_note:
            changed += 1
        raw["status"] = verdict.status
        raw["note"] = new_note
    data["taxonomy_source"] = (
        data.get("taxonomy_source", "").split(" Checked against")[0].rstrip()
        + " Checked against the GBIF Backbone (species match API)."
    )
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return changed
