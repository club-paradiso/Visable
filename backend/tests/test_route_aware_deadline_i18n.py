"""Deterministic frontend coverage for the route-aware deadline / i18n PR.

These tests parse index.html as text (matching the established pattern in
test_scenario_procedure_variants.py) and assert the presence/shape of:
  - the F-4 route-aware intake wizard (Part B),
  - the deadline / calendar calculator (Part C/I),
  - the HiKorea pre-checkbox gate removal (Part D),
  - procedure-description fallbacks (Part E),
  - site-wide localization coverage for the new surfaces (Part A).

They never execute a browser; they guard against regressions in the inline
strings, wiring, and localization keys for all four supported UI languages
(Korean, English, Simplified Chinese `zh`, Traditional Chinese `zhHant`).
"""
from __future__ import annotations

import re
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]


def _extract_function(html: str, name: str) -> str:
    """Return the source slice from `function <name>(` up to the next
    top-level `function ` declaration (good enough for substring guards)."""
    start = html.find(f"function {name}(")
    assert start != -1, f"function {name} not found in index.html"
    nxt = html.find("\nfunction ", start + 1)
    return html[start: nxt if nxt != -1 else start + 4000]


class _IndexHtml(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html = (REPO_ROOT / "index.html").read_text(encoding="utf-8")


class F4RouteWizardFrontendTests(_IndexHtml):
    def test_route_chooser_title_present_in_all_languages(self):
        self.assertIn("F-4는 어떤 경로로 진행하시나요?", self.html)
        self.assertIn("Which F-4 route applies to you?", self.html)
        self.assertIn("您属于哪一种 F-4 办理路径？", self.html)
        self.assertIn("您屬於哪一種 F-4 辦理路徑？", self.html)

    def test_route_intro_present_in_all_languages(self):
        self.assertIn("F-4는 입국 전 사증 발급, 국내 체류자격 변경, 국내거소신고, 체류기간 연장 등 경로가 나뉠 수 있습니다. 본인에게 맞는 경로를 먼저 확인하세요.", self.html)
        self.assertIn("F-4 can involve different routes, including pre-entry visa issuance, domestic status change, domestic residence reporting, and extension of stay. Confirm which route matches your situation first.", self.html)
        self.assertIn("F-4 可能涉及不同路径，包括入境前签证签发、境内资格变更、国内居所申报和停留期间延期。请先确认哪一种路径符合您的情况。", self.html)
        self.assertIn("F-4 可能涉及不同路徑，包括入境前簽證核發、境內資格變更、國內居所申報和停留期間延期。請先確認哪一種路徑符合您的情況。", self.html)

    def test_all_five_route_labels_present_in_all_languages(self):
        ko = [
            "재외공관에서 F-4 사증을 받아 입국하는 경우",
            "B-2·C-3 등으로 입국 후 국내에서 F-4로 변경하는 경우",
            "H-2에서 F-4로 변경하는 경우",
            "F-4 국내거소신고",
            "F-4 체류기간 연장",
        ]
        en = [
            "Entering with an F-4 visa issued by a Korean mission abroad",
            "Changing to F-4 in Korea after entering with B-2, C-3, or another eligible status",
            "Changing from H-2 to F-4",
            "F-4 domestic residence report",
            "F-4 extension of stay",
        ]
        zh = [
            "通过驻外韩国使领馆取得 F-4 签证后入境",
            "以 B-2、C-3 等身份入境后在韩国境内变更为 F-4",
            "从 H-2 变更为 F-4",
            "F-4 国内居所申报",
            "F-4 停留期间延期",
        ]
        zh_hant = [
            "透過駐外韓國使領館取得 F-4 簽證後入境",
            "以 B-2、C-3 等身分入境後在韓國境內變更為 F-4",
            "從 H-2 變更為 F-4",
            "F-4 國內居所申報",
            "F-4 停留期間延期",
        ]
        for label in ko + en + zh + zh_hant:
            self.assertIn(label, self.html, label)

    def test_domestic_residence_report_distinct_from_foreigner_registration(self):
        # Route 4 must read as a domestic residence report (거소신고), not a
        # generic foreigner registration (외국인등록).
        self.assertIn("F-4 국내거소신고", self.html)
        self.assertIn("F-4 domestic residence report", self.html)
        self.assertIn("국내거소신고 대상일 수 있습니다", self.html)
        # The English residence-report copy must not mislabel it as registration.
        self.assertIn("distinct from a general foreigner registration", self.html)

    def test_show_all_reset_action_present(self):
        self.assertIn("전체 경로 보기", self.html)
        self.assertIn("Show all F-4 routes", self.html)
        self.assertIn('data-action="show-all-f4-routes"', self.html)

    def test_route_selection_does_not_imply_approval(self):
        # Source note must explicitly disclaim eligibility/approval.
        self.assertIn("경로를 선택해도 자격이나 허가가 보장되지 않습니다", self.html)
        self.assertIn("Selecting a route does not imply eligibility or approval", self.html)
        fn = _extract_function(self.html, "selectF4Route")
        for forbidden in ("eligible", "approved", "guaranteed", "qualif"):
            self.assertNotIn(forbidden, fn.lower(), f"route selection code must not imply {forbidden}")

    def test_route_with_no_docs_directs_to_official_channels(self):
        self.assertIn("HiKorea, 1345 또는 관할 출입국·외국인관서에서 직접 확인하세요.", self.html)
        self.assertIn("Confirm directly with HiKorea, 1345, or the competent immigration office.", self.html)

    def test_wizard_is_additive_and_does_not_hide_procedures(self):
        # Injected before procedures, and de-emphasis is opacity-only (a CSS
        # class), never display:none / removing variants.
        self.assertIn("${renderF4RouteChooser(v)}", self.html)
        self.assertIn(".procedure-tab.is-route-muted { opacity:", self.html)
        fn = _extract_function(self.html, "selectF4Route")
        self.assertNotIn("display:none", fn.replace(" ", ""))
        self.assertNotIn(".remove()", fn)

    def test_generic_f4_does_not_force_a_route(self):
        # Nothing auto-selects a route: the popup trigger shows a neutral label
        # and the explanation area starts hidden until the user picks a route.
        chooser = _extract_function(self.html, "renderF4RouteChooser")
        self.assertIn('data-action="open-route-picker"', chooser)
        self.assertIn('role="status" aria-live="polite" hidden', chooser)
        self.assertNotIn('data-selected-route="', chooser)

    def test_wizard_does_not_expose_raw_manualrefs_or_requireddocs(self):
        chooser = _extract_function(self.html, "renderF4RouteChooser")
        self.assertNotIn("manualRefs", chooser)
        self.assertNotIn("requiredDocs", chooser)

    def test_route_chips_are_buttons_for_keyboard_access(self):
        # The popup trigger and the in-popup route choices are all real buttons.
        chooser = _extract_function(self.html, "renderF4RouteChooser")
        self.assertIn('<button type="button" class="f4-route-trigger"', chooser)
        picker = _extract_function(self.html, "openRoutePicker")
        self.assertIn('<button type="button" class="scenario-choice route-picker-choice"', picker)


class DeadlineCalculatorFrontendTests(_IndexHtml):
    def test_required_labels_present_korean(self):
        for s in ["기한 계산기", "캘린더에 추가", "ICS 파일 다운로드", "Google Calendar에 추가",
                  "입국일", "체류만료일", "예상 등록 기한", "연장 준비 알림",
                  "공식 기한은 개인 상황과 관할 판단에 따라 달라질 수 있습니다."]:
            self.assertIn(s, self.html, s)

    def test_required_labels_present_english(self):
        for s in ["Deadline calculator", "Add to calendar", "Download ICS file", "Add to Google Calendar",
                  "Entry date", "Stay expiry date", "Estimated registration deadline",
                  "Extension preparation reminders",
                  "Official deadlines may differ depending on your facts and the competent office."]:
            self.assertIn(s, self.html, s)

    def test_required_labels_present_simplified_chinese(self):
        for s in ["期限计算器", "添加到日历", "下载 ICS 文件", "添加到 Google Calendar",
                  "入境日期", "停留期限到期日", "预计外国人登记期限", "延期准备提醒",
                  "正式期限可能因个人情况和管辖机构判断而不同。"]:
            self.assertIn(s, self.html, s)

    def test_required_labels_present_traditional_chinese(self):
        for s in ["期限計算器", "加入行事曆", "下載 ICS 檔案", "加入 Google Calendar",
                  "入境日期", "停留期限到期日", "預計外國人登錄期限", "延期準備提醒",
                  "正式期限可能因個人情況和管轄機構判斷而不同。"]:
            self.assertIn(s, self.html, s)

    def test_ninety_day_registration_rule_labeled_as_preparation_aid(self):
        self.assertIn("paradisoDeadlineAddDays(entry, 90)", self.html)
        # The 90-day estimate must be presented as a general preparation aid.
        self.assertIn("일반 준비용 안내이며 공식 확정 기한이 아닙니다.", self.html)
        self.assertIn("general preparation aid, not a confirmed official deadline", self.html)

    def test_extension_reminder_offsets_present(self):
        self.assertIn("[60, 30, 7, 0]", self.html)

    def test_invalid_date_handling_present(self):
        # The pure date helper guards input with a strict YYYY-MM-DD regex.
        fn = _extract_function(self.html, "paradisoDeadlineAddDays")
        self.assertIn(r"/^(\d{4})-(\d{2})-(\d{2})$/", fn)
        self.assertIn("return ''", fn)

    def test_ics_generation_contains_dtstart_and_summary(self):
        fn = _extract_function(self.html, "buildDeadlineIcs")
        self.assertIn("DTSTART;VALUE=DATE:", fn)
        self.assertIn("SUMMARY:", fn)
        self.assertIn("BEGIN:VEVENT", fn)

    def test_ics_has_no_personal_data_fields(self):
        fn = _extract_function(self.html, "buildDeadlineIcs")
        for forbidden in ("passport", "email", "phone", "nationality", "name:"):
            self.assertNotIn(forbidden, fn.lower())

    def test_google_calendar_url_encodes_safely(self):
        fn = _extract_function(self.html, "deadlineGoogleCalUrl")
        self.assertIn("https://calendar.google.com/calendar/render?action=TEMPLATE", fn)
        self.assertIn("encodeURIComponent(title)", fn)

    def test_disclaimer_and_privacy_note_present(self):
        self.assertIn("입력한 날짜는 브라우저에만 표시되며 저장하거나 AI·서버로 전송하지 않습니다.", self.html)
        self.assertIn("Dates you enter are shown only in your browser and are not saved or sent to AI or the server.", self.html)

    def test_calculator_state_not_in_ai_payload(self):
        # The /api/ask request body must not carry any calculator/reminder state.
        start = self.html.find("function submitAiAnalysis")
        self.assertNotEqual(start, -1)
        body = self.html[start: start + 3500]
        send = body[body.find("JSON.stringify"): body.find("signal:")]
        for forbidden in ("deadline", "data-deadline", "reminder", "entryDate", "expiryDate"):
            self.assertNotIn(forbidden, send, f"AI payload must not include {forbidden}")

    def test_calculator_does_not_persist_dates_to_localstorage(self):
        # Ephemeral by design: the calculator render/compute functions never
        # touch localStorage.
        for name in ("renderDeadlineCalculator", "computeDeadlines"):
            fn = _extract_function(self.html, name)
            self.assertNotIn("localStorage", fn)

    def test_calendar_links_use_safe_rel(self):
        fn = _extract_function(self.html, "deadlineRowHtml")
        self.assertIn('target="_blank" rel="noopener noreferrer"', fn)


class HiKoreaGateRemovalFrontendTests(_IndexHtml):
    def test_start_button_is_not_disabled(self):
        self.assertIn(
            '<button type="button" class="cb on" id="hkStartBtn" data-action="start-hikorea-guide">',
            self.html,
        )
        self.assertNotIn(
            'id="hkStartBtn" data-action="start-hikorea-guide" disabled',
            self.html,
        )

    def test_start_handler_has_no_checkbox_gate(self):
        self.assertIn(
            "'start-hikorea-guide': () => { hikoreaGuideState.step = 0; renderHikoreaGuide(); },",
            self.html,
        )

    def test_change_listener_no_longer_blocks_start(self):
        self.assertIn("if (startBtn) startBtn.disabled = false;", self.html)
        self.assertNotIn(
            "startBtn.disabled = !(hikoreaGuideState.emailOk && hikoreaGuideState.pwOk && hikoreaGuideState.expOk)",
            self.html,
        )

    def test_visible_caution_replaces_gate_in_all_languages(self):
        self.assertIn('class="hikorea-precheck-caution"', self.html)
        self.assertIn("아래 항목은 예약 준비를 돕기 위한 확인 사항입니다. 체크하지 않아도 다음 단계로 진행할 수 있습니다.", self.html)
        self.assertIn("You can continue to the next step without checking them.", self.html)
        self.assertIn("即使不勾选也可继续下一步。", self.html)
        self.assertIn("即使不勾選也可繼續下一步。", self.html)

    def test_disclaimers_still_present(self):
        self.assertIn("hkDisc1", self.html)
        self.assertIn("Paradiso는 공식 정부 서비스가 아닙니다.", self.html)


class ProcedureFallbackDescriptionFrontendTests(_IndexHtml):
    def test_fallback_keys_mapped_for_three_procedures(self):
        self.assertIn("visaIssuance: 'procFallbackInitial'", self.html)
        self.assertIn("registration: 'procFallbackRegistration'", self.html)
        self.assertIn("extension: 'procFallbackExtension'", self.html)

    def test_fallback_only_applies_when_summary_empty(self):
        # The fallback must not overwrite an existing/source-backed summary.
        self.assertIn(
            "renderProcedureSummaryBlock(proc.summary, keywords) || renderProcedureFallbackSummary(proc.key)",
            self.html,
        )

    def test_fallback_copy_present_all_languages(self):
        # Korean + English are provided verbatim by the task.
        self.assertIn("입국 전 사증 발급 또는 해당 체류자격 신청 단계에서 확인하는 절차입니다.", self.html)
        self.assertIn("This covers the pre-entry visa issuance or initial status application stage.", self.html)
        # Simplified + Traditional Chinese equivalents.
        self.assertIn("此为入境前签证签发或相应停留资格申请阶段需确认的程序。", self.html)
        self.assertIn("此為入境前簽證核發或相應停留資格申請階段需確認的程序。", self.html)

    def test_registration_fallback_distinguishes_residence_report(self):
        self.assertIn("외국인등록 또는 국내거소신고가 필요할 수 있습니다", self.html)
        self.assertIn("foreigner registration or domestic residence reporting", self.html)


class RouteAwareI18nCoverageTests(_IndexHtml):
    """Guards that the new surfaces are localized in all four target packs."""

    NEW_KEYS = [
        "f4RouteTitle", "f4RouteIntro", "f4RouteShowAll", "f4RouteSourceNote",
        "f4RouteNoDocsNote", "f4Route1Label", "f4Route5Desc",
        "deadlineCalcTitle", "deadlineEntryDate", "deadlineExpiryDate",
        "deadlineRegEstimate", "deadlineExtReminders", "deadlineAddGoogle",
        "deadlineDisclaimer", "deadlinePrivacyNote", "deadlineDaysBefore",
        "hkPreCheckCaution", "procFallbackInitial", "procFallbackRegistration",
        "procFallbackExtension",
    ]

    def _pack(self, code: str) -> str:
        # Slice a single UI_TRANSLATIONS language pack body for substring checks.
        ui = self.html.find("const UI_TRANSLATIONS =")
        assert ui != -1, "UI_TRANSLATIONS not found"
        scope = self.html[ui:]
        m = re.search(rf"\n    {re.escape(code)}: {{", scope)
        assert m, f"language pack {code} not found"
        return scope[m.start(): m.start() + 70000].split("\n    },", 1)[0]

    def test_new_keys_in_all_four_packs(self):
        for code in ("ko", "en", "zh", "zhHant"):
            pack = self._pack(code)
            for key in self.NEW_KEYS:
                self.assertIn(f"{key}:", pack, f"{key} missing from {code} pack")

    def test_placeholder_token_present_for_days_before(self):
        self.assertIn("{days}일 전", self.html)
        self.assertIn("{days} days before", self.html)


if __name__ == "__main__":
    unittest.main()
