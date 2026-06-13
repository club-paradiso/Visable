# Source-Grounding & Law-MCP Audit — 2026-06-14

**Repository:** `lucanomics/Paradiso`
**Branch:** `claude/beautiful-shannon-zkufpv`
**Scope:** Verify whether live/user-facing Paradiso content is actually grounded in
up-to-date official manuals, laws, public APIs and source data; verify whether public-API
integrations actually function at runtime or are decorative; evaluate the linked Korean-law /
MCP projects; and implement a minimal, durable source-grounding metadata model.
**Author:** AI audit (read-mostly). **Human review required** before promoting any law-grounding
to a user-visible "verified" state. This document is data-hygiene/architecture work, **not** a
legal revalidation of any visa rule.

> **Headline finding, stated plainly.** The task brief assumed the public-API integration might be
> "only decorative." It is **not**. Law grounding is genuinely wired into the runtime `/api/ask`
> pipeline behind a documented feature flag (`LAW_GROUNDING_MODE`). The real problems are narrower
> and specific: (a) **stale internal documentation/metadata** that claims the opposite of what the
> code now does; (b) the law API is **not verified-working with the committed config** (the
> `.env.example` placeholder OC returns HTTP 403); (c) two **dormant/dead** adapters
> (`public_data_client.py`, `korean_law_client.py`); (d) a **declared-but-unimplemented cache**;
> and (e) the rich grounding metadata exists but is **not formalized into one named model**. This
> audit fixes (a) and (e), documents (b)–(d) with evidence, and lists the rest as scoped follow-ups.

---

## 0. Method & evidence base

- Read the runtime path end-to-end: `ai.html` → `POST /api/ask` (`backend/paradiso_backend.py`)
  → `backend/services/*`.
- Read every grounding/source data file under `data/`, `backend/data/`, `docs/source-manuals/`.
- Ran a **live reachability probe** of the National Law API (documented in
  `docs/integrations/LAW_OPEN_API_RUNTIME_PROBE_2026_06_14.md`).
- Re-evaluated the three linked GitHub references against current upstream state (web).
- Cross-checked the repo's own prior audits and found two of them now stale (see §6).

Line/file references below are anchors as of this branch.

---

## 1. Current source architecture

### 1.1 The serving path (what a user actually hits)

```
ai.html  ──POST /api/ask──▶  backend/paradiso_backend.py: ask()  (line 3495)
                              │
                              ├─ detect visa code / sub-code / task type / risk
                              ├─ MANUAL grounding (primary, LOCAL): source-confirmed
                              │   structured requirements + procedure packets
                              │   (backend/data/manual_grounding/*, structured_requirements.py,
                              │    procedure_packet_builder.py)
                              ├─ LAW grounding (supplemental, EXTERNAL, gated):
                              │   should_attempt_law_grounding() (line 3587)
                              │   → if LAW_GROUNDING_MODE in {audit,enabled}:
                              │        build_law_grounding_context()  (line 3591)
                              │        → law_tools.search_laws() → law.go.kr/DRF
                              ├─ build_law_evidence_pack() (line 3663): normalize evidence,
                              │   compute answer_certainty_level, legal_analysis
                              ├─ confidence gate + answer-shape contract injected into prompt
                              │   (lines 3715–3751)
                              ├─ LLM synthesis (OpenRouter primary; Groq opt-in; deterministic
                              │   fallback if all providers fail)
                              └─ post-answer quality gate / deterministic repair
                              ▶ AskResponse (rich grounding metadata; see §4)
```

**Source-of-truth hierarchy actually enforced:** local source-confirmed manual evidence and
structured requirements are authoritative for documents/fees/deadlines/procedures; law grounding is
**supplemental legal context only** and is explicitly forbidden from inventing a document checklist
(`paradiso_backend.py` lines 3625–3635, 3715–3722). This matches `CLAUDE.md`'s separation rules.

### 1.2 Data layer (where visa/stay/residence info is stored)

