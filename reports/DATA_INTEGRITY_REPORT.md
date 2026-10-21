# Data Integrity & Verification Report: VISABLE Immigration Checklists

**Date**: 2026-10-19  
**Source Edition**: 2026.09 South Korea Immigration Manual Compilation  
**Data Validation Script**: `scripts/check_immigration_checklists.mjs`  
**Status**: **100% PASSED** (647 Scenarios across 26 Immigration Offices)

---

## 1. Dataset Scope & Preservation Guarantee

No immigration rules, requirements, exemptions, or status codes were fabricated, altered, or omitted during this redesign. All underlying JSON structures are preserved in their authoritative form:

| Dataset File | Procedure Category | Authentic Item Count | Status |
|---|---|---:|:---:|
| `data/immigration-checklists/extension-202609.json` | 체류기간 연장 (Extension of Stay) | **224** | Verified |
| `data/immigration-checklists/change-202609.json` | 체류자격 변경 (Change of Status) | **251** | Verified |
| `data/immigration-checklists/registration-202609.json` | 외국인등록·거소신고 (Alien Registration) | **172** | Verified |
| **Total Authentic Scenarios** | | **647** | **Preserved** |

### Office Infrastructure
- `data/local-practice-202609.json`: **26 jurisdictional immigration offices and branch offices** across South Korea (e.g., Seoul, Incheon, Suwon, Busan, Jeju, etc.).
- `data/immigration-checklists/local-overrides.json`: Official office overrides with verified evidence citations.
- `data/immigration-checklists/reference-notes-202609.json`: Cross-cutting regulatory notes and procedural footnotes.

---

## 2. Provenance Tracking & Legal Cautions

Every personalized checklist card rendered in Flow D displays:
1. **Source Provenance**: Exact source line number and manual chapter reference (e.g., `2026.09 매뉴얼 편집본 412행 (유학/어학연수 편)`).
2. **Review State**: Explicit badge indicating curation state (`COMPILED_NEEDS_REVIEW` displayed as `검토 필요`).
3. **Legal Disclaimer**: Clear notification that document preparation does not guarantee approval, as immigration officers retain statutory discretion under the Immigration Act.
4. **Cross-Reference Links**: Direct outbound links to the Ministry of Justice HiKorea portal (`hikorea.go.kr`) and the **1345** Immigration Contact Center.

---

## 3. Transparency Policy on Jurisdictional Office Differences

To prevent misinformation:
- When a user selects a specific immigration office (e.g., 제주출입국·외국인청 or 서울출입국·외국인청):
  - If a verified override exists in `local-overrides.json`, it is prominently flagged with an "추가 확인" badge and exact citation note.
  - If no verified regional override exists, the interface explicitly displays:  
    > *"이 관서에 대해 별도로 확인된 서류 차이는 아직 없어요. 전국 공통 기준이 적용되며, 방문 전 관할청의 최신 안내를 확인해 주세요."*
- Unverified, hypothetical, or crowd-sourced assertions are never published to public users.
- Local drafts edited via the maintainer modal are tagged with `review_state: "DRAFT"` and remain strictly isolated to the browser's local session.

---

## 4. Verification & QA Quality Gates

The implementation passed all automated verification checks:

1. **Data Integrity Test**:
   ```bash
   node scripts/check_immigration_checklists.mjs
   # Output: Immigration checklist validation passed: 647 cases / 26 offices
   ```

2. **Korean Language Quality Lint (`kolint`)**:
   ```bash
   node /Users/seonjaekim/dev/korean-language-quality/bin/kolint.mjs --genre ux immigration-checklists.html form-helper.html
   # Output: kolint: 0 unit(s) with findings, 0 blocking (S1, non-advisory).
   ```

3. **Playwright E2E Matrix (Chromium across 6 viewports)**:
   - `desktop-1280`: 7/7 passed
   - `tablet-768`: 7/7 passed
   - `mobile-430`: 7/7 passed
   - `mobile-390`: 7/7 passed
   - `mobile-360`: 7/7 passed
   - `mobile-320`: 7/7 passed
   - **Total: 42 passed (100%)**

4. **Playwright Safari WebKit Test**:
   - `webkit-iphone-390`: 7/7 passed
   - `webkit-iphone-320`: 7/7 passed
   - **Total: 14 passed (100%)**

5. **Form Helper Mobile Collision Regression Check**:
   - Verified that on viewports <= 360px and <= 520px, `.fh-checklist-link` and top navigation controls fit within the screen without clipping, wrapping under the brand mark, or triggering horizontal page overflow.
