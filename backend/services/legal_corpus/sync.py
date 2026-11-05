"""Legal corpus synchronisation CLI.

Usage (from the repository root)::

    python3 -m backend.services.legal_corpus.sync [--check] [--law SLUG ...]

Behaviour:

* Discovers the current version of every registered P0 law from the
  official National Law Information Center pages and imports any version
  that is not stored yet. Stored versions are never modified in place —
  a changed law creates a *new* version directory.
* When nothing changed, no file is rewritten (byte-identical outputs,
  original ``retrievedAt`` preserved), so repeated runs are idempotent
  and produce empty git diffs.
* A fetch or parse failure aborts the affected law with a classified
  error and leaves every stored version untouched. It never deletes a
  stored version and never marks unverified data as current.
* English translations are probed per version. Because the official
  translations are KLRI/ministerial copyrighted works whose
  redistribution is not permitted, only alignment metadata is stored.
* Annex 7 is downloaded as the official PDF, preserved verbatim, parsed
  into structured JSON and *compared* with the existing calculator
  rules. Calculator amounts are never auto-changed.

The optional DRF Open API cross-check activates only when the
``LAW_API_OC`` environment variable is present; its value is never
logged or written anywhere.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from . import alignment, annex7, diffing
from .client import LawGoKrClient, LawSourceError
from .markdown import render_korean_markdown
from .parser import (
    parse_annex_list,
    parse_english_law_html,
    parse_korean_law_html,
    parse_notice_html,
    sha256_text,
)
from .registry import ALL_LAWS, ANNEX7, P0_NOTICES
from .validator import canonical_json_hash, scan_for_secrets

KST = timezone(timedelta(hours=9))
REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CORPUS_ROOT = REPO_ROOT / "backend" / "data" / "legal-corpus"
LEGAL_RULES_PATH = REPO_ROOT / "backend" / "data" / "enforcement" / "legal_rules.json"

PROVIDER_KO = "국가법령정보센터 (법제처)"
REUSE_KO = (
    "FREE_WITH_ATTRIBUTION — 법령 본문은 저작권법 제7조상 보호받지 못하는 저작물이며, "
    "국가법령정보센터 법령정보는 공공데이터로서 출처 표시를 조건으로 영리 목적 포함 자유 이용이 보장됩니다. "
    "위조·변조 및 출처 미표기는 금지됩니다."
)
REUSE_EN_METADATA_ONLY = (
    "METADATA_ONLY — 공식 영문 번역본의 저작권은 한국법제연구원(또는 소관부처)에 있으며 무단 복제·배포가 "
    "금지되어 있어, 이 코퍼스에는 번역 본문을 저장하지 않고 메타데이터·조문 제목·해시·공식 링크만 저장합니다."
)


def now_iso() -> str:
    return datetime.now(KST).replace(microsecond=0).isoformat()


def _write_if_changed(path: Path, content: bytes) -> bool:
    if path.exists() and path.read_bytes() == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return True


def _json_bytes(obj: Any) -> bytes:
    return (json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=False) + "\n").encode("utf-8")


class CorpusSync:
    def __init__(self, corpus_root: Path, *, check: bool = False, cache_dir: Optional[Path] = None):
        self.root = corpus_root
        self.check = check
        self.client = LawGoKrClient()
        self.cache_dir = cache_dir
        self.changed: List[str] = []
        self.report: Dict[str, Any] = {"laws": [], "notices": [], "errors": []}
        self._html_cache: Dict[str, str] = {}

    # -- fetching with an optional on-disk cache (for reproducible runs) ---

    def _cached(self, key: str, fetch) -> str:
        if key in self._html_cache:
            return self._html_cache[key]
        if self.cache_dir:
            f = self.cache_dir / f"{key}.html"
            if f.exists():
                # Binary round-trip: text mode would normalise CRLF and
                # change the source hash between runs.
                self._html_cache[key] = f.read_bytes().decode("utf-8")
                return self._html_cache[key]
        data = fetch()
        self._html_cache[key] = data
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            (self.cache_dir / f"{key}.html").write_bytes(data.encode("utf-8"))
        return data

    def law_body(self, mst: str, effective_from: str) -> str:
        return self._cached(f"{mst}.ko", lambda: self.client.fetch_law_body_html(mst, effective_from))

    def law_english(self, mst: str) -> str:
        return self._cached(f"{mst}.en", lambda: self.client.fetch_english_body_html(mst))

    # -- one law ------------------------------------------------------------

    def sync_law(self, law: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        slug = law["slug"]
        try:
            current_mst, current_ef = self.client.discover_current(law["titleKo"])
        except LawSourceError as exc:
            self.report["errors"].append({"law": slug, "stage": "discover", "kind": exc.kind, "message": str(exc)})
            return None

        versions_spec = {v["mst"]: v["effectiveFrom"] for v in law["known_versions"]}
        versions_spec[current_mst] = f"{current_ef[:4]}-{current_ef[4:6]}-{current_ef[6:]}"
        ordered = sorted(versions_spec.items(), key=lambda kv: kv[1])

        built: List[Dict[str, Any]] = []
        en_indexes: Dict[str, Dict[str, Any]] = {}
        for mst, effective_from in ordered:
            try:
                html = self.law_body(mst, effective_from)
                parsed = parse_korean_law_html(html)
            except LawSourceError as exc:
                self.report["errors"].append({"law": slug, "stage": "fetch-ko", "mst": mst, "kind": exc.kind})
                return None
            if not parsed["articles"] or not parsed["titleBlock"]:
                self.report["errors"].append({"law": slug, "stage": "parse-ko", "mst": mst, "kind": "parse"})
                return None
            try:
                en_html = self.law_english(mst)
                en_index = parse_english_law_html(en_html)
            except LawSourceError as exc:
                # A failed English fetch is NOT evidence that no official
                # translation exists. Fail the law for this run (the stored
                # snapshot is kept by the fallback) instead of recording a
                # false NOT_AVAILABLE determination.
                self.report["errors"].append({"law": slug, "stage": "fetch-en", "mst": mst, "kind": exc.kind})
                return None
            en_index = dict(en_index)
            en_index["mst"] = mst
            en_index["sourceUrl"] = f"https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq={mst}&urlMode=engLsInfoR&viewCls=engLsInfoR"
            if en_index.get("hasContent"):
                # Same promulgation as the Korean version identified by MST.
                en_index["promulgationNo"] = parsed["titleBlock"]["promulgationNo"]
                en_index["effectiveFrom"] = effective_from
            en_indexes[mst] = en_index
            built.append(
                {
                    "mst": mst,
                    "effectiveFrom": effective_from,
                    "parsed": parsed,
                    "htmlSha256": sha256_text(html.replace("\r\n", "\n")),
                    "annexes": parse_annex_list(html) if slug == "immigration-rule" else [],
                }
            )

        # Translation status per version.
        en_bearing = [b for b in built if en_indexes[b["mst"]].get("hasContent")]
        manifest_versions: List[Dict[str, Any]] = []
        previous_articles: Optional[List[Dict[str, Any]]] = None
        for idx, b in enumerate(built):
            parsed = b["parsed"]
            tb = parsed["titleBlock"]
            articles_doc_articles = [
                {k: a[k] for k in ("articleId", "articleNumber", "branchNumber", "titleKo", "deleted", "paragraphs", "text", "textSha256")}
                for a in parsed["articles"]
            ]
            articles_doc = {
                "lawId": law["lawId"],
                "lawSlug": slug,
                "effectiveFrom": b["effectiveFrom"],
                "articles": articles_doc_articles,
            }
            content_hash = canonical_json_hash(articles_doc)
            vdir_rel = f"laws/{slug}/versions/{b['effectiveFrom']}"
            vdir = self.root / vdir_rel
            meta_path = vdir / "metadata.json"
            existing_meta: Dict[str, Any] = {}
            if meta_path.exists():
                existing_meta = json.loads(meta_path.read_text(encoding="utf-8"))
            unchanged = existing_meta.get("contentSha256") == content_hash and existing_meta.get("sourceIdentifier") == b["mst"]
            retrieved_at = existing_meta.get("retrievedAt") if unchanged else now_iso()

            en_index = en_indexes[b["mst"]]
            if en_index.get("hasContent"):
                align = alignment.align_version(
                    ko_articles=articles_doc_articles,
                    en_index=en_index,
                    ko_promulgation_no=tb["promulgationNo"],
                    ko_effective_from=b["effectiveFrom"],
                )
                translation = {
                    "status": align["status"],
                    "englishVersion": {
                        "mst": b["mst"],
                        "promulgationNo": tb["promulgationNo"],
                        "effectiveFrom": b["effectiveFrom"],
                        "sourceUrl": en_index["sourceUrl"],
                    },
                    "pairs": align["pairs"],
                    "englishArticleCount": align["englishArticleCount"],
                    "koreanArticleCount": align["koreanArticleCount"],
                    "englishOnlyArticles": align["englishOnlyArticles"],
                    "note": "공식 영문 번역본의 본문은 저작권상 재배포가 허용되지 않아 저장하지 않습니다. 조문 제목·해시·대응 관계만 기록합니다.",
                    "checkedAt": retrieved_at,
                }
                translation_provider = "한국법제연구원 (KLRI) — 국가법령정보센터 영문법령"
                translation_updated = b["effectiveFrom"]
            elif en_bearing:
                newest_en = en_bearing[-1]
                translation = {
                    "status": "OLDER_TRANSLATION",
                    "englishVersion": {
                        "mst": newest_en["mst"],
                        "promulgationNo": newest_en["parsed"]["titleBlock"]["promulgationNo"],
                        "effectiveFrom": newest_en["effectiveFrom"],
                        "sourceUrl": en_indexes[newest_en["mst"]]["sourceUrl"],
                    },
                    "pairs": [],
                    "note": "이 한국어 버전에 대응하는 공식 영문 번역본은 아직 제공되지 않습니다. 최신 공식 영문본은 구버전 기준이며, 조문 대응은 해당 구버전 디렉터리의 translation.json을 참조하십시오. 번호가 같다는 이유만으로 현행 조문과 동일시하지 않습니다.",
                    "checkedAt": retrieved_at,
                }
                translation_provider = "한국법제연구원 (KLRI) — 국가법령정보센터 영문법령"
                translation_updated = newest_en["effectiveFrom"]
            else:
                translation = {
                    "status": "NOT_AVAILABLE",
                    "englishVersion": None,
                    "pairs": [],
                    "note": "공식 영문 번역본이 제공되지 않습니다 (국가법령정보센터 영문 페이지가 헤더만 반환함을 확인). 영문 파일을 생성하지 않았습니다.",
                    "checkedAt": retrieved_at,
                }
                translation_provider = None
                translation_updated = None

            priority_present = all(
                any(a["articleId"] == p for a in articles_doc_articles) for p in law.get("priority_articles", [])
            )
            verification = "VERIFIED_OFFICIAL_SNAPSHOT" if priority_present else "VERIFICATION_REQUIRED"

            effective_until = built[idx + 1]["effectiveFrom"] if idx + 1 < len(built) else None
            metadata = {
                "lawId": law["lawId"],
                "titleKo": law["titleKo"],
                "titleEn": law["titleEn"],
                "jurisdiction": law["jurisdiction"],
                "lawType": law["lawType"],
                "promulgationDate": tb["promulgationDate"],
                "promulgationNo": tb["promulgationNo"],
                "promulgationKindKo": tb["lawKindKo"],
                "revisionTypeKo": tb["revisionTypeKo"],
                "effectiveFrom": b["effectiveFrom"],
                "effectiveUntil": effective_until,
                "sourceProvider": PROVIDER_KO,
                "sourceUrl": f"https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq={b['mst']}",
                "sourceIdentifier": b["mst"],
                "retrievedAt": retrieved_at,
                "lastVerifiedAt": retrieved_at,
                "contentSha256": content_hash,
                "sourceFormat": "HTML (law.go.kr lsInfoR) parsed to structured JSON + Markdown",
                "language": "ko",
                "translationProvider": translation_provider,
                "translationUpdatedAt": translation_updated,
                "translationAlignment": translation["status"],
                "reusePermission": REUSE_KO,
                "verificationStatus": verification,
            }
            source_doc = {
                "provider": PROVIDER_KO,
                "sourceUrl": metadata["sourceUrl"],
                "bodyEndpoint": f"https://www.law.go.kr/LSW/lsInfoR.do?lsiSeq={b['mst']}&efYd={b['effectiveFrom'].replace('-', '')}&ancYnChk=0",
                "drfApi": {
                    "lawSearch": "https://www.law.go.kr/DRF/lawSearch.do?target=law",
                    "lawService": "https://www.law.go.kr/DRF/lawService.do?target=law",
                    "note": "DRF Open API는 OC(등록된 식별자 + 서버 IP/도메인)가 필요해, 코퍼스 수집은 동일한 공식 본문을 제공하는 공개 웹 엔드포인트로 수행했습니다. LAW_API_OC가 설정된 환경에서는 sync가 DRF 교차 검증을 시도할 수 있습니다.",
                    "crossCheckPerformed": False,
                },
                "sourceHtmlSha256": b["htmlSha256"],
                "retrievedAt": retrieved_at,
                "reusePermission": REUSE_KO,
            }
            if previous_articles is None:
                changes = {
                    "type": "INITIAL_IMPORT",
                    "previousVersion": None,
                    "note": "이 코퍼스에 처음 수집된 버전입니다. 이전 저장 버전이 없어 조문 diff는 생성하지 않았습니다.",
                }
            else:
                changes = {
                    "type": "VERSION_DIFF",
                    "previousVersion": built[idx - 1]["effectiveFrom"],
                    **diffing.diff_articles(previous_articles, articles_doc_articles),
                }
            previous_articles = articles_doc_articles

            files = {
                "metadata.json": _json_bytes(metadata),
                "source.json": _json_bytes(source_doc),
                "articles.ko.json": _json_bytes(articles_doc),
                "translation.json": _json_bytes(translation),
                "changes.json": _json_bytes(changes),
                "ko.md": render_korean_markdown(metadata, parsed, b["annexes"]).encode("utf-8"),
            }
            if slug == "immigration-rule":
                files["annexes.json"] = _json_bytes({"annexes": b["annexes"]})
            for name, payload in files.items():
                target = vdir / name
                if self.check:
                    if not target.exists() or target.read_bytes() != payload:
                        self.changed.append(str(target.relative_to(self.root)))
                elif _write_if_changed(target, payload):
                    self.changed.append(str(target.relative_to(self.root)))

            manifest_versions.append(
                {
                    "effectiveFrom": b["effectiveFrom"],
                    "promulgationNo": tb["promulgationNo"],
                    "promulgationDate": tb["promulgationDate"],
                    "revisionTypeKo": tb["revisionTypeKo"],
                    "sourceIdentifier": b["mst"],
                    "path": vdir_rel,
                    "articleCount": len(articles_doc_articles),
                    "verificationStatus": verification,
                    "translationAlignment": translation["status"],
                }
            )
            b["articlesDoc"] = articles_doc
            b["translation"] = translation
            b["metadata"] = metadata

        self.report["laws"].append({"slug": slug, "versions": [v["effectiveFrom"] for v in manifest_versions]})
        return {"law": law, "versions": manifest_versions, "built": built}

    # -- Annex 7 --------------------------------------------------------------

    def sync_annex7(self, rule_result: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not rule_result:
            return None
        current = rule_result["built"][-1]
        annex = next((a for a in current["annexes"] if a["titleKo"].startswith("[별표 7]")), None)
        if annex is None:
            self.report["errors"].append({"stage": "annex7", "kind": "parse", "message": "별표 7 not found in Rule annex list"})
            return None
        pdf_bytes: Optional[bytes] = None
        pdf_fl_seq: Optional[str] = None
        file_records = []
        for f in annex["files"]:
            try:
                data = self.client.download_annex_file(f["flSeq"], f["bylClsCd"])
            except LawSourceError as exc:
                self.report["errors"].append({"stage": "annex7-download", "flSeq": f["flSeq"], "kind": exc.kind})
                continue
            fmt = annex7.sniff_format(data)
            file_records.append(
                {"flSeq": f["flSeq"], "bylClsCd": f["bylClsCd"], "detectedFormat": fmt, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)}
            )
            if fmt == "pdf" and pdf_bytes is None:
                pdf_bytes, pdf_fl_seq = data, f["flSeq"]
        if pdf_bytes is None:
            self.report["errors"].append({"stage": "annex7", "kind": "parse", "message": "no PDF variant among Annex 7 files"})
            return None

        tmp_pdf = self.root / ".annex7-tmp.pdf"
        if not self.check:
            tmp_pdf.parent.mkdir(parents=True, exist_ok=True)
            tmp_pdf.write_bytes(pdf_bytes)
            try:
                text = annex7.extract_pdf_text(tmp_pdf)
            finally:
                tmp_pdf.unlink(missing_ok=True)
        else:
            import tempfile

            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as fh:
                fh.write(pdf_bytes)
                tmp_name = fh.name
            try:
                text = annex7.extract_pdf_text(Path(tmp_name))
            finally:
                Path(tmp_name).unlink(missing_ok=True)

        parsed = annex7.parse_annex7_text(text)
        revised = parsed.get("revisedDate")
        if not revised:
            self.report["errors"].append({"stage": "annex7", "kind": "parse", "message": "Annex 7 revision date not parsed"})
            return None
        adir_rel = f"annexes/{ANNEX7['slug']}/versions/{revised}"
        adir = self.root / adir_rel
        metadata = {
            "annexOf": "immigration-rule",
            "parentRuleMst": current["mst"],
            "parentRuleEffectiveFrom": current["effectiveFrom"],
            "annexNo": "7",
            "titleKo": ANNEX7["titleKo"],
            "revisedDate": revised,
            "sourceProvider": PROVIDER_KO,
            "sourceUrl": f"https://www.law.go.kr/LSW/flDownload.do?gubun=&flSeq={pdf_fl_seq}&bylClsCd={ANNEX7['bylClsCd']}",
            "retrievedAt": now_iso(),
            "reusePermission": REUSE_KO,
            "files": file_records,
            "verificationStatus": "VERIFIED_OFFICIAL_SNAPSHOT",
        }
        comparison = None
        if LEGAL_RULES_PATH.exists():
            legal_rules = json.loads(LEGAL_RULES_PATH.read_text(encoding="utf-8"))
            comparison = annex7.compare_with_legal_rules(parsed, legal_rules)
        payloads = {
            "metadata.json": _json_bytes(metadata),
            "annex7.json": _json_bytes(parsed),
            "annex7.txt": text.encode("utf-8"),
            "annex7.pdf": pdf_bytes,
        }
        if comparison is not None:
            payloads["annex7-vs-legal-rules.json"] = _json_bytes(comparison)
        for name, payload in payloads.items():
            target = adir / name
            if name == "metadata.json" and target.exists():
                # Preserve the original retrieval timestamp when the annex
                # itself is unchanged.
                old = json.loads(target.read_text(encoding="utf-8"))
                if old.get("files") == file_records:
                    continue
            if self.check:
                if not target.exists() or target.read_bytes() != payload:
                    self.changed.append(str(target.relative_to(self.root)))
            elif _write_if_changed(target, payload):
                self.changed.append(str(target.relative_to(self.root)))
        return {"path": adir_rel, "revisedDate": revised, "comparison": comparison}

    # -- MOJ notice -------------------------------------------------------------

    def sync_notice(self, notice: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            html = self._cached(f"notice-{notice['admRulSeq']}", lambda: self.client.fetch_notice_body_html(notice["admRulSeq"]))
        except LawSourceError as exc:
            self.report["errors"].append({"notice": notice["slug"], "stage": "fetch", "kind": exc.kind})
            return None
        parsed = parse_notice_html(html)
        ndir_rel = f"notices/{notice['slug']}"
        ndir = self.root / ndir_rel
        existing_notice_meta: Dict[str, Any] = {}
        notice_meta_path = ndir / "metadata.json"
        if notice_meta_path.exists():
            existing_notice_meta = json.loads(notice_meta_path.read_text(encoding="utf-8"))
        notice_retrieved_at = (
            existing_notice_meta.get("retrievedAt")
            if existing_notice_meta.get("contentSha256") == parsed["textSha256"]
            else now_iso()
        )
        tb = parsed["titleBlock"] or {}
        metadata = {
            "slug": notice["slug"],
            "titleKo": notice["titleKo"],
            "noticeNo": notice["noticeNo"],
            "issuer": notice["issuer"],
            "effectiveFrom": tb.get("effectiveFrom") or notice["effectiveFrom"],
            "promulgationDate": tb.get("promulgationDate"),
            "revisionTypeKo": tb.get("revisionTypeKo"),
            "sourceProvider": PROVIDER_KO,
            "sourceUrl": f"https://www.law.go.kr/LSW/admRulLsInfoP.do?admRulSeq={notice['admRulSeq']}",
            "sourceIdentifier": notice["admRulSeq"],
            "retrievedAt": notice_retrieved_at,
            "contentSha256": parsed["textSha256"],
            "related": notice["related"],
            "reusePermission": REUSE_KO,
            "verificationStatus": "VERIFIED_OFFICIAL_SNAPSHOT",
        }
        ko_md = (
            f"# {notice['titleKo']}\n\n"
            f"- 고시번호: {notice['noticeNo']}\n"
            f"- 소관: {notice['issuer']}\n"
            f"- 시행일: {metadata['effectiveFrom']}\n"
            f"- 원문 출처: {PROVIDER_KO} — {metadata['sourceUrl']}\n"
            f"- 수집일: {metadata['retrievedAt']}\n\n"
            f"{parsed['text']}\n"
        )
        for name, payload in {"metadata.json": _json_bytes(metadata), "ko.md": ko_md.encode("utf-8")}.items():
            target = ndir / name
            if self.check:
                if not target.exists() or target.read_bytes() != payload:
                    self.changed.append(str(target.relative_to(self.root)))
            elif _write_if_changed(target, payload):
                self.changed.append(str(target.relative_to(self.root)))
        self.report["notices"].append({"slug": notice["slug"], "effectiveFrom": metadata["effectiveFrom"]})
        return {"slug": notice["slug"], "path": ndir_rel, "effectiveFrom": metadata["effectiveFrom"], "noticeNo": notice["noticeNo"]}

    # -- fallback: keep the stored snapshot when a fetch fails ---------------

    def _stored_result(self, law: Dict[str, Any], previous_entry: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Rebuild a sync result from the already-stored snapshot on disk.

        A failed fetch must never shrink the corpus: the manifest,
        coverage report and article index keep listing the stored,
        verified versions (the fetch error itself is still reported, and
        nothing is re-marked as freshly verified).
        """
        if not previous_entry:
            return None
        built: List[Dict[str, Any]] = []
        for version in previous_entry.get("versions", []):
            vdir = self.root / version["path"]
            articles_file = vdir / "articles.ko.json"
            if not articles_file.exists():
                return None
            translation_file = vdir / "translation.json"
            built.append(
                {
                    "articlesDoc": json.loads(articles_file.read_text(encoding="utf-8")),
                    "translation": json.loads(translation_file.read_text(encoding="utf-8")) if translation_file.exists() else {},
                }
            )
        self.report["laws"].append(
            {"slug": law["slug"], "versions": [v["effectiveFrom"] for v in previous_entry["versions"]], "keptStoredSnapshot": True}
        )
        return {"law": law, "versions": previous_entry["versions"], "built": built}

    # -- top level -----------------------------------------------------------

    def run(self, law_slugs: Optional[List[str]] = None) -> Dict[str, Any]:
        previous_manifest: Dict[str, Any] = {}
        manifest_file = self.root / "manifest.json"
        if manifest_file.exists():
            previous_manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
        previous_laws = {entry["slug"]: entry for entry in previous_manifest.get("laws", [])}

        results: List[Dict[str, Any]] = []
        for law in ALL_LAWS:
            if law_slugs and law["slug"] not in law_slugs:
                continue
            result = self.sync_law(law)
            if result is None:
                result = self._stored_result(law, previous_laws.get(law["slug"]))
                if result is not None:
                    self.report["errors"].append(
                        {"law": law["slug"], "stage": "fallback", "kind": "stored-snapshot-kept"}
                    )
            if result:
                results.append(result)
        rule_result = next((r for r in results if r["law"]["slug"] == "immigration-rule"), None)
        annex_result = self.sync_annex7(rule_result) if not law_slugs or "immigration-rule" in law_slugs else None
        if annex_result is None and previous_manifest.get("annexes"):
            prev_annex = previous_manifest["annexes"][0]
            annex_result = {"path": prev_annex["path"], "revisedDate": prev_annex["revisedDate"], "comparison": None}
        notice_results = []
        previous_notices = {n["slug"]: n for n in previous_manifest.get("notices", [])}
        for notice in P0_NOTICES:
            synced = self.sync_notice(notice)
            if synced is not None:
                notice_results.append(synced)
            elif notice["slug"] in previous_notices:
                notice_results.append(previous_notices[notice["slug"]])

        manifest = {
            "corpus": "Visable Legal Corpus — Korean immigration law (official sources only)",
            "corpusVersion": "1.1.0",
            "jurisdiction": "KR",
            "languages": ["ko", "en (metadata only — redistribution restricted)"],
            "laws": [
                {
                    "slug": r["law"]["slug"],
                    "lawId": r["law"]["lawId"],
                    "titleKo": r["law"]["titleKo"],
                    "titleEn": r["law"]["titleEn"],
                    "lawType": r["law"]["lawType"],
                    "priority": r["law"]["priority"],
                    "versions": r["versions"],
                }
                for r in results
            ],
            "notices": notice_results,
            "annexes": ([{"slug": ANNEX7["slug"], **{k: annex_result[k] for k in ("path", "revisedDate")}}] if annex_result else []),
        }
        coverage = self._coverage(results, annex_result)
        index = self._article_index(results)

        for name, payload in {
            "manifest.json": _json_bytes(manifest),
            "coverage-report.json": _json_bytes(coverage),
            "indexes/articles-index.json": _json_bytes(index),
        }.items():
            target = self.root / name
            if self.check:
                if not target.exists() or target.read_bytes() != payload:
                    self.changed.append(name)
            elif _write_if_changed(target, payload):
                self.changed.append(name)

        if annex_result and annex_result.get("comparison") is not None:
            target = self.root / "rules" / "annex7-vs-legal-rules.diff.json"
            payload = _json_bytes(annex_result["comparison"])
            if self.check:
                if not target.exists() or target.read_bytes() != payload:
                    self.changed.append("rules/annex7-vs-legal-rules.diff.json")
            elif _write_if_changed(target, payload):
                self.changed.append("rules/annex7-vs-legal-rules.diff.json")

        if not self.check:
            findings = scan_for_secrets(self.root)
            if findings:
                self.report["errors"].append({"stage": "secret-scan", "findings": findings})
        self.report["changedFiles"] = sorted(set(self.changed))
        self.report["manifestLaws"] = [law["slug"] for law in manifest["laws"]]
        return self.report

    def _coverage(self, results: List[Dict[str, Any]], annex_result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        laws_cov = []
        total_ko = total_en_aligned = 0
        for r in results:
            law = r["law"]
            versions_cov = []
            for v, b in zip(r["versions"], r["built"]):
                articles = b["articlesDoc"]["articles"]
                priority = law.get("priority_articles", [])
                versions_cov.append(
                    {
                        "effectiveFrom": v["effectiveFrom"],
                        "articleCount": len(articles),
                        "priorityArticles": {p: any(a["articleId"] == p for a in articles) for p in priority},
                        "translationAlignment": v["translationAlignment"],
                        "englishArticleCount": b["translation"].get("englishArticleCount"),
                    }
                )
                total_ko += len(articles)
                if v["translationAlignment"] == "ALIGNED":
                    total_en_aligned += len(articles)
            laws_cov.append({"slug": law["slug"], "titleKo": law["titleKo"], "versions": versions_cov})
        return {
            "generatedBy": "backend.services.legal_corpus.sync",
            "scope": "P0 (Immigration Act / Enforcement Decree / Enforcement Rule / MOJ Notice 2020-212 / Annex 7) + P1 (Framework Act on Treatment of Foreigners / Refugee Act family / Nationality Act family / Act on the Employment of Foreign Workers family)",
            "laws": laws_cov,
            "annex7": (
                {"stored": True, "revisedDate": annex_result["revisedDate"], "path": annex_result["path"]}
                if annex_result
                else {"stored": False, "reason": "see sync errors"}
            ),
            "totals": {
                "koreanArticlesStored": total_ko,
                "articlesWithAlignedOfficialEnglish": total_en_aligned,
                "englishBodyTextStored": 0,
                "englishNote": "Official English body text is never stored (KLRI/ministerial copyright, redistribution prohibited). Alignment metadata only.",
            },
            "notCovered": [
                {"item": "출입국관리법 시행규칙 영문본", "status": "NOT_AVAILABLE", "reason": "국가법령정보센터 영문 페이지가 현행·직전 버전 모두 본문 없이 헤더만 반환함을 2026-11-04 확인"},
                {"item": "P1 시행규칙 3종 영문본 (난민법·국적법·외국인근로자 고용법 시행규칙)", "status": "NOT_AVAILABLE", "reason": "국가법령정보센터 영문 페이지가 현행 버전에서 본문 없이 헤더만 반환함을 2026-11-05 확인. 부처 시행규칙은 출입국관리법 시행규칙과 동일하게 영문 본문이 제공되지 않는 패턴"},
            ],
        }

    def _article_index(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        entries: List[Dict[str, Any]] = []
        for r in results:
            slug = r["law"]["slug"]
            by_article: Dict[str, Dict[str, Any]] = {}
            for v, b in zip(r["versions"], r["built"]):
                for a in b["articlesDoc"]["articles"]:
                    entry = by_article.setdefault(
                        a["articleId"], {"lawSlug": slug, "articleId": a["articleId"], "titleKo": a.get("titleKo"), "versions": []}
                    )
                    entry["versions"].append(v["effectiveFrom"])
            entries.extend(by_article.values())
        entries.sort(key=lambda e: (e["lawSlug"], [int(x) for x in e["articleId"].split("-")]))
        return {"articles": entries}


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Sync the Visable legal corpus from official sources")
    parser.add_argument("--check", action="store_true", help="report what would change; write nothing")
    parser.add_argument("--law", action="append", dest="laws", help="limit to a law slug (repeatable)")
    parser.add_argument("--corpus-root", type=Path, default=DEFAULT_CORPUS_ROOT)
    parser.add_argument("--cache-dir", type=Path, default=None, help="optional HTML cache directory")
    args = parser.parse_args(argv)

    sync = CorpusSync(args.corpus_root, check=args.check, cache_dir=args.cache_dir)
    report = sync.run(args.laws)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