| Layer | File(s) | Role | Read by `/api/ask`? |
|---|---|---|---|
| Live visa/status records | `visa_data.json`, `backend/data/visas.json` | 39 체류자격 records; per-record `sourceManualStatus`, `manualRequiredDocAudit`, `procedures[].manualRefs[]` | **Yes** (`/api/visas`, grounding) |
| Document registry | `doc_master.json` | doc-type id → ko/en name/description | Yes (doc rendering) |
| Source-confirmed structured requirements | `backend/data/manual_grounding/structured_requirements_2026_05.json` | PDF-verified required-docs per status/procedure | **Yes** |
| Manual grounding fixture | `backend/data/manual_grounding/stay_manual_grounding_2026_05.json` | deterministic manual context | **Yes** |
| Evidence bindings | `data/procedure_evidence_bindings.json` | code → manual section/page/date/confidence + `sourceBackedFields` | Audit/build input |
| Visa-issuance records | `data/visa_issuance_records.json` | issuance procedures + `sourceRefs` | Audit/build input |
| Short-stay sources | `data/short-stay/sources.json` | fine-grained source notes (B/C) | Audit/build input |
| **Source registry (monitoring)** | `data/source_registry.json` | allow-list of monitored official sources | **No** (monitor-only, by design) |
| Manual manifest | `docs/source-manuals/source_manifest.json` | canonical current-manual metadata + SHA-256 | check scripts |
| Web/notice catalogs | `data/sources/hikorea_source_catalog.json`, `immigration_notice_sources.json` | monitoring catalogs (scrape disabled) | No |

### 1.3 Freshness model — **it exists** (this is good news)

The repo already recognizes the current official manuals and records their versions/dates/hashes:

- **Visa issuance manual:** version `2026.5`, source date **2026-05-21**, 484 pages, SHA-256 pinned
  (`docs/source-manuals/source_manifest.json` → `current.visa_issuance_manual`;
  `data/source_registry.json` → `visa_manual_2026_05_pdf`, status `active`).
- **Stay/residence manual:** version `2026.5`, source date **2026-06-01**, 777 pages, SHA-256 pinned;
  **supersedes** the 2026-05 stay manual (which is correctly marked `deprecated` +
  `superseded_by`).
- Per-record provenance lives in `visa_data.json` (`sourceManualStatus.stayManualSourceDate`,
  `manualRequiredDocAudit.{manualVersion,sourceDate,sourceFile}`, `procedures[].manualRefs[]` with
  `confidence` + `needsManualReview`).
- `check_repo.sh` enforces `manualRequiredDocAudit.manualVersion == "2026.5"` across status records.

**Conclusion:** the freshness *fields* are present and the **2026-05-21 / 2026-06-01** manuals are
recognized. What was missing is a single **named, validated model** tying these together and a
**cross-file consistency guard** — added by this PR (§7).

---

## 2. Public-API integration status — is it actually used at runtime?

| Integration | Adapter | Wired into `/api/ask`? | Verdict |
|---|---|---|---|
| **National Law Open API (법제처 DRF, `law.go.kr`)** | `backend/services/law_tools.py` (DRF endpoints `lawSearch.do`/`lawService.do`, lines 113–115) | **YES**, via `build_law_grounding_context` (line 3591), gated by `LAW_GROUNDING_MODE` + `LAW_API_OC` | **LIVE but config-gated, and not verified-working with committed config** (see §2.3) |
| Korean law HTTP client (legacy) | `backend/services/korean_law_client.py` | **No** — `_guard` requires `LAW_API_BASE_URL` (blank in `.env.example`), so it never fires; referenced **only by tests** (`test_paradiso_backend.py:1721+`) | **Superseded / dead at runtime** |
| Public Data API (`data.go.kr`) | `backend/services/public_data_client.py` | **No** — never instantiated in the serving path; requires `PUBLIC_DATA_BASE_URL` (blank) | **Stubbed / dormant** |
| HiKorea / Visa Portal / MOJ pages | (none) | No — referenced as **user-guidance URLs** and monitoring catalog entries only; scraping explicitly disabled | **Documented-only (by policy)** |
| Source monitoring | `scripts/check_source_updates.py`, `run_hikorea_monitor_smoke.py` | No (manual/CI-dispatch only; no network by default) | **Script-only** |
| Supabase / DB | `SUPABASE_*`, `DATABASE_URL` | No call path; `/health` presence-flag only | **Declared-only** |

