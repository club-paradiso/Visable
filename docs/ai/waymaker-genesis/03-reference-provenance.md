# 03 — Reference provenance, licensing and clean-room policy

Status: reference inventory and licence facts **VERIFIED** as tagged below; the
existing Waymaker port **REQUIRES LEGAL REVIEW**, and its remedy is **DEFERRED**
to Mission 002; this mission's clean-room rules are **COMPLETED** for the WLIE code
as far as artefacts can show (§5.3). The process claim itself (no agent read the
reference while writing WLIE code) rests on the orchestration record. This document
is not legal advice.

Sources: [research-notes/ref-ops-license.md](research-notes/ref-ops-license.md)
(licensing, provenance, clean-room process, verification pass),
[research-notes/ref-capabilities.md](research-notes/ref-capabilities.md) (hosted
observation calls), [research-notes/official-api.md](research-notes/official-api.md)
(official guides, terms, copyright), [research-notes/law-identity.md](research-notes/law-identity.md)
(law.go.kr pages) and the other notes named in §2. Tag conventions are those of
[02 §0](02-korean-law-mcp-study.md): `ref:` marks a path in the reference repository,
`[NOTE file §n]` names the research-note section.

## 1. Rules that applied to every reference

* External repositories, web pages and API responses were **untrusted data**. The
  reference clone sat in the session scratchpad, outside the Waymaker repo. It was
  never executed, built, installed or tested, and its `CLAUDE.md`, `skills/` and
  `.claude/` files were read as data, not followed [NOTE ref-ops-license, method;
  ref-capabilities §0].
* Raw captures were parsed with `python -I` from their own directories. No secret
  (OC value, key, token) was printed or stored in the notes; OC-bearing links are
  described by shape only [NOTE official-api, credential hygiene; §7].
* No code, regular expression, prompt, tool description or fixture from the
  reference appears in the notes or in this document set. Behaviour is paraphrased
  with file and function pointers [NOTE ref-ops-license, method].
* The reference author's personal contact data, which appears in git metadata and a
  plugin manifest, was deliberately left out [NOTE ref-ops-license, method and
  verification pass].

## 2. References consulted

### 2.1 Third-party repositories and packages

| Reference | Identity | How it was used | Evidence |
|---|---|---|---|
| `chrisryugj/korean-law-mcp` | Commit `0a8f08ef4f697e08047f76bfab8be435f5bdda5a` (2026-10-15), package 4.15.9, MIT. Full clone: 473 commits on HEAD, 32 tags | Read-only study: [02](02-korean-law-mcp-study.md). Other notes touched it only lightly: file and function names (ai-lifecycle §2.7, knowledge-platform), a keyword grep (status-classifier §12), or single files cited for comparison (law-stack Q2, Q8, Q11, (f)). The model-training note did not use it [NOTE training-distill, live log] | [LIVE git rev-parse, 2026-10-19] VERIFIED |
| `chrisryugj/lexdiff` | Public; `LICENSE` = Business Source License 1.1, Licensor `chrisryugj`, Change Date 2030-04-14, Change License Apache-2.0, extra grant for non-production use only; exactly one commit touches `LICENSE`: `dbe9bbb`, 2026-04-13 | Licence metadata only; no code read | [LIVE GET api.github.com …/lexdiff/license and …/commits?path=LICENSE, 2026-10-19, 200; re-fetched by verifier] OBSERVED |
| `rabqatab/LexLink-ko-mcp` | Public; `license: null`; last push 2026-06-21 | Licence metadata only | [LIVE GET api.github.com …/LexLink-ko-mcp, 2026-10-19, 200; re-fetched by verifier] OBSERVED |
| `roboco-io/hwp2md` | MIT | Licence metadata only (its influence on the reference survives only in deleted history) | [LIVE GET api.github.com …/hwp2md, 2026-10-19, 200] OBSERVED |
| npm `korean-law-mcp@4.15.9` | MIT; the registry record has no provenance attestation | Registry metadata only; the tarball was **not** downloaded | [LIVE GET registry.npmjs.org/korean-law-mcp/4.15.9, 2026-10-19, 200, 3,482 B] OBSERVED |

### 2.2 Hosted reference MCP (observation only)

See §7. 19 calls were attempted across the research passes and 18 returned a result.

### 2.3 Official Open API documentation (open.law.go.kr)

