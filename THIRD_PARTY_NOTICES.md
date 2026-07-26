# Third-Party Notices

Notices for third-party work whose **source code or algorithms** were ported into
Paradiso's backend. Vendored browser libraries, fonts and official government
forms are catalogued separately in [`ATTRIBUTIONS.md`](ATTRIBUTIONS.md).

---

## korean-law-mcp

- **Project:** [chrisryugj/korean-law-mcp](https://github.com/chrisryugj/korean-law-mcp)
- **Author:** Chris (`chrisryugj`)
- **License:** MIT
- **Upstream version studied:** npm `korean-law-mcp@4.9.0`
- **Relationship:** algorithms **ported to Python**. No upstream file is vendored,
  bundled, or executed; Paradiso does not depend on the npm package at build or
  runtime.

### What was ported

Ported into [`backend/services/law_query_normalizer.py`](backend/services/law_query_normalizer.py),
translated from TypeScript to Python and re-scoped to immigration law:

| Upstream source | Ported as | Notes |
| --- | --- | --- |
| `lib/search-normalizer.ts` → `normalizeLawSearchText` | `normalize_law_search_text` | Same normalization ladder (NFC, exotic spaces/dashes, `§` → `제`, Latin/Hangul boundary). |
| `lib/search-normalizer.ts` → `normalizeAliasKey` | `normalize_alias_key` | Same space/case/interpunct-insensitive key. |
| `lib/search-normalizer.ts` → `resolveLawAlias`, `extractEmbeddedAliases`, `expandLawQuery` | `resolve_law_alias`, `extract_embedded_aliases`, `expand_law_query` | Same alias-resolution mechanism and longest-alias-first matching. **The alias table itself is Paradiso's own** — the upstream tax/labour/finance entries are not carried over; Paradiso's entries cover immigration and status-of-stay statutes. |
| `lib/law-search.ts` → `looseMatchLawName`, `resolvedLawMatches` | `loose_match_law_name`, `resolved_law_matches` | Same interpunct/spacing-tolerant match guard, including the `(법률\|법)$` suffix rule. |
| `lib/law-search.ts` → `scoreLawRelevance` | `score_law_relevance` | Same scoring weights (100 / 80 / 10 per word / +5 for a parent Act). |
| `lib/law-search.ts` → `NON_LAW_NAME_RE`, `stripNonLawKeywords` | `_NON_LAW_KEYWORD_RE`, `strip_non_law_keywords` | Keyword list re-scoped to immigration procedure vocabulary. |
| `lib/law-search.ts` → `findLaws` fallback ladder and `searchDisplay = 100` | `law_tools.search_laws_ranked` | Same reasoning: the 법제처 `lawSearch` API is a LIKE substring match returned in 가나다 order, so a wide window plus local re-ranking is required before `results[0]` can be trusted. Same rule that infrastructure errors must not be laddered away into "not found". |

The upstream insight that this defends against — 「민법」 matching 「난민법」 through
substring search — is preserved as a regression test in
`backend/tests/test_law_query_normalizer.py`.

### What was NOT taken

- No MCP server, transport, tool registry or CLI code.
- No `kordoc` document-extraction engine.
- No precedent compaction (`decision-compact.ts`) or citation content matcher.
- No upstream alias data for tax, labour, customs, finance or local ordinances.

### MIT license text (korean-law-mcp)

```
MIT License

Copyright (c) 2025 Chris

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## Public-Regulation-MCP-Builder

- **Project:** [koul777/Public-Regulation-MCP-Builder](https://github.com/koul777/Public-Regulation-MCP-Builder)
- **License:** MIT
- **Relationship:** **design principle only — no code was copied or ported.**

That project is a Windows Streamlit application for turning institutional
regulation documents into an approved MCP search tool. Paradiso adopted its
governing rule, not its implementation:

> Only content a human has compared against the original document and approved
> may be exposed to an AI assistant; everything else stays a review-stage draft.

Realized in Paradiso as:

- [`backend/services/manual_registry.py`](backend/services/manual_registry.py) —
  the `draft` / `parsed` / `needs_review` / `approved` / `superseded` / `rejected`
  state machine, and the rule that only `approved` may back a direct assertion.
- [`data/manual_approval_index.json`](data/manual_approval_index.json) — the
  review record, fail-closed when missing or corrupt.
- [`scripts/build_manual_search_index.py`](scripts/build_manual_search_index.py) —
  carries approval state into the search index so unapproved chunks remain
  visible-but-labelled rather than silently promoted.

No Streamlit application, upload pipeline, Vercel deployment scaffold, or
configuration-file format from that project was reused. Because nothing was
copied, its MIT license imposes no further obligation here; the attribution is
recorded because the design debt is real.

---

## Scope note

Neither project is a runtime dependency, a git submodule, or a build input.
Paradiso's backend remains `fastapi + starlette + uvicorn + pydantic + httpx`
(see `backend/requirements.txt`), and the site itself has no build system.
