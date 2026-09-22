# Immigration source-conflict report — 2026-09-22

Scope: everything the post-search guidance layer (`assets/js/status-guidance.js`,
`data/status-guidance-202609.json`) says is derived from the two September 2026
Ministry of Justice manuals. This report lists every place where those manuals
disagree with the structured data already in the repository, or where the
repository names something the manuals do not. It is generated from
`data/status-coverage-202609.json → conflicts` by `scripts/build_status_coverage_manifest.py`
and annotated by hand; regenerate the manifest before editing the counts.

| Source | Edition | Role in this report |
| --- | --- | --- |
| 사증발급 안내매뉴얼 | 2026.9 / 2026-09-01 (`docs/source-manuals/2026-09/visa_manual_260901.pdf`) | authoritative for 사증발급 / 사증발급인정서 / 전자사증 |
| 외국인체류 안내매뉴얼 | 2026.9 / 2026-09-18 (`docs/source-manuals/2026-09/stay_manual_260918.pdf`) | authoritative for every 체류 procedure |
| `visa_data.json` / `backend/data/visas.json` | 2026.6 (2026-06-17 / 2026-06-23 editions) | legacy structured records — **protected, not edited** |
| `doc_master.json` | 2026.6 | legacy document master — **protected, not edited** |

Resolution policy (from `CLAUDE.md`): protected files receive no bulk edits, no
requirement is invented, nothing is deleted. Every conflict is therefore resolved
by (a) the new layer citing the September page, (b) the legacy card being
labelled with its own edition, and (c) the manifest recording the state so the
resolver never targets an unverifiable code. Items needing a human decision are
marked **manual review**.

## Summary

| Kind | Count | Handling |
| --- | --- | --- |
| Edition lag (structured record 2026.6 vs manual 2026.9) | 37 | guidance cites 2026.9; legacy card labelled |
| Code in `visa_data.json` not found in either September manual | 37 | manifest `UNVERIFIED`; resolver never targets it; legacy card still reachable |
| Code in the September manual absent from `visa_data.json` | 1 | manifest carries it (SOURCE_ONLY / SUPPORTED); legacy search cannot land on it |
| Value changed between editions | 1 | **manual review** — protected file not edited |
| Abolished code still listed as active | 1 | manifest `LEGACY_ONLY` + `superseded_by` |
| **Total** | **77** | |

## 1. Value changes (manual review)

| Status | Procedure | 2026.6 structured value | 2026.9 manual | Impact | Resolution |
| --- | --- | --- | --- | --- | --- |
| E-7-4 | status_change | 소득요건 2,500만원 (2026.6 text) | 2,589만원 (2026.9) | legacy summary understates the income threshold | not edited (protected file); flagged for manual review |

The E-7-4 income threshold is the only numeric value the comparison found
changed in a place the legacy card renders as prose. The 2026.9 stay manual
(E-7 chapter, 숙련기능인력 점수제 section) gives 2,589만원; the 2026.6 summary in
`visa_data.json` still says 2,500만원. The guidance layer shows the 2026.9 figure
with its page; the legacy card keeps its 2026.6 label until a human edits the
protected file.

## 2. Abolished / legacy codes

