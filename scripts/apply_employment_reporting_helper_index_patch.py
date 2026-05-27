#!/usr/bin/env python3
"""Patch index.html to render HiKorea-like employment-reporting helper steps.

This helper is intentionally deterministic and small because index.html is a
large single-file frontend. The patch inserts a guidance block into the existing
job/industry-code modal without touching visa data, backend visa data,
verification metadata, or the KSCO8/KSIC11 source tables.
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = ROOT / "index.html"

MARKER = "EMPLOYMENT_REPORTING_HELPER_STEPS_2026_05"

INSERT_AFTER = """            <div class=\"jc-ai-search-row\">\n                <button type=\"button\" class=\"ai-btn\" data-action=\"search-jobcode-ai\" style=\"width:100%; justify-content:center; padding:0.8rem;\">\n                    <span id=\"jcNaturalSearchLabel\">자연어 키워드로 공식 직종·업종 찾기</span>\n                    <div class=\"spinner\" id=\"jcAiSpinner\" style=\"margin-left:8px;\"></div>\n                </button>\n            </div>\n"""

HELPER_BLOCK = """\n            <!-- EMPLOYMENT_REPORTING_HELPER_STEPS_2026_05 -->\n            <div class=\"jc-disclaimer\" data-employment-reporting-helper=\"true\">\n                <b>하이코리아 취업정보 신고 흐름</b>\n                <ol style=\"margin:0.5rem 0 0 1.1rem; line-height:1.65;\">\n                    <li>체류자격이 신고 대상인지 확인합니다. 대상 예: E-1~E-10, D-7~D-9, F-2/F-4/F-6, H-2.</li>\n                    <li>영리활동 중인지 확인합니다. F-5 또는 영리활동이 없는 경우는 신고 대상이 아닐 수 있습니다.</li>\n                    <li><b>직종</b>은 한국표준직업분류(KSCO8) 기준으로 조회합니다.</li>\n                    <li><b>업종</b>은 한국표준산업분류(KSIC11) 기준으로 조회합니다.</li>\n                    <li>연간소득 구간을 선택한 뒤, 방문예약 중 신고 또는 전자민원 신고 경로를 선택합니다.</li>\n                </ol>\n                <p style=\"margin-top:0.5rem;\">현재 Paradiso 데이터는 seed 단계입니다. 상세 코드 확정 전에는 HiKorea 또는 통계분류포털에서 최종 확인하세요.</p>\n            </div>\n"""


def main() -> int:
    text = INDEX.read_text(encoding="utf-8")
    if MARKER in text:
        print("employment reporting helper block already present")
        return 0
    if INSERT_AFTER not in text:
        raise SystemExit("target job-code modal block not found; index.html structure may have changed")
    text = text.replace(INSERT_AFTER, INSERT_AFTER + HELPER_BLOCK, 1)
    INDEX.write_text(text, encoding="utf-8")
    print("patched index.html with employment reporting helper steps")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
