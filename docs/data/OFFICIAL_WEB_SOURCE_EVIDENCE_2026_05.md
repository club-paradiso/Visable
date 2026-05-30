# Official Web Source Evidence — 2026-05

Live-official-source pass for PR #222. The goal was to source-ground additional
safe corrections from the two official public sites:

- **Korea Visa Portal** — https://www.visa.go.kr/ (authority for visa issuance /
  entry visa / overseas application)
- **HiKorea** — https://www.hikorea.go.kr/ (authority for stay / extension /
  change / registration / report / civil petition)

## Access result: BLOCKED by environment egress allowlist

**No live official page content could be retrieved from this environment**, so
**no web-sourced correction was applied**. The task's explicit fallback applies:
record `SOURCE_ACCESS_BLOCKED_OR_DYNAMIC`, do not patch from memory.

| Site | URLs attempted | Methods | Result | Status |
| --- | --- | --- | --- | --- |
| visa.go.kr | `/`, `/openPage.do?MENU_ID=10101`, `/openPage.do?MENU_ID=10201` | curl (browser UA, `Accept-Language: ko-KR`), WebFetch | **HTTP 403 `host_not_allowed`** | `SOURCE_ACCESS_BLOCKED_OR_DYNAMIC` |
| hikorea.go.kr | `/`, `/Main.pt`, `/info/InfoDatail.pt?CAT_SEQ=181&PARENT_ID=140`, `/cvlappl/CvlapplInfoPageR.pt` | curl (browser UA, `Accept-Language: ko-KR`), WebFetch | **HTTP 403 `host_not_allowed`** | `SOURCE_ACCESS_BLOCKED_OR_DYNAMIC` |

**Access date:** 2026-05-30

### Diagnosis (not a bypass)

- DNS resolves for all four hostnames and the TLS handshake completes — but
  verbose `curl` shows the certificate is issued by
  `O=Anthropic; CN=sandbox-egress-production TLS Inspection CA`. The connection
  therefore terminates at **this environment's inspecting egress proxy**, not the
  real origin.
- That proxy returns `HTTP/2 403` with header **`x-deny-reason: host_not_allowed`**
  — i.e. `visa.go.kr` and `hikorea.go.kr` are **not on the environment's egress
  allowlist**. This is the configured network policy of the remote execution
  environment (see https://code.claude.com/docs/en/claude-code-on-the-web), not an
  origin-side refusal and not something to work around.
- `WebSearch` (scoped to `hikorea.go.kr` / `visa.go.kr`) does return official
  result **links** (e.g. `CAT_SEQ=183 체류기간연장`, `CAT_SEQ=180 외국인등록`,
  `CAT_SEQ=186 체류자격변경`), but only **titles/snippets**, not full
  authoritative page bodies. Per task policy, search snippets are **not**
  authoritative source evidence and were **not** used to patch any data.

### What was **not** done (by constraint)

- No attempt to bypass the 403 / access control (no header spoofing tricks, no
  proxy hopping, no session/CAPTCHA circumvention).
- No use of unofficial blogs, law-firm pages, third-party mirrors, AI summaries,
  or search snippets as substitute "evidence".
- No patching of visa/stay data from memory.

## Consequence for this pass

- **Live-web corrections applied: 0.**
- The branch keeps the previously verified local-grounding correction (D-4
  extension `pageRange` `p. 90` → `pp. 90-91`, from the committed
  `backend/data/manual_grounding/stay_manual_grounding_2026_05.json`). It was not
  re-touched here.
- If/when the environment's network policy permits reaching `visa.go.kr` /
  `hikorea.go.kr` (or official pages are mirrored into the repo as committed
  attachments), this file should be re-run and populated with real per-source
  entries (URL, title, accessed date, source type, procedure/status, exact
  section heading, excerpt, supported field).

---

## Update 2026-05-31 — out-of-band official source maps added

Two official-source maps were added to PR #222 as **registry/procedure-reference
evidence**. Neither was fetched in Claude Code cloud, and **no data was patched
from them** in this pass (machine-readable detail:
`docs/data/official_web_source_evidence_2026_05.json`; full inventory and
readiness analysis: `docs/data/OFFICIAL_SOURCE_RETRIEVAL_REPORT_2026_05.md`).

Three clearly distinguished retrieval channels:

1. **HiKorea / Visa Portal — blocked in Claude Code cloud** (above): direct
   fetches return `403 host_not_allowed`. Status `SOURCE_ACCESS_BLOCKED_OR_DYNAMIC`.
2. **HiKorea / Visa Portal — retrieved by ChatGPT web access** (out-of-band):
   12 official pages — HiKorea main, the 출입국/체류안내 index, and the common
   procedure pages (체류일반, 외국인등록, 체류기간연장, 체류자격변경, 체류자격외활동,
   근무처변경/추가, 체류자격부여, 재입국허가, 각종신고의무) plus the Korea Visa Portal
   entry-purpose guide. Readiness: 3 `READY_FOR_SOURCE_REGISTRY`, 9
   `READY_FOR_PROCEDURE_SOURCE_REFERENCE`, 0 `READY_FOR_FIELD_PATCH`. These are
   **common procedure overviews**; each defers status-specific document lists to
   the status-specific manual/table, so they are **not sufficient alone** for
   per-status required-document rewrites.
3. **KIS / MOJ source map — supplied by the user**
   (`docs/data/official_source_map_2026_05.json`): 5 sources + 3 attachments.
   Readiness: 3 `READY_FOR_SOURCE_REGISTRY`, 1
   `READY_FOR_PROCEDURE_SOURCE_REFERENCE`, 1 `DO_NOT_USE_FOR_PATCH`, 0
   `READY_FOR_FIELD_PATCH`. The Visa Navigator manuals are status-level only and
   are **not** a required-document authority (they defer to HiKorea); the E-7-4
   page supports E-7-4 eligibility/quota reference only.

### Readiness summary across channels 2 + 3

| Channel | SOURCE_REGISTRY | PROCEDURE_REFERENCE | DO_NOT_USE | FIELD_PATCH |
| --- | --- | --- | --- | --- |
| ChatGPT-retrieved HiKorea/Visa Portal | 3 | 9 | 0 | 0 |
| User KIS/MOJ map | 3 | 1 | 1 | 0 |

**No source in either channel is `READY_FOR_FIELD_PATCH`.** Consequently no
status-specific required-document data was rewritten. The only production data
correction on this branch remains the D-4 extension `pageRange` fix.