| Code | Manual statement | Temporal fields in the manifest | Resolution |
| --- | --- | --- | --- |
| F-2-6 | 2019-10-01 폐지, 기존 허가자는 기타 장기체류자(F-2-99)로 직권 정정되었습니다. (stay p. 412) | effective_to=2019-10-01 · new_application_allowed=False · existing_holder_only=False · superseded_by=F-2-99 · legacy_alias=None | coverage `LEGACY_ONLY`; resolver shows the legacy rule, never a fresh-application checklist |
| H-2 | 2026-02-12부터 신규 사증 발급 중단(동포 체류자격 F-4 통합). 기존 소지자 체류관리는 계속됩니다. (stay p. 532) | effective_to=2026-02-12 · new_application_allowed=False · existing_holder_only=True · superseded_by=F-4 · legacy_alias=None | coverage `PARTIAL`; resolver shows the legacy rule, never a fresh-application checklist |
| D-3-1 | 2006-12-31까지 등록자에게만 남아 있는 구 약호입니다. (stay p. 58) | effective_to=2006-12-31 · new_application_allowed=False · existing_holder_only=True · superseded_by=D-3-11 · legacy_alias=None | coverage `SOURCE_ONLY`; resolver shows the legacy rule, never a fresh-application checklist |
| F-1-1 | 기존 F-1-1로 체류 중인 국민의 미성년 외국인 자녀는 확인 즉시 수수료 없이 F-2-2로 변경됩니다. (stay p. 370) | effective_to=None · new_application_allowed=True · existing_holder_only=False · superseded_by=F-2-2 · legacy_alias=None | coverage `SOURCE_ONLY`; resolver shows the legacy rule, never a fresh-application checklist |
| E-7-91 | 구약호 T6에서 이어지는 FTA 독립전문가 약호입니다. (stay p. 214) | effective_to=None · new_application_allowed=True · existing_holder_only=False · superseded_by=None · legacy_alias=T6 | coverage `PARTIAL`; resolver shows the legacy rule, never a fresh-application checklist |

## 3. Codes the September manuals do not mention (`UNVERIFIED`)

These codes exist in `visa_data.json` (2026.6) and are still searchable through
the legacy card, but neither September manual names them. The guidance layer
does not resolve to them, does not show a checklist for them, and the manifest
records `coverage_state: UNVERIFIED` with the legacy label so a reviewer can
decide whether they were renamed, folded into a parent, or dropped.

| Code | Legacy label (2026.6) | Note |
| --- | --- | --- |
| B-1-1 | B-1 일반여권 유효 67개국 | not found in either September manual; **manual review** |
| B-1-2 | B-1 일시정지 3개국 | not found in either September manual; **manual review** |
| B-2-1 | 일반 무사증 (45개국·지역) | not found in either September manual; **manual review** |
| B-2-2 | 제주 무사증 입국 | not found in either September manual; **manual review** |
| D-1-00 | 문화예술연수 | legacy placeholder code |
| D-7-1 | 외국기업 주재 | not found in either September manual; **manual review** |
| D-7-2 | 내국기업 주재 | not found in either September manual; **manual review** |
| D-7-91 | FTA전근 | not found in either September manual; **manual review** |
| D-7-92 | FTA계약 | not found in either September manual; **manual review** |
| D-8-91 | FTA전근 | not found in either September manual; **manual review** |
| D-9-2 | 수출설비 | not found in either September manual; **manual review** |
| D-9-3 | 선박설비 | not found in either September manual; **manual review** |
| E-7-91FTA | FTA 독립전문가 | the manual writes the FTA exception as E-7-91 (T6 구약호); the FTA suffix is a legacy display code |
| E-7-M | K-CORE(육성형 전문기술인력) | legacy pseudo-code for the metropolitan pilot; see program METRO |
| E-9-JS | 구직신청자 특례 | job-seeker special case appears in the manual as a scenario under E-9, not a subcode |
| E-9-R | 외국인등록 제출서류 | regional pathway is expressed as E-7-4R (지역특화형), not an E-9 subcode |
| F-1-9 | 동포배우자 등 | not found in either September manual; **manual review** |
| F-3-1 | 동반 기본 | not found in either September manual; **manual review** |
| F-3-2 | 소득요건(25.7.1 개편) | not found in either September manual; **manual review** |
| F-3-3 | 소득요건 면제 | not found in either September manual; **manual review** |
| F-4-11 | 재외동포 본인 (구 분류·레거시) | not found in either September manual; **manual review** |
| F-4-12 | 직계비속 (구 분류·레거시) | not found in either September manual; **manual review** |
| F-4-13 | D·E계열 6개월↑ (구 분류·레거시) | not found in either September manual; **manual review** |
| F-4-14 | 대학 졸업자 (구 분류·레거시) | not found in either September manual; **manual review** |
| F-4-15 | OECD영주자 (구 분류·레거시) | not found in either September manual; **manual review** |
| F-4-16 | 법인대표 등 (구 분류·레거시) | not found in either September manual; **manual review** |
| F-4-17 | 10만불 기업가 (구 분류·레거시) | not found in either September manual; **manual review** |
| F-4-18 | 다국적기업 종사자 (구 분류·레거시) | not found in either September manual; **manual review** |
| F-4-19 | 동포단체대표 (구 분류·레거시) | not found in either September manual; **manual review** |
| F-4-20 | 공무원 등 (구 분류·레거시) | not found in either September manual; **manual review** |
| F-4-21 | 교원 (구 분류·레거시) | not found in either September manual; **manual review** |
| F-4-25 | 60세 이상자 (구 분류·레거시) | not found in either September manual; **manual review** |
| F-4-30 | 국내 초·중·고 재학 동포 자녀 (구 분류·레거시) | not found in either September manual; **manual review** |
| G-1-13 | 장기체류 아동 (장기체류 아동 체계) | not found in either September manual; **manual review** |
| G-1-14 | 장기체류 아동 (장기체류 아동 체계) | not found in either September manual; **manual review** |
| REGIONAL-D-2 | 광역형 비자 유학생 (시범사업) | legacy pseudo-record; 광역형 D-2 is now a program record (METRO) |
| REGIONAL-E-7 | 광역형 비자 특정활동 (시범사업) | legacy pseudo-record; 광역형 E-7 is now a program record (METRO) |

