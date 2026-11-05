# Precedent grounding follow-up — production diagnosis & public-endpoint evidence (2026-11-05)

## What was actually broken (measured, not assumed)

The working assumption was "DRF registration blocks precedent grounding the
same way it blocked the Vercel enforcement path". Production evidence says
otherwise for the Railway backend:

- `GET /api/legal/precedents/search?q=출입국관리법` → **9 real precedents**
  (DRF `target=prec` works from Railway; the OC registration for this egress
  is valid).
- `GET /api/legal/precedents/search?q=강제퇴거` → **6**, `q=출국명령` → 3,
  `q=귀화` → 7, `q=난민` → 10, `q=사증발급` → 7, `q=체류자격변경` → 2,
  `q=체류기간연장` → 9.
- The exact planner phrase used inside /api/ask,
  `q=출입국관리법 체류자격 신고의무 신고` → **0**. `q=근무처 변경` → 0.
- `GET /api/legal/precedents/detail?id=234321` → full body (DRF detail works).
- /api/ask answers nevertheless carried `precedent: no_results` and
  `legal_evidence_status: no_relevant_results`.

Root causes, both in query construction, not credentials:

1. **Evidence pack** (`law_tools.build_evidence_pack`) searched precedents
   with `law_queries_attempted[0]` — a long planner phrase the DRF case-name
   search cannot match.
2. **Legal evidence** (`legal_evidence.retrieve_legal_evidence`) stopped at
   the first query variant returning *anything*. The broad statute-name
   variant returns criminal-title cases (`…출입국관리법위반`), which the
   topic gate then rejected wholesale → `no_relevant_results`, shadowing the
   on-topic variants behind it.

Fixes shipped: bare issue keywords derived from the question
(`citation_verifier.precedent_keyword_queries`, mirrored in
`legal_evidence._QUERY_KEYWORDS`) are retried/tried before the broad
variants, and legal-evidence collection continues across variants until a
case passes the relevance gate. The gates themselves are unchanged.

## Credential-free public precedent access (law.go.kr) — endpoint evidence

Tested from the build VM with real requests, 2026-11-05:

| Capability | Endpoint | Result |
|---|---|---|
| Body by identifier | `GET /LSW/precInfoR.do?precSeq=<id>` | **Works, no credential.** HTTP 200, full text with 【판시사항】/【판결요지】/【참조조문】/【전문】 sections. The `precSeq` is the *same* serial DRF returns (DRF ID 234321 → 대법원 2023. 3. 13. 선고 2021도3652). |
| Print/detail shell | `GET /LSW/precInfoP.do?precSeq=<id>` | 200 (94 KB shell page). `precInfoR.do` is the reliable body source. |
| Friendly path | `GET /판례/(<id>)` | 200, 1,196-byte shell (JS redirect); not used. |
| Keyword search | `GET /LSW/precScListR.do?query=…` | **Does not work** — returns a 5,278-byte app shell with no results. |
| Keyword search | `GET /LSW/lsScListR.do?menuId=7&subMenuId=47&tabMenuId=213&q=…` | Empty for precedents (the same XHR with menuId=1 returns *statute* results only; there is no precedent tab in the unified search). |
| Keyword search | `GET /LSW/searchResult.do?q=…` | No precedent results. |
| Search UI | `GET /LSW/precSc.do?menuId=7&subMenuId=47&tabMenuId=213` | 200 search page; results load through a JS-driven flow that could not be reproduced with plain GETs (no `data-prec-seq` result links in the served HTML). |

Conclusion: **public precedent access exists for by-identifier body fetch
only; there is no credential-free public keyword search.** Accordingly:

- `precedent_sources.get_precedent_detail` now falls back to `precInfoR.do`
  when the DRF detail call fails (same transport-gate discipline as the
  statute fallback: default transport only, `not_configured` excluded). The
  parser requires the bracketed court header, so the site's error page can
  never be mistaken for a precedent.
- List search stays DRF-only; if the DRF registration ever breaks, precedent
  *search* degrades to unavailable — documented here as a known limit, with
  no unofficial scraper substituted.

## Statute fallback note

The same follow-up added the Python twin of the JS public statute transport
(`services/law_public.py`, PR for Task 1): `/법령/<법령명>` current-version
discovery + `/LSW/lsInfoR.do` body fetch with the legal-corpus parser. DRF
law search/detail are currently healthy on Railway, so the fallback is a
resilience path; it fires on DRF official/HTTP/timeout/bad-response errors
or empty results, never on `not_configured`.
