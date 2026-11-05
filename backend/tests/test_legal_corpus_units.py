"""Unit tests for the legal corpus machinery (no network, no corpus writes).

Covers the parser normalisation rules, the English 'header-only shell'
detection, alignment status logic, the Annex 7 tier state machine, the
version diff, the metadata validator, and the read-only adapter's
date-based version selection — including the safety rule that an
uncovered date must yield VERIFICATION_REQUIRED, never a guessed basis.
"""

from __future__ import annotations

from backend.services.legal_corpus.adapter import LegalCorpus
from backend.services.legal_corpus.alignment import align_version
from backend.services.legal_corpus.annex7 import parse_period_tiers, sniff_format
from backend.services.legal_corpus.diffing import diff_articles
from backend.services.legal_corpus.parser import normalize_statute_text, parse_english_law_html
from backend.services.legal_corpus.validator import validate_metadata


# ---------------------------------------------------------------------------
# parser normalisation
# ---------------------------------------------------------------------------

def test_normalize_rejoins_link_split_tokens():
    # The provider HTML splits tokens at hyperlink boundaries; the stored
    # text must read as the official printed statute reads.
    assert normalize_statute_text("제3조 제1항 을 위반한 경우 )") == "제3조제1항을 위반한 경우)"
    assert normalize_statute_text("제21조 제1항 단서에 따라 신고") == "제21조제1항 단서에 따라 신고"
    assert normalize_statute_text("  다중   공백  정리 ") == "다중 공백 정리"


def test_normalize_does_not_change_words():
    src = "외국인이 대한민국에서 취업하려면 체류자격에 해당하는 활동을 해야 한다."
    assert normalize_statute_text(src) == src


# ---------------------------------------------------------------------------
# English shell detection
# ---------------------------------------------------------------------------

def test_english_header_only_shell_is_not_content():
    shell = "<html><body><h2></h2><p>[Enforcement Date 02. Oct, 2026]</p></body></html>"
    parsed = parse_english_law_html(shell)
    assert parsed["hasContent"] is False
    assert parsed["articles"] == []


# ---------------------------------------------------------------------------
# alignment
# ---------------------------------------------------------------------------

def _ko(*ids):
    return [{"articleId": i, "titleKo": f"제목{i}"} for i in ids]


def _en(ids, promulgation_no="100", effective_from="2026-01-23"):
    return {
        "hasContent": True,
        "articles": [{"articleId": i, "titleEn": f"Title {i}", "textSha256": "x" * 64} for i in ids],
        "mst": "999",
        "promulgationNo": promulgation_no,
        "effectiveFrom": effective_from,
        "sourceUrl": "https://www.law.go.kr/LSW/engLsInfoR.do?lsiSeq=999",
    }


def test_alignment_same_promulgation_full_coverage():
    result = align_version(
        ko_articles=_ko("1", "2"), en_index=_en(["1", "2"]),
        ko_promulgation_no="100", ko_effective_from="2026-01-23",
    )
    assert result["status"] == "ALIGNED"
    assert all(p["status"] == "ALIGNED" for p in result["pairs"])


def test_alignment_same_promulgation_partial_coverage():
    result = align_version(
        ko_articles=_ko("1", "2", "3"), en_index=_en(["1", "2"]),
        ko_promulgation_no="100", ko_effective_from="2026-01-23",
    )
    assert result["status"] == "PARTIAL"


def test_alignment_number_match_across_versions_is_never_aligned():
    # Same article numbers, different promulgation: correspondence by
    # number alone must NOT be reported as aligned.
    result = align_version(
        ko_articles=_ko("1", "2"), en_index=_en(["1", "2"], promulgation_no="99", effective_from="2025-01-01"),
        ko_promulgation_no="100", ko_effective_from="2026-01-23",
    )
    assert result["status"] == "OLDER_TRANSLATION"
    assert all(p["status"] == "UNVERIFIED" for p in result["pairs"])


