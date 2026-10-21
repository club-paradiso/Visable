# Waymaker Genesis — Sources, document extraction, change monitoring, CI

Audit target: `club-paradiso/Visable` origin/main `0713370` (worktree `/Users/seonjaekim/dev/Visable-genesis`), audited 2026-10-19.
Unpushed branch `fix/waymaker-qa-2026-10-16` (~/dev/Paradiso) is mentioned only where it changes a conclusion (§7).

Status legend: VERIFIED (I checked primary evidence), OBSERVED (seen live), README-ONLY (only docs say so), INFERRED (my reasoning), UNVERIFIED.

## 0. What I did (live actions) and one incident

- Read every file named in the brief plus the scripts they call; listed `docs/source-manuals/`, `docs/source-laws/`, `data/sources/`, `data/manual-corpus/`, `backend/data/sources/manuals/`.
- Ran, offline, inside the worktree: `scripts/check_source_updates.py` (default + `--catalog-dry-run`, no network), `scripts/check_source_manuals.py`, `scripts/check_source_grounding_metadata.py`; script tests `test_decrypt_hwp_distribution`, `test_diff_manual_versions`, `test_monitor_hikorea_manual_board`, `test_convert_manual_hwp`, `test_current_manual_index` (all pass); the 6 script tests CI never runs (50 passed); backend tests `test_source_grounding_pipeline`, `test_source_grounding_metadata_schema` (19 passed), `test_manual_registry`, `test_manual_index_readiness`, `test_manual_locator`, `test_knowledge_deploy_context` (50 passed, 1 skipped: "index not built in this environment"); five non-CI check scripts (§4.4).
- **Reproduced the approved HWP extractions byte-for-byte** with the repo's own `scripts/decrypt_hwp_distribution.py` (olefile is not installed in `.venv-check` or any local Python, so I wrote a ~120-line stdlib CFB reader shim in the scratchpad; repo code unchanged). Results in §2.1.
- `gh run list` for all 11 workflows; `gh run view --log` for the latest board-monitor, manual-sync and repo-validation runs; `gh api` for branch protection and rulesets.
- 2 public GETs to `api.osv.dev` (Starlette advisories); 1 query through the session's korean-law MCP connector (`search_law "출입국관리법"`).
- **Incident (disclosed):** `scripts/visa/check_260617_subcode_inventory_coverage.py` is a "check" script that *writes* `docs/data/2026_06_17_subcode_coverage_report.json`. Running it modified that tracked file in the read-only worktree. I copied the output to the scratchpad (`work/subcode_coverage_report_run.json`) and restored the file with `git checkout -- <file>`; `git status --short` is empty afterwards (verified). The finding it produced is in §4.4.

---

## 1. Source document inventory

### 1.1 Manual editions (MoJ 출입국·외국인정책본부)

Canonical pointer: `docs/source-manuals/source_manifest.json` (`current`, `pending_review_editions`, `special_program_manuals`, `audit_history`). Approval layer: `data/manual_approval_index.json` (byte-identical copy in `backend/data/knowledge_deploy/`). Monitor allow-list: `data/source_registry.json` (identical deploy copy). [CODE files; diff run: identical] VERIFIED

| Edition (role) | Format / path | Extraction method | Extracted text | Review status on main |
|---|---|---|---|---|
| 2026.7 visa, 2026-07-31 | 배포용 HWP `docs/source-manuals/2026-07-31/visa_manual_260731.hwp` (sha `0c5bc2d1…`) | `scripts/decrypt_hwp_distribution.py` (ViewText AES-128-ECB → PARA_TEXT) | `…/extracted/full_text/visa_manual_260731.txt` 471,659 chars | **approved** 2026-08-09 by a named reviewer; manifest `current` |
| 2026.7 stay, 2026-07-31 | 배포용 HWP `docs/source-manuals/2026-07-31/stay_manual_260731.hwp` (sha `d2c6dc54…`, 3,274,752 B) | same | `stay_manual_260731.txt` 720,629 chars | **approved** 2026-08-09; `current` |
| 2026.7 stay, 2026-07-31 (**second, different binary**) | `backend/data/sources/manuals/260731_stay_manual.hwp` (sha `bde0e845…`, 3,252,736 B) | pyhwp ViewText traversal (per `docs/audits/manual-260731-targeted-refresh.md`) | `260731_stay_manual_extracted.txt` | not registered anywhere; cited by 10 `visa_data.json` refs [corrected by verifier: not in the registry, manifest or approval index, but its sha256 `bde0e845…` and size are recorded in `docs/audits/manual-260731-targeted-refresh.md:14` as the 260731 attachment of HiKorea notice NTCCTT_SEQ=1062, so it is documented, just not registered. The 10 refs cite the pyhwp text `260731_stay_manual_extracted.txt` (committed sha256 `58c152c5…`), not the binary. The backend visa copy `260731_visa_manual.hwp` has the same sha256 as the approved visa HWP (`0c5bc2d1…`), so only the stay copy differs. VERIFIED by shasum and grep, 2026-10-19] |
| 2026.9 visa, 2026-09-01 | 배포용 HWP `docs/source-manuals/2026-09-01/visa_manual_260901.hwp` | decrypt script | 474,472 chars | needs_review (pending) |
| 2026.9 stay, 2026-09-01 | 배포용 HWP `…/2026-09-01/stay_manual_260901.hwp` | decrypt script | 726,288 chars | needs_review (pending; superseded in-manifest by 09-18) |
| 2026.9 visa, 2026-09-01 | PDF `docs/source-manuals/2026-09/visa_manual_260901.pdf`, 519 pp | `scripts/build_current_manual_corpus.py` (PyMuPDF 1.28.2 words, geometric de-dup) | `data/manual-corpus/visa_manual_2026_09_01_pdf.json` + `.txt` | needs_review |
| 2026.9 stay, 2026-09-18 | PDF `…/2026-09/stay_manual_260918.pdf`, 810 pp | same | `stay_manual_2026_09_18_pdf.json` | needs_review |
| 2026.9 stay, 2026-09-18 | 배포용 HWP `…/2026-09/stay_manual_260918.hwp` | decrypt script | 726,907 chars | needs_review; edition pinned by diff vs 09-01 HWP + PDF (`audits/manual-refresh-260921/stay_hwp_260901_to_260918.md`) |
| 2026.6 visa 06-17 / stay 06-23 | PDF exports `backend/data/sources/manuals/2606{17,23}_*_exported.pdf` (487/780 pp) + `*_readable.txt`, `*_sections.json` | pdf text layer (`scripts/visa/extract_2026_pdf_manuals.py`) | yes | superseded (registry `deprecated`) |
| 2026.6 stay HWPX 06-23 + change log HWPX | `260623_stay_manual.hwpx`, `260623_visa_stay_change_log.hwpx` | `scripts/extract_hwpx_text.py` | output is only `UNREADABLE: manifest marks this section as encrypted` per section | diagnostic only |
| 2026.6 visa HWP 06-17 | `260617_visa_manual.hwp` | none recorded | — | unregistered |
| 2026.5 (05-21) visa/stay | PDF + 배포용 HWP in `docs/source-manuals/2026-05/` (+ `incoming/` copies) | pdftotext/pypdf; HWP was "blocked" at the time | 2026-05 crosswalk files | superseded |
| 2026.5 stay 06-01 | PDF + HWP `docs/source-manuals/2026-06/` | pypdf sampling | page samples | superseded |
| 2026-07-09 extracts | `260709_{visa,stay}_manual_extracted.txt` (no binary) | unknown | — | unregistered |
| 2026-07-31 change history | `260731_change_history.hwp` + 3-line extract | pyhwp table traversal | yes | unregistered |
| K-CORE (E-7-M) 2026.6, 시행 2026-03-05 | standard HWP `260629_kcore_manual.hwp` | olefile BodyText PARA_TEXT (`scripts/extract_kcore_manual_260629.py`) | 15,970 chars, 13 sections | `special_program_manuals` status current; **not in source_registry or approval index** |
| 외국국적동포 manual 2026.2 | PDF `260421_dongpo_manual.pdf` (2-up, 32 pp) | pypdf (`scripts/extract_dongpo_manual_2026_02.py`) | 32 sections | indexed as needs_review (no registry entry → defaults to most restrictive state) |