| Reference | Coverage | Pointer |
|---|---|---|
| Guide index `LSO/openApi/guideList.do` | HTTP 200, 62,520 B, "총 191 건", 195 distinct guide identifiers (gap unexplained) | [NOTE official-api §0] VERIFIED |
| Guide pages `guideResult.do?htmlName=…` | 55 guides plus 2 mobile guides fetched by the verifier; the other ~138 not opened | [NOTE official-api §0, §1] VERIFIED |
| Usage and policy pages | `information/service.do`, `information/guide.do` (copyright policy, onboarding, restrictions), `openApi/openApiManual.do`, notices, Q&A and support-case views (IP, referer-domain and target binding, 2015) | [NOTE official-api §0, §5, §6] VERIFIED |
| Documented sample calls | 3 guide sample URLs with the guide's published sample credential (S1 `eflaw` list, S2 `law` body for 건강가정기본법, S3 `lsJoHstInf`); no real OC used | [NOTE official-api §7] OBSERVED |
| data.go.kr mirror pages | 15058878 (법제처 current-law article API, LINK type) and 15075354 | [NOTE official-api §5, §9] VERIFIED |

The S2 response is a real DRF JSON shape: 47 조문단위, of which 5 are 전문 heading
units, and a polymorphic 항. It is the documented shape that
`evaluation/fake_drf.py` follows (its docstring cites it). It also shows heading
units inside the article list, the case that [07](07-evidence-verification-design.md)
L3 excludes [NOTE official-api §7 S2; CODE
experiments/waymaker-ai/waymaker_ai/evaluation/fake_drf.py, module docstring].

### 2.4 law.go.kr public pages and statute text

| Reference | Coverage | Pointer |
|---|---|---|
| Statute route, consolidated body and 연혁 pages (`/법령/<name>`, `LSW/lsInfoR.do`, `LSW/lsHstListR.do`), admin-rule search and frame pages | 60 GETs by the research agent and 39 by the verifier, 1.5–2 s apart, no key, OC or cookie; all HTTP 200, nothing blocked | [NOTE law-identity §1, verification pass] OBSERVED |
| 법적효력/저작권 page and 저작권법 articles (제7조, 제24조의2, 제37조, 제137조, 제138조) | Version 저작권법 [시행 2026. 8. 11.] [법률 제21336호] | [NOTE official-api §6] VERIFIED |
| Derived records | `research-notes/law_identity_seed.json` (22 records); `experiments/waymaker-ai/datasets/registry/law_identity_2026-10-19.json`; the `verified_web` bundle `datasets/fixtures/sources/law_go_kr_capture_2026_10_19.json` | See §3.6 for the provenance fields |

### 2.5 Other references, by category

| Category | What | Pointer |
|---|---|---|
| Open-weight model repos and licences | Hugging Face public API `/api/models/<id>` for 84 + 4 repos with revision SHAs pinned, `config.json` and LICENSE/NOTICE files at the pinned SHA, model cards, licence pages (Gemma 4, OpenMDW and others) | [NOTE models §10] |
| Provider terms and model-training clauses | OpenRouter, Anthropic, Google AI, NVIDIA API Trial, Thinking Machines, OpenAI, Groq terms; OpenRouter model and provider catalogues; arXiv papers resolved through the arXiv API | [NOTE training-distill §7 L1–L31] |
| Prices | Model API, GPU rental, managed fine-tuning and hosting price pages, all dated 2026-10-19 | [NOTE cost §12] |
| Security advisories and CI state | `api.osv.dev` advisories; GitHub Actions run logs, branch protection and rulesets via `gh` | [NOTE sources-monitoring §0, verification pass] |
| Public-sector policy pages | 문화체육관광부 press releases on a 공공누리 type for AI training (title and date only; attachments not opened); a 2024 법제처 legal-tech press release (title and date only) | [NOTE official-api §6] VERIFIED for titles and dates, UNVERIFIED for content |
| Waymaker's own deployment | Read-only GETs to the Railway backend (`/health`, `/api/health/ai`, preflight, law and precedent search). These are observations of Waymaker, not third-party references | [NOTE law-stack §0; official-api §7 B1–B4] |

## 3. Licensing facts

### 3.1 korean-law-mcp: MIT

The copyright line names 2025 and "Chris" [CODE ref:LICENSE] VERIFIED. In summary, MIT
allows anyone to use, copy, modify, merge, publish, distribute, sublicense and sell
the software free of charge. Its one condition is that the copyright notice and the
permission notice go with all copies or substantial portions. The software comes
as-is, without warranty or liability. MIT has no NOTICE clause, no patent clause, no
UI attribution requirement and no copyleft. Any reused portion would have to carry
the exact copyright line, the full permission paragraph and the disclaimer
[NOTE ref-ops-license §2.1].

Scope caveat: the reference's own NOTICE limits the MIT grant to code its maker
wrote. MIT therefore does not by itself clear portions that the NOTICE or the code
headers identify as derived from other projects. Git history shows 23 author names,
and the project has no CLA, DCO or inbound-licence clause (inbound = outbound is the
usual assumption, INFERRED) [NOTE ref-ops-license §2.1].

`CITATION.cff` asks users to cite the software. That is a request, not a licence
condition [NOTE ref-ops-license §2.4].

### 3.2 NOTICE: anti-bot module re-implemented from an unlicensed project → DO NOT USE