def test_alignment_no_content_is_not_available():
    result = align_version(
        ko_articles=_ko("1"), en_index={"hasContent": False, "articles": [], "mst": "1"},
        ko_promulgation_no="100", ko_effective_from="2026-01-23",
    )
    assert result["status"] == "NOT_AVAILABLE"
    assert result["pairs"] == []


# ---------------------------------------------------------------------------
# Annex 7
# ---------------------------------------------------------------------------

def test_sniff_format_uses_magic_bytes_not_labels():
    assert sniff_format(b"%PDF-1.7 rest") == "pdf"
    assert sniff_format(bytes.fromhex("d0cf11e0a1b11ae1") + b"rest") == "hwp"


def test_parse_period_tiers_handles_pdf_column_interleaving():
    # Layout taken from the official PDF: an upper bound may be printed
    # after its amount, just before the next tier's lower bound.
    segment = "1개월 미만 200만원 1개월 이상 300만원 3개월 미만 3개월 이상 400만원 6개월 미만 6개월 이상 700만원"
    tiers = parse_period_tiers(segment)
    assert tiers == [
        {"minimumMonths": 0, "maximumMonths": 1, "amountKrw": 2_000_000},
        {"minimumMonths": 1, "maximumMonths": 3, "amountKrw": 3_000_000},
        {"minimumMonths": 3, "maximumMonths": 6, "amountKrw": 4_000_000},
        {"minimumMonths": 6, "maximumMonths": None, "amountKrw": 7_000_000},
    ]


# ---------------------------------------------------------------------------
# diffing
# ---------------------------------------------------------------------------

def test_diff_articles_added_removed_modified():
    old = [
        {"articleId": "1", "textSha256": "a"},
        {"articleId": "2", "textSha256": "b"},
        {"articleId": "3", "textSha256": "c"},
    ]
    new = [
        {"articleId": "1", "textSha256": "a"},
        {"articleId": "2", "textSha256": "B"},
        {"articleId": "4", "textSha256": "d"},
    ]
    diff = diff_articles(old, new)
    assert diff["addedArticles"] == ["4"]
    assert diff["removedArticles"] == ["3"]
    assert [m["articleId"] for m in diff["modifiedArticles"]] == ["2"]
    assert diff["unchangedCount"] == 1


# ---------------------------------------------------------------------------
# metadata validator
# ---------------------------------------------------------------------------

def _valid_meta():
    return {
        "lawId": "001707",
        "titleKo": "출입국관리법",
        "titleEn": "IMMIGRATION ACT",
        "jurisdiction": "KR",
        "lawType": "ACT",
        "promulgationDate": "2026-08-04",
        "effectiveFrom": "2026-10-02",
        "effectiveUntil": None,
        "sourceProvider": "국가법령정보센터 (법제처)",
        "sourceUrl": "https://www.law.go.kr/LSW/lsInfoP.do?lsiSeq=290729",
        "sourceIdentifier": "290729",
        "retrievedAt": "2026-11-04T00:00:00+09:00",
        "lastVerifiedAt": "2026-11-04T00:00:00+09:00",
        "contentSha256": "a" * 64,
        "sourceFormat": "HTML (lsInfoR)",
        "language": "ko",
        "translationProvider": "한국법제연구원 (KLRI)",
        "translationUpdatedAt": "2026-01-23",
        "translationAlignment": "OLDER_TRANSLATION",
        "reusePermission": "test",
        "verificationStatus": "VERIFIED_OFFICIAL_SNAPSHOT",
    }


def test_validate_metadata_accepts_valid():
    assert validate_metadata(_valid_meta()) == []


def test_validate_metadata_rejects_bad_values():
    meta = _valid_meta()
    meta["effectiveFrom"] = "2026-13-45"
    meta["contentSha256"] = "not-a-hash"
    meta["translationAlignment"] = "GUARANTEED"
    errors = validate_metadata(meta)
    assert len(errors) >= 3


