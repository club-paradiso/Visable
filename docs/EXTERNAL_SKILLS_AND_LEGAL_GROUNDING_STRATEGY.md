# External Skills and Legal Grounding Strategy

**Date:** 2026-05-20  
**Branch:** `audit/external-skills-grounding-strategy`  
**Author:** AI audit — human review required before any production change  
**Repository:** `lucanomics/Paradiso`

---

## 0. Prerequisites and prior art

Before reading the strategy, understand what already exists on `main`:

| Artifact | Path | Status |
|---|---|---|
| Law grounding config | `backend/services/grounding_config.py` | On `main`. **Disabled by default** (`LAW_GROUNDING_MODE=disabled`). |
| Korean law HTTP client | `backend/services/korean_law_client.py` | On `main`. Calls configurable law API base URL. Gated by mode + env key. |
| Law grounding intent router | `backend/services/law_grounding.py` | On `main`. Regex-based intent detection; calls law client if intent matched. |
| Citation extractor/verifier | `backend/services/citation_verifier.py` | On `main`. Extracts 법령 제N조 patterns; raises `CITATION_VERIFICATION_NOT_WIRED`. |
| Public data client | `backend/services/public_data_client.py` | On `main`. Same disabled-by-default pattern. Not yet wired to `/api/ask`. |
| Law grounding audit | `docs/integrations/PUBLIC_DATA_AND_LAW_GROUNDING_AUDIT.md` | On `main`. Confirms all external API grounding is **inactive at runtime**. |
| Smoke test (results) | `docs/integrations/LAW_GROUNDING_LIVE_SMOKE_RESULTS.md` | On `main`. Result: `NOT_READY`. Railway blocked; local pip blocked. |
| Smoke script | `scripts/smoke_law_grounding.sh` | On `main`. Functional but not yet successfully run end-to-end. |
| Phase 1+2 rewrite analysis | `docs/FULL_REWRITE_PHASE_1_2_ANALYSIS.md` | On `main` (merged from PR #104). |

**Bottom line:** The grounding adapter infrastructure already exists in the codebase. The gap is not code — it is configuration, environment wiring, and the operator deciding which external service the law client should point at.

---

## 1. Executive Summary

### 1.1 Why PR #104 did not change the app

PR #104 was an **analysis-only PR**. It added a single markdown document (`docs/FULL_REWRITE_PHASE_1_2_ANALYSIS.md`) containing:
- The Phase 1 preservation inventory: 180 JS functions, ~100 DOM ids, ~90 CSS classes, 47 `data-action` values, and all API/data-file wiring required before the HTML/CSS can be rewritten safely.
- The Phase 2 design system spec: canonical `:root` token block and component CSS sketches.

No `index.html`, no CSS, no JS, no backend code, and no data files were modified. The purpose was to validate the extraction before any code is replaced. It is a gate, not an outcome.

### 1.2 Why this PR exists before implementation

Three external tools have been identified as potentially valuable for Paradiso. Before integrating any of them into runtime, a strategy audit is necessary because:

1. **Legal hallucination risk is non-negotiable.** Paradiso informs users about Korean immigration/stay administration. Inaccurate legal citations can cause real harm: overstay fines, visa revocations, failed applications. Any law grounding layer must be treated with the same rigor as the data itself.
2. **The grounding adapter is already built but unconnected.** Adding `korean-law-mcp` is now a configuration decision, not a code decision. That means the strategy audit comes *before* the env-var change, not after.
3. **Compliance pages (`korean-privacy-terms`) have legal review requirements.** Generating them in production before answering "what personal data do we collect?" is backwards.
4. **`dot-studio` is a development-workflow tool**, not a production dependency. Adopting it without a workflow design would mean adding a dependency that produces no runtime value.

### 1.3 Go/No-go recommendation summary

| Repository | Verdict | Horizon | Integration tier |
|---|---|---|---|
| `chrisryugj/korean-law-mcp` | **Go (phased)** | Near-term | Backend grounding layer (disabled→audit→enabled) |
| `kimlawtech/korean-privacy-terms` | **Go (compliance)** | Near-term | Compliance document generation; no runtime dependency |
| `dance-of-tal/dot-studio` | **Go (dev-only)** | Medium-term | Agent workflow design tool; explicitly NOT production runtime |

---

## 2. Repository Assessment

### 2.1 `chrisryugj/korean-law-mcp`

**What it provides:**  
An MCP server wrapping South Korea's 법제처 (Ministry of Government Legislation) APIs, transforming 41 official API endpoints into 15 unified tools for AI use. Capabilities include:
- Full-text statute search (1,600+ active laws, 10,000+ administrative regulations)
- Supreme Court / Constitutional Court / tax tribunal decision lookup
- Automatic citation verification (validates whether "출입국관리법 제10조" actually exists)
- `time_travel` — automated diff of law text between two dates (critical for "is this regulation still current?")
- `action_plan` — converts citizen questions into step-by-step legal procedures
- `impact_map` — shows which other laws are affected by an amendment
- Remote endpoint: `korean-law-mcp.fly.dev`

**How it helps Paradiso:**  
The current `/api/ask` grounding layer in `backend/services/korean_law_client.py` already makes HTTP calls to a configurable `LAW_API_BASE_URL`. Setting `LAW_API_BASE_URL=https://korean-law-mcp.fly.dev` (or a self-hosted instance) and `LAW_GROUNDING_MODE=audit` is the minimal integration path. No new code required.

Specifically:
- When a user asks "What is the legal basis for E-7 renewal?" the intent router (`law_grounding.py`) already detects the pattern ("법적 근거") and would route to the law client.
- `citation_verifier.py` already extracts 법령 제N조 patterns and would call `law_client.get_article()` to verify them — currently this raises `CITATION_VERIFICATION_NOT_WIRED` because no client is connected.
- The `time_travel` tool would be extremely valuable for detecting stale Paradiso manual data vs. current law.

**Integration tier:** Backend grounding layer. Not a frontend dependency. Not a user-facing feature at first.

**Risks:**
- `korean-law-mcp.fly.dev` is a community-run remote endpoint. Uptime, rate limits, and data freshness are not operator-controlled. Self-hosting (via `npx` or container) should be the production path.
- 법제처 API access requires a (free, but registered) API key from the Korean government. The remote endpoint may proxy this; operator confirmation needed.
- "Legal grounding" ≠ legal advice. Results must be surfaced with clear citations and uncertainty markers. The current `CITATION_VERIFICATION_NOT_WIRED` warning must become a rendered UI element, not a silent flag.
- Data can be one amendment behind. `time_travel` helps detect this, but a stale law result shown with false confidence is worse than no grounding at all.

**License:** MIT — permissive, commercial use allowed, attribution not required.

**Recommendation:** Connect in audit mode first (see §6 roadmap). Surface grounding results in a debug panel before making them user-visible. Gate on operator confirming that the grounding endpoint is either self-hosted or rate-limit-safe.

---

### 2.2 `kimlawtech/korean-privacy-terms`

**What it provides:**  
A Claude Code skill (Apache 2.0) for generating Korean privacy policies and terms of service based on actual Korean law: PIPA (개인정보 보호법), Consumer Protection Act, E-Commerce Law, and 2026 amendments. Features:
- Four modular skills: `privacy-terms`, `privacy-kr`, `privacy-eu`, `privacy-global`
- Jurisdiction branching: Korea (PIPA), EU (GDPR), US (CCPA/CPRA)
- AI service-specific templates (directly applicable to Paradiso.ai)
- React components for cookie banners and consent modals
- MDX output compatible with Next.js — not directly applicable to Paradiso's vanilla HTML architecture, but the legal content is portable

**How it helps Paradiso:**  
Paradiso currently has no privacy policy, terms of service, AI disclaimer, or cookie/consent notice. These are legal requirements for operating an AI service in Korea. The `korean-privacy-terms` skill can generate first drafts of all of these, scoped to AI service type, with PIPA compliance. The generated MDX can be converted to HTML and placed in a `/legal/` directory or inlined as static pages.

This is a **compliance prerequisite** — completing these documents is required before expanding AI features or storing user data.

**Integration tier:** Development tool. Run as a Claude Code skill to generate documents. Output is reviewed by a qualified attorney, then converted to static HTML pages. Zero runtime dependency.

**Risks:**
- Generated documents are first drafts, not legally binding until reviewed by a Korean attorney or licensed administrative scrivener (행정사).
- PIPA compliance depends on accurate answers to the data-processing questions in §4.
- The React/MDX component format does not match Paradiso's vanilla HTML architecture. The legal text can be extracted; the React components cannot be used directly.

**License:** Apache 2.0 — permissive, commercial use allowed.

**Recommendation:** Use immediately as a Claude Code skill to generate compliance document drafts. Do not add to production runtime. Legal text requires attorney review before publication.

---

### 2.3 `dance-of-tal/dot-studio`

**What it provides:**  
A local-first visual workspace (TypeScript/React, MIT) for designing and orchestrating AI agent workflows. Uses a Figma-like canvas to map performers and Acts (agent roles), then exports runtime configuration for OpenCode-compatible workflows. Features include AI-assisted editing, integrated chat, Discord runtime integration, and agent inspection. 401 GitHub stars.

**How it helps Paradiso:**  
Paradiso already involves multiple AI orchestration concerns that benefit from visual design:
- Claude Code (this session): exploratory analysis, code generation
- Codex/Antigravity-style runners: automated PR generation, data pipeline
- Backend AI pipeline: intent routing → visa data layer → law grounding → answer composition
- Future: automated QA agents, regression runners, compliance document updaters

dot-studio provides a visual canvas to design these workflows, assign responsibilities, and export runtime configuration — before any code is written. This is valuable for **designing the Paradiso.ai answer pipeline** (§3) as a multi-agent system.

**Integration tier:** Development workflow tool only. Not a production runtime dependency. Should not be added to `backend/requirements.txt`, `package.json`, or any CI pipeline.

**Risks:**
- OpenCode runtime is not currently used by Paradiso. The exported configuration format may not be compatible with the existing Railway/FastAPI backend.
- Adding a Node.js ≥20 dependency to the development workflow adds environment complexity if contributors don't have it installed.
- The Discord runtime integration is not relevant to Paradiso.

**License:** MIT — permissive.

**Recommendation:** Use for workflow design documentation (especially for §3 architecture and §6 PR planning) but do not install as a project dependency. Consider adding dot-studio diagrams as artifacts in `docs/architecture/`.

---

## 3. Proposed Architecture: Paradiso.ai Grounding Pipeline

This is a design target — not the current state. Current state is described in §0.

```
User question (Paradiso.ai)
│
▼
┌─────────────────────────────────────────────────────┐
│  INTENT ROUTER                                      │
│  law_grounding.py: should_attempt_law_grounding()   │
│  → detects: 법적 근거 / 제N조 / legal basis / etc.  │
└─────────────────┬───────────────────────────────────┘
                  │
      ┌───────────┴───────────┐
      │                       │
      ▼                       ▼
  No law intent           Law intent detected
      │                       │
      │               ┌───────▼────────┐
      │               │ VISA/MANUAL     │
      │               │ DATA LAYER      │
      │               │ (current: local │
      │               │  JSON fixtures) │
      │               └───────┬─────────┘
      │                       │
      │               ┌───────▼────────┐
      │               │ PUBLIC DATA    │
      │               │ LAYER          │
      │               │ public_data_   │
      │               │ client.py      │
      │               │ (disabled now) │
      │               └───────┬─────────┘
      │                       │
      │               ┌───────▼────────────────┐
      │               │ LEGAL GROUNDING LAYER   │
      │               │ korean_law_client.py    │
      │               │ → korean-law-mcp server │
      │               │   (disabled by default) │
      │               │   modes: disabled /     │
      │               │          audit /        │
      │               │          enabled        │
      │               └───────┬─────────────────┘
      │                       │
      │               ┌───────▼────────────────┐
      │               │ CITATION VERIFIER       │
      │               │ citation_verifier.py    │
      │               │ extracts 법령 제N조     │
      │               │ verifies via law client │
      │               │ (currently: NOT_WIRED)  │
      └──────────┐    └───────┬─────────────────┘
                 │            │
                 ▼            ▼
          ┌──────────────────────────────────────┐
          │  ANSWER COMPOSER                     │
          │  /api/ask → LLM synthesis            │
          │  Grounding context injected into     │
          │  system prompt as structured data    │
          │  Current: OpenRouter / Groq          │
          └──────────────────┬───────────────────┘
                             │
                 ┌───────────▼───────────┐
                 │  CITATION/UNCERTAINTY │
                 │  RENDERER             │
                 │  Surface:             │
                 │  - verified citations │
                 │  - law article text   │
                 │  - freshness date     │
                 │  - warnings:          │
                 │    LAW_GROUNDING_     │
                 │    DISABLED /         │
                 │    CITATION_NOT_      │
                 │    VERIFIED / etc.    │
                 └───────────┬───────────┘
                             │
                 ┌───────────▼───────────────────┐
                 │  UI RESULT CARDS              │
                 │  (ai.html / Paradiso.ai)      │
                 │  - Answer text                │
                 │  - Source evidence panel      │
                 │    (ai-grounding-panel CSS)   │
                 │  - Citation chips             │
                 │  - Uncertainty badge          │
                 │  - "Not legal advice" strip   │
                 └───────────────────────────────┘
```

**Architecture principles:**

1. **`korean-law-mcp` is a backend grounding layer**, not a frontend dependency. The MCP protocol is irrelevant at the UI layer; the backend calls it and includes structured results in the answer context.

2. **Law grounding is opt-in by intent**, not applied to every question. The intent router (`should_attempt_law_grounding()`) already implements this; it should be extended to also detect visa-code-specific questions (e.g., "Is the D-10 period still 6 months?" triggers a `time_travel` check).

3. **Three-mode gate is mandatory** (`disabled` → `audit` → `enabled`). Each mode change requires an operator decision and documented test outcome. The current `grounding_config.py` already implements this.

4. **Source-of-truth hierarchy** (hard constraint):
   1. Official current law/regulations (verified by `korean-law-mcp` + 법제처)
   2. Official government/HiKorea guidance
   3. Visa/stay civil manuals (current: `backend/data/` fixtures)
   4. Public data sources (current: inactive)
   5. Paradiso internal normalized data (`visa_data.json`)
   6. LLM synthesis — **never presented as authoritative; always labeled as AI-generated summary**

5. **Uncertainty must be visible.** Every response that uses law grounding must render which citations were verified, which were not, and the retrieval timestamp. Every response that *could not* use law grounding (disabled mode, key missing, timeout) must render a visible degraded-mode indicator — not silently omit the grounding.

---

## 4. Privacy and Compliance Layer

### 4.1 What `korean-privacy-terms` generates

Run as a Claude Code skill (`/privacy-terms` or equivalent), it produces:
- **Privacy policy** (개인정보처리방침): PIPA-compliant, AI-service type, Korean + optional English
- **Terms of service** (이용약관): Consumer Protection Act / E-Commerce Act compliant
- **AI disclaimer**: AI-generated content limitations, not a substitute for professional advice
- **Cookie/consent notice**: If applicable to Paradiso's architecture
- **Data retention and logging statement**: What is collected, how long it's kept, deletion policy

### 4.2 Questions Paradiso must answer before generating final documents

These must be answered by the operator, not by AI inference, before final legal documents are published:

| Question | Why it matters | Current answer |
|---|---|---|
| What personal data is collected? | Defines data subject rights under PIPA | Unknown — search queries? IP? Calendar reminders? |
| Are user questions stored? | PIPA Article 15 (purpose limitation); AI liability | Unknown — `/api/ask` logs not audited |
| Are server logs stored? | Log retention under PIPA Article 21 | Unknown — Railway logs may be retained |
| Are third-party AI APIs used? | PIPA Article 17 (third-party provision); user consent | Yes — OpenRouter/Groq used for LLM |
| Are emails/SMS/calendar reminders planned? | Direct marketing consent under PIPA Article 22 | ICS calendar export exists; no email/SMS yet |
| Are EU/US/global users targeted? | GDPR/CCPA applicability | Unknown — service is in Korean but globally accessible |
| Is the operator based in Korea? | PIPA jurisdiction; local representative requirement if non-Korean | Assumed yes (Korean-language immigration service) |
| Are children under 14 targeted? | PIPA Article 22 (special consent rules) | No |
| Is there a data processing officer (DPO)? | PIPA Article 31 (개인정보 보호책임자) required for certain processors | Unknown |

### 4.3 Implementation plan

**Step 1 (this PR):** Document the questions above and what is currently known.

**Step 2 (next PR, operator action):** Operator fills in answers. Runs `korean-privacy-terms` Claude Code skill with accurate inputs.

**Step 3 (subsequent PR):** Adds `/legal/privacy.html`, `/legal/terms.html`, `/legal/ai-disclaimer.html` as static pages. Links from footer and `ai.html`. No runtime dependency; no database.

**Step 4 (future):** If user data retention is confirmed, add PIPA-required data subject request form (erasure/portability).

---

## 5. dot-studio Usage Plan

dot-studio is adopted **as a design and documentation tool**, not as a production dependency.

### 5.1 Workflow mapping use cases

Use dot-studio's canvas to visualize and export diagrams for:

| Workflow | Performers (agents) | Acts (tasks) |
|---|---|---|
| Legal grounding pipeline | IntentRouter, LawClient, CitationVerifier, AnswerComposer | Detect intent, query law, verify citations, compose |
| Data update pipeline | VisaDataBuilder, ManualParser, SchemaValidator | Pull HiKorea manual, normalize, validate, publish |
| Compliance document generation | PrivacySkillRunner, AttorneyReview (human), DeployGate | Generate, review, approve, deploy |
| UX rewrite pipeline | HTMLPreserver, CSSRewriter, JSWirer, RegressionTester | Preserve, rewrite, verify, test |
| QA and regression pipeline | GoldenSetRunner, SmokeTestRunner, VisaRegression | Run golden evals, smoke backend, regression DOM |

### 5.2 Agent responsibility boundaries

| Agent | Tooling | Scope |
|---|---|---|
| Claude Code (this session) | Analysis, code generation, PR management | Codebase changes, audit docs, PR creation |
| Codex/Antigravity runners | Automated scripts, data pipelines | Scripted data transformations, batch builds |
| dot-studio (design-time) | Visual canvas, act choreography | Workflow documentation and runtime design artifacts |
| Human operator | Legal review, production env decisions, URL/key confirmation | Anything requiring authorization or legal judgment |

### 5.3 What dot-studio does NOT do

- dot-studio is **not installed** in this project's dependencies.
- dot-studio does **not** run on Railway or GitHub Actions.
- dot-studio output (visual diagrams, runtime configs) are stored as `docs/architecture/` artifacts, not executed directly.

---

## 6. PR Roadmap

| PR # | Branch prefix | Title | Scope | Status |
|---|---|---|---|---|
| #104 | `feature/full-rewrite-figma-aligned` | Phase 1+2 analysis: preservation inventory + design system spec | Analysis doc only | **Merged** |
| #105 (this PR) | `audit/external-skills-grounding-strategy` | External skills and legal grounding strategy | Strategy doc only | **This PR** |
| #106 | `feature/legal-grounding-debug-adapter` | Wire `korean-law-mcp` as disabled-by-default debug endpoint | Backend only: wire `law_grounding.py` into `/api/ask`; add `/api/debug/law-grounding` endpoint; default `LAW_GROUNDING_MODE=disabled`; no UI change | Pending |
| #107 | `feature/compliance-pages-shell` | Privacy / terms / AI disclaimer shell pages | Add `/legal/privacy.html`, `/legal/terms.html`, `/legal/ai-disclaimer.html`; link from footer | Pending operator data-answers |
| #108 | `feature/html-css-full-rewrite` | Figma-aligned HTML/CSS rewrite (Phases 3–8) | Uses Phase 1+2 preservation contract from PR #104; new CSS from canonical `:root` | Pending green-light |
| #109 | `feature/answer-quality-result-card` | Answer quality and result card layer | Citation chip rendering; grounding-source panel; uncertainty badge; `LAW_GROUNDING_DISABLED` visible indicator | After #106 |
| #110 | `qa/regression-and-smoke-tests` | Regression and smoke test hardening | Fix smoke_law_grounding.sh blockers; add DOM id/class regression; visa golden eval expansion | After #106 |

---

## 7. Test and Validation Plan

Every PR in the roadmap must pass these checks before merge. Commands are relative to the repository root.

### 7.1 Repository health baseline

```bash
bash scripts/check_repo.sh
```

Expected: exits 0. Currently passes on `main`.

### 7.2 JSON schema validation

```bash
python3 -m json.tool visa_data.json > /dev/null && echo "visa_data.json: VALID"
python3 -m json.tool doc_master.json > /dev/null && echo "doc_master.json: VALID"
python3 -m json.tool data/jobcode_master.json > /dev/null 2>&1 && echo "jobcode_master.json: VALID"
```

### 7.3 Secret leakage check

```bash
grep -rn "LAW_API_KEY\s*=" . --include="*.py" --include="*.js" --include="*.json" \
  --exclude-dir=.git --exclude="*.env.example" \
  | grep -v "os.environ\|os.getenv\|env.get\|\.env.example\|test\|mock\|fake"
# Expected: no output
```

```bash
grep -rn "sk-\|Bearer [a-zA-Z0-9]\{20,\}\|api_key\s*=\s*['\"][a-zA-Z0-9]\{10,\}" \
  . --include="*.py" --include="*.js" --include="*.html" --include="*.json" \
  --exclude-dir=.git
# Expected: no output
```

### 7.4 Disabled-by-default env behavior

```bash
LAW_GROUNDING_MODE=disabled python3 -c "
from backend.services.law_grounding import build_law_grounding_context
result = build_law_grounding_context('출입국관리법 제10조의 근거가 무엇인가요?')
assert result['law_grounding_used'] == False
assert 'LAW_GROUNDING_DISABLED' in result['grounding_warnings']
print('PASS: disabled mode correctly suppresses law grounding')
"
```

### 7.5 Law grounding debug endpoint smoke test

(After PR #106 is merged and a test backend is available)

```bash
BACKEND_URL=http://127.0.0.1:8000

# Start backend with disabled mode
LAW_GROUNDING_MODE=disabled uvicorn backend.paradiso_backend:app --port 8000 &
sleep 2

curl -s -X POST "$BACKEND_URL/api/debug/law-grounding" \
  -H "Content-Type: application/json" \
  -d '{"question":"출입국관리법 제10조의 법적 근거는?"}' \
  | python3 -c "
import sys, json
d = json.load(sys.stdin)
assert d.get('law_grounding_used') == False
assert 'LAW_GROUNDING_DISABLED' in d.get('grounding_warnings', [])
print('PASS: debug endpoint returns expected disabled state')
"
```

Full smoke suite:

```bash
BACKEND_URL=http://127.0.0.1:8000 bash scripts/smoke_law_grounding.sh
```

### 7.6 Visa-code required-document regression

```bash
python3 scripts/check_required_documents_coverage.py
```

And key manual spot-checks:

```bash
for CODE in D-2 E-7 F-6 F-1 D-10; do
  python3 -c "
import json
data = json.load(open('visa_data.json'))
match = [v for v in data if v.get('code') == '$CODE']
print(f'$CODE: {len(match)} record(s)')
assert len(match) >= 1, 'MISSING VISA CODE'
"
done
```

### 7.7 DOM id/class/data-action preservation check (against PR #104 preservation contract)

```bash
# Critical IDs from Phase 1 preservation inventory
for ID in q rlist qf hikoreaGuideOverlay aiModalOverlay docModalOverlay \
           faqModalOverlay jobCodeModalOverlay jurisdictionModalOverlay \
           hikoreaGuideBody hero searchForm; do
  COUNT=$(grep -c "id=\"$ID\"\|id='$ID'" index.html 2>/dev/null || echo 0)
  if [ "$COUNT" -lt 1 ]; then
    echo "FAIL: id=$ID missing in index.html"
  else
    echo "PASS: id=$ID found ($COUNT)"
  fi
done

# Critical data-action values (static HTML)
for ACTION in toggle-search open-hikorea-guide open-jobcode-modal \
              open-jurisdiction-modal close-ai-modal toggle-theme; do
  COUNT=$(grep -c "data-action=\"$ACTION\"" index.html 2>/dev/null || echo 0)
  if [ "$COUNT" -lt 1 ]; then
    echo "FAIL: data-action=$ACTION missing in index.html"
  else
    echo "PASS: data-action=$ACTION found"
  fi
done
```

### 7.8 JS function preservation check (against the 180-function inventory)

```bash
for FN in renderResults executeSearch calculateScore loadVisaData \
           openModal closeModal openAiModal openDocModal openFaqModal \
           openHikoreaGuide submitAiAnalysis applyLanguage toggleTheme \
           openJobCodeModal openJurisdictionModal resetToLanding \
           startPreEntryTrack startInKoreaTrack; do
  COUNT=$(grep -c "function $FN\b\|$FN = function\|$FN = (" index.html 2>/dev/null || echo 0)
  if [ "$COUNT" -lt 1 ]; then
    echo "FAIL: $FN not found in index.html"
  else
    echo "PASS: $FN"
  fi
done
```

### 7.9 CSS regression: single :root block

```bash
COUNT=$(grep -c "^:root\|^ *:root" index.html 2>/dev/null || echo 0)
echo ":root blocks: $COUNT (expected: 1 after full rewrite, <=13 before)"
IMPORTANT_COUNT=$(grep -c "!important" index.html 2>/dev/null || echo 0)
echo "!important count: $IMPORTANT_COUNT (target after rewrite: <30)"
```

### 7.10 Accessibility and mobile layout

Manual checks (cannot be automated in this environment):
- 390px viewport: no horizontal overflow, no overlapping elements
- All interactive elements ≥44px touch target
- Body base font ≥16px
- Focus rings visible on keyboard navigation
- Screen reader: `aria-label` on all icon-only buttons
- `prefers-reduced-motion`: canvas and reveal animations disabled

---

## 8. Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| 1 | **Legal hallucination** — AI presents incorrect law citation as verified | Medium | Critical | Citation verifier must be active before any law grounding is user-visible; unverified citations must be labeled `NOT_VERIFIED`; `time_travel` used to detect staleness |
| 2 | **Outdated law/manual conflicts** — Paradiso manual data says one thing, 법제처 API returns a newer amendment | High | High | Freshness timestamp shown on every law result; `time_travel` diff run on all cited articles during data pipeline refresh |
| 3 | **Overreliance on unofficial tools** — `korean-law-mcp` is community-maintained, not a government service | Medium | High | Self-host the MCP server; treat remote `fly.dev` endpoint as dev-only; always attribute source to 법제처 API, not to the MCP wrapper |
| 4 | **Privacy compliance gap** — AI service processes user questions without PIPA-compliant disclosure | High | High | Complete §4.2 operator checklist before expanding AI features; deploy compliance pages (PR #107) before opening AI features to broader users |
| 5 | **UI rewrite breaking preserved JS wiring** — a renamed id or removed `data-action` silently breaks a modal or search feature | Medium | High | Run §7.7–7.8 checks on every HTML commit; the Phase 1 preservation contract in PR #104 is the binding spec |
| 6 | **Performance and latency** — law API calls add 500ms–3s to `/api/ask` responses | High | Medium | Strict timeout (`grounding_config.py`: 8s), disabled by default, async if possible, result cached (TTL: 24h per config) |
| 7 | **API key leakage** — `LAW_API_KEY` or `PUBLIC_DATA_API_KEY` exposed in logs, error messages, or committed files | Low | Critical | Keys read only from env; `grounding_config.py` never logs key values; §7.3 secret scan in CI |
| 8 | **User mistakes AI output for official legal advice** — user overstays visa or files wrong documents based on Paradiso.ai answer | Medium | Critical | Every AI response must include visible disclaimer strip ("이 정보는 AI 생성 요약이며 법적 효력이 없습니다. 정확한 정보는 1345에 확인하세요."); compliance pages (PR #107) must be linked from every AI response |
| 9 | **korean-law-mcp.fly.dev downtime** — community remote endpoint goes offline | High | Low (if gated) | `disabled` mode is the default; law grounding is additive, not required for baseline functionality; degraded-mode indicator shown in UI |
| 10 | **dot-studio runtime dependency creep** — someone adds dot-studio to requirements or package.json | Low | Medium | Explicitly document "no production runtime" in §5; keep out of `backend/requirements.txt` and any CI step |

---

## 9. Recommended Immediate Next Step

### 9.1 Do not integrate all three tools simultaneously

Attempting to activate `korean-law-mcp`, generate compliance pages, and redesign agent workflows in a single PR creates an untestable change with compounded risk surface.

### 9.2 Ordered action plan

**Right now (this PR):** This strategy doc is the only deliverable. No production behavior changes.

**Next PR (#106) — law grounding debug adapter:**
1. Wire `build_law_grounding_context()` into `/api/ask` response payload as a non-rendered `debug` field (never user-visible until deliberately promoted).
2. Add `/api/debug/law-grounding` POST endpoint that accepts a question and returns the grounding context (only reachable in non-production or with explicit auth header).
3. Set `LAW_GROUNDING_MODE=disabled` as the Railway production env default — the wiring exists but does nothing until the operator sets `audit`.
4. Verify §7.4–7.5 tests pass.
5. Operator confirms smoke against their Railway instance before merging.

**Operator action (before PR #107):** Answer all questions in §4.2. Provide truthful answers; do not guess.

**PR #107 — compliance pages:**
1. Run `korean-privacy-terms` skill with operator's answers.
2. Convert MDX output to vanilla HTML.
3. Add `/legal/privacy.html`, `/legal/terms.html`, `/legal/ai-disclaimer.html`.
4. Link from footer (`<footer class="ft">`) and from `ai.html` response header.
5. Attorney review before publishing. (The PR can be opened; merge after attorney sign-off.)

**PR #108 — HTML/CSS full rewrite:**
Use the Phase 1+2 preservation contract from PR #104. Phases 3–8 as scoped there.

**PR #109 — answer quality layer:**
Promote law grounding results from debug to user-visible. Render citation chips, verification status, freshness date, and disclaimer strip in AI result cards. Only after PR #106 has run in `audit` mode without incidents.

### 9.3 The one thing that must not happen

Paradiso must never present AI-generated legal summaries as official legal determinations. The disclaimer hierarchy is:

> 이 서비스는 베타 테스트 중이며, 제공되는 정보는 법적 효력을 갖지 않습니다.  
> AI 답변은 공식 법령/정부 기관의 결정을 대체하지 않습니다.  
> 정확한 정보는 반드시 1345(외국인종합안내센터) 또는 관할 출입국관서에 확인하세요.

This text must appear on every AI response surface, in all four supported languages (ko/en/zh/vi), before any law grounding feature is promoted to `enabled` mode.

---

*Document generated: 2026-05-20. No production runtime files modified. No secrets exposed. This document is a strategy artifact; it does not constitute legal advice.*
