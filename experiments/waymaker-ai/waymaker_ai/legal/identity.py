"""Exact legal-source identity: titles, official hosts, and bundle records.

Why this module exists: the backend matches a law title by stripping
whitespace and accepting the first search row, so 「출입국관리법 시행령」 can stand
in for 「출입국관리법」 and a near spelling can stand in for either. WLIE treats a
title as a *name*, never as an identity (spec 06 §1):

* A title resolves only by an exact match after ``contracts.compact()``,
  against the official, former and short titles the source prints.
* Near matches are listed for a person reading ``detail``. They are never
  returned as the identity (spec 07 §2, invariant 3).
* Any URL that is shown or fetched must point at an allowlisted official host
  (``contracts.OFFICIAL_SOURCE_HOSTS``). The check is on the parsed host, not on
  a substring, so ``https://law.go.kr.example.com`` and
  ``https://law.go.kr@example.com`` are rejected.

It also turns source-bundle records into ``SourceIdentity`` and
``SourceVersion`` so that every consumer reads a bundle the same way.
"""
from __future__ import annotations

import difflib
from typing import Any, Iterable, List, Mapping, Optional, Sequence, Tuple
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from waymaker_ai.contracts import (
    OFFICIAL_SOURCE_HOSTS,
    ParseStatus,
    ProvenanceStatus,
    SourceFamily,
    SourceIdentity,
    SourceVersion,
    compact,
    normalize_text,
    parse_date,
)

DECREE_SUFFIX = "시행령"
RULE_SUFFIX = "시행규칙"

#: Near matches below this similarity are not worth showing a reviewer.
NEAR_MATCH_MIN_RATIO = 0.6

#: Query keys an official URL may keep when it is shown publicly. Everything
#: else (notably ``OC``, the Open API user id) is dropped, never echoed.
PUBLIC_QUERY_KEYS = frozenset({
    "lsiSeq", "efYd", "MST", "ID", "lsId", "admRulSeq", "chrClsCd", "joNo", "target", "type",
})


# ---------------------------------------------------------------------------
# Titles
# ---------------------------------------------------------------------------
def title_key(title: str) -> str:
    """The comparison key of a title: ``compact()`` of it, nothing looser."""
    return compact(title)


def titles_of(identity: SourceIdentity, *, current_only: bool = False) -> Tuple[str, ...]:
    """Titles an identity answers to. ``current_only`` leaves out former titles.

    A current-title index (scenario G) knows the official title and the
    official short title, not the names a law had before it was renamed.
    """
    if current_only:
        return (identity.official_title,) + tuple(identity.short_titles)
    return identity.all_titles()


def matches_title(identity: SourceIdentity, title: str, *, current_only: bool = False) -> bool:
    key = title_key(title)
    return bool(key) and any(title_key(candidate) == key for candidate in titles_of(identity, current_only=current_only))


def exact_matches(
    identities: Iterable[SourceIdentity], title: str, *, current_only: bool = False
) -> List[SourceIdentity]:
    """Every identity with an exact compact match. More than one is ambiguity, not a choice."""
    found: List[SourceIdentity] = []
    seen = set()
    for identity in identities:
        if identity.stable_id in seen:
            continue
        if matches_title(identity, title, current_only=current_only):
            found.append(identity)
            seen.add(identity.stable_id)
    return found


def near_matches(
    identities: Iterable[SourceIdentity], title: str, *, limit: int = 5, current_only: bool = False
) -> List[str]:
    """Titles that resemble ``title`` without matching it. For ``detail`` only.

    Containment (a prefix, the Act inside its decree's title) ranks first, then
    ``difflib`` similarity. The result is a list of display strings, never
    identities, so a caller cannot accidentally substitute one. ``current_only``
    keeps a current-title index from listing names it does not know.
    """
    key = title_key(title)
    if not key:
        return []
    scored: List[Tuple[float, str, str]] = []
    for identity in identities:
        best: Optional[Tuple[float, str]] = None
        for candidate in titles_of(identity, current_only=current_only):
            candidate_key = title_key(candidate)
            if not candidate_key or candidate_key == key:
                continue
            if key in candidate_key or candidate_key in key:
                score = 1.0 + min(len(key), len(candidate_key)) / max(len(key), len(candidate_key))
            else:
                score = difflib.SequenceMatcher(None, key, candidate_key).ratio()
            if score >= NEAR_MATCH_MIN_RATIO and (best is None or score > best[0]):
                best = (score, candidate)
        if best is not None:
            scored.append((best[0], best[1], identity.stable_id))
    scored.sort(key=lambda row: (-row[0], row[1], row[2]))
    return [f"{candidate} ({stable_id})" for _, candidate, stable_id in scored[:limit]]