The NOTICE has three parts [DOC ref:NOTICE] VERIFIED [NOTE ref-ops-license §2.2]:

1. **Data source.** Statute and other text comes from the 법제처 Open API. The source
   is credited. Accuracy follows the provider, and the original text must be checked
   for legal effect. Each user needs their own OC key, which only its holder may use.
2. **Third-party implementation.** `ref:src/lib/law-antibot.ts` re-implements, in
   TypeScript, the anti-bot page-parsing approach of LexLink-ko-mcp's client and
   uses the same patterns. The NOTICE explains the identical patterns by the identical
   format of the law.go.kr script being parsed. It warns that the upstream shows no
   licence, that an unlicensed work is all rights reserved, and that copied
   expression, if any, has no redistribution basis without permission. It calls
   itself provisional. The module's own header goes further and calls it a port
   (이식). LexLink-ko-mcp still reported no licence on 2026-10-19 (L2, L2').
3. Dependencies follow their own licences.

Timeline [CODE git log --diff-filter=A -- NOTICE; git show --stat e41c4ce] VERIFIED:
`law-antibot.ts` arrived in `92d5a74` on 2026-07-04. `NOTICE` arrived in `e41c4ce`
on 2026-07-31, the same commit that deleted a tracked test-results file holding a
real key value (history not rewritten; the blob was not opened). No tag up to
v4.9.1 contains a NOTICE. The npm package ships `LICENSE` and `NOTICE` today, and its
`exports` expose `./lib/*` and `./tools/*`, so the anti-bot module and the
LexDiff-marked modules can be imported from the package [CODE ref:package.json:9-26, 92-97].

**Decision: DO NOT USE** the anti-bot module, its tests and fixtures, the anti-bot
hook in `ref:src/lib/fetch-with-retry.ts` (around lines 189-205), or the feature
itself. Waymaker also must not depend on the npm package or import its internals.

### 3.3 Files marked as ported from LexDiff (BSL 1.1 since 2026-04-13) → DO NOT USE

LexDiff's `LICENSE` has been the Business Source License 1.1 since `dbe9bbb`
(2026-04-13): Licensor `chrisryugj`, non-production use only until the Change Date
2030-04-14, then Apache-2.0. Before that date LexDiff had no file at the `LICENSE`
path (GitHub path history does not follow renames, so a differently named file is
not excluded) [NOTE ref-ops-license §2.3, verification pass L4', L5', claim 3].

Files whose headers, comments or house rules say they were ported from LexDiff
[CODE file headers; DOC ref:CLAUDE.md "Critical Rules" 1; ref:docs/DEVELOPMENT.md:200, 252] VERIFIED:

| File | Note |
|---|---|
| `ref:src/lib/search-normalizer.ts` (+ its alias test) | LexDiff header since the first commit `8b8c31f` (2025-12-19); alias table synced from LexDiff on 2026-04-15, after the BSL commit |
| `ref:src/lib/law-parser.ts`, `ref:src/lib/law-jo.ts` | Article-code conversion and its wrapper |
| `ref:src/lib/three-tier-parser.ts`, `ref:src/lib/three-tier-citation.ts` | Three-tier parser and its adapter |
| `ref:src/lib/citation-content-matcher.ts` (+ its test) | Port landed in `92d5a74` on 2026-07-04, after the BSL commit. The pinned LexDiff commit in its header is a later comparison reference (`787a7fc`, 2026-08-17), not the recorded port source; the same comment says the upstream file last changed on 2026-04-12. Either way it was never under a permissive LexDiff licence |
| The LexDiff-style JSON parsing section of `ref:src/tools/law-text.ts` (~line 113) and the `licbyl` path of `ref:src/lib/api-client.ts` (~line 319) | Marked in comments |
| The content-verification step of `ref:src/tools/verify-citations.ts` (~line 494) and `ref:src/lib/article-anchor.ts` (~lines 108-122, a consumer of the normaliser and alias table) | Added by the verifier |

The NOTICE does not mention LexDiff. The LexDiff licensor and the korean-law-mcp
author appear to be the same account, so the author may have chosen to publish these
files under MIT. But the BSL text claims derivative works of BSL versions, the
NOTICE limits MIT to the maker's own code, and syncs after 2026-04-13 exist. The
status of LexDiff-derived code is **unresolved** (INFERRED) [NOTE ref-ops-license §2.3].

**Decision: DO NOT USE** any of these files, in any form: copy, translation,
line-by-line re-expression or close paraphrase.

### 3.4 Lower-risk lineage (Tier C)

* `extractEmbeddedAliases`, added 2026-05-19 (`1a9d9df`) inside the LexDiff-headed
  normaliser file, credits a pattern from the author's "stats-mcp" (licence not
  checked, UNVERIFIED).
* HWP/HWPX parsers written "with reference to" `roboco-io/hwp2md` (MIT) were deleted
  on 2026-04-01 when parsing moved to the `kordoc` dependency; they exist only in
  history.
