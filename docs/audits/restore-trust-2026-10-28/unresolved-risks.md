# Unresolved risks — Restore Trust (2026-10-28)

Each item says what it needs: **H** = human legal or immigration review, **S** = an additional
official source, **E** = environment or production access, **D** = a design decision.

| # | Risk | Needs | Detail |
|---|---|---|---|
| U-1 | 1,449 of 2,456 status × procedure cells have no organised guidance (`원문 확인`). The browser shows 1,444 such badges across 258 codes | H | This is a content gap, not a rendering bug. Filling it means authoring rules from the manual, and each rule needs human review. The badge now appears only where it is true, and the answer shows the cited page verbatim. Nothing was invented to shrink the number |
| U-2 | Cited page still the handbook cover (p.383) for F-5-family visa cells and for 사증발급인정서 / 전자사증 in the F-4 and H-2 families (RT-14) | H, S | A keyword scan of pp.383–457 found no section for these. A reviewer must pick a page or decide that the procedure does not apply |
| U-3 | H-2 사증발급 stays SOURCE_ONLY, although p.386 says new H-2 issuance is suspended | H | Changing the state would be a legal assertion. Left for review |
| U-4 | The 2026-10-19 manuals carry conflicting review flags: `approval_state: approved` in `data/manual-corpus/catalog.json`, `needs_review` elsewhere, and the reader catalog says edition 2026.9 (RT-13) | H | Not changed. The UI shows the "아직 사람이 대조 검토하지 않았어요" notice. A future UI must not read `approved` as human-verified |
| U-5 | Status-only evidence for F-4 still lists 113 pages, 33 of which never mention F-4 / 재외동포 | D | The 33 carry no status code at all: continuation pages inside the F-4 chapter range. Filtering them out could hide real F-4 text. A tighter chapter range for F-4 inside the 동포 handbook (393–398 by heading) would need an authored chapter boundary |
| U-6 | Verbatim excerpts come from PDF text extraction. Tables can be column-interleaved (e.g. p.394) | — | Disclosed in the preview note. The full page and the PDF link remain one click away |
| U-7 | `tests/e2e/waymaker-quick-answer.spec.mjs:131` times out under a 6-worker full run | — | It uses fixed `waitForTimeout(800)` between three chained searches. It passes 32/32 in isolation on both base and fix. Pre-existing; outside this change |
| U-8 | Production was not driven directly; all browser evidence is from the same commit served locally | E | Production should match once deployed. The before screenshots come from the base commit (06390bc), which is the code behind the reported screens |
| U-9 | No automated broken-link crawl of external official URLs (hikorea.go.kr and others) | E | Sandbox egress restrictions. The local PDF and page links were exercised by the tests |
| U-10 | Sheet breakpoints differ: language ≤680px, theme ≤600px | D | See `RT-UI-overlay-anchoring.md` |
| U-11 | No legal requirement in the product was re-validated against statutes in this pass | H | This work touched rendering, routing and page references only. It is not a legal revalidation |