F-4-11 … F-4-30: the September visa manual (ch. 38 알기쉬운 외국국적동포 업무매뉴얼)
and stay manual (ch. 36) describe 동포 statuses by scenario and by the F-4-R /
F-5-6R regional codes, not by the 2026.6 F-4-1x/2x numeric subcodes. The manifest
keeps them `UNVERIFIED` rather than guessing a mapping.

## 4. Codes present in the manuals but missing from the legacy data

| Code | Manual | Resolution |
| --- | --- | --- |
| F-5-27 (난민 거주 2년 체류자) | stay p. 434 (table) | manifest + resolver carry it (SOURCE_ONLY or SUPPORTED) |

Codes the manifest added as `SOURCE_ONLY` from the September tables are listed
in `reports/data-coverage/status-coverage-202609.md` (taxonomy_evidence =
`table` / `mention` with `legacy: null`).

## 5. Edition lag (every status record)

All 37 status records in `visa_data.json` cite the 2026.6 editions (사증 2026-06-17,
체류 2026-06-23) while the manual corpus and the new guidance cite 2026.9. The
legacy card is not modified; the guidance layer renders each answer with its
September page and shows the legacy card as a separately labelled fallback.

| Status | Structured edition | Manual edition | Resolution |
| --- | --- | --- | --- |
| A-1 | 2026.6 / 2026-06-23 | 2026.9 (stay 2026-09-18, visa 2026-09-01) | new guidance layer cites 2026.9 pages; legacy card labelled with its own edition |
| A-2 | 2026.6 / 2026-06-23 | 2026.9 (stay 2026-09-18, visa 2026-09-01) | new guidance layer cites 2026.9 pages; legacy card labelled with its own edition |
| A-3 | 2026.6 / 2026-06-23 | 2026.9 (stay 2026-09-18, visa 2026-09-01) | new guidance layer cites 2026.9 pages; legacy card labelled with its own edition |
| B-1 | 2026.6 / 2026-06-23 | 2026.9 (stay 2026-09-18, visa 2026-09-01) | new guidance layer cites 2026.9 pages; legacy card labelled with its own edition |
| B-2 | 2026.6 / 2026-06-23 | 2026.9 (stay 2026-09-18, visa 2026-09-01) | new guidance layer cites 2026.9 pages; legacy card labelled with its own edition |
| C-1 | 2026.6 / 2026-06-23 | 2026.9 (stay 2026-09-18, visa 2026-09-01) | new guidance layer cites 2026.9 pages; legacy card labelled with its own edition |
| C-3 | 2026.6 / 2026-06-23 | 2026.9 (stay 2026-09-18, visa 2026-09-01) | new guidance layer cites 2026.9 pages; legacy card labelled with its own edition |
| C-4 | 2026.6 / 2026-06-23 | 2026.9 (stay 2026-09-18, visa 2026-09-01) | new guidance layer cites 2026.9 pages; legacy card labelled with its own edition |
| D-1 | 2026.6 / 2026-06-23 | 2026.9 (stay 2026-09-18, visa 2026-09-01) | new guidance layer cites 2026.9 pages; legacy card labelled with its own edition |
| D-10 | 2026.6 / 2026-06-23 | 2026.9 (stay 2026-09-18, visa 2026-09-01) | new guidance layer cites 2026.9 pages; legacy card labelled with its own edition |
| D-2 | 2026.6 / 2026-06-23 | 2026.9 (stay 2026-09-18, visa 2026-09-01) | new guidance layer cites 2026.9 pages; legacy card labelled with its own edition |
| D-3 | 2026.6 / 2026-06-23 | 2026.9 (stay 2026-09-18, visa 2026-09-01) | new guidance layer cites 2026.9 pages; legacy card labelled with its own edition |
| D-4 | 2026.6 / 2026-06-23 | 2026.9 (stay 2026-09-18, visa 2026-09-01) | new guidance layer cites 2026.9 pages; legacy card labelled with its own edition |
| D-5 | 2026.6 / 2026-06-23 | 2026.9 (stay 2026-09-18, visa 2026-09-01) | new guidance layer cites 2026.9 pages; legacy card labelled with its own edition |
| D-6 | 2026.6 / 2026-06-23 | 2026.9 (stay 2026-09-18, visa 2026-09-01) | new guidance layer cites 2026.9 pages; legacy card labelled with its own edition |
| D-7 | 2026.6 / 2026-06-23 | 2026.9 (stay 2026-09-18, visa 2026-09-01) | new guidance layer cites 2026.9 pages; legacy card labelled with its own edition |
| D-8 | 2026.6 / 2026-06-23 | 2026.9 (stay 2026-09-18, visa 2026-09-01) | new guidance layer cites 2026.9 pages; legacy card labelled with its own edition |
| D-9 | 2026.6 / 2026-06-23 | 2026.9 (stay 2026-09-18, visa 2026-09-01) | new guidance layer cites 2026.9 pages; legacy card labelled with its own edition |
| E-1 | 2026.6 / 2026-06-23 | 2026.9 (stay 2026-09-18, visa 2026-09-01) | new guidance layer cites 2026.9 pages; legacy card labelled with its own edition |
| E-10 | 2026.6 / 2026-06-23 | 2026.9 (stay 2026-09-18, visa 2026-09-01) | new guidance layer cites 2026.9 pages; legacy card labelled with its own edition |
| E-2 | 2026.6 / 2026-06-23 | 2026.9 (stay 2026-09-18, visa 2026-09-01) | new guidance layer cites 2026.9 pages; legacy card labelled with its own edition |
| E-3 | 2026.6 / 2026-06-23 | 2026.9 (stay 2026-09-18, visa 2026-09-01) | new guidance layer cites 2026.9 pages; legacy card labelled with its own edition |
| E-4 | 2026.6 / 2026-06-23 | 2026.9 (stay 2026-09-18, visa 2026-09-01) | new guidance layer cites 2026.9 pages; legacy card labelled with its own edition |
| E-5 | 2026.6 / 2026-06-23 | 2026.9 (stay 2026-09-18, visa 2026-09-01) | new guidance layer cites 2026.9 pages; legacy card labelled with its own edition |
| E-6 | 2026.6 / 2026-06-23 | 2026.9 (stay 2026-09-18, visa 2026-09-01) | new guidance layer cites 2026.9 pages; legacy card labelled with its own edition |
| E-7 | 2026.6 / 2026-06-23 | 2026.9 (stay 2026-09-18, visa 2026-09-01) | new guidance layer cites 2026.9 pages; legacy card labelled with its own edition |
| E-8 | 2026.6 / 2026-06-23 | 2026.9 (stay 2026-09-18, visa 2026-09-01) | new guidance layer cites 2026.9 pages; legacy card labelled with its own edition |
| E-9 | 2026.6 / 2026-06-23 | 2026.9 (stay 2026-09-18, visa 2026-09-01) | new guidance layer cites 2026.9 pages; legacy card labelled with its own edition |
| F-1 | 2026.6 / 2026-06-23 | 2026.9 (stay 2026-09-18, visa 2026-09-01) | new guidance layer cites 2026.9 pages; legacy card labelled with its own edition |
| F-2 | 2026.6 / 2026-06-23 | 2026.9 (stay 2026-09-18, visa 2026-09-01) | new guidance layer cites 2026.9 pages; legacy card labelled with its own edition |
| F-3 | 2026.6 / 2026-06-23 | 2026.9 (stay 2026-09-18, visa 2026-09-01) | new guidance layer cites 2026.9 pages; legacy card labelled with its own edition |
| F-4 | 2026.6 / 2026-06-23 | 2026.9 (stay 2026-09-18, visa 2026-09-01) | new guidance layer cites 2026.9 pages; legacy card labelled with its own edition |
| F-5 | 2026.6 / 2026-06-23 | 2026.9 (stay 2026-09-18, visa 2026-09-01) | new guidance layer cites 2026.9 pages; legacy card labelled with its own edition |
| F-6 | 2026.6 / 2026-06-23 | 2026.9 (stay 2026-09-18, visa 2026-09-01) | new guidance layer cites 2026.9 pages; legacy card labelled with its own edition |
| G-1 | 2026.6 / 2026-06-23 | 2026.9 (stay 2026-09-18, visa 2026-09-01) | new guidance layer cites 2026.9 pages; legacy card labelled with its own edition |
| H-1 | 2026.6 / 2026-06-23 | 2026.9 (stay 2026-09-18, visa 2026-09-01) | new guidance layer cites 2026.9 pages; legacy card labelled with its own edition |
| H-2 | 2026.6 / 2026-06-23 | 2026.9 (stay 2026-09-18, visa 2026-09-01) | new guidance layer cites 2026.9 pages; legacy card labelled with its own edition |