### 2.1 The law API IS wired (proof)

`paradiso_backend.py`:
- `intent = should_attempt_law_grounding(prompt)` is computed for **every** question (line 3587).
- `if mode in {"audit","enabled"}: law_context = build_law_grounding_context(prompt)` (line 3590-3591)
  → `law_grounding.py:247` → `law_tools.search_laws(...)` → `law_tools._execute` →
  `GET http://www.law.go.kr/DRF/lawSearch.do?OC=<oc>&target=law&type=JSON&query=...`.
- The OC is embedded server-side and **sanitized out** of every returned URL (`law_tools._sanitize_url`);
  tests assert `OC=` never appears in output.

### 2.2 Defaults and the disabled→audit→enabled gate

- **Code default** is safe: `grounding_config.py:22,94` → `mode="disabled"`. In disabled mode no
  external call is made; `/api/ask` still returns honest metadata
  (`law_grounding_status="disabled"`, warning `LAW_GROUNDING_DISABLED`).
- **`backend/.env.example` recommends** `LAW_GROUNDING_MODE=audit` with `LAW_API_OC=paradiso`
  (lines 68, 83). So the *intended* Railway posture is audit-mode-on. Whether the live Railway env
  actually sets these (and with a **valid** OC) could not be verified from this environment.

### 2.3 Is it *working*? — live probe says: reachable, but 403 with the committed config

A 2026-06-14 read-only probe (`docs/integrations/LAW_OPEN_API_RUNTIME_PROBE_2026_06_14.md`):

- `law.go.kr/DRF/lawSearch.do` is **reachable** (~245 ms HTTP response).
- With the **`.env.example` placeholder `OC=paradiso`** → **HTTP 403 Forbidden**.

So with the committed configuration, audit-mode law calls would **fail and degrade** to
manual/generic grounding. A **registered OC** (free, from `open.law.go.kr`) set as a Railway secret
is required for live retrieval. This is the single most important "is it actually working?" finding:
**the wiring is real; the credential is a placeholder that does not authorize retrieval.**

### 2.4 Failure handling — surfaced, not silently swallowed (good)

On 403/timeout/parse error, `law_tools._execute` (lines 612–647) returns a **typed** error
(`LAW_API_HTTP_ERROR`, `LAW_API_TIMEOUT`, `LAW_API_NOT_CONFIGURED`, …). `/api/ask` then sets
`law_grounding_status="unavailable"`, attaches the marker to `law_grounding_warnings`, keeps
answering from manual grounding, and the source panel shows a "확인 필요"/limited state. No crash,
no raw provider error to the user, **no fabricated citation**. Environment-variable validation is
non-fatal-by-design (`load_grounding_config` collects non-secret warnings like
`LAW_API_OC_RECOMMENDED`).

### 2.5 Caching / normalization — partial

- **Normalization:** strong. Law results are normalized (`law_tools` → `OfficialSourceResult`-style
  dicts), the raw payload is stripped before reaching the LLM, and a single compact `evidence_summary`
  is injected.
- **Caching:** **declared but not implemented.** `LAW_GROUNDING_CACHE_TTL_SECONDS` is read into config
  (default 86400) but there is **no cache backend** — repeated identical questions in audit mode would
  re-hit the API. Low user risk (audit-mode + short timeout), but it should be implemented before
  `enabled` mode at scale. (Follow-up F-4.)
- **Evidence metadata attachment:** law results are attached to the answer's response metadata
  (`law_sources`, `citation_verification`, counts) but are **not persisted** to a store (AnswerGrounding
  is computed, not saved — see §4).

---

## 3. Waymaker answer-generation grounding

Waymaker (`ai.html` title; backend `/api/ask`) is **evidence-first**, not a free-form chatbot:

