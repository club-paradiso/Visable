"""Deterministic frontend coverage for the grounding-readiness / transparency PR.

Parses index.html for wiring/structure (functions, CSS, data-* hooks) and asserts
localized copy against the externalized locale packs in ``data/i18n/`` (the inline
``UI_TRANSLATIONS`` object was migrated to per-locale JSON files loaded at runtime).
Guards:
  - the law-grounding status row + localized labels (Part C),
  - the partial-language fallback notice + support map (Part F),
  - deadline calculator source-status labeling + calendar caution (Part H),
  - site-wide i18n coverage for the new labels across supported languages (Part G),
  - F-4 route-aware follow-through still localized + distinct (Part J).

No browser is executed; functional behavior of the JS date/ICS/Google-Calendar
helpers is covered separately by scripts/check_deadline_helpers.js. Localized copy
is checked against the three supported locales (ko, en, zh-CN); Traditional Chinese
(zh-Hant) aliases to zh-CN in the manifest and is no longer a separate display
locale, so Simplified Chinese is validated against zh-CN.
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _i18n_pack_support import SUPPORTED_LOCALES, load_packs, pack_blobs  # noqa: E402


def _fn(html: str, name: str) -> str:
    start = html.find(f"function {name}(")
    assert start != -1, f"function {name} not found"
    nxt = html.find("\nfunction ", start + 1)
    return html[start: nxt if nxt != -1 else start + 4000]


class _IndexHtml(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (REPO_ROOT / "index.html").read_text(encoding="utf-8")
        cls.packs = load_packs()
        cls.blobs = pack_blobs()


class LawGroundingStatusPanelTests(_IndexHtml):
    # The status-row label was renamed product-wide to "Legal analysis basis"
    # (법률 분석 근거 / 法律分析依据) when copy moved to the external packs; the four
    # state labels are unchanged.
    def test_labels_present_korean(self):
        for s in ["법률 분석 근거", "시도하지 않음", "설정상 비활성화", "외부 법령 API 확인 불가", "법령 검색 결과 사용"]:
            self.assertIn(s, self.blobs["ko"], s)

    def test_labels_present_english(self):
        for s in ["Legal analysis basis", "Not attempted", "Disabled by configuration",
                  "External law API unavailable", "Law search results used"]:
            self.assertIn(s, self.blobs["en"], s)

    def test_labels_present_simplified_chinese(self):
        for s in ["法律分析依据", "未尝试", "因设置而停用", "无法确认外部法令 API", "已使用法令搜索结果"]:
            self.assertIn(s, self.blobs["zh-CN"], s)

    def test_panel_renders_normalized_status_row(self):
        fn = _fn(self.html, "renderGroundingSourcePanel")
        self.assertIn("lawGroundingStatusLabel", fn)
        self.assertIn("law_grounding_status", fn)
        # Only the "used" state maps to a verified/source-present style; disabled
        # and unavailable must not imply official confirmation.
        self.assertIn("lawGroundingStatusUsed", fn)
        self.assertIn("lawGroundingStatusDisabled", fn)
        self.assertIn("lawGroundingStatusUnavailable", fn)

    def test_status_row_only_for_law_intent(self):
        fn = _fn(self.html, "renderGroundingSourcePanel")
        # The row is gated to used/unavailable/disabled (not shown for not_attempted).
        self.assertIn("lawStatusKey === 'used' || lawStatusKey === 'unavailable' || lawStatusKey === 'disabled'", fn)

    def test_used_state_is_the_only_verified_class(self):
        fn = _fn(self.html, "renderGroundingSourcePanel")
        # Find the status block and confirm 'state-verified' is tied to 'used'.
        self.assertRegex(fn, r"lawStatusKey === 'used'\).*?state-verified")


class PartialLanguageNoticeTests(_IndexHtml):
    def test_support_map_declares_supported_locales(self):
        # This used to assert the literal map text from the era when only ko/en
        # were full and zh-CN was 'preparing'. The site has since finished more
        # locales, so the literal became a record of a past state rather than a
        # property. What must hold is that the map exists, is the single place
        # support level is declared, and still declares ko/en — the two locales
        # every other assertion in this file depends on.
        self.assertIn("const LANGUAGE_SUPPORT = {", self.html)
        self.assertIn("function languageSupportLevel(", self.html)
        support = self.html[self.html.index("const LANGUAGE_SUPPORT = {"):]
        support = support[:support.index("}") + 1]
        for locale in ("ko:", "en:", "'zh-CN':"):
            self.assertIn(locale, support, f"{locale} must have a declared support level")

    def test_notice_present_all_supported_languages(self):
        self.assertIn("이 언어는 일부 화면에서 한국어가 함께 표시될 수 있습니다. 공식 서류명은 출입국 매뉴얼과 맞추기 위해 한국어로 유지됩니다.", self.blobs["ko"])
        self.assertIn("Some interface text may still appear in Korean for this language. Official document names remain in Korean to match the immigration manual.", self.blobs["en"])
        self.assertIn("此语言的部分界面文字仍可能显示为韩文。正式材料名称会保留韩文，以便与出入境手册一致。", self.blobs["zh-CN"])

    def test_notice_gated_to_partial_languages_only(self):
        fn = _fn(self.html, "renderLanguageMenu")
        # The notice is only emitted when the active language is partial.
        self.assertIn("languageSupportLevel(currentLanguage) === 'partial'", fn)
        self.assertIn("partialLanguageNotice", fn)
        self.assertIn("data-language-partial-notice", fn)

    def test_partial_badge_present_and_used(self):
        self.assertIn("일부 번역", self.blobs["ko"])
        self.assertIn("Partial", self.blobs["en"])
        self.assertIn("部分翻译", self.blobs["zh-CN"])
        fn = _fn(self.html, "renderLanguageMenu")
        self.assertIn("languagePartialBadge", fn)

    def test_official_korean_document_helper_still_present(self):
        # Must not be removed by this PR.
        self.assertIn("officialDocumentNamesKoNote", self.html)
        self.assertIn("공식 문서명은 출입국 매뉴얼과 일치하도록 한국어로 표시됩니다.", self.blobs["ko"])


class DeadlineSourceStatusTests(_IndexHtml):
    def test_common_rule_label_present_all_languages(self):
        self.assertIn("공통 규칙 기반 준비 참고일", self.blobs["ko"])
        self.assertIn("Common-rule preparation date", self.blobs["en"])
        self.assertIn("基于通用规则的准备参考日期", self.blobs["zh-CN"])

    def test_registration_90day_uses_common_rule_not_official(self):
        fn = _fn(self.html, "computeDeadlines")
        # The 90-day registration row is tagged as a common-rule preparation aid.
        self.assertIn("paradisoDeadlineAddDays(entry, 90)", fn)
        self.assertRegex(fn, r"deadlineRowHtml\(tx\('deadlineRegEstimate'\),\s*regDate,\s*tx\('deadlineRegCaution'\),\s*tx\('deadlineSourceCommonRule'\)\)")
        # The reg caution explicitly states it is not an official deadline.
        self.assertIn("일반 준비용 안내이며 공식 확정 기한이 아닙니다.", self.blobs["ko"])
        self.assertIn("not a confirmed official deadline", self.blobs["en"])

    def test_custom_reminder_uses_custom_source(self):
        fn = _fn(self.html, "computeDeadlines")
        self.assertIn("tx('deadlineSourceCustom')", fn)

    def test_row_renders_source_badge(self):
        fn = _fn(self.html, "deadlineRowHtml")
        self.assertIn("deadline-row-source", fn)
        self.assertIn("data-deadline-source", fn)

    def test_ics_description_carries_caution_not_just_summary(self):
        fn = _fn(self.html, "buildDeadlineIcs")
        self.assertIn("DESCRIPTION:", fn)
        self.assertIn("item.note", fn)
        self.assertIn("Not an official deadline", fn)

    def test_google_calendar_includes_details_caution(self):
        fn = _fn(self.html, "deadlineGoogleCalUrl")
        self.assertIn("&details=", fn)
        self.assertIn("encodeURIComponent(note)", fn)

    def test_calendar_caution_label_present_all_languages(self):
        self.assertIn("Visable 준비용 알림입니다. 공식 기한이 아니며 HiKorea·1345·관할 출입국·외국인관서에서 확인하세요.", self.blobs["ko"])
        self.assertIn("Visable preparation reminder. Not an official deadline; confirm with HiKorea, 1345, or the competent immigration office.", self.blobs["en"])

    def test_local_reminder_state_not_sent_to_ai(self):
        start = self.html.find("function submitAiAnalysis")
        self.assertNotEqual(start, -1)
        body = self.html[start: start + 3500]
        send = body[body.find("JSON.stringify"): body.find("signal:")]
        for forbidden in ("deadline", "data-deadline", "reminder", "entryDate", "expiryDate"):
            self.assertNotIn(forbidden, send, forbidden)

    def test_calculator_does_not_persist_dates(self):
        for name in ("renderDeadlineCalculator", "computeDeadlines"):
            self.assertNotIn("localStorage", _fn(self.html, name))


class F4RouteFollowThroughTests(_IndexHtml):
    def test_route_labels_still_localized(self):
        self.assertIn("F-4는 어떤 경로로 진행하시나요?", self.blobs["ko"])
        self.assertIn("Which F-4 route applies to you?", self.blobs["en"])
        self.assertIn("您属于哪一种 F-4 办理路径？", self.blobs["zh-CN"])

    def test_residence_report_distinct_from_foreigner_registration(self):
        self.assertIn("F-4 국내거소신고", self.blobs["ko"])
        self.assertIn("F-4 domestic residence report", self.blobs["en"])
        self.assertIn("distinct from a general foreigner registration", self.blobs["en"])

    def test_generic_f4_does_not_force_a_route(self):
        # Nothing auto-selects a route: the popup trigger is neutral and no route
        # is pre-selected until the user opens the picker and chooses.
        chooser = _fn(self.html, "renderF4RouteChooser")
        self.assertIn('data-action="open-route-picker"', chooser)
        self.assertNotIn('data-selected-route="', chooser)

    def test_route_selection_does_not_imply_approval(self):
        self.assertIn("경로를 선택해도 자격이나 허가가 보장되지 않습니다", self.blobs["ko"])
        fn = _fn(self.html, "selectF4Route")
        for forbidden in ("eligible", "approved", "guaranteed"):
            self.assertNotIn(forbidden, fn.lower())


class NewKeyI18nParityTests(_IndexHtml):
    NEW_KEYS = [
        "lawGroundingStatusLabel", "lawGroundingStatusNotAttempted",
        "lawGroundingStatusDisabled", "lawGroundingStatusUnavailable",
        "lawGroundingStatusUsed", "partialLanguageNotice", "languagePartialBadge",
        "deadlineSourceCommonRule", "deadlineSourceCustom", "deadlineCalendarCaution",
    ]

    def test_new_keys_in_all_supported_packs(self):
        for locale in SUPPORTED_LOCALES:
            pack = self.packs[locale]
            for key in self.NEW_KEYS:
                self.assertIn(key, pack, f"{key} missing from {locale} pack")


if __name__ == "__main__":
    unittest.main()