def test_validate_metadata_rejects_missing_field():
    meta = _valid_meta()
    del meta["sourceUrl"]
    assert validate_metadata(meta)


# ---------------------------------------------------------------------------
# title block — ministries beyond the original whitelist
# ---------------------------------------------------------------------------

def test_title_block_accepts_any_ministry_ordinance():
    from backend.services.legal_corpus.parser import parse_title_block

    block = parse_title_block("[시행 2025. 6. 2.] [고용노동부령 제442호, 2025. 6. 2., 일부개정]")
    assert block is not None
    assert block["lawKindKo"] == "고용노동부령"
    assert block["promulgationNo"] == "442"
    assert block["effectiveFrom"] == "2025-06-02"
    block2 = parse_title_block("[시행 2026. 10. 23.] [법무부령 제1172호, 2026. 10. 23., 일부개정]")
    assert block2 is not None and block2["lawKindKo"] == "법무부령"


# ---------------------------------------------------------------------------
# HTTP client — truncated chunked responses are retried, never used partial
# ---------------------------------------------------------------------------

def test_client_retries_on_incomplete_read():
    import http.client
    import urllib.request
    from unittest import mock

    from backend.services.legal_corpus.client import LawGoKrClient

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *exc):
            return False

        def read(self):
            return b"<html>ok</html>"

    calls = {"n": 0}

    def flaky_urlopen(req, timeout=None):
        calls["n"] += 1
        if calls["n"] < 3:
            raise http.client.IncompleteRead(b"partial-bytes")
        return _Resp()

    client = LawGoKrClient(retries=3, sleep=lambda s: None)
    with mock.patch.object(urllib.request, "urlopen", flaky_urlopen):
        assert client._get("https://www.law.go.kr/example") == "<html>ok</html>"
    assert calls["n"] == 3


# ---------------------------------------------------------------------------
# sync fallback — a failed fetch keeps the stored snapshot in the manifest
# ---------------------------------------------------------------------------

def test_stored_result_fallback_rebuilds_from_disk(tmp_path):
    import json as _json

    from backend.services.legal_corpus.sync import CorpusSync

    vdir = tmp_path / "laws" / "demo-act" / "versions" / "2025-01-01"
    vdir.mkdir(parents=True)
    articles_doc = {
        "lawId": "000000", "lawSlug": "demo-act", "effectiveFrom": "2025-01-01",
        "articles": [{"articleId": "1", "articleNumber": "1", "branchNumber": 0,
                      "titleKo": "목적", "deleted": False, "paragraphs": ["본문"],
                      "text": "본문", "textSha256": "x" * 64}],
    }
    (vdir / "articles.ko.json").write_text(_json.dumps(articles_doc), encoding="utf-8")
    (vdir / "translation.json").write_text(
        _json.dumps({"status": "NOT_AVAILABLE", "pairs": [], "englishArticleCount": None}), encoding="utf-8"
    )
    (vdir / "annexes.json").write_text(
        _json.dumps({"annexes": [{"titleKo": "[별표 7] 데모", "files": []}]}), encoding="utf-8"
    )
    previous_entry = {
        "slug": "demo-act",
        "versions": [{"effectiveFrom": "2025-01-01", "path": "laws/demo-act/versions/2025-01-01",
                      "sourceIdentifier": "999999", "translationAlignment": "NOT_AVAILABLE"}],
    }
    law = {"slug": "demo-act", "priority_articles": ["1"]}
    sync = CorpusSync(tmp_path)
    result = sync._stored_result(law, previous_entry)
    assert result is not None
    assert result["versions"] == previous_entry["versions"]
    assert result["built"][0]["articlesDoc"]["articles"][0]["articleId"] == "1"
    # The stored annex list must be restored too — Annex 7 sync reads it
    # from the built version and crashed on fallback results without it.
    assert result["built"][0]["annexes"][0]["titleKo"].startswith("[별표 7]")
    assert result["built"][0]["mst"] == "999999"
    assert result["built"][0]["effectiveFrom"] == "2025-01-01"
    assert sync._stored_result(law, None) is None