- **Retrieval before generation:** manual + (gated) law evidence are assembled *before* the prompt is
  built; the model receives a normalized evidence summary + a backend-prepared `legal_analysis` object
  with an explicit instruction *"explain this; do not invent it"* (lines 3728–3751).
- **Official-source-only modes exist:** `answer_quality.classify_answer_quality` →
  `source_confirmed / source_assisted / source_limited / source_unavailable / generic_advisory`;
  `requires_official_confirmation` is `True` unless `source_confirmed`.
- **Uncertainty / refusal language is enforced deterministically:** a confidence gate strips absolute
  verbs ("가능합니다", "신고 의무는 없습니다", "허용됩니다") when `answer_certainty_level != direct`,
  `missing_direct_authority`, `direct_evidence_count == 0`, or a law lookup error occurred
  (line 3748). A manual-to-law fallback block forbids inventing documents (lines 3625–3635). A
  case-law uncertainty answer refuses to cite precedents without verifiable basis.
- **Source distinction is represented:** manual vs law vs precedent vs "related statuses (NOT sources)"
  are separate response fields; the source panel maps technical markers to user-friendly labels.
- **Do-not-invent posture:** prompt repeatedly forbids inventing article numbers, deadlines, fees, or
  documents (line 3720). The Gemma fine-tune experiment (`experiments/waymaker-gemma4-finetune/`) is
  **not wired to production** and is explicitly designed to train *behavior with evidence*, never legal
  facts.

**Verdict:** Waymaker's grounding/guardrail design is **already strong** and aligns with the task's
requirements. The residual gap is **freshness-into-the-answer** (warning the user when the cited
manual is older than the registry head) and **citation-against-official-DB verification**
(`citation_verifier` extracts citations but does not verify them against a live law DB — it depends on
the same law API being configured). These are follow-ups F-2/F-3, not rewrites. **I intentionally did
not modify Waymaker prompt logic** — per `CLAUDE.md` it is lower-risk to harden via the data/metadata
layer and tests than to rewrite a working legal-answer pipeline.

---

## 4. The requested model vs. what exists (SourceRecord / EvidenceRecord / AnswerGrounding)

All three concepts **already exist functionally** but were unnamed and inconsistently fielded
(`source_date` vs `sourceDate` vs `sourceRevisionDate`; `local_path` vs `localPath` vs `file`).
This PR formalizes them in `data/schemas/source_grounding_schema.json` (a documentation+validation
layer, **not** a new runtime contract) with a field **crosswalk** to the real files.

| Requested concept | Where it already lives | Status |
|---|---|---|
| **SourceRecord** (id, source_type, title, issuing_authority, official_url, retrieved_at, published_or_updated_at, version_label, hash_or_etag, language, confidence, review_status) | `data/source_registry.json`, `docs/source-manuals/source_manifest.json`, `data/short-stay/sources.json` | Present; gaps: `confidence`, `language`, `retrieved_at` unpopulated on manual entries (now flagged as warnings by the validator) |
| **EvidenceRecord** (source_id, visa_or_status_code, topic, excerpt, location_reference, normalized_summary, last_verified_at, verification_method, reviewer_note) | `data/procedure_evidence_bindings.json` (`manualSources[]`, `sourceBackedFields`, `reviewStatus`), `data/visa_issuance_records.json` (`sourceRefs[]`), `backend/data/manual_grounding/structured_requirements_2026_05.json` (`manualSource`) | Present across files; field names vary (crosswalked) |
| **AnswerGrounding** (cited_evidence_ids, missing_evidence_flags, uncertainty_flags, prohibited_claim_flags, generated_at, answer_id) | `AskResponse` (`grounding_sources`, `law_sources`, `missing_direct_authority`, `requires_official_confirmation`, `source_confidence_level`, `law_grounding_status`, `grounded_answer_limited`, …) | **Computed at runtime, not persisted.** No `answer_id`/`generated_at`/`request_id` stored. |

---

## 5. MCP feasibility & architecture review (the linked projects)