[DOC docs/source-manuals/source_manifest.json; CODE data/source_registry.json; CODE data/manual_approval_index.json; LIVE shasum of all binaries 2026-10-19] VERIFIED.

Observations:
- `docs/source-manuals/SOURCE_MANUALS.md` still says the "current" manuals are the 2026-06-17/23 PDFs, while the manifest's `current` is the 2026-07-31 HWP pair. [DOC SOURCE_MANUALS.md vs source_manifest.json] VERIFIED doc drift.
- Registry lacks entries for `visa_manual_2026_09_01_hwp`, `stay_manual_2026_09_01_hwp`, the K-CORE manual, and the dongpo manual, though the approval index has the first two. [CODE data/source_registry.json] VERIFIED.
- `docs/source-manuals/ocr` is a 1-byte file (a newline), not a directory; there is no OCR stage anywhere (§2). VERIFIED.
- The approved 2026.7 edition is ~7 weeks behind the 2026.9 edition that HiKorea has published. The repo's own change review lists, e.g., the E-7-4 income threshold change 2,500→2,589만원 and a 시행일 shift to '26.8.31 (`audits/manual-refresh-260901/README.md`). On main these 2026.9 changes exist only as 검토 전 material. [DOC audits/manual-refresh-260901/README.md] VERIFIED (that the doc says so); the legal content itself was not checked by me.

### 1.2 Laws and annex forms

| Item | Path | Edition / provenance | Status |
|---|---|---|---|
| Law source-set inventory (14 statutes/decrees/rules + HiKorea pages) | `docs/source-laws/LAW_SOURCESET_INVENTORY_2026_05.md`, `law_sources_2026_05.json` (40 entries) | URLs only, `OFFICIAL_ROUTE_RECORDED`, `inventory_version 2026-05-v5`; no MST, no dates | route list, not text |
| 출입국관리법 article text | `docs/source-manuals/law/crosscheck/lawgokr_act_272921_articles.txt` | header: lsiSeq 272921, [시행 2025-07-22], collected 2026-06-12 via "Legal Data Hunter MCP" | static snapshot |
| 출입국관리법 시행규칙 articles | `…/crosscheck/lawgokr_rule_283059_articles.txt` | lsiSeq 283059, [시행 2026-01-23], no 별표/서식 | static snapshot |
| 시행규칙 print PDF + text | `immigration_control_act_enforcement_rule_moj_01106_2026_01_23.pdf` (sha `ec72b933…`), `rule_1106_full.txt` (pdftotext `-layout`) | 법무부령 제1106호, 2026-01-23 | pinned in `data/forms_rule_1106_annex_pages.json` |
| 10 form images | `docs/source-manuals/law/forms/*.jpg` (150 dpi) | from rule 1106 | used by doc guide |
| Status-guidance law pins | `scripts/status_guidance/author_rules.py:316-318` | act MST 272921 labelled `effective 2026-01-23`; decree MST 289697 `2026-09-15`; rule MST 289833 `2026-09-15` | manual pins, read 2026-09-22 |

Live check [LIVE korean-law MCP `search_law("출입국관리법")`, 2026-10-19] OBSERVED: the Act is now MST **290729** (promulgated 2026-08-04, effective 2026-10-02); the Decree is MST **290501** (promulgated 2026-09-29, effective 2026-10-02); the Rule is MST 289833 (2026-09-15), **plus a future-effective amendment (제01125호, promulgated 2026-09-15, effective 2027-09-16)**. Nothing in the repo references 290729 or 290501 (grep, VERIFIED). So the Act and Decree pins are at least one version behind, and nothing detected it. [corrected by verifier: addition. The stale pins are not confined to the authoring script. They ship in the deployed knowledge file `backend/data/knowledge_deploy/status-guidance-202609.json` (act `mst 272921` at lines 379/395/411, decree `mst 289697` at 427-475). `data/form_schemas.json` pins the rule MST 289833, which is still current. The unpushed branch leaves `author_rules.py:316-318` unchanged. VERIFIED by git grep and git show, 2026-10-19; live MCP result re-observed by the verifier, same date.] A further inconsistency: `author_rules.py:316` labels act MST 272921 `effective 2026-01-23`, but the crosscheck snapshot of the same lsiSeq says [시행 2025-07-22]. [CODE scripts/status_guidance/author_rules.py:316; DOC crosscheck header] VERIFIED.

`data/forms_inventory.json` records that the rule "was amended again with effect 2026-09-15 (MST 289833); annex revisions after 2026-01-23 could not be verified offline". It holds per-form `revision_on_form` and `edition_verification` (14 `VERIFIED_CURRENT`, 1 `PENDING_HIKOREA` = F06), and per-annex `revision` strings ("개정 2012.1.19") for all 292 annexes. [CODE data/forms_inventory.json] VERIFIED. This is the only place with date-specific annex versioning, and it is maintained by hand.

### 1.3 `data/sources/`

| File | What it is | Extraction |
|---|---|---|
| `hikorea_employment_reporting_overview.hwpx`, `…_procedure_visit.hwpx` (7 embedded BinData images), `…_faq.docx` | 취업정보 신고 attachments | cited as provenance by `scripts/build_employment_reporting_dataset.py:337-339`; images not extracted |
| `ksco7th_provided_text_2026-06-14.txt`, `ksco8_isco08_linkage_2026.xlsx` (→ `scripts/convert_ksco8_isco_linkage.py`), `ksic11_full_2038.csv` | occupation/industry classifications | `scripts/extract_employment_reporting_full_tables.py` (pdftotext `-layout` + line regex) |
| `민원대행_등록기관_2026-04-30.{pdf,xlsx}`, `medical-institutions/…_2026-04-30.pdf` | agency/clinic directories | separate builders (not audited in depth) |
| `hikorea_manual_sync.json`, `hikorea_manual_board_watch.json`, `hikorea_source_catalog.json` (+`.example`), `immigration_notice_sources.json` | monitor configs | §3 |