## 6. Procedure-scope conflicts observed while authoring

These are not data conflicts but places where the legacy renderer mixed source
domains; the new layer keeps them separate (visa-manual procedures vs
stay-manual procedures) as `CLAUDE.md` requires.

- `F-6 → status_change` in the legacy card lists 사증발급 documents. The 2026.9
  stay manual says the change to F-6-1 “준용” the visa issuance list; the new
  layer states that as a note with the page and marks the checklist
  SOURCE_ONLY instead of copying the visa list into a stay procedure.
- `E-9` legacy card extension list is the manufacturing baseline; the 2026.9
  visa manual (ch. 27, 허용업종 table) carries the hotel/hospitality track as
  E-9-5. The guidance layer asks the procedure and resolves E-9-5 with the
  common extension rule inherited from E-9, flagged `inherited_from_parent`.
- `H-2` legacy record still exposes a visa-issuance-shaped procedure list
  although new issuance stopped 2026-02-12. The manifest marks visa procedures
  `NOT_APPLICABLE` for H-2 and the resolver shows the F-4 통합 note first.

## 7. Not verified in this sprint

- The 2026.9 editions remain `pending_review` / `needs_review` in
  `docs/source-manuals/source_manifest.json`; nothing here promotes them.
- Every guidance entry and document item carries
  `review_state: SEPT_2026_ORIGINAL_UNREVIEWED`. A line-by-line human review of
  the 110 entries / 687 items against the PDF is still required before the
  legacy card can be retired.
- Fee amounts are quoted from the 공통사항 fee table only; per-procedure fee
  exceptions outside that table were not cross-checked.