| Project | What it is (current) | License / maintained | Relevance to Paradiso grounding | Recommendation |
|---|---|---|---|---|
| **`chrisryugj/korean-law-mcp`** | MCP server wrapping **42 법제처 APIs** (`law.go.kr`/`open.law.go.kr`) into ~9 tools: statute/precedent search, **citation verification against the official DB**, **temporal "time-travel" law diff**, precedent citator, annex extraction. Needs the **same free OC token**. Remote `korean-law-mcp.fly.dev` + `npx`. | MIT; **actively maintained** (~2k★, v4.4.x) | **Paradiso already calls the same underlying 법제처 DRF API directly** in `law_tools.py`, so core statute retrieval does **not** need this dependency. Its *additive* value is citation-verification-against-DB and **time-travel diffing** (ideal for staleness detection). | **Extract principles, don't vendor.** Either (a) extend `law_tools.py`/`citation_verifier.py` with a citation-against-DB check + a date-diff freshness check, or (b) optionally point the existing `LAW_API_BASE_URL` flag at a **self-hosted** korean-law-mcp instance as an alternate transport. Treat `fly.dev` as dev-only. Attribute concepts; copy no code. |
| **`kimlawtech/korean-privacy-terms`** | Claude Code **skill** generating PIPA (2026.3 amendments)/GDPR/CCPA/APPI privacy+terms docs (MDX/React/HTML). | Apache-2.0; active (v3.0.0, 2026-04) | **Not a grounding source.** Relevant only to the separate compliance-pages need (privacy policy / AI disclaimer), which is a PIPA prerequisite for storing user questions. | Out of scope for source grounding. Use later as a dev-time skill for `/legal/*` pages; zero runtime dependency; attorney review required. |
| **`dance-of-tal/dot-studio`** | Now **"APM Studio"** — a local GUI/package manager for agent configs (TypeScript). **No legal/law-data function.** | MIT; active (v0.3.5, 2026-06) | **None** for source grounding. | Dev-workflow tool only; do **not** add to `requirements.txt`/`package.json`/CI. |

**Document-conversion backends** (`hwp2md`, `kordoc`): correctly treated by the repo as **manual
extraction aids, not legal-source authorities**. The repo's manuals are installed as PDFs (HWP
distribution-mode body extraction is blocked, documented in `source_manifest.json`). No change needed;
keep them out of the "law source" tier.