Employment table manifests: `data/employment_reporting_full_table_extraction_manifest_2026_05.json` (status `CANDIDATE_EXTRACTED_FROM_USER_PROVIDED_PDFS`, `runtime_use NOT_ENABLED_FOR_PRODUCTION_RUNTIME`; KSCO8 1,999 rows, KSIC11 2,038 rows) and `…_table_sample_validation_2026_05.json` (`SAMPLE_VALIDATION_PASSED_WITH_RUNTIME_GATES_REMAINING`; count match, 0 duplicate/blank/missing-parent). The two candidate CSVs it names (`data/generated/employment_reporting_{ksco8,ksic11}_full_candidate.csv`) are **not in the repo**; only `employment_reporting_ksco8_candidate.csv` and `data/sources/ksic11_full_2038.csv` exist. `docs/data/EMPLOYMENT_HELPER_FULL_TABLE_RUNTIME_2026_05.md` says the same ("Not present"). [CODE data/*.json; ls data/generated] VERIFIED, and the gap is documented.

---

## 2. Extraction audit

### 2.1 Pipelines

1. **배포용 HWP → text** (`scripts/decrypt_hwp_distribution.py`). It reads `ViewText/Section*`, derives the AES key from the in-file DISTRIBUTE_DOC_DATA record, decrypts, inflates, and keeps only `HWPTAG_PARA_TEXT` records, at every nesting level, in stream order (`:268-270`). Every control character is dropped: inline/extended controls take 8 WCHARs and include tab (9), tables/drawing objects (11), header/footer (16) and footnote/endnote (17) (`:51-53`, `:233-235`). Code 10/13 becomes `\n`; other char-controls below 32 (for example 24 hyphen, 30 non-breaking space, 31 fixed-width space) are silently dropped (`:226-238`). [CODE] VERIFIED. [corrected by verifier: wording. "Every control character is dropped" overstates it: line break (10) and paragraph break (13) are kept as `\n`. Everything else below 32 is dropped. Codes in `CTRL_INLINE` {4-9,19,20} and `CTRL_EXTENDED` {1-3,11,12,14-18,21-23} each skip 8 WCHARs (`:51-53`, `:234-236`). Only `TAG_PARA_TEXT` (67) records are kept (`:268-270`). Re-read 2026-10-19.]
   - Reproduction [LIVE local run 2026-10-19, shim + repo code]: visa 07-31 → `a80ec1f3…` = committed; stay 07-31 (`d2c6dc…`) → `f9f040b1…` = committed; stay 09-18 → `807c19ae…` = committed; all `U+FFFD = 0`. **VERIFIED** (the "byte-for-byte" claim was README-ONLY until now).
   - Running the same extractor on the **other** 07-31 stay binary (`backend/…/260731_stay_manual.hwp`, `bde0e845…`) yields `8fb99359…` (720,633 chars). It differs from the approved text in exactly one line, at approved-text line 8237 (E-7-4 동시고용 section, "5 시행 일자 등"): approved copy `‘26. 7. 9.(목)` vs backend copy `‘24. 11. 27.(수)`. Two files both presented as "the 260731 stay manual" therefore disagree on a 시행일자, and neither the manifest, the registry, nor any audit records the discrepancy. [LIVE diff] VERIFIED. The backend copy came in with PR #552 (2026-08-03) and is the `sourceFile` behind 10 `visa_data.json` refs; the approved copy came in with PR #562 (2026-08-09). [git log] VERIFIED. Which file HiKorea serves today is UNVERIFIED (I did not download it). [corrected by verifier: more precisely, the 10 refs name `backend/data/sources/manuals/260731_stay_manual_extracted.txt`, the committed pyhwp extraction of the backend copy, which has the `‘24. 11. 27.(수)` line at its line 7899. The same `‘24. 11. 27.` value appears in the older `260709_stay_manual_extracted.txt:15774`, and both 2026.9 stay HWP texts read `‘26. 8. 31.(목)` at line 8261. The backend copy therefore carries the earlier edition's value, but which 07-31 binary is authentic is still UNVERIFIED. Diff re-run by verifier, 2026-10-19: exactly one differing line, 8237.]
2. **Standard HWP** (K-CORE): olefile BodyText PARA_TEXT parser, with the same control-skipping semantics. [CODE scripts/extract_kcore_manual_260629.py, scripts/extract_hwp_manual_text.py] VERIFIED.
3. **HWPX** (`scripts/extract_hwpx_text.py`): ZIP + XML walk; emits ` | ` after each `tc`/`cell` and `\n` after each `tr` (`:70-76`); ignores `rowSpan`/`colSpan`; encrypted sections become an explicit `UNREADABLE:` line (`:119`). `paragraph_nodes()` (`:87`) returns *every* `p`, including paragraphs nested in table cells, and `xml_text()` walks descendants, so cell text can be emitted twice: once inside the parent paragraph and once on its own (INFERRED from code; untested against a real readable HWPX). Not run in CI (§4.4).
4. **PDF 2026.9 corpus** (`scripts/build_current_manual_corpus.py`): validates sha and page count *before* writing (`:66-70`); per page it removes duplicate-paint words by geometry, records `has_images` (`:89`), `status_codes_detected`, `subcodes_detected`; raises on an empty page or U+FFFD (`:79`). It writes the registry, approval-index and manifest entries as `needs_review` and never overwrites an existing review (`setdefault`, `:124`). [CODE] VERIFIED. Counts [LIVE local read]: visa 135/519 pages have images, stay 199/810; 15 visa and 23 stay pages have under 200 characters of text (for example visa p.278 "붙임13 외국인등록용 사진 규격" with an image, and p.346 containing only "- 346 -").
5. **Legacy PDF tools**: `scripts/extract_manual_page_text.py` is still hard-wired to the 2026-05 visa and 2026-06-01 stay PDFs (`:31-38`), so it cannot verify page citations for any current edition. [CODE] VERIFIED (stale tool).
6. **Converter benchmark** (`scripts/convert_manual_hwp.py`): runs `viewtext_aes`, olefile, LibreOffice→pdftotext, and optional external CLIs (pyhwp `hwp5txt`, hephaex/hwp2md, kordoc, roboco hwp2md). Its quality score is length, Korean ratio and anchor/code counts only; it has no table or structure metric. Its docstring and `docs/hikorea_manual_sync.md` still say no open tool can extract 배포용 HWP, which the decrypt script contradicts. [CODE; DOC] VERIFIED doc drift.
7. **Employment classification tables**: pdftotext `-layout` text parsed line by line with code regexes; short Korean continuation fragments are appended to the previous title. Merged cells and multi-line titles are handled heuristically, and validation is limited to level counts. [CODE scripts/extract_employment_reporting_full_tables.py:1-60,149] VERIFIED.

### 2.2 Feature matrix (what is handled, what is flattened, and whether the gap is marked)

| Feature | 배포용/standard HWP (approved path) | 2026.9 PDF corpus | HWPX | Marked as unverified? |
|---|---|---|---|---|
| Merged cells | **Flattened.** Cell texts emitted in record order; spans lost. Example: the 심사수수료 table in `stay_manual_260731.txt` from line 82 (`근거`/`업무명`/`수수료` header cells) becomes a run of `업무명`/`수수료` lines. The sub-row `결혼이민(F-6) 4만원` follows `체류자격 부여 8만원` with nothing tying it to its parent row. | Flattened by reading order (`get_text(sort=True)`) | rowSpan/colSpan ignored | Yes, per document: `table_extraction_warnings` in the approval index ("must not be read as a structured table") and manifest notes. **Not per passage**: the warning is consumed only by `manual_registry.py:149-182,271` and the `/api/search/manual-evidence-state` summary. No hit or answer carries it (grep, VERIFIED). |
| Nested tables | Cell paragraphs inlined; nesting invisible | inlined | possible duplication (INFERRED) | Same document-level warning only |
| Empty cells | Disappear (no PARA_TEXT, or an empty line), so column alignment shifts silently | disappear | ` | ` separators keep the position | No |
| Footnotes/endnotes | Ctrl 17 skipped; the note's paragraphs appear after the anchoring paragraph with no marker (INFERRED from record order). Manual-style `*`/`※` notes are plain text and preserved, e.g. `국민고용*인원` followed by `* 4대 사회보험…`. | preserved as page text | as text | No |
| Multi-page tables | No pages, so the table stays contiguous (advantage) | Split across page chunks; header not repeated; no join | n/a | No |
| Numbered exceptions / list markers | Hancom private-use glyphs pass through unmapped: visa 07-31 has 281 PUA chars (18 distinct), stay 07-31 436, stay 09-18 PDF 455. Circled list numbers come out as U+F02B1, U+F02B2, …, before items like `신고대상` and `신고시기`; a TOC glyph comes out as U+F007E. (`(특례)`, `가.`, `-` markers are ordinary text and preserved.) | same PUA in PDF text | n/a | No. Search/regex for ①② will miss them, and UIs may show tofu. |
| Special symbols (○ ※ ☞ ‣ ✕ ’ ｢｣) | preserved | preserved; fancy dashes normalised for code detection only (`DASHES`) | preserved | n/a |
| Tabs / NBSP | Tab (9) and NBSP (30) dropped **without a space**, so adjacent tokens can glue (INFERRED from code; `extract_hwp_manual_text.py` then collapses spaces). Committed text has 0 tab characters (VERIFIED). | n/a | NBSP→space | No |
| Scanned pages | n/a (text layer) | No OCR. Empty pages hard-fail the build, but a page with only a footer passes silently. | n/a | Partially: `has_images` flag in the corpus JSON, and the catalog warning "image content … require checking the original page". |
| Embedded images | **Dropped with no placeholder.** Example: approved visa text line ~8177 `붙임13 외국인등록용 사진 규격` is followed directly by the next chapter. Flowcharts and photo specs vanish. | `has_images` recorded per page, but **no consumer** in `assets/js` or `backend/services` (grep, VERIFIED) | BinData ignored | Not in the HWP path; the PDF flag is unused |
| Table references (별표 N, 붙임 N) | Preserved as text; never resolved or linked | same | same | No |
| Date-specific annex versions | Manuals: none (one edition per file; no 별표-level dating) | none | n/a | Forms only: per-annex `revision`, per-form `edition_verification` in `data/forms_inventory.json` (manual) |

Bottom line for (b): the approved evidence is a faithful *linear text layer*, reproducibly extracted. All table structure, images and footnote linkage are flattened. The repo is honest about tables at the document level, but **no passage-level "this came from a table / page has images / glyph unmapped" flag reaches retrieval or answers**. The unpushed branch partly addresses this (§7).

---

## 3. Regulatory change detection

### 3.1 What exists today

| Mechanism | What it actually detects | Live status |
|---|---|---|
| `scripts/check_source_updates.py` (CI step [5/12], `source-monitoring.yml` manual-only) | sha256 of **committed local files** against `last_known_hash` (`_check_local`, `:501`). `law_api`/`notice_index` entries are `not_configured`, and even with `--allow-network` it returns "HTTP fetch not implemented in skeleton" (`:547`). Catalog dry-run: 0 eligible records (all `monitor_enabled=false`). | Local run: 5 unchanged, 11 skipped. It detects tampering with the repo, **not upstream change**. [LIVE local] OBSERVED [corrected by verifier: with the current registry, `--allow-network` would not produce the "not implemented" message. `_check_source` (`:567-573`) returns `skipped: not_configured` for every law_api/notice entry before it reaches `_check_network_entry`. The "HTTP fetch not implemented in skeleton" string (`:547`) is reachable only for a law_api/notice entry whose status is not `not_configured`. The catalog dry-run path does have a real allowlisted fetcher (`:464`), but all 34 catalog records are `monitor_enabled=false` (`--list-disabled`). Re-run 2026-10-19: 16 total, 5 unchanged, 11 skipped; Eligible records: 0.] |
| `hikorea-manual-board-monitor.yml` (weekly) → `monitor_hikorea_manual_board.py` | sha256 of the full visible text of the HiKorea 자료실 and 공지 list pages against `baseline_content_hash` | **Both baselines are `null`** in `data/sources/hikorea_manual_board_watch.json`, so every run returns `baseline_unset` (`:96-97`) and can never report `changed`. Runs on 2026-10-05 and 2026-10-12 fetched successfully and logged `{"hikorea_materials_board":"baseline_unset","hikorea_notice_board":"baseline_unset"}` with conclusion success. [LIVE gh run view 38211467187, 37270107456] **OBSERVED**. Change detection is structurally off behind a green check. Even with a baseline, a whole-page hash of a notice list would fire on every unrelated notice (INFERRED). |
| `hikorea-manual-sync.yml` (1st/15th) → `sync_hikorea_manuals.py` | sha of a *supplied* HWP against `baseline_sha256` | `download_url: null` for both manuals, so the scheduled run is a no-op. The 2026-10-15 log says "no manual input and no usable download_url" (each run still apt-installs LibreOffice). [LIVE gh run 38688541847] OBSERVED. The baselines point at the 2026-09-01 HWPs, not the approved 07-31 or the newer stay 09-18. [corrected by verifier: addition. Setting `download_url` alone would not fix the cron. The workflow adds `--allow-network` only when `inputs.allow_network == 'true'`, and that input exists only on `workflow_dispatch`, so scheduled runs never fetch (log line: `if [ "" = "true" ]`). [CODE .github/workflows/hikorea-manual-sync.yml run-manual-sync step; LIVE gh run view 38688541847, 2026-10-19] OBSERVED] |
| `diff_manual_versions.py` (page) / `diff_manual_paragraph_editions.py` (paragraph) | Structured edition diff: hunks, anchors, `affected_status_codes`, `extraction_mismatch_suspected` | Used manually for `audits/manual-refresh-260901/*` (visa 107 hunks/12 parents; stay 120/12) and `audits/manual-refresh-260921/*` (stay PDF 334 page changes, 150 codes). The paragraph tool's test is **not in CI**. [CODE; DOC] VERIFIED |
| Knowledge layer (`backend/services/knowledge/`) | Facts carry `effective_from/effective_to`, lifecycle `SUPERSEDED`; `evaluate_source_refresh` (`adapters.py:153`) marks a source `refresh_due` when PUBLISHED facts cite a superseded edition **and** a newer *approved* edition exists. `diff.py` gives a deterministic ADDED/REMOVED/CHANGED fact diff between two editions. | Edition-granular. It needs both editions already turned into facts, and never fires while the newer edition is unapproved (true on main for 2026.9). [CODE] VERIFIED; runtime population UNVERIFIED |
| Runtime law layer (`law_tools.py:382-411`, `law_query_normalizer.py:574-602`) | Per-request live search returns 공포일자/시행일자/현행연혁코드; `classify_law_lifecycle` maps repealed and 시행예정 (status token or future 시행일). **연혁 (historical) rows are labelled `verified`**, the same label as current ones (`:600-601`). | Query-time only. Nothing persists the law identities a fact relies on, and nothing compares across time. [CODE] VERIFIED |
| `short-stay-freshness.yml` (monthly) | Date-based staleness for short-stay data; opens or closes an issue | success 2026-10-01 [LIVE gh] OBSERVED |
| Manual edition-identity pinning | sha256 per file, verified on every CI run for current and pending (`check_source_manuals.py`) | OK; but `extracted_text_sha256` of **current** entries is not re-verified (only pending ones are). I verified the hashes by hand: all match. |

### 3.2 Target vs today

| Target capability | Today | Gap |
|---|---|---|
| Track law identities (법령ID + MST per fact) | Hand-pinned in `author_rules.py:316-318` and `forms_inventory.json`; the registry's `law_api_placeholder` is `not_configured` | No registry of law IDs, no link from facts to law versions |
| Detect new versions | None automated. The Act moved 272921→290729 and the Decree 289697→290501 (both effective 2026-10-02) undetected (OBSERVED) | Need a scheduled poller keyed by 법령ID |
| Promulgated vs effective | Captured at query time only; the inventory JSON has no dates | Persist both dates per version |
| Future-effective amendments | Runtime `시행예정` classification only; the Rule's 2027-09-16 amendment is not recorded anywhere in the repo | Need a forward calendar plus a "pending effective" fact state |
| Modified provisions | Manual: paragraph/page diff with affected codes (good). Law: none (no 신구대조/article-history use) | Article-level diff for laws |
| Affected knowledge facts | Edition-level `refresh_due`; manual diff → affected *status codes* | No provision→fact mapping |
| Outdated checklists/citations | Not detected. 1,268 of 1,292 `visa_data.json` `sourceFile` refs point at superseded 2026.6 and 2026.5 files (859 to `260623_stay_manual_readable.txt`, 368 to `260617_visa_manual_readable.txt`, 41 to the 2026-06-01 PDF); only 22 refs are `manualVersion 2026.7`. CI step [3/12] actively **requires** `manualRequiredDocAudit.manualVersion == "2026.5"` (`check_repo.sh:122`). [LIVE count; CODE] VERIFIED | Need a citation-freshness check; the current one pins staleness |
| Human-review flags | Strong. Approval index fails closed; `current` slot is approval-gated by test; pending editions are hash-pinned; status records keep `needsManualReview` | Good |
| Structured change report | Exists for manual editions (JSON+MD, hunks, affected codes) | Not produced automatically; not for laws, forms or notices |

### 3.3 Does anything auto-publish?

- No workflow edits production data, merges, or deploys. Writers: `hikorea-manual-sync` (`contents: write`, `pull-requests: write`) can push branch `auto/hikorea-manual-sync` and open a **draft** PR limited to `docs/source-manuals/incoming/**`; the board monitor and short-stay workflows (`issues: write`) open, update and close issues. [CODE workflows] VERIFIED. [corrected by verifier: only `short-stay-freshness.yml` closes issues (`state: 'closed'`, line 82). The board monitor opens or updates one marker issue, and only when `changed == 'true'`, which cannot happen while baselines are null; it never closes one.]
- But `main` has **no branch protection and no rulesets** (`gh api …/branches/main/protection` → 404 "Branch not protected"; `/rulesets` → `[]`) [LIVE 2026-10-19] OBSERVED. A push to main is followed by an asynchronous Railway deploy, which `railway-live-smoke.yml` waits for and verifies by commit SHA (INFERRED from its readiness loop); `vercel.json` indicates Vercel Git integration for the static site (INFERRED). So any merged change to `visa_data.json` or the approval index goes live with no required checks. The human-in-the-loop guarantee is procedural, not enforced. [corrected by verifier: the Railway coupling is now OBSERVED, not just inferred. The `railway-live-smoke` run 38292940698 for push `0713370` logged 11 probes of "health=ok but serving 283983fcbb9b, waiting for 071337067352", then "deploy verification: serving 071337067352, matches this commit" at 18:46:19Z, about 2 minutes after the 18:44 push. Also `gh api repos/club-paradiso/Visable/rules/branches/main` → `[]`, so no org-level ruleset applies either. LIVE 2026-10-19. The Vercel part is still INFERRED.]
- `railway-live-smoke.yml` (push to main) **POSTs to production `/api/ask` 3 times** (one with diagnostics, sending the `PARADISO_DIAGNOSTICS_TOKEN` secret header) and to `/api/enforcement/analyze`, which uses real provider quota on every merge. `enforcement-runtime-benchmark.yml` POSTs to production `/api/enforcement/{extract,analyze}`. [CODE] VERIFIED.

---

## 4. CI coverage

### 4.1 Workflows (last 3 runs via `gh run list`, 2026-10-19)

| Workflow | Trigger | Runs | Secrets / vars | Can write? | Last 3 |
|---|---|---|---|---|---|
| repo-validation | PR; push main/feat/fix/test; dispatch | `check_repo.sh` (Py 3.11 + requirements-dev + PyMuPDF 1.28.2); mobile-render-qa (Node 22, puppeteer-core 24.16.0); webkit QA (PR only); 10 Playwright specs (`@playwright/test@1.61.0`) | none | read | success ×3 (2026-10-12, head `0713370`); webkit job skipped on push [corrected by verifier: only the latest run (38292940589, push) is at `0713370`; the other two are PR head `47c5d86` and push `283983f`, both 2026-10-12] |
| hikorea-manual-board-monitor | cron Mon 00:30 UTC; dispatch | board monitor `--allow-network` | GITHUB_TOKEN | issues | success ×3 (09-28, 10-05, 10-12), all `baseline_unset` |
| hikorea-manual-sync | cron 1st/15th 01:00; dispatch | apt LibreOffice+poppler, `pip install olefile pyhwp` (**unpinned**), converter self-test, sync | vars `HWP2MD_HEPHAEX_CMD`, `KORDOC_CMD`, `HWP2MD_ROBOCO_CMD`; GITHUB_TOKEN | contents+PR (draft PR via `peter-evans/create-pull-request@v6`) | success ×3 (09-15, 10-01, 10-15), no-op |
| hikorea-manual-converter-benchmark | dispatch only | installs `cargo install hwp2md`, `go install …@latest`, `npm install -g kordoc` (**all unpinned**) | none | read | never run |
| hikorea-source-monitor-smoke | dispatch only | `run_hikorea_monitor_smoke.py` | none | read | success ×3 (2026-05-25) |
| source-monitoring | dispatch only | `check_source_updates.py --local-only`; candidate validator | none | read | never run |
| manual-code-coverage | PR/push on data and manual paths | `build_visa_data.py --check`; `check_manual_code_coverage.py` (system python, unpinned) | none | read | success ×3 (2026-09-22) |
| short-stay-freshness | cron monthly | `check_short_stay_freshness.mjs` (Node 20) | GITHUB_TOKEN | issues | success ×3 |
| railway-live-smoke | push main; dispatch | live probes of the production backend (above) | `PARADISO_DIAGNOSTICS_TOKEN` | read | success ×3 |
| enforcement-model-benchmark | dispatch; push to `perf/enforcement-benchmark-20260904` | dry-run, then live OpenRouter comparison (Py 3.12) | `OPENROUTER_API_KEY` | read | success ×3 (2026-09-04) |
| enforcement-runtime-benchmark | dispatch; same perf branch | POSTs to production enforcement API | none | read | success, success, cancelled (2026-09-04) |

Action refs are tag-pinned (`@v4/@v5/@v6/@v7`), not SHA-pinned. `hikorea-manual-sync.yml` interpolates `${{ inputs.manual_hwp_* }}` straight into a shell line, so a dispatch input can inject shell (needs write access; low). The `*_CMD` repo variables are templates that `convert_manual_hwp.py` executes. PRs opened with GITHUB_TOKEN do not trigger other workflows, so the auto draft PR gets no CI run (INFERRED, standard GitHub behaviour).

### 4.2 `scripts/check_repo.sh` (14 labelled steps; numbering mixes /12 and /14)

JSON validity and U+FFFD scan; representative manual-aware schema (C-3, D-2, F-6, K-STAR must stay `needsManualReview=true`; every status needs extension/registration `manualRefs`; **`manualVersion` must be "2026.5"**); `check_source_manuals.py`; `check_source_updates.py --local-only` (report-only); script tests `test_diff_manual_versions`, `test_monitor_hikorea_manual_board`, `test_decrypt_hwp_distribution` (synthetic payloads only; it never decrypts a committed HWP, and the pycryptodome cross-check is skipped), `test_railway_live_smoke`; offline board monitor; `check_source_grounding_metadata.py` + its schema tests; `check_current_manual_corpus.mjs` + `test_current_manual_index.py` (asserts the 2026.9 PDFs stay `needs_review` with empty reviewer, 1,329 pages, exact-subcode search); candidate validator; coverage matrix; `git diff --check`; landing shell and tokens; i18n; employment dataset and helper suites; F-4 hub; subcode modal and dummy-text scans; route guides; status-guidance `--check` builds and ~10 Node checks; visa-issuance UI; Waymaker navigator; nationality data; enforcement contracts; branding regex; `sync_visa_data.py --check`; required-docs coverage; procedure semantics; duplicate-render audit; AI architecture guard; **full backend suite via `run_backend_tests.py`**; golden eval (non-strict); knowledge eval corpus (`--strict`). [CODE scripts/check_repo.sh] VERIFIED.

### 4.3 `scripts/run_backend_tests.py` and the KNOWN_FAILING register

It discovers every `backend/tests/test_*.py` (81 modules) and runs each in its own subprocess under pytest. A 0-test collection counts as failure. Buckets PASS/KNOWN/NEW/FIXED/SKIP; NEW or FIXED fail the build; `--strict` also fails on KNOWN. **`KNOWN_FAILING` is empty** (`:70`). Its comments record four former entries that were fixed by rewriting stale assertions (`test_core_journey_ux_hardening`, `test_expanded_route_wizard` + `test_i18n_sweep_route_wizard`, `test_source_grounding_pipeline`, `test_reentry_procedure_coverage`). `OPTIONAL_DEPENDENCY_MODULES` maps two pytest-style modules to `pytest` for SKIP when pytest is absent. CI log for `0713370`: "81 modules (via pytest) PASS 81 KNOWN 0 SKIP 0 NEW 0 FIXED 0 — full backend suite clean". [CODE; LIVE gh run view 38292940589] VERIFIED/OBSERVED.

### 4.4 What CI skips

- **Script tests never run by CI** (not in `check_repo.sh` or any workflow): `test_check_source_updates_catalogs`, `test_diff_manual_paragraph_editions`, `test_extract_hwpx_text`, `test_generate_candidate_from_matrix`, `test_generate_source_update_brief`, `test_run_hikorea_monitor_smoke`. Run locally: **50 passed**. `test_convert_manual_hwp` runs only inside the sync and benchmark workflows. [TEST scripts/tests/* (ran: pass)]
- **DOM tests self-skip in CI**: the `validate` job never runs `npm install`, so jsdom is absent. Log: "jsdom not installed — skipping DOM smoke test … SKIP" (×2) and the `check_public_dummy_text` rendered scan was skipped ("rendered: 0 HTML files"). [LIVE CI log] OBSERVED. There is no lockfile; `package.json` uses caret ranges (`@playwright/test ^1.61.0`, `jsdom ^24.1.0`), while CI installs exact versions ad hoc with `--package-lock=false`.
- **E2E specs not in CI** (8 of 18): bilingual-doc-names, complex-status-guide, easy-mode, new-home, search-smoke, unified-search, ux10-a11y, waymaker-navigator. [CODE] VERIFIED.
- **Check scripts never invoked** (directly or via tests), among others: `check_doc_master_integrity.py`, `check_model_catalog.py`, `check_visa_data_text_integrity.py`, `scripts/visa/check_manual_refresh_coverage.py`, `check_subcode_parity.py`, **`check_260617_subcode_inventory_coverage.py`**, `check_exact_code_search*.{js,py}`, `check_status_variant_indexing.py`, `check_record_store_union_parity.py`, `check_short_stay_rules.mjs`, `check_d2_student_journey.js`, `check_priority/remaining_status_journeys.js`, plus all `smoke_ai_*.py` / `smoke_*law*`. I ran five: four pass, but **`check_260617_subcode_inventory_coverage.py` FAILS on main**: 13 authoring subcodes (F-4-11…F-4-21, F-4-25, F-4-30) lack source support, manualRefs and `needsManualReview`, and F-2-6 is shown active although deprecated or abolished. The committed report (`docs/data/2026_06_17_subcode_coverage_report.json`, last changed 2026-06-28) still says `passes: true` with 0 issues. [TEST (ran: fail); git log] VERIFIED. This is a silent regression of the "no subcode without source/review flag" invariant.
- No CI job decrypts a real HWP, so a regression in the approved extraction path would go unnoticed. The KNOWN register being empty does not cover script- or Node-level suites.

### 4.5 Runtimes and dependencies

- Python: CI 3.11 (repo-validation, board monitor, smoke, benchmark), 3.12 (enforcement benchmarks), **unpinned runner `python3`** (manual-sync, manual-code-coverage); [corrected by verifier: only `enforcement-model-benchmark` sets 3.12. `enforcement-runtime-benchmark` (line 37) and `railway-live-smoke` (line 23, inline `python3 -u -`) have no setup-python and also use the unpinned runner `python3`. CODE grep, 2026-10-19] local `.venv-check` 3.11.15. Railway uses NIXPACKS with no `runtime.txt` or `.python-version`, so the production Python is unpinned (INFERRED).
- Node: 22 (QA/E2E jobs), 20 (short-stay, converter benchmark), runner default for `check_repo.sh` (unpinned); local v24.14.0. No `.nvmrc`.
- `backend/requirements.txt`: fastapi 0.115.0, starlette 0.38.6, uvicorn[standard] 0.30.6, pydantic 2.9.2, httpx 0.27.2 (exact pins, no hashes). `requirements-dev.txt`: + pytest 9.1.1. `scripts/requirements-manuals.txt`: PyMuPDF 1.28.2. **olefile is in no requirements file**: `decrypt_hwp_distribution.py`, `extract_kcore_manual_260629.py` and `convert_manual_hwp.py` need it [corrected by verifier: so does `scripts/extract_hwp_manual_text.py`, so four scripts import it (git grep "import olefile")], and the venv lacks it (VERIFIED: `ModuleNotFoundError`). pycryptodome is optional.
- Security: starlette 0.38.6 is in range for **CVE-2024-47874** (GHSA-f96h-pmfr-66vw, fixed 0.40.0) and **CVE-2025-54121** (GHSA-2c2j-9gv5-cj73, fixed 0.47.2), both multipart DoS [WEB https://api.osv.dev/v1/vulns/GHSA-f96h-pmfr-66vw and …/GHSA-2c2j-9gv5-cj73, accessed 2026-10-19] VERIFIED. Exposure looks low: no `UploadFile`/`Form`/`request.form()` in the backend, and `python-multipart` is not installed (grep and import, VERIFIED). Upgrading requires a FastAPI bump, because 0.115.0 caps starlette below 0.39 (INFERRED from FastAPI's published constraints; not re-checked). [corrected by verifier: now VERIFIED. The installed fastapi 0.115.0 metadata in `.venv-check` declares `starlette<0.39.0,>=0.37.2`. The verifier also checked CVE-2025-62727 (GHSA-7f5h-v6xp-fcq8, Range-header DoS in FileResponse): its affected range starts at 0.39.0, so 0.38.6 is not affected, and the backend uses no `StaticFiles`/`FileResponse`. WEB https://api.osv.dev/v1/vulns/GHSA-7f5h-v6xp-fcq8, accessed 2026-10-19] Unpinned installs: `olefile pyhwp` in a write-token job, plus `kordoc`, `hwp2md`, roboco `@latest` in the benchmark. No Dependabot config (`.github/` contains only `workflows/`).

---

## 5. Risk register

| ID | Title | Sev | Evidence | Remedy |
|---|---|---|---|---|
| SRC-01 | Board change detection permanently off (null baselines) behind green runs | high | `hikorea_manual_board_watch.json` baselines null; runs 37270107456/38211467187 `baseline_unset` | Commit baselines; diff the parsed notice *rows* (title, date, attachment names) instead of a page hash; turn persistent `baseline_unset` or `unreachable` into a failure or issue |
| SRC-02 | No upstream law change detection; Act and Decree pins already stale (272921→290729, 289697→290501, effective 2026-10-02); 2027-09-16 future amendment unrecorded | high | `author_rules.py:316-318`; korean-law MCP live result | Law-identity registry (법령ID, MST, 공포/시행일, 시행예정) polled on schedule; open an issue and a structured change report; flag facts that cite each law |
| SRC-03 | Two different "260731 stay manual" binaries disagree on a 시행일자 ('26.7.9 vs '24.11.27); the unapproved one feeds 10 `visa_data.json` refs | high | sha `d2c6dc…` vs `bde0e8…`; reproduced-text diff line 8237 | Register or retire the backend copy; re-point refs to the approved text; add a guard that every manual binary in the repo is registered |
| SRC-04 | Approved evidence edition (2026.7) lags the published 2026.9 edition; 2026.9 deltas (e.g. E-7-4 thresholds) exist only as 검토 전 | high | manifest `current`; `audits/manual-refresh-260901/README.md` | Finish review (branch does this, §7); add an "approved edition older than newest received" alarm |
| SRC-05 | Stale citations not detected, and CI pins `manualVersion == 2026.5` | medium | 1,268/1,292 refs to superseded files; `check_repo.sh:122` | Citation-freshness check against registry `status`; replace the version pin with "cites a registered, non-deprecated edition or is flagged" |
| EXT-01 | Table, image and footnote structure flattened in approved text, warned only at document level | high | `decrypt_hwp_distribution.py:51,233,268`; fee-table and 붙임13 examples; `has_images` unused | Emit passage-level flags (`in_table`, `image_omitted`, `pua_glyph`) and propagate them to hits and answers; a table-aware HWP path (LIST_HEADER/TABLE/CELL records) or the branch's Markdown tables |
| EXT-02 | Hancom PUA glyphs (circled numbers etc.) unmapped | medium | 281/436/455 PUA chars | Normalisation table PUA→Unicode applied in search and display, never to the pinned original |
| EXT-03 | Tab/NBSP controls dropped without whitespace | low | `:51`, `:226-238` | Emit a space or `\t` for code 9/30/31; re-pin hashes |
| EXT-04 | Image-only / near-empty PDF pages pass silently; no OCR | medium | visa p.278, p.346 | Mark pages under N chars or with images as `needs_original_check`; optional reviewed OCR as a candidate layer |
| EXT-05 | Legacy page-citation tool hard-wired to 2026.5/6 PDFs | low | `extract_manual_page_text.py:31-38` | Drive it from the manifest |
| CI-01 | `main` unprotected; merge = auto-deploy; CI advisory | high | `gh api` 404 / `[]` | Protect main and require repo-validation (and manual-code-coverage) |
| CI-02 | Failing invariant hidden: `check_260617_subcode_inventory_coverage.py` fails on main, committed report says pass; ~25 checks and 6 script tests never run | medium | §4.4 | Add them to CI (check-only, no writes); make "check" scripts never write into tracked paths |
| CI-03 | No CI test decrypts a real committed HWP; olefile undeclared | medium | `test_decrypt_hwp_distribution.py`; venv import error | Add olefile to a pinned requirements file; CI step re-extracts the current and pending HWPs and compares `extracted_text_sha256`; also verify current-entry text hashes in `check_source_manuals.py` |
| CI-04 | DOM tests and 8 E2E specs skipped; no lockfile | medium | CI log "jsdom not installed … SKIP" | `npm ci` with a committed lockfile |
| CI-05 | Live smoke POSTs to production AI on every merge with a secret header | low | `railway-live-smoke.yml` | Rate-limit or tag synthetic traffic; keep the diagnostics token scoped |
| SUP-01 | Unpinned tool installs (pip/npm/go/cargo `@latest`), tag-pinned actions, write-token job, shell-interpolated dispatch inputs | medium | workflows | Pin versions and hashes, SHA-pin actions, pass inputs via env |
| SUP-02 | starlette 0.38.6 multipart DoS CVEs (low exposure) | low | OSV | Bump FastAPI/Starlette together |
| DOC-01 | Docs drift: SOURCE_MANUALS "current" = 2026.6; sync docs say 배포용 HWP is unextractable; `source_monitoring_pipeline.md` describes skeleton only | low | files cited | Update docs |

---

## 6. Reference: korean-law-mcp v4.15.9 (MIT, commit 0a8f08e) — behaviours relevant to the target (described, not copied)

From module header comments only; I did not run any of its code. Its search adds a future-effective notice for the queried law, which I saw live (§1.2). Behaviours that map onto the gaps:

- `src/lib/law-lineage.ts`: lists every enacted version of a law by its stable 법령ID through the effective-version search, so history survives title changes and full rewrites. This is the right key for a Visable law-identity registry (SRC-02).
- `src/lib/upcoming-laws.ts`, and the `시행예정` notice on search: surfaces promulgated-but-not-yet-effective amendments.
- `src/tools/applicable-law.ts`: picks the version effective on a reference date, compares that article with the current one, and pulls transitional provisions (부칙) from later amendments.
- `src/tools/annex-history.ts`: picks the 별표 set of the version effective on a date, with separate slices when one MST has staggered effective dates. This is the date-specific annex versioning Visable does by hand for forms.
- `src/tools/law-history.ts`, `article-history.ts`, `comparison.ts` (신구 대조): version list, per-article amendment history, old/new comparison, i.e. "modified provisions".
- `src/tools/ordinance-radar.ts`: flags a lower rule for review when a cited higher law changed after the lower rule's effective date. The same pattern applies to "fact cites law X; X changed after the fact's review date".
- `src/lib/abolished-laws.ts`: detects repealed laws and rules and names their successors.
- `src/lib/image-only-body.ts`: treats a response with images but almost no real text as empty rather than valid. This is the guard missing in the PDF corpus (EXT-04).
- `src/lib/annex-file-parser.ts`: delegates HWP/HWPX/PDF annex parsing to kordoc. Per its comment, kordoc places HWP5 cells by column and row address and detects PDF tables two ways. That is a candidate for the table gap; licence MIT; it would need its own vetting.

---

## 7. Where the unpushed branch changes conclusions

From `git show fix/waymaker-qa-2026-10-16:<path>`:
- `data/manual_approval_index.json`: 2026.9 visa HWP, visa PDF, stay 09-18 PDF and stay 09-18 HWP **approved 2026-10-16**; 07-31 pair and stay 09-01 HWP become `superseded`. The manifest `current` becomes the 2026.9 PDFs. This resolves SRC-04 once pushed.
- It adds `*_md` derived corpora from "the owner's HWP→Markdown conversion" whose parser converts HTML tables into `열이름: 값` rows with a page map (`scripts/build_manual_markdown_corpus.py`), status `needs_review`. That is the first table-structure-preserving path, which partly addresses EXT-01, though unapproved. `check_source_manuals.py` gains alternate-file and derived-text pinning that refuses any approval claim on derived texts.
- It adds `backend/services/manual_evidence.py` (grounding `/api/ask` in approved excerpts) and relabels 955 `visa_data.json` manualRefs to 2026.9, which shrinks SRC-05.
- Unchanged by the branch: SRC-01, SRC-02, SRC-03 (backend 260731 copy), CI-01..04, SUP-01/02, olefile undeclared.

---

## 8. Open questions

1. Which 260731 stay binary did HiKorea actually publish, and was there a silent re-upload? The `'26.7.9` vs `'24.11.27` line decides which 시행일 is right.
2. Is the knowledge store populated in production (Railway) or only in evals? That decides whether `refresh_due` ever fires.
3. Is a Railway/Vercel deploy gated on anything besides a push to main?
4. Has anyone checked whether HiKorea's 자료실 HTML contains per-request dynamic tokens? If so, even a set baseline would flap.
5. Are the 13 F-4 subcodes flagged by the coverage check intentionally unsourced (for example, newly added from 2026.9)?

## 9. Recommendations (priority order)

1. Protect `main` and require repo-validation.
2. Fix the board monitor: commit baselines, parse rows, alert on persistent `baseline_unset`/`unreachable`.
3. Build a law-identity registry (법령ID/MST/공포일/시행일/시행예정) with a scheduled poller that writes a structured change report and opens an issue. Never auto-edit data.
4. Resolve the duplicate 260731 stay binary, and add a "every manual binary is registered" guard.
5. Add olefile (pinned) and a CI step that re-extracts committed HWPs and checks `extracted_text_sha256` (including current entries).
6. Carry passage-level extraction flags (table, image omitted, PUA glyph, near-empty page) into retrieval and answers.
7. Add a citation-freshness check and drop the `manualVersion == 2026.5` pin.
8. Bring the 6 script tests, the subcode-coverage check (made non-writing), the DOM tests (`npm ci` + lockfile) and the remaining E2E specs into CI.
9. Pin tool installs and SHA-pin actions; pass dispatch inputs via env; bump FastAPI/Starlette.

---

## Verification pass

Adversarial re-check by a second agent on 2026-10-19 against worktree `0713370` (still clean: `git status --short` empty before and after). What the verifier did:
- Re-ran the repo's own `scripts/decrypt_hwp_distribution.py` with its own driver (`scratchpad/verifier/src_mon/myrepro.py`). It reuses the first agent's stdlib olefile shim, which the verifier read in full first: about 100 lines of CFB parsing, no I/O beyond reading the HWP.
- Re-pulled 5 GitHub run logs and branch/ruleset APIs.
- Ran 1 korean-law MCP `search_law("출입국관리법")`.
- Made 3 GETs to `api.osv.dev`: the 2 original GHSAs plus GHSA-7f5h-v6xp-fcq8.
- Re-ran `check_source_updates.py` (default, `--catalog-dry-run`, `--list-disabled`) and the 6 non-CI script tests.
- Ran `check_260617_subcode_inventory_coverage.py` by import, with its report write redirected to the scratchpad, so nothing was written into the worktree.

The disk on this machine hit ENOSPC twice during the pass (about 180 MB free). The verifier deleted its own scratch copies of the reproduced texts after hashing and diffing them.

### Verdicts on the 15 consequential claims

| # | Claim (short) | Verdict | Evidence / correction |
|---|---|---|---|
| 1 | 07-31 visa/stay and 09-18 stay HWP extractions reproduce byte-for-byte, U+FFFD 0 | **confirmed** | LIVE verifier re-run: visa `a80ec1f3…` (471,659 chars), stay 07-31 `f9f040b1…` (720,629), stay 09-18 `807c19ae…` (726,907), all equal to `shasum` of the committed texts; fffd=0 for all three. Caveat: the run used a shim, not the real `olefile`. The hash match makes that immaterial for these files. |
| 2 | Second 260731 stay binary differs in one line (E-7-4 시행일자 '26.7.9 vs '24.11.27); unregistered; behind 10 refs | **confirmed** (with precision added inline) | LIVE: backend copy `bde0e845…` → `8fb99359…` (720,633 chars); `diff` shows only line 8237. Registry, manifest and approval index have no entry. Its sha is recorded in `docs/audits/manual-260731-targeted-refresh.md:14`. The 10 refs name `260731_stay_manual_extracted.txt`, whose line 7899 carries '24.11.27. '24.11.27 also appears in the 260709 extract; 2026.9 reads '26.8.31. The branch keeps the binary (same blob `a8bab944`) and the 10 refs. |
| 3 | Board monitor cannot detect change: null baselines → `baseline_unset` with success | **confirmed** | CODE `hikorea_manual_board_watch.json` (both `null`), `monitor_hikorea_manual_board.py:96-97`. LIVE logs of 38211467187 (10-12), 37270107456 (10-05) and also 36382717727 (09-28): both targets `baseline_unset`, `"changed": false`, conclusion success. Baselines are still null on the unpushed branch. |
| 4 | Scheduled manual-sync is a no-op (download_url null, no input); baselines → 09-01 HWPs | **confirmed**, strengthened | LIVE 38688541847: both manuals `status: no_source`, detail "no manual input and no usable download_url". Additional finding: cron runs never pass `--allow-network`, because that input exists only on dispatch, so setting `download_url` alone would still not fetch (inline correction). |
| 5 | `check_source_updates.py` only detects local-file changes; law/notice not_configured; network "not implemented"; catalog 0 eligible | **corrected** | Core claim holds (re-run: 16 total / 5 unchanged / 11 skipped; Eligible 0; 34 catalog records all `monitor_enabled=false`). Correction: with `--allow-network` the law/notice entries still return `not_configured` (`:567-573`). The "HTTP fetch not implemented in skeleton" path (`:547`) is reachable only for a configured network entry. The catalog path has a real allowlisted fetcher (`:464`) that is never exercised. |
| 6 | Pins stale: Act now MST 290729 (공포 2026-08-04, 시행 2026-10-02), Decree 290501 (시행 2026-10-02), Rule 289833 + 2027-09-16 future amendment; repo pins 272921/289697 | **confirmed** | LIVE korean-law MCP 2026-10-19 returned exactly these values (Decree 공포 20260929; Rule 공포/시행 20260915; 시행예정 제01125호, 2026-09-15 공포, 시행 2027-09-16). CODE `author_rules.py:316-318`. Grep for 290729/290501 hits only `data/agent_registry_2026-04-30.json:23786`. Added: the stale MSTs ship in `backend/data/knowledge_deploy/status-guidance-202609.json`. The source is a third-party MCP over law.go.kr, not law.go.kr directly (OBSERVED). |
| 7 | Extractor drops every control char incl. tab/table/footnote/header; PARA_TEXT only; cells flattened; images vanish (visa line 8177) | **corrected** (wording only) | CODE `:51-53`, `:226-238`, `:268-270` re-read. Codes 10/13 are kept as `\n`, so "every" is too strong; the rest is accurate. The 심사수수료 table at stay line 82+ is a flat run of cell lines. Visa lines 8176-8177 `붙임13 / 외국인등록용 사진 규격` are followed directly by the E-8 chapter. The 2026.9 PDF p.278 has `has_images: true` with only the caption text, which corroborates an image-only page. |
| 8 | Table/image caveats only per document; no consumer attaches them to hits/answers; `has_images` unused | **confirmed** | git grep: `table_extraction_warnings` in `manual_registry.py:149,181,271` and its writer `build_current_manual_corpus.py:131` only. Hit dict in `manual_search.py:214-226` has no table/image/glyph field. `has_images` appears in code only at `build_current_manual_corpus.py:89,110` (writer). |
| 9 | Hancom PUA glyphs unmapped: 281 / 436 / 455 | **confirmed** | LIVE count: visa 07-31 281 (18 distinct), stay 07-31 436 (23), stay 09-18 PDF text 455 (24). Extra: stay 09-18 HWP 436, visa 09-01 PDF 299. Context shows U+F02B1 before `신고대상` and U+F02B2 before `신고시기`; U+F007E before `목차`. |
| 10 | main unprotected, no rulesets; merge → Railway deploy | **confirmed**, strengthened | LIVE: `branches/main/protection` → 404 "Branch not protected"; `/rulesets` → `[]`; `/rules/branches/main` → `[]`; `protected: false`. Deploy coupling is now OBSERVED from run 38292940698: production switched from `283983f` to `0713370` about 2 min after the push. Actions default token permission is `read`. |
| 11 | CI runs all 81 backend modules under pytest; all pass on 0713370; KNOWN_FAILING empty | **confirmed** | CODE `run_backend_tests.py:70` (dict body is empty); 81 `backend/tests/test_*.py`. LIVE log 38292940589: "81 modules (via pytest)", PASS 81, KNOWN 0, SKIP 0, NEW 0, FIXED 0, "full backend suite clean". |
| 12 | `check_260617_subcode_inventory_coverage.py` not in CI, fails on main (13 F-4 + F-2-6); committed report says passes:true | **confirmed** | TEST (ran via import with redirected write: rc 1, FAIL): `authoringSubcodesWithoutSourceOrReviewFlag` 13 (F-4-11…21, F-4-25, F-4-30, all in `statuses/F-4.json`), `deprecatedOrAbolishedShownActive` 1 (F-2-6, inventory class `abolished_subcode`, authoring `active`). Committed report: all counts 0, `passes: true`, last commit `bc93ba4` 2026-06-28. Nuance: the 13 records carry `status: "legacy"` and `needsManualReview: false`. None of those codes occurs in the 07-31 or 09-18 manual texts or the dongpo manual text. `F-4.json` last changed 2026-07-09 (#534), after the report. |
| 13 | CI skips 6 script tests (pass locally), 8/18 Playwright specs, jsdom DOM tests; validate has no npm install; no lockfile | **confirmed** | TEST 6 modules under `.venv-check` pytest: 50 passed, 3 subtests passed. CODE: the 10 specs named in `repo-validation.yml:135-153` vs 18 in `tests/e2e/`; the validate job (`:17-38`) has no setup-node or npm. No package-lock, yarn, pnpm or shrinkwrap file. LIVE log: "jsdom not installed — skipping DOM smoke test … SKIP" ×2 plus the dummy-text rendered scan skipped. |
| 14 | 1,268/1,292 refs point at superseded files; `check_repo.sh:122` requires 2026.5 | **confirmed** | LIVE count: 859 + 368 + 41 = 1,268 superseded; 22 at 2026.7; 2 K-CORE (current special manual). CODE `check_repo.sh:121-122`. On the unpushed branch, 955 refs move to 2026.9 PDF texts and 313 superseded refs remain. |
| 15 | starlette 0.38.6 affected by CVE-2024-47874 (fix 0.40.0) and CVE-2025-54121 (fix 0.47.2); low exposure | **confirmed** | WEB OSV re-fetched 2026-10-19: ranges `introduced 0 → fixed 0.40.0` and `→ 0.47.2`. No `UploadFile`/`Form(`/`request.form(`, no `StaticFiles`/`FileResponse` in `backend/`; `multipart`/`python_multipart` not importable. FastAPI 0.115.0 metadata `starlette<0.39.0,>=0.37.2` (VERIFIED). CVE-2025-62727 does not apply (introduced 0.39.0). |

### Other inline corrections made
- §1.1 backend stay copy: documented in an audit, but not registered. The backend visa copy is identical to the approved visa HWP.
- §3.3: the board monitor never closes issues; only short-stay-freshness closes.
- §4.1: repo-validation's last 3 runs are on 3 different heads; only the latest is `0713370`.
- §4.5: `railway-live-smoke` and `enforcement-runtime-benchmark` also use an unpinned runner `python3`. A fourth script, `extract_hwp_manual_text.py`, imports the undeclared `olefile`.

### Omissions against the brief
Filled:
- **Law-pin propagation (c).** The stale MSTs reach the deployed knowledge file `status-guidance-202609.json`, not just the authoring script. This widens SRC-02, because any answer citing those status-guidance facts carries a superseded Act/Decree MST.
- **Cron sync cannot fetch even when configured (c).** See claim 4. Add to SRC-01's remedy: let the schedule pass `--allow-network`, or keep the job honest by reporting `no_source` as a warning or issue rather than a green no-op.
- **Inventory (a).** The duplicate-binary problem is limited to the stay manual. `backend/…/260731_visa_manual.hwp` is byte-identical to the approved visa HWP.
- **CI (d).** The deploy-verification loop shows production follows main within minutes. That upgrades CI-01 from inferred to observed impact.

Could not fill:
- Which 260731 stay binary HiKorea actually served, and therefore whether '26.7.9 or '24.11.27 is correct. That needs a download from hikorea.go.kr, which was out of scope.
- Whether MST 272921 is really the 시행 2026-01-23 version as `author_rules.py` labels it, or the 시행 2025-07-22 version the crosscheck header shows. Settling this needs a law.go.kr history query beyond the single permitted search.
- Whether Vercel deploys on push. No Vercel API was queried.
- The `extract_hwpx_text.py` double-emission of nested-cell text is still INFERRED. No readable HWPX exists in the repo: all 23 sections of `260623_stay_manual.hwpx` come out as `UNREADABLE: manifest marks this section as encrypted`, which the verifier confirmed.
