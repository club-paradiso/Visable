"""A bounded, JSON-compatible evidence package for the model (spec 07 §5).

Why: the backend appends law text to one flat prompt with no size cap, no
record of what was cut, and no line between "source text" and "instructions".
The package fixes the shape instead:

* at most 12 items, 2,400 characters of source text per item and 20,000 in
  total (``PackageLimits``). Anything cut or dropped is recorded in
  ``truncation``; nothing is cut silently. ``text_sha256`` is the hash of the
  *full* source text, so a truncated item can still be checked against its
  source;
* every item carries its identity, version key, effective date (for the
  provision), provision key, scope, verification summary, provenance and
  attribution, and its text is marked ``text_role = "quoted_source_data"``;
* instruction-like text is flagged per item (``untrusted_content_flags``, see
  ``injection.py``) and stays quoted data; flags never change a verification;
* ``public_view()`` is what a client sees: no ``diagnostics`` (upstream call
  counts, lookup errors, raw URLs), only allowlisted official URLs with the
  Open-API user id stripped, layer codes without free-text detail, and no
  synthetic-fixture text unless a test asks for it explicitly.

Real statute text is not protected by copyright (저작권법 제7조) but it is
attributed: items from law.go.kr carry ``LAW_GO_KR_ATTRIBUTION`` and their
retrieval provenance (URL, ``retrieved_at``, capture ``content_sha256``).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
from urllib.parse import urlsplit

from waymaker_ai.contracts import (
    AnchorKind,
    ClaimVerification,
    GuidanceItem,
    ProvenanceStatus,
    ProvisionText,
    RelevantDates,
    Scope,
    SourceFamily,
    SourceIdentity,
    SourceVersion,
    sha256_text,
)
from waymaker_ai.legal.citations import article_key_of
from waymaker_ai.legal.identity import is_official_url, public_official_url
from waymaker_ai.legal.injection import scan_flags

PACKAGE_VERSION = "wlie-evidence/0.1"
LAW_GO_KR_ATTRIBUTION = "출처: 법제처 국가법령정보센터 (law.go.kr)"
SYNTHETIC_ATTRIBUTION = "synthetic test fixture: fictional, not legal information"
TEXT_ROLE = "quoted_source_data"
LAW_GO_KR_HOSTS = frozenset({"law.go.kr", "www.law.go.kr", "open.law.go.kr"})


@dataclass(frozen=True)
class PackageLimits:
    max_items: int = 12
    max_item_chars: int = 2400
    max_total_chars: int = 20000


DEFAULT_LIMITS = PackageLimits()


@dataclass(frozen=True)
class EvidenceSource:
    """One provision or guidance item offered to the package, with its context."""

    evidence_id: str
    kind: str                                   # "provision" | "guidance"
    text: str
    identity: Optional[SourceIdentity] = None
    version: Optional[SourceVersion] = None
    provision_key: Optional[str] = None
    heading: Optional[str] = None
    scope: Optional[Scope] = None
    official_url: Optional[str] = None
    provenance: ProvenanceStatus = ProvenanceStatus.UNVERIFIED
    family: Optional[SourceFamily] = None
    topic: Optional[str] = None
    value: Optional[str] = None
    edition_date: Optional[str] = None
    review_state: Optional[str] = None
    verification: Optional[Mapping[str, Any]] = None

    @classmethod
    def from_provision(
        cls, text: ProvisionText, *, identity: Optional[SourceIdentity] = None,
        version: Optional[SourceVersion] = None, verification: Optional[Mapping[str, Any]] = None,
    ) -> "EvidenceSource":
        return cls(
            evidence_id=text.evidence_id, kind="provision", text=text.full_text(), identity=identity,
            version=version, provision_key=text.provision_key, heading=text.heading, scope=text.scope,
            official_url=text.official_url or (version.official_url if version else None),
            provenance=text.provenance, family=identity.family if identity else None, verification=verification,
        )

    @classmethod
    def from_guidance(cls, item: GuidanceItem, *, verification: Optional[Mapping[str, Any]] = None) -> "EvidenceSource":
        return cls(
            evidence_id=item.evidence_id, kind="guidance", text=item.text, scope=item.scope, family=item.family,
            topic=item.topic, value=item.value,
            edition_date=item.edition_date.isoformat() if item.edition_date else None,
            review_state=item.review_state, verification=verification,
        )


def _scope_dict(scope: Optional[Scope]) -> Optional[Dict[str, Any]]:
    if scope is None:
        return None
    data = asdict(scope)
    for key in ("status_codes", "subcodes", "procedures"):
        data[key] = list(data[key])
    return data


def _identity_dict(identity: Optional[SourceIdentity]) -> Optional[Dict[str, Any]]:
    if identity is None:
        return None
    return {
        "provider": identity.provider,
        "stable_id": identity.stable_id,
        "official_title": identity.official_title,
        "former_titles": list(identity.former_titles),
        "short_titles": list(identity.short_titles),
        "family": identity.family.value,
        "authority_type": identity.authority_type,
    }


def _attribution(source: EvidenceSource) -> Optional[str]:
    if source.provenance is ProvenanceStatus.SYNTHETIC_FIXTURE:
        return SYNTHETIC_ATTRIBUTION
    url = source.official_url
    host = urlsplit(url).hostname if url and is_official_url(url) else None
    provider = source.identity.provider if source.identity else None
    if host in LAW_GO_KR_HOSTS or provider in LAW_GO_KR_HOSTS:
        return LAW_GO_KR_ATTRIBUTION
    return None


def _item(source: EvidenceSource, text: str, truncated: bool) -> Dict[str, Any]:
    version = source.version
    article = article_key_of(source.provision_key) if source.provision_key else None
    effective = version.effective_date_for(article) if version else None
    return {
        "evidence_id": source.evidence_id,
        "kind": source.kind,
        "identity": _identity_dict(source.identity),
        "family": source.family.value if source.family else None,
        "version_key": list(version.key) if version else None,
        "effective_date": effective.isoformat() if effective else None,
        "promulgation_date": version.promulgation_date.isoformat() if version and version.promulgation_date else None,
        "provision_key": source.provision_key,
        "heading": source.heading,
        "topic": source.topic,
        "value": source.value,
        "edition_date": source.edition_date,
        "review_state": source.review_state,
        "text_role": TEXT_ROLE,
        "text": text,
        "text_chars": len(source.text),
        "truncated": truncated,
        "text_sha256": sha256_text(source.text),
        "scope": _scope_dict(source.scope),
        "verification": dict(source.verification) if source.verification else None,
        "untrusted_content_flags": list(scan_flags(source.text)),
        "provenance": source.provenance.value,
        "attribution": _attribution(source),
        "official_url": public_official_url(source.official_url),
        "retrieved_at": version.retrieved_at if version else None,
        "content_sha256": version.content_sha256 if version else None,
    }


def _claim_public(claim: Mapping[str, Any]) -> Dict[str, Any]:
    """Layer codes without free-text detail: details can carry lookup errors."""
    return {
        "claim_id": claim["claim_id"],
        "overall": claim["overall"],
        "highest_verified_layer": claim["highest_verified_layer"],
        "layers": [{k: layer[k] for k in ("layer", "outcome", "code")} for layer in claim["layers"]],
        "conflicts": [{k: c[k] for k in ("topic", "kind", "evidence_ids", "requires_review")}
                      for c in claim.get("conflicts", [])],
    }


@dataclass(frozen=True)
class EvidencePackage:
    question: str
    relevant_dates: Dict[str, str]
    anchor: Optional[str]
    anchor_date: Optional[str]
    items: Tuple[Dict[str, Any], ...]
    claims: Tuple[Dict[str, Any], ...]
    truncation: Tuple[Dict[str, Any], ...]
    limits: Dict[str, int]
    diagnostics: Dict[str, Any] = field(default_factory=dict)
    package_version: str = PACKAGE_VERSION

    @property
    def total_chars(self) -> int:
        return sum(len(item["text"]) for item in self.items)

    def to_dict(self) -> Dict[str, Any]:
        """The full package, diagnostics included (server side only)."""
        return {
            "package_version": self.package_version,
            "question": self.question,
            "relevant_dates": dict(self.relevant_dates),
            "anchor": self.anchor,
            "anchor_date": self.anchor_date,
            "items": [dict(item) for item in self.items],
            "claims": [dict(claim) for claim in self.claims],
            "truncation": [dict(record) for record in self.truncation],
            "limits": dict(self.limits),
            "diagnostics": json.loads(json.dumps(self.diagnostics, default=str)),
        }

    def public_view(self, *, allow_synthetic: bool = False) -> Dict[str, Any]:
        """What a client receives. Synthetic-fixture items are withheld unless ``allow_synthetic``."""
        data = self.to_dict()
        data.pop("diagnostics")
        items = data["items"]
        if not allow_synthetic:
            withheld = [i["evidence_id"] for i in items if i["provenance"] == ProvenanceStatus.SYNTHETIC_FIXTURE.value]
            data["items"] = [i for i in items if i["provenance"] != ProvenanceStatus.SYNTHETIC_FIXTURE.value]
            data["withheld_synthetic_items"] = len(withheld)
        data["claims"] = [_claim_public(c) for c in data["claims"]]
        return data

    def fingerprint(self) -> str:
        """sha256 of the canonical public content (synthetic items included), for audit records."""
        canonical = json.dumps(self.public_view(allow_synthetic=True), ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _dates_dict(dates: RelevantDates) -> Dict[str, str]:
    return {name: value.isoformat() for name, value in dates.present().items()}


def build_evidence_package(
    *,
    question: str,
    dates: RelevantDates,
    anchor: Optional[AnchorKind],
    sources: Sequence[EvidenceSource],
    verifications: Sequence[ClaimVerification] = (),
    diagnostics: Optional[Mapping[str, Any]] = None,
    limits: PackageLimits = DEFAULT_LIMITS,
) -> EvidencePackage:
    """Assemble the package in the order given, within ``limits``; record every cut."""
    items: List[Dict[str, Any]] = []
    truncation: List[Dict[str, Any]] = []
    raw_urls: Dict[str, str] = {}
    seen = set()
    used = 0
    for source in sources:
        if source.evidence_id in seen:
            continue
        seen.add(source.evidence_id)
        original = len(source.text)
        if len(items) >= limits.max_items:
            truncation.append(_cut(source, "item_count_limit", "dropped", original, 0))
            continue
        remaining = limits.max_total_chars - used
        if remaining <= 0:
            truncation.append(_cut(source, "total_char_limit", "dropped", original, 0))
            continue
        text = source.text
        if len(text) > limits.max_item_chars:
            text = text[:limits.max_item_chars]
            truncation.append(_cut(source, "item_char_limit", "truncated", original, len(text)))
        if len(text) > remaining:
            text = text[:remaining]
            truncation.append(_cut(source, "total_char_limit", "truncated", original, len(text)))
        used += len(text)
        items.append(_item(source, text, truncated=len(text) < original))
        if source.official_url:
            raw_urls[source.evidence_id] = source.official_url
    anchor_date = dates.get(anchor) if anchor is not None else None
    private = dict(diagnostics or {})
    private["raw_urls"] = raw_urls
    private["rejected_urls"] = sorted(e for e, url in raw_urls.items() if not is_official_url(url))
    return EvidencePackage(
        question=question,
        relevant_dates=_dates_dict(dates),
        anchor=anchor.value if anchor is not None else None,
        anchor_date=anchor_date.isoformat() if anchor_date else None,
        items=tuple(items),
        claims=tuple(v.to_dict() for v in verifications),
        truncation=tuple(truncation),
        limits=asdict(limits),
        diagnostics=private,
    )


def _cut(source: EvidenceSource, reason: str, action: str, original: int, kept: int) -> Dict[str, Any]:
    return {"evidence_id": source.evidence_id, "reason": reason, "action": action,
            "original_chars": original, "kept_chars": kept}


def sources_from_report(report: Any) -> List[EvidenceSource]:
    """Evidence sources of a ``verification.VerificationReport``: cited provisions first, then guidance.

    The attributed version's text comes first; the candidate's text is added
    when it differs, so the model sees both sides of a version mismatch.
    """
    summary_base = {"claim_id": report.claim_id, "overall": report.overall().value}
    sources: List[EvidenceSource] = []
    for check in report.citation_checks:
        verification = dict(summary_base, layer_codes={r.layer.value: r.code.value for r in check.layers})
        pairs = [(check.attributed_provision, check.attributed_version), (check.candidate_provision, check.candidate)]
        for text, version in pairs:
            if text is not None:
                sources.append(EvidenceSource.from_provision(text, identity=check.identity, version=version,
                                                             verification=verification))
    for item in report.guidance:
        sources.append(EvidenceSource.from_guidance(item, verification=summary_base))
    return sources


def package_from_report(
    report: Any, *, question: str, dates: RelevantDates, anchor: Optional[AnchorKind],
    diagnostics: Optional[Mapping[str, Any]] = None, limits: PackageLimits = DEFAULT_LIMITS,
) -> EvidencePackage:
    return build_evidence_package(
        question=question, dates=dates, anchor=anchor, sources=sources_from_report(report),
        verifications=[report], diagnostics=diagnostics, limits=limits,
    )


__all__ = [
    "DEFAULT_LIMITS",
    "EvidencePackage",
    "EvidenceSource",
    "LAW_GO_KR_ATTRIBUTION",
    "PACKAGE_VERSION",
    "PackageLimits",
    "SYNTHETIC_ATTRIBUTION",
    "TEXT_ROLE",
    "build_evidence_package",
    "package_from_report",
    "sources_from_report",
]
