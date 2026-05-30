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