# ---------------------------------------------------------------------------
# sync — an English fetch failure must never become a NOT_AVAILABLE finding
# ---------------------------------------------------------------------------

def test_sync_en_fetch_failure_fails_law_instead_of_faking_not_available(tmp_path):
    from backend.services.legal_corpus.client import LawSourceError
    from backend.services.legal_corpus.sync import CorpusSync

    ko_html = """<html><body>
    <div>[시행 2025. 1. 1.] [법률 제12345호, 2025. 1. 1., 제정]</div>
    <p class="pty1_p4"><input type="checkbox" name="joNoList" value="1:0:000100:1" /> <span class="bl">제1조(목적)</span> 이 법은 목적을 정한다.</p>
    </body></html>"""

    class _StubClient:
        def discover_current(self, title_ko):
            return "999999", "20250101"

        def fetch_law_body_html(self, mst, effective_from):
            return ko_html

        def fetch_english_body_html(self, mst):
            raise LawSourceError("network", "simulated outage")

    law = {
        "slug": "demo-act", "lawId": "000001", "titleKo": "데모법", "titleEn": "DEMO ACT",
        "jurisdiction": "KR", "lawType": "ACT", "priority": "P1",
        "known_versions": [{"mst": "999999", "effectiveFrom": "2025-01-01"}],
        "priority_articles": ["1"],
    }
    sync = CorpusSync(tmp_path)
    sync.client = _StubClient()
    assert sync.sync_law(law) is None
    assert any(e.get("stage") == "fetch-en" for e in sync.report["errors"])
    # …and no version directory with a fabricated translation status exists.
    assert not (tmp_path / "laws" / "demo-act").exists()


# ---------------------------------------------------------------------------
# adapter — date-based version selection and safety states
# ---------------------------------------------------------------------------

def test_adapter_selects_version_in_force_on_the_case_date():
    corpus = LegalCorpus()
    past = corpus.get_article("immigration-act", "21", "2026-06-01")
    assert past["version"]["effectiveFrom"] == "2026-01-23"
    assert past["status"] == "HISTORICAL_VERSION_VERIFIED"
    assert "근무처" in (past["article"]["titleKo"] or "") or past["article"]["text"]

    current = corpus.get_article("immigration-act", "21", "2026-11-04")
    assert current["version"]["effectiveFrom"] == "2026-10-02"
    assert current["status"] == "LOCAL_OFFICIAL_SNAPSHOT"
    # The current Korean text is ahead of the official translation.
    assert current["translationStatus"] == "OLDER_TRANSLATION"
    assert "TRANSLATION_OUTDATED" in current.get("translationNote", "")


def test_adapter_uncovered_date_requires_verification():
    corpus = LegalCorpus()
    result = corpus.get_article("immigration-act", "21", "2020-01-01")
    assert result["status"] == "VERIFICATION_REQUIRED"
    assert result["article"] is None


def test_adapter_period_coverage_and_gap_detection():
    corpus = LegalCorpus()
    inside = corpus.version_coverage("immigration-decree", "2025-07-01", "2025-12-31")
    assert inside["hasGap"] is False
    assert inside["status"] == "COVERED_BY_STORED_VERSIONS"
    assert len(inside["versions"]) == 1

    spanning = corpus.version_coverage("immigration-decree", "2025-07-01", "2026-11-01")
    assert spanning["hasGap"] is False
    assert len(spanning["versions"]) == 2  # both sides of the 2026-10-02 revision

    gapped = corpus.version_coverage("immigration-decree", "2024-01-01", "2025-07-01")
    assert gapped["hasGap"] is True
    assert gapped["status"] == "VERIFICATION_REQUIRED"
