# Held-out set v12: where is the person, and what does the page really allow?

You write test material for a Korean visa/stay Q&A assistant. Read only this brief and `pages_checks.json` in this directory. Do not open, list or search anything else. Write only `heldout_v12_checks.json` here.

Background: Korean immigration has two separate procedures. **visa** = getting a visa or a visa issuance certificate (사증발급인정서) to come to Korea from abroad (the applicant is abroad; an inviter in Korea may file the certificate for them). **stay** = procedures for a foreigner already in Korea (extension of stay, change of status, alien registration, re-entry permit, permission for other activities, workplace change).

## Part R — 30 routing questions (no pages needed)
Questions a real person might type: 20 in Korean, 10 in English. Each says or implies where the person (or the foreigner the question is about) is, in varied natural wording — not formulaic. Give each a gold `procedure`: `visa`, `stay`, or `unclear` (cannot tell from the question). Aim for about 12 visa, 12 stay, 6 unclear. Include hard ones: someone in Korea inviting a relative who is abroad (visa); someone abroad asking about a family member already in Korea (stay); the word 체류기간 inside a visa question; a place named that is not where the person is ("한국에 있는 회사가…", "my company in Seoul"); a person in Korea on a short visit; questions with no clue at all (unclear).
`{"id": "R-01", "question": "...", "procedure": "visa|stay|unclear", "why": "Korean, one sentence"}`

## Part C — 30 answer checks on real manual pages
`pages_checks.json` holds real pages of the 2026-10-19 manuals. For an item, pick a page and a rule on it that is either
- a **permission or limit with a count or period** ("…2회를 초과할 수 없음", "체류기간 1년을 넘을 수 없다", "…할 수 없다"), or
- a **period counted from a start** ("입국일로부터 90일 이내", "변경일로부터 6개월").

Pick only rules of the first kind (a permission, prohibition or limit), with or without a number: "…할 수 없음", "불가", "불허", "인정하지 않음", "제한", "…까지만", "…범위 내".
Write a natural `question` (Korean) the rule answers. Then:
- `right_answers`: 2 short answers stating the rule correctly; make one a **different but equivalent wording**.
- `wrong_answers`: 2 confident answers that flip it: they say it is allowed, unlimited or does not apply where the page says it is not (or the reverse). Vary the wording: some keep the page's words and turn them, some say it in everyday words ("상관없이 됩니다", "그건 문제없어요", "제한은 따로 없습니다"). `kind` is always "flipped".
`{"id": "C-01", "page_id": "...", "rule_quote": "exact substring of the page text", "question": "...", "right_answers": ["...", "..."], "wrong_answers": [{"text": "...", "kind": "flipped"}, ...]}`
Use at least 15 different pages.

## File
`{"version": "heldout-v12-checks", "created": "2026-10-28", "authorship": "written by an agent that saw only this brief and pages_checks.json", "route": [...], "checks": [...]}`
Self-check with `python3 -I`: 30 + 30 items, unique ids, every `rule_quote` is an exact substring of its page text, every item has 2 right and 2 wrong answers. Report in four lines: counts by procedure, counts by wrong kind and pages used, the self-check result, one example of each part.
