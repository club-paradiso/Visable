# Paradiso — Working Rules

## Project
Korean visa/status-of-stay information platform. 39 체류자격 categories.
Stack: vanilla HTML/CSS/JS, single-file, no build system.

## Protected files (NEVER broadly rewrite or modify during data work)
- `visa_data.json`
- `backend/data/visas.json`
- `doc_master.json`

These may receive ONLY safe, surgical edits (see below). Never bulk-rewrite.

## Code hierarchy
- 2 segments (D-2, G-1, E-7, F-2, D-10) = parent/base code.
- 3+ segments (D-2-1, G-1-5, E-7-1) = subcode, classified UNDER its parent.
- `*-T` variants (D-10-T, E-7-T, F-2-T, F-5-T) = special variants; classify by actual data structure, not numeric subcode logic.
- G-1-5 is a subcode of G-1, NEVER a top-level family.
- Parent records must NOT render subcode-specific rules as universal parent requirements.

## Procedure scope — keep strictly separate
- Visa manual sources (`visa_manual_260521.txt`) → 사증발급 / 사증발급인정서 / 공관장 재량 사증 / 사증 첨부서류.
- Stay manual sources (`stay_manual_260601.txt`) → 체류자격 변경 / 체류기간 연장 / 외국인등록 / 재입국 / 체류자격외 활동 / 근무처 변경·추가.
- NEVER mix 사증발급 requirements into 체류 procedures, or vice versa.
- OCR txt = readable source aid for auditing only. NOT a license to invent requirements.

## Non-negotiable constraints
- Do NOT invent legal/immigration content.
- Do NOT add document requirements not already in local data/source files.
- Do NOT remove or weaken: disclaimers, cautions, official-source warnings, uncertainty notices, review-needed warnings.
- Do NOT flatten subcodes into parents.
- Prefer renderer/resolver fixes over data edits.
- Do NOT claim full legal correctness — this is rendering/data-hygiene work, not legal revalidation.

## Safe data edits (allowed)
- Remove exact duplicate strings from the same array.
- Move prose out of document arrays IF a suitable note field already exists and the renderer supports it.
- Remove duplicated prose ONLY if the same text remains in the correct overview/detail/note field.

## Unsafe (forbidden)
- Rewriting legal requirements; adding new requirements.
- Deleting content not preserved elsewhere.
- New schema the UI/backend doesn't understand.
- Treating OCR artifacts as confirmed requirements without manual review.

## When uncertain
Keep data intact → prevent misleading rendering → log it in the audit report as needing manual review.