> **MCP integration honesty (per the task's non-negotiables):** I am **not** claiming MCP integration
> is complete. None of these MCP servers is wired into Paradiso runtime, and this PR does not wire one.
> The audit's recommendation is principle-extraction behind the **existing** `LAW_API_BASE_URL` /
> `LAW_GROUNDING_MODE` feature flags.

---

## 6. Stale / ungrounded / source-ambiguous content found

1. **`data/source_registry.json` — stale runtime claim (FIXED in this PR).** The `law_api_placeholder`
   note read *"No live retrieval reachable from /api/ask."* That is false: `/api/ask` reaches the same
   법제처 source via `law_tools.py`. Corrected to distinguish the **monitor** placeholder from the
   **runtime** law path, and to record the 403-with-placeholder-OC fact.
2. **`docs/integrations/PUBLIC_DATA_AND_LAW_GROUNDING_AUDIT.md` (2026-05-19) — internally contradictory /
   stale.** Its executive verdict says "/api/ask does **not** call the law API" (lines 51–52, 99), yet
   its own Phase 4 note (line 312) admits law grounding was *later* wired into `/api/ask`. Its
   "grounded only for {D-2,D-4,E-7} extension" scope (lines 88–90) and "default `disabled`" posture are
   superseded. **Recommend** prepending a "SUPERSEDED — see 2026-06-14 audit" banner (follow-up F-1; not
   auto-edited here to preserve its history).
3. **`docs/EXTERNAL_SKILLS_AND_LEGAL_GROUNDING_STRATEGY.md` (2026-05-20) — partially stale.** It frames
   `korean_law_client.py` (needs `LAW_API_BASE_URL`) as the integration point and
   `CITATION_VERIFICATION_NOT_WIRED` as current; runtime has since moved to `law_tools.py` (built-in DRF
   endpoints) and audit-mode default. Useful as strategy; add a pointer to this audit.
4. **`LAW_GROUNDING_LIVE_SMOKE_RESULTS.md` — `NOT_READY`, never validated against the API.** The blocker
   was the *Railway* URL/proxy (`CONNECT tunnel 403`), not `law.go.kr`. Superseded by the 2026-06-14
   probe (which reached the API and got an *application* 403 due to the placeholder OC).
5. **Dormant adapters present in the tree:** `public_data_client.py` (never instantiated) and
   `korean_law_client.py` (only exercised by tests). Not harmful, but a reader could mistake them for
   the live path. Recommend a module docstring marking them legacy/dormant (follow-up F-5).
6. **No ungrounded *legal content* was introduced or found to need deletion.** Per `CLAUDE.md`, no visa
   data was rewritten; protected files (`visa_data.json`, `backend/data/visas.json`, `doc_master.json`)
   were **not touched**.

---

## 7. UI / content-surface verification

I verified these surfaces by reading the response contract and the source-panel derivation
(`_derive_source_panel_metadata`, `AskResponse`), **not** by running the live UI (no browser/runtime in
this environment — see Risks).

| Surface | Shows source info? | Current? | Distinguishes manual vs law? | Exposes uncertainty? | Notes |
|---|---|---|---|---|---|
| Waymaker `/api/ask` answers | Yes — source panel (manual / law-citation / public-data sections) | Manual = 2026.5 (2026-05-21 / 2026-06-01); law = live-or-degraded | **Yes** (separate fields + labels) | **Yes** (`requires_official_confirmation`, "확인 필요", confidence chip) | Strongest surface |
| Visa/status detail cards, document guidance | Yes — `manualRequiredDocAudit` (version/date/page) | 2026.5 | Manual-only by design | `needsManualReview` flags retained | Per-record provenance present |
| Scenario / route flows (F-4, D-2, G-1, E-7, F-2/5/6, K-ETA/no-visa) | Partial — procedure-variant context marked `needs_manual_review` | Mixed | Manual context only | Yes (variants never asserted as confirmed) | Variant grounding deliberately conservative |
| "Official basis limited" warnings | Yes (`source_limited`/`source_unavailable` states) | n/a | n/a | Yes | Working as intended |

**Overclaim check:** the pipeline's confidence gate and `requires_official_confirmation` default
specifically prevent overclaiming when evidence is incomplete. No surface was found asserting
verified legal certainty without evidence. (Caveat: not runtime-rendered here.)

---

## 8. Implemented changes (this PR)

Minimal, additive, and compatible — no runtime answer behavior changed; no protected data touched.

| # | File | Change |
|---|---|---|
| 1 | `data/schemas/source_grounding_schema.json` | **New.** Canonical SourceRecord / EvidenceRecord / AnswerGrounding model + field **crosswalk** to existing files + `manual_version_invariants` + freshness policy. Documentation/validation layer only. |
| 2 | `scripts/check_source_grounding_metadata.py` | **New.** Stdlib-only, offline validator: schema shape, registry enum validity, manual-version invariants (visa 2026-05-21/2026.5; stay 2026-06-01/2026.5 superseding prior), and **registry↔manifest SHA-256 parity** (catches "updated one file, not the other"). Freshness gaps → non-blocking warnings. |
| 3 | `backend/tests/test_source_grounding_metadata_schema.py` | **New.** 8 stdlib `unittest` tests: schema validation, manual-version metadata, no hash drift, and a static check that the **AnswerGrounding crosswalk targets actually exist on `AskResponse`**. No fastapi/pytest dependency. |
| 4 | `data/source_registry.json` | **Surgical note edit.** Corrected the stale "no live retrieval reachable from /api/ask" claim; added monitor-vs-runtime clarification + the 403-probe fact. No source added/removed; no requirement changed. |
| 5 | `scripts/check_repo.sh` | Added step **[5b/14]** running the new validator + tests (CI gate). |
| 6 | `docs/integrations/LAW_OPEN_API_RUNTIME_PROBE_2026_06_14.md` | **New.** Executable evidence of law-API reachability + the 403-with-placeholder-OC result. |
| 7 | `docs/audits/source-grounding-and-law-mcp-audit-2026-06-14.md` | **New.** This report. |

---

## 9. Recommended architecture (target)

Keep the current Paradiso-native design; evolve it incrementally:

1. **Verify the law path for real (operator):** set a **registered** `LAW_API_OC` as a Railway secret;
   confirm `LAW_GROUNDING_MODE=audit`; run `scripts/probe_korean_law_open_api_2026_05.py` from a
   reaching host and record `LIVE_SOURCE_MATCHED`.
2. **Implement the declared cache** (`LAW_GROUNDING_CACHE_TTL_SECONDS`) before `enabled` at scale.
3. **Citation-against-DB + freshness-diff** (principle from korean-law-mcp): have `citation_verifier`
   actually verify extracted `법령 제N조` against the law API, and emit `STALE_SOURCE_WARNING` into the
   answer when a cited manual/article predates the registry head.
4. **Optionally** point `LAW_API_BASE_URL` at a **self-hosted** korean-law-mcp instance as an alternate
   transport — behind the existing flag, dev-validated first.
5. **Persist AnswerGrounding** (add `request_id` + `generated_at` to `AskResponse`) only **after** the
   PIPA/compliance questions in the external-skills strategy doc are answered (storing user questions
   has legal implications).

---

## 10. Remaining risks

| # | Risk | Severity | Mitigation / status |
|---|---|---|---|
| R1 | Law API **not verified-working** with committed config (placeholder OC → 403) | High (feature silently degrades) | Documented (§2.3); operator must set a registered OC. Degradation is safe. |
| R2 | Live Railway env config unknown from here (mode/OC may differ) | Medium | Flagged; needs operator confirmation. |
| R3 | Declared cache unimplemented → API re-hits in audit/enabled | Low–Med | Follow-up F-4; short timeout limits blast radius. |
| R4 | Stale sibling docs may mislead future contributors | Medium | Source-registry note fixed; F-1 banners recommended for the two stale docs. |
| R5 | UI source panel not runtime-verified in this audit | Low | Verified by contract reading; recommend a browser smoke before promoting law grounding to user-visible "verified". |
| R6 | Dormant adapters (`public_data_client`, `korean_law_client`) could be mistaken for live | Low | Documented (§2, §6); F-5 docstrings. |
| R7 | `citation_verification` extracts but does not verify against a live DB | Medium | Depends on R1; F-3. Until then, citations are surfaced as "present/unverified". |

## 11. Follow-up tasks

- **F-1** Add "SUPERSEDED — see 2026-06-14 audit" banners to `PUBLIC_DATA_AND_LAW_GROUNDING_AUDIT.md`
  and `EXTERNAL_SKILLS_AND_LEGAL_GROUNDING_STRATEGY.md`.
- **F-2** Emit `STALE_SOURCE_WARNING` into answers when a cited source predates the registry head.
- **F-3** Wire real citation-against-DB verification in `citation_verifier` (needs R1).
- **F-4** Implement the law-result cache (`LAW_GROUNDING_CACHE_TTL_SECONDS`).
- **F-5** Mark `public_data_client.py` / `korean_law_client.py` as legacy/dormant in their docstrings.
- **F-6** Populate `confidence`/`language`/`retrieved_at` on the manual SourceRecords (validator already
  flags these as freshness gaps).
- **F-7** Operator: register an OC, set Railway secrets, run the live probe, update the probe doc.
- **F-8** Optional: self-host korean-law-mcp behind `LAW_API_BASE_URL`; or persist AnswerGrounding after
  PIPA sign-off.

---

## 12. Non-negotiables compliance

- No legal/immigration content invented; no document requirements added.
- No disclaimers/cautions/uncertainty notices removed or weakened.
- No subcodes flattened; protected data files untouched.
- Conflicts/uncertainty **preserved and surfaced** (the 403 result and stale-doc conflicts are reported,
  not papered over).
- **No claim that MCP integration is complete.** It is not, and this PR does not wire one.
- Full legal correctness is **not** claimed — this is rendering/data-hygiene/architecture work.
