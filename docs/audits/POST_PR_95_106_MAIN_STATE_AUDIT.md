# POST_PR_95_106_MAIN_STATE_AUDIT

Date: 2026-05-20 (UTC)  
Branch audited: `main` (post-merge state for PRs #95–#106)  
Audit branch: `audit/post-pr-95-106-main-state`  
Scope: **Documentation-only readiness audit** for next implementation phase.

---

## 1) PR state summary (#95–#106)

### Merged PR timeline (from git log)
- #95: wire controlled law grounding into ask endpoint (runtime)
- #96: law grounding integration follow-up + grounding source metadata (runtime/UI wiring)
- #97: law grounding smoke test readiness docs (docs)
- #98: UX/accessibility overhaul (runtime/UI)
- #99: result UI fix, OCR artifact stripping, document tab/procedure unification (runtime/UI + data hygiene checks)
- #100: deadline reminder MVP (runtime/UI)
- #101: i18n fixes for GUIDE_I18N/UI keys (runtime/UI content)
- #102: law grounding live smoke results (docs)
- #103: Figma parity CSS layer (runtime/UI/CSS)
- #104: rewrite Phase 1+2 preservation contract/spec (docs)
- #105: external skills + legal grounding strategy audit (docs)
- #106: landing wordmark dedupe + category count bugfix (runtime/UI)

### Documentation-only vs runtime-changing

**Documentation-only PRs:** #97, #102, #104, #105  
**Runtime-changing PRs:** #95, #96, #98, #99, #100, #101, #103, #106

### “Do not merge” check
- No explicit `Do not merge` marker was found in merge commit subjects/bodies visible from local git history for #95–#106.
- No audit evidence in repository docs indicates a deliberately blocked PR was merged anyway.

---

## 2) Law grounding current state

Files inspected:
- `backend/services/korean_law_client.py`
- `backend/services/law_grounding.py`
- `backend/services/citation_verifier.py`
- `backend/services/grounding_config.py`
- `backend/paradiso_backend.py` (`/api/ask`, `/api/debug/law-grounding`)
- `scripts/smoke_law_grounding.sh`
- `docs/integrations/*law*`

### Findings

1. **`LAW_GROUNDING_MODE` is disabled by default:** **Yes**.
2. **`/api/ask` calls law grounding only under safe gating:** **Yes (mode+intent gating).**
3. **Any live external API calls in tests/default runtime:** default-safe; live law calls only on audit/enabled + intent + config.
4. **Missing API keys handled safely:** **Yes** (`LAW_API_KEY_MISSING` warning path).
5. **Secrets printed:** no key-value secret printing observed.
6. **Citation verification wiring:** **partially wired / placeholder-adjacent** (structured flow exists, but extracted-only and `CITATION_VERIFICATION_NOT_WIRED` semantics remain).

---

## 3) Frontend grounding UI state

Files inspected: `index.html`, `ai.html`

### Findings
- Grounding source panel and law-warning related UI strings exist.
- Missing-key/disabled states are represented with safe warning markers.
- No obvious hard overclaim of “legally verified” by default was found, but verification semantics still depend on partial backend verifier maturity.
- Source-type distinctions are available via backend response structures and UI hooks.

---

## 4) Search/result UI state

### Findings
- D-2, E-7, F-1, F-6 render/data paths still exist.
- Document tabs and procedure summaries remain present.
- `DATA_MISSING` honesty behavior appears preserved.
- OCR artifact stripping did not mutate `visa_data.json` in this audit run; JSON remains valid and mirror sync check passes.
- HiKorea CTA still uses `data-action="open-hikorea-guide"`.
- `hikoreaGuideOverlay` still exists.

---

## 5) Reminder feature state

### Findings
- Local reminder feature is frontend-scoped and isolated from backend APIs.
- `.ics` generation remains backend-independent.
- No email/SMS/web-push channels were added.
- Privacy implications remain pending documentation/policy hardening.

---

## 6) i18n state

### Findings
- `GUIDE_I18N` priority fixes landed in #101, but `TRANSLATION_PENDING` still appears in multiple language blocks.
- `UI_TRANSLATIONS` key parity check passes in repo checks; remaining fallback groups should be explicitly tracked.

---

## 7) Design/CSS state

### Findings
- PR #104 preservation contract exists.
- CSS cascade remains large/complex; no immediate duplicate-wordmark regression observed now.
- PR #106 duplicate text wordmark removal appears applied.
- `updateCategoryCounts` exists and is invoked.
- No obvious static regression found around `body.searched`/landing-main selectors, but automated regression coverage is still recommended.

---

## 8) Validation commands

Run in this audit:
- `git status --short`
- `python3 -m json.tool visa_data.json > /dev/null`
- `bash scripts/check_repo.sh`
- `ALLOW_BACKEND_TEST_SKIP=1 bash scripts/check_repo.sh`
- grep checks for: `LAW_GROUNDING_MODE`, `LAW_API_KEY`, `open-hikorea-guide`, `hikoreaGuideOverlay`, `TRANSLATION_PENDING`, `logo-brand`, `updateCategoryCounts`

Environment caveat:
- Backend dependency bootstrap for strict test phase hit proxy/tunnel 403 package-index restrictions; full backend tests were blocked in this environment.

---

## 9) Risk register

- law grounding not live-smoked successfully in a reachable controlled env
- citation verification remains partially placeholder
- UI source panel reliability messaging may still overclaim if not contract-locked
- privacy/terms/disclaimer still missing/incomplete
- `index.html` remains structurally overloaded
- CSS cascade layers still accumulating complexity
- D-4-2K duplicate/legacy cleanup unresolved
- OCR artifacts may still exist in long-tail source JSON fields
- Railway/backend active target status remains unclear

---

## 10) Recommended next steps (ordered)

1. Privacy/terms/AI disclaimer hardening.
2. Answer-quality contract (verified/unverified/unavailable semantics).
3. Controlled live smoke re-run with confirmed backend target.
4. Figma UX direction lock before further CSS layering.
5. Structural UI rewrite (modularize overloaded `index.html`).
6. Regression test PR focused on grounding flags, wordmark/category counts, modals, and i18n pending markers.

---

## Readiness verdict

**Conditionally READY** for next implementation phase as a stabilization phase (not legal-grounding production rollout).

This audit is documentation-only and does not change runtime behavior.