* `kordoc` (MIT per the lockfile, same author) may be used only as a separate tool,
  never copied. Waymaker's manual pipeline already names it as an optional external
  converter run as a subprocess [NOTE ref-ops-license §2.3, §3.2].

### 3.5 The reference's dependencies

All 339 lockfile dependencies declare a licence. The 123-package production graph is
permissive (104 MIT, 7 ISC, 4 Apache-2.0, 3 BSD-2, 2 BSD-3, plus Python-2.0,
"MIT OR GPL-3.0-or-later" and "MIT AND Zlib"). LGPL-3.0 appears only in optional image
packages and MPL-2.0 only in dev tooling. Lockfile fields are self-declared metadata,
not audited licence texts [NOTE ref-ops-license §2.5, verification pass claim 11].
This matters only if Waymaker ever depended on the package, which it must not (§3.2).

### 3.6 Statute text and other official data

| Fact | Evidence |
|---|---|
| 저작권법 제7조 leaves unprotected: (1) the Constitution, laws, treaties, orders, ordinances and rules; (2) state and local 고시·공고·훈령 and similar; (3) court judgments, decisions and orders, and 심판/행정심판 decisions; (4) state or local compilations or translations of those; (5) news reports of bare facts | [DOC https://www.law.go.kr/법령/저작권법/제7조] VERIFIED [NOTE official-api §6] |
| 제24조의2 allows free use of public works made by the state in the course of duty, with exceptions. 제37조 requires the source to be stated for uses under that sub-section, and 제138조 item 2 sanctions a failure to do so. For 법령해석례 and MOJ manuals, attribution is therefore plausibly a statutory duty, not just a platform expectation (INFERRED) | [NOTE official-api §6, verifier additions] |
| open.law.go.kr copyright policy: free use including commercial use; criminal-liability warning (citing 저작권법 제137조 and 제138조) for forging or altering law information, and for using it **without stating the source or naming another agency as the source** | [DOC https://open.law.go.kr/LSO/information/guide.do] VERIFIED |
| law.go.kr: the information has **no legal effect**, is reference material, and the 관보 prevails; translations are unofficial | [DOC https://www.law.go.kr/lawPetitionForm.do?menuId=13&subMenuId=79] VERIFIED |
| Some APIs are said to be non-commercial, but no fetched page says which | [NOTE official-api §5] UNVERIFIED |
| AI and model training: no fetched open.law.go.kr or law.go.kr page mentions it. A 2026-01-28 문화체육관광부 release announces a 공공누리 type for AI training; its conditions sit in unopened attachments, and no evidence shows 법제처 data carries any 공공누리 label | [NOTE official-api §6] VERIFIED (absence on fetched pages); details UNVERIFIED |
| The reference repo grants nothing for model training. Its outputs are government data it does not own, so it cannot licence training on them. Waymaker must not treat the reference or its outputs as training or evaluation data | [NOTE ref-ops-license §2.8] VERIFIED (no statement found) / INFERRED (consequence) |

**Rule applied in this mission.** Real statute text is not protected (제7조), but every
record that carries it states the attribution `출처: 법제처 국가법령정보센터 (law.go.kr)`
together with its retrieval provenance: the official URL, `retrieved_at`
(2026-10-19) and the sha256 of the capture file it was parsed from. Answers must
never present API or page text as more authoritative than the 관보, and must never
present altered text as official.

Where this is recorded today. The `verified_web` bundle
`experiments/waymaker-ai/datasets/fixtures/sources/law_go_kr_capture_2026_10_19.json`
carries that attribution string at bundle level. When this document was written it
held 15 identities, 506 version rows and 245 provision units. Every version row
has an official URL on `www.law.go.kr` and a `retrieved_at` timestamp on 2026-10-19.
Its `captures` list has 57 records, 36 from the research captures and 21 from the
verifier captures, each with a sha256 and a role (route or frame page, history list,
history cross-check, consolidated body, verifier text extract). The raw files sit in
the session scratchpad, not in the repo; the recorded hashes let a later re-capture be
compared with them.

**Synthetic fixtures** (`synthetic_core.json`, `synthetic_adversarial.json`) use
obviously fictional law names, carry provenance `synthetic_fixture`, and never mix
synthetic text into a record that carries a real law id. The contract type
`SYNTHETIC_FIXTURE` is documented as never reaching a user
[CODE experiments/waymaker-ai/waymaker_ai/contracts.py:122-129].

## 4. Existing Waymaker provenance issue — REQUIRES LEGAL REVIEW

This predates Mission 001. It was found while studying the reference, and **this
mission did not modify any of the files involved.**

### 4.1 What ref-ops-license.md verified

Each item was checked by the original agent and re-checked by the verifier
[NOTE ref-ops-license §3.1-3.3, verification pass claims 4-5 and the lineage addendum].

1. **`backend/services/law_query_normalizer.py` closely translates the reference's
   `search-normalizer.ts` and `law-search.ts`.**
   * `normalize_law_search_text` follows the upstream replacement sequence step for
     step (lines 131-148). The order is NFC, exotic spaces, dashes, equals signs, the
     section sign, dash and dot spacing, the typo map, the Latin/Hangul split,
     whitespace collapse and parenthesis trim. The only difference is which
     equals-sign variant is folded.
   * The typo map is the six "법" substitutions of the upstream map, in upstream
     order (lines 113-114).
   * The non-law keyword list has 60 entries. 48 of them are shared with the upstream
     list of 85, the first 25 are in identical order, and the longest common
     subsequence is 43 (lines 419-425). The verifier recomputed this with an
     independent script.
   * The loose-match rule (lines 447-454) and the relevance weights (lines 469-486)
     mirror upstream.
   * `LAW_ALIAS_ENTRIES` reuses the upstream identifier, although the alias content is
     Waymaker's own immigration list.
2. **`backend/services/law_tools.py` `search_laws_ranked` (lines 786-860)** implements
   the ported fallback ladder and the display-100 reasoning.
3. **Lineage split of the port.**
   * The **LexDiff-marked half** comes from `search-normalizer.ts`, which has carried
     a "ported from LexDiff" header since its first commit. It covers the normaliser,
     the typo map, the alias key and alias resolution. In Waymaker these are
     `normalize_law_search_text`, `_BASIC_CHAR_MAP` / `normalize_basic_typos`,
     `normalize_alias_key` and `resolve_law_alias`.
   * The **unmarked half** comes from `law-search.ts`, created in korean-law-mcp on
     2026-04-18 (`67d0880`) with no LexDiff marker. It covers the loose match,
     relevance weights, keyword list and fallback ladder: `loose_match_law_name`,
     `resolved_law_matches`, `score_law_relevance`, `_NON_LAW_KEYWORD_RE` and
     `search_laws_ranked`. As far as the repository shows, this half is the
     korean-law-mcp author's own MIT code.
   * `extract_embedded_aliases` is mixed: it sits in the LexDiff-headed file but
     credits "stats-mcp".
4. **Version studied.** Waymaker studied npm `korean-law-mcp@4.9.0` (CHANGELOG dated
   2026-07-26) and ported in commit `98288ad` (PR #545, 2026-07-27). That version
   predates the NOTICE (2026-07-31). The LexDiff header was present in the 4.9.0-era
   source (`git show 23f9947:src/lib/search-normalizer.ts`). That the compiled npm
   build also carried it is INFERRED: tsconfig does not strip comments, and the
   tarball was not downloaded.
5. **Notices.**
   * `THIRD_PARTY_NOTICES.md` (lines 9-69) credits korean-law-mcp: MIT, "upstream
     version studied: npm korean-law-mcp@4.9.0", "algorithms ported to Python", a
     function mapping table, a "not taken" list and the full MIT text.
   * It does **not** mention LexDiff. A Waymaker grep for lexdiff and lexlink finds
     0 hits. `ATTRIBUTIONS.md` does not mention korean-law-mcp at all.
   * The file still uses the pre-rebrand name "Paradiso", which is cosmetic.
6. **Contradicting statements.**
   * The module docstring of `backend/services/law_tools.py` (lines 1-17) says the
     layer was built without copying any third-party code (lines 5-7). Blame dates
     that text to 2026-06-04, before the 2026-07-27 port.
   * `docs/integrations/PUBLIC_DATA_AND_LAW_GROUNDING_AUDIT.md:228` calls
     korean-law-mcp "conceptual inspiration only".
   * `docs/data/LAW_API_OC_EVIDENCE_TOOL_LAYER_2026_05.md:65` says no third-party
     code is used.
   * All three have been stale since the port.
7. **Assessed as not derived**, as far as seen (INFERRED):
   * `citation_verifier.py`, `legal_analysis.py` and `legal_research.py` share only
     tool names with the reference.
   * `statute_citation_guard.py` (same commit `98288ad`) has a title check based on
     normalised equality or containment. It has no substring layer and no bigram
     threshold, and its failure taxonomy is Waymaker's own.
8. **Other facts.** The owner's unpushed branch `fix/waymaker-qa-2026-10-16` touches
   none of these files and adds no korean-law-mcp or LexDiff text. The tests pinning
   the ported behaviour pass: `test_law_query_normalizer.py` + `test_law_tools.py`
   gave 142 passed (T1, T1').

Re-checked for this document on the branch base `fc896c2`:
* `git diff --stat 0713370 HEAD` over `law_query_normalizer.py`, `law_tools.py`,
  `statute_citation_guard.py`, `THIRD_PARTY_NOTICES.md`, `ATTRIBUTIONS.md` and the
  two docs printed nothing, so they are unchanged since the audit.
* `git show HEAD:` shows the attribution paragraph of `law_query_normalizer.py` at
  lines 25-30, the `law_tools.py` "without … copying any third-party code" wording at
  lines 5-7, and the quoted sentences of both docs.
* `git grep -i "lexdiff\|lexlink" HEAD`, excluding `docs/ai/waymaker-genesis`, finds
  nothing.

### 4.2 Status

**REQUIRES LEGAL REVIEW.** Two questions are for the owner or counsel.

1. Whether the LexDiff-marked half can be relied on as MIT through korean-law-mcp.
   Written confirmation from the author would be one route [NOTE ref-ops-license §5].
2. Whether the notices are adequate in the meantime.

### 4.3 Recommended remedy (Mission 002; not done in this mission)

1. **Clean-room replacement.** Re-implement at least the LexDiff-marked half
   (normaliser, typo map, alias key and resolution, embedded aliases) through the
   process in §5.4. Preferably replace the whole port, so that one provenance story
   covers the module. WLIE's own exact-title identity resolution
   ([06 §1](06-temporal-law-and-source-identity.md), `legal/identity.py`) makes much
   of the fuzzy search machinery unnecessary on the answer path.
2. **Corrected notices.** Do these together with the replacement, or sooner if counsel
   prefers:
   * While the port remains, record its full lineage in `THIRD_PARTY_NOTICES.md`:
     the upstream files, the 4.9.0 version, the LexDiff marker on the normaliser half
     and the unmarked half. After the replacement, change the entry to an
     independent-development record (PR, reviewer).
   * Correct the `law_tools.py` docstring and the two docs listed in §4.1 item 6.
     **Done 2026-10-21 (PR #671):** the docstring now points at the port, both docs
     carry a dated correction, the §2.1 third-party-endpoint advice is marked withdrawn,
     and `THIRD_PARTY_NOTICES.md` records the LexDiff header and the open question.
     Legal review and the clean-room replacement remain open.
   * Withdraw the advice in `docs/EXTERNAL_SKILLS_AND_LEGAL_GROUNDING_STRATEGY.md`
     §2.1 to point the law client at a third-party hosted endpoint [NOTE law-stack Q15, R7].
   * Fix the doubtful "(Python)" label for `kordoc` in `docs/hikorea_manual_sync.md`
     (INFERRED error) [NOTE ref-ops-license §3.2].
3. Until counsel decides, do not extend the ported functions or copy their behaviour
   into new modules.

## 5. Clean-room independent development policy

### 5.1 What may and may not be taken

Functional overlap that cannot be avoided, because it comes from the official API,
the MCP specification or generic engineering, is allowed. That covers:
* the DRF endpoints, parameter names, target codes, display ceiling, response field
  names, the 6-digit article code and the 200-status error envelopes;
* observable API behaviour, such as LIKE matching in 가나다 order (the 민법/난민법
  hazard), transient errors and empty bodies;
* MCP protocol shapes;
* generic patterns: retry with backoff and jitter, Retry-After, token buckets, LRU
  with TTL, per-request context, cancellation, length caps before pattern matching,
  output truncation with a marker, and secret masking.

Ideas and facts are free; the expression must be Waymaker's own
[NOTE ref-ops-license §4.2].

Distinctive expression to avoid, beyond the DO-NOT-USE files of §3.2–3.4
[NOTE ref-ops-license §4.1]:
* the tool catalogue (names, descriptions, exposure choices, categories);
* natural-language routing tables and vocabularies;
* scenario and chain designs and their feature names;
* curated data lists (risk rules, the non-law keyword list, alias dictionaries,
  ordinance fallbacks);
* precedent-compaction heuristics;
* error-label wording and model-directed warnings;
* all tests and fixtures, prose, media and plugin manifests;
* tuning-constant sets justified by the reference's own measurements;
* browser impersonation, Referer forging, anti-bot handling and scraping fallbacks.

### 5.2 What this mission actually did

| Rule | How it was applied | Status |
|---|---|---|
| Research and implementation kept apart | Only research agents read the reference, and they wrote paraphrased notes with pointers. The agents that wrote WLIE code (`experiments/waymaker-ai/`) worked from specs 06/07, the official-API notes, the law-identity and law-stack notes and the contracts. The orchestration rule for those agents was never to open the reference clone | Process rule from the orchestration record; not independently verifiable from artefacts |
| Specs written from Waymaker needs and the official API | [06](06-temporal-law-and-source-identity.md) and [07](07-evidence-verification-design.md) cite law.go.kr facts captured on 2026-10-19 and Waymaker code, not reference code. Where the study found a reference weakness, the specs chose a different rule: exact heading match instead of a similarity threshold (07 L4); recorded truncation instead of silent caps (07 §5); the worst outcome over all citations, so an unchecked unit never passes (07 §3); version keys that include the effective date (06 §1) | VERIFIED (document text) |
| Tests from the official spec and Waymaker captures | `fake_drf.py` renders the response shapes of [NOTE official-api §2.1] and the documented S2 sample. Fixtures are synthetic with fictional law names, or `verified_web` captures with per-file sha256. No reference fixture, test name or test structure is used | VERIFIED (module docstrings, bundle provenance fields) |
| No reference identifiers in WLIE code | A grep of `experiments/waymaker-ai` for korean-law-mcp, LexDiff, LexLink, chrisryugj and the hosted endpoint's domain found 0 hits. A grep of its Python files for the reference's distinctive markers (its bracket verdict labels, its fatal-error re-throw helper, browser UA strings, Referer, anti-bot) also found 0. The only Jaccard computations are character and word 3-gram near-duplicate and leakage checks in `dataset/validate.py` and `distillation/leakage.py`. They are generic dataset hygiene, not citation-content matching, which WLIE does by exact comparison | VERIFIED (grep, 2026-10-20) |
| Similarity review against the DO-NOT-USE files | Not run for WLIE. It would need someone to read the reference, which the WLIE code path was kept away from | NOT STARTED; required for the Mission 002 normaliser replacement (§5.4 step 6) |

### 5.3 Scope of the "COMPLETED" claim

The artefact checks above hold for the WLIE package as of this document. They show
that the code carries no reference identifiers, wording or fixtures. They cannot
prove that nobody looked at the reference. They also do not cover the backend
law-client fixes made by a separate agent in this mission (uncommitted at the time
of writing), which this document does not assess.

### 5.4 Process for Mission 002 (normaliser replacement and any law-client work)

Paraphrased from [NOTE ref-ops-license §4.3]:

1. Write requirements from Waymaker needs (immigration scope, evidence statuses,
   disclaimers) and the official guide pages, recording each URL and access date.
2. Write the design first, citing only the official guide, MCP documentation, Python
   documentation and Waymaker measurements. The author states in writing that the
   reference source was not consulted.
3. Write tests first, from the official specification and from responses Waymaker
   captured itself, with OC redacted at capture.
4. Implement in a session that does not have the reference in context, and never open
   the clone while writing the module.
5. People who have read the reference answer only functional yes/no questions, and
   each question is logged in the PR.
6. Before merge, a reviewer compares the diff with §5.1 and the DO-NOT-USE files
   (identifiers, list contents and order, pattern literals, comments, error strings,
   test names). The reviewer also runs a token n-gram overlap check and records the
   result in the PR.
7. Update `THIRD_PARTY_NOTICES.md` per module: either "independently developed under
   the clean-room process (PR, reviewer)", or, for a real port, the full lineage.

## 6. Anti-bot policy

The reference sends a hard-coded browser User-Agent and forges a law.go.kr Referer.
On cloud IPs it decodes and follows law.go.kr's JavaScript challenge
[CODE ref:src/lib/fetch-with-retry.ts:88-107, 173-205; ref:src/lib/law-antibot.ts:1-14] VERIFIED.
Waymaker must not adopt any of this, whatever the licence position:

1. **Identify honestly.** Waymaker's client sends its own User-Agent
   (`Paradiso-law-tool-layer/2026.05`, still the pre-rebrand name)
   [CODE backend/services/law_tools.py:137 at fc896c2] VERIFIED. It never sends a
   browser UA string or a forged Referer.
2. **Never circumvent a bot check.** That rules out decoding or following challenge
   scripts, solving CAPTCHAs, replaying cookies, and rotating IPs or proxies to avoid
   limits.
3. **A challenge is an outage, not data.** An HTML or challenge body maps to
   `LookupStatus.UNAVAILABLE_PARSE` (or another `unavailable_*` status). WLIE then
   reports `verification_unavailable`, and never "not found"
   ([07 §2](07-evidence-verification-design.md) invariant 1).
4. **Fix access through the official channel.**
   * Register the server's egress IPs on the OC application. Official Q&A pages from
     2015 describe IP, referer-domain and target binding; whether this is still
     enforced is UNVERIFIED.
   * Request each target family before code depends on it [NOTE official-api §5, §8.7].
5. **Production uses the Open API, not page scraping.** The research GETs to law.go.kr
   public pages were polite: 1.5–2 s apart, with no key, OC or cookie. Nothing was
   blocked (OBSERVED). Their output is fixture data, not a production data path. The
   reference's secondary scrape of the NTS site is a pattern Waymaker does not follow.
6. **No third-party proxies.** Never point Waymaker's law client at a third-party
   endpoint. Never import the reference npm package (§3.2).

## 7. Hosted reference MCP: observation calls and the routing decision

A hosted instance of the reference server was reachable from the research session as
an MCP connector. Its tool set matches 4.15.9. The exact version and the host's
logging and retention policy are unknown [NOTE ref-capabilities §0, §7].

| Pass | Calls | Inputs | Results |
|---|---|---|---|
| ref-capabilities, original | 8 of a budget of 8: search ×1, law text ×3, annex ×1, citation check ×1, applicable law ×1, interpretation search ×1 | Public law names (출입국관리법 and its 시행규칙), the public serial 289833, article keys, dates, the query 체류자격, and a block of **fabricated** citations | All answered [NOTE ref-capabilities §5] |
| ref-capabilities, verifier | 9 attempted: applicable law ×2 (the first failed: "server isn't responding"), law text ×5, citation check ×1, interpretation search ×1 | Same kinds of input | 8 answered. The verifier disclosed this as one call over budget if a failed attempt counts [NOTE ref-capabilities, verification pass] |
| sources-monitoring, original and verifier | 1 + 1: search "출입국관리법" | Public law name | Both answered; used to confirm stale law pins [NOTE sources-monitoring §0, verification pass] |

Total: 19 attempts, 18 answered. No user question, personal data, Waymaker
credential or OC value was sent. Which upstream key the hosted instance used for
these calls is not known; `ref:server.json` says keyless callers are served with the
operator's shared key (README-ONLY).

**Decision: Waymaker does not route user questions, or any Visable data, to a
third-party hosted law server** ([05 §6](05-legal-intelligence-architecture.md)).
Reasons:

* **Data boundary.** User questions can contain personal data and immigration
  status. Sending them to a third party with unknown logging and retention moves them
  outside Visable's control.
* **Unknown, fast-moving version.** The hosted version is unknown. The reference
  shipped ten v4.15.x tags in 17 days [NOTE ref-ops-license §2.6].
* **Credentials and terms.** Keyless callers are served with the operator's shared
  key under a rate limit, while the reference's own NOTICE says a key may be used
  only by its holder. Whether shared-key use is permitted is a terms question
  (UNVERIFIED).
* **Wrong output contract.** The server returns prose containing instructions to the
  model. Waymaker needs typed identity, version and verification fields
  ([07 §5](07-evidence-verification-design.md)).
* **Weaker verification than claimed.** Content checks are heading similarity only,
  and 호, 목, 별표 and 부칙 citations go unchecked. A serial-only read returned
  not-yet-effective text under an in-force header (V7–V9)
  ([02 §3–5](02-korean-law-mcp-study.md)).
* **Access method.** The upstream access path relies on browser impersonation and
  anti-bot decoding (§6).
* **Licence position.** Parts of the code have an unresolved licence position (§3.2–3.3).

Waymaker calls law.go.kr directly with its own credential, server-side. Further
observation calls in later missions follow the same limits: a stated budget, public
law names and fabricated citations only, and every call logged in the notes.

## 8. Summary: DO-NOT-USE list

| Tier | Paths (reference repo) | Reason |
|---|---|---|
| A | `ref:src/lib/law-antibot.ts` and its two tests; the anti-bot hook in `ref:src/lib/fetch-with-retry.ts` (~189-205); the feature itself | Re-implemented from an unlicensed project (NOTICE), and an anti-bot bypass (policy) |
| B | `ref:src/lib/search-normalizer.ts` (+ alias test), `law-parser.ts`, `law-jo.ts`, `three-tier-parser.ts`, `three-tier-citation.ts`, `citation-content-matcher.ts` (+ test); LexDiff-marked sections of `ref:src/tools/law-text.ts` (~113), `ref:src/lib/api-client.ts` (~319), `ref:src/tools/verify-citations.ts` (~494); `ref:src/lib/article-anchor.ts` (~108-122) | Marked as ported from LexDiff, BSL 1.1 since 2026-04-13; status unresolved |
| C | `extractEmbeddedAliases` (stats-mcp credit); deleted hwp2md-referenced parsers (history); `kordoc` (tool use only) | Unknown or lower-risk lineage |
| Package | npm `korean-law-mcp` as a dependency or import | Exposes Tier A/B modules; no provenance attestation |
| Data | Reference tests, fixtures and tool outputs as Waymaker training or evaluation data | No grant; outputs are government data the project does not own |

## 9. Open questions

* Does the author confirm that the LexDiff-derived files published in korean-law-mcp
  are MIT despite LexDiff's BSL 1.1? [NOTE ref-ops-license §5]
* What do the Open API's own terms say about redistribution, AI use and shared keys?
  Which APIs are "non-commercial"? [NOTE official-api §5, §10]
* Did LexDiff have a licence file under another name before 2026-04-13? Not queried.
* Did the compiled `korean-law-mcp@4.9.0` tarball carry the LexDiff header? Checking
  would mean downloading it, which needs the user's permission.
* What are the conditions of the 2026-01 공공누리 AI-training type, and does any 법제처
  data carry a 공공누리 label?
* What is the hosted reference instance's logging and retention policy? Unknown;
  irrelevant to Waymaker as long as §7 holds.