def title_kind(title: str) -> str:
    """'rule', 'decree' or 'act', read from the title's suffix. Used for short forms only."""
    key = title_key(title)
    if key.endswith(RULE_SUFFIX):
        return "rule"
    if key.endswith(DECREE_SUFFIX):
        return "decree"
    return "act"


def act_title_of(title: str) -> str:
    """'X 시행령' / 'X 시행규칙' → 'X'. Any other title is returned normalized."""
    value = normalize_text(title)
    for suffix in (RULE_SUFFIX, DECREE_SUFFIX):
        if value.replace(" ", "").endswith(suffix):
            trimmed = value[: len(value) - len(suffix)] if value.endswith(suffix) else value
            return trimmed.rstrip()
    return value


def decree_title_of(title: str) -> str:
    return f"{act_title_of(title)} {DECREE_SUFFIX}"


def rule_title_of(title: str) -> str:
    return f"{act_title_of(title)} {RULE_SUFFIX}"


# ---------------------------------------------------------------------------
# Official hosts
# ---------------------------------------------------------------------------
def is_official_url(url: Optional[str]) -> bool:
    """True only for an http(s) URL whose parsed host is in OFFICIAL_SOURCE_HOSTS."""
    if not url or not isinstance(url, str):
        return False
    if any(ch.isspace() or ord(ch) < 0x20 for ch in url) or "\\" in url:
        return False
    try:
        parts = urlsplit(url)
        port = parts.port
    except ValueError:
        return False
    if parts.scheme not in ("https", "http"):
        return False
    if parts.username is not None or parts.password is not None:
        return False
    if port is not None and port != (443 if parts.scheme == "https" else 80):
        return False
    host = parts.hostname
    if not host or not host.isascii():
        return False
    return host in OFFICIAL_SOURCE_HOSTS


def public_official_url(url: Optional[str]) -> Optional[str]:
    """An allowlisted URL with only PUBLIC_QUERY_KEYS kept; None for anything else."""
    if not is_official_url(url):
        return None
    parts = urlsplit(url or "")
    kept = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True) if key in PUBLIC_QUERY_KEYS]
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(kept), ""))


# ---------------------------------------------------------------------------
# Bundle records
# ---------------------------------------------------------------------------
def identity_from_record(record: Mapping[str, Any]) -> SourceIdentity:
    return SourceIdentity(
        provider=str(record["provider"]),
        family=SourceFamily(record["family"]),
        stable_id=str(record["stable_id"]),
        official_title=normalize_text(record["official_title"]),
        former_titles=tuple(normalize_text(t) for t in record.get("former_titles") or ()),
        short_titles=tuple(normalize_text(t) for t in record.get("short_titles") or ()),
        competent_ministry=record.get("competent_ministry"),
    )


def provision_key_of(value: str) -> str:
    """Bundle provision keys are compared without spaces ('제 73 조' == '제73조')."""
    return normalize_text(value).replace(" ", "")


def version_from_record(record: Mapping[str, Any]) -> SourceVersion:
    changed = record.get("changed_provisions")
    return SourceVersion(
        stable_id=str(record["stable_id"]),
        version_id=str(record["version_id"]),
        effective_date=parse_date(record.get("effective_date")),
        promulgation_date=parse_date(record.get("promulgation_date")),
        promulgation_no=record.get("promulgation_no"),
        amendment_type=record.get("amendment_type"),
        end_date=parse_date(record.get("end_date")),
        provision_effective_dates={
            provision_key_of(key): parse_date(value)
            for key, value in (record.get("provision_effective_dates") or {}).items()
        },
        official_url=record.get("official_url"),
        retrieved_at=record.get("retrieved_at"),
        content_sha256=record.get("content_sha256"),
        parse_status=ParseStatus(record.get("parse_status") or ParseStatus.NOT_PARSED.value),
        provenance=ProvenanceStatus(record.get("provenance") or ProvenanceStatus.UNVERIFIED.value),
        has_transitional_provisions=record.get("has_transitional_provisions"),
        is_repeal=bool(record.get("is_repeal", False)),
        changed_provisions=None if changed is None else tuple(provision_key_of(key) for key in changed),
    )


def load_identities(bundle: Mapping[str, Any]) -> List[SourceIdentity]:
    return [identity_from_record(record) for record in bundle.get("identities") or ()]


def load_versions(bundle: Mapping[str, Any], stable_id: Optional[str] = None) -> List[SourceVersion]:
    """Versions of one identity (or all), oldest first; undated versions last."""
    versions = [
        version_from_record(record)
        for record in bundle.get("versions") or ()
        if stable_id is None or str(record.get("stable_id")) == stable_id
    ]
    return sort_versions(versions)


def sort_versions(versions: Sequence[SourceVersion]) -> List[SourceVersion]:
    return sorted(
        versions,
        key=lambda v: (v.effective_date is None, v.effective_date.isoformat() if v.effective_date else "", v.version_id),
    )
