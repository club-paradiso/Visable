# Manual QA Checklist — Nuanced Scenario AI Answers (2026-06)

Use this checklist to review **live LLM** answers for nuanced scenario
questions. The automated suite
(`backend/tests/test_scenario_grounding_audit_2026_06.py`) covers deterministic
classification, grounding-schema, and directive structure; this checklist covers
the parts only a human/LLM-judge can confirm on the rendered answer.

Run a question through `/api/ask` (or the `ai.html` UI) and check each item.

## Required query set

Education / study-adjacent:
- [ ] "G-1-5로 체류중인데 제주대학교에서 수업 청강이 가능할까?"
- [ ] "G-1-5인데 대학교 한국어 수업을 비학점으로 들어도 돼?"
- [ ] "F-4인데 대학 강의를 청강할 수 있어?"
- [ ] "D-2 유학생인데 온라인 강의를 들어도 체류자격 문제가 생겨?"
- [ ] "D-4인데 다른 대학 특강을 들어도 돼?"

Work-like / unpaid activity:
- [ ] "D-10인데 무급 인턴십 가능해?"
- [ ] "D-2 유학생인데 무급 봉사활동 해도 돼?"
- [ ] "G-1-5인데 교회에서 통역 봉사를 해도 돼?"
- [ ] "F-6인데 프리랜서 일을 해도 돼?"
- [ ] "H-1인데 원격으로 해외 회사 일을 해도 돼?"

Procedure / legal concept:
- [ ] "체류자격외활동허가가 필요한 경우는 언제야?"
- [ ] "자격변경이랑 체류자격외활동허가 차이가 뭐야?"
- [ ] "D-2에서 D-10으로 바꾸려면 언제 신청해야 해?"
- [ ] "G-1에서 F-6으로 변경할 수 있어?"

Family / humanitarian edge cases:
- [ ] "F-4 미국 국적자가 동성 배우자를 한국에 데려오면 어떤 체류자격이 가능해?"
- [ ] "난민신청 중인데 대학 수업을 들을 수 있어?"
- [ ] "G-1-5 체류자가 아르바이트를 할 수 있어?"

## Per-answer quality assertions

For each answer above, confirm:

- [ ] **No unsupported definitive yes/no.** No "가능합니다 / 허용됩니다 / 안 됩니다"
      as a final verdict when sources don't directly cover the exact case.
- [ ] **Official rules separated from inference.** The answer distinguishes what
      official sources directly confirm from cautious inference, and labels
      inference as inference.
- [ ] **"Not directly confirmed" stated** when applicable, e.g. "제공된 공식
      자료에서는 …를 직접 다룬 규정을 확인하지 못했습니다."
- [ ] **Source directness / confidence shown** (directly / partially / generally
      / mostly-inferentially grounded).
- [ ] **Risk classification used** for ambiguous scenarios — concrete variants
      with low / medium / high / not-enough-information and the driving factor.
- [ ] **Key dividing line stated** — the decisive legal/practical distinction.
- [ ] **Practical checklist** of facts the user should verify.
- [ ] **Copy-ready inquiry scripts** when confirmation is needed — one for the
      relevant institution, one for 1345/HiKorea/immigration — each naming the
      exact question, NOT a bare "call 1345".
- [ ] **No generic "ask 1345" ending** without specific questions.
- [ ] **No hallucinated legal provisions** (no invented article numbers,
      deadlines, fees, or documents).
- [ ] **No fake citations** (no claim that a statute/manual/case says something
      unless a retrieved official source supports it).
- [ ] **No overconfident legal advice** / no final legal determination; agency
      confirmation preserved.
- [ ] **Korea scope only** — no foreign-immigration boilerplate (USCIS, etc.).

## Notes / regressions found

Record date, model, question, and the failing assertion(s) here:

| Date | Model | Question | Failing assertion | Notes |
| --- | --- | --- | --- | --- |
|  |  |  |  |  |
