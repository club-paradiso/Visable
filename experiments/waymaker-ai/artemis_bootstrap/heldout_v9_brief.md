# Held-out set v9: real questions about which row a number belongs to

You write test cases for a Korean visa/stay Q&A assistant. Each page in `pages.json` (this directory) is a real page of the 2026-10-19 Korean immigration manuals: `domain` is `visa_issuance` (사증 매뉴얼, people applying from abroad) or `stay` (체류 매뉴얼, people already in Korea). Many pages give **different numbers for different people or rows** on the same page — different status codes or sub-codes, household sizes, degree levels, nationalities, first grant vs. extension, and so on. An assistant that reads the page can still give the number from the wrong row. Your cases measure whether a checker notices that.

Read only `pages.json` and this brief. Do not open any other file or directory, and do not search the disk. Write only `heldout_v9_cases.json` in this directory.

## Write 24 cases
Spread them over the pages (at most two per page; use at least 15 pages). For each case pick a page that states two or more values of the **same kind** (fees, amounts of money, income thresholds, deposits, periods of stay, validities, deadlines, waiting periods) for **different subjects**.

- `question`: what a real person would type, in Korean (about 4 in English). Describe yourself in **your own words** — "박사과정 유학생인데요", "아내와 아이 둘, 네 식구예요", "인도 국적인데" — not by copying a table heading or row label word for word. Name a status code only where a person plausibly would (people often know "D-2" or "F-6"; they rarely know sub-codes). The question must be answerable from the page alone. Stay inside the page's domain: a stay page is about someone in Korea, a visa page about someone applying from abroad.
- `right`: the value the page gives for that person, as `{"amount": number, "unit": "krw"|"usd"|"day"|"month"|"year"}`. Use months for compound periods ("4년 10개월" → 58 month).
- `right_answers`: 3 short answers (1–2 sentences each) that a careful assistant could give, all stating the right value, with varied wording: one that copies the page's notation, one with another notation of the same value (e.g. "2년" / "24개월", "60,000원" / "6만 원"), one that also mentions the person's group in their own words.
- `wrong_answers`: 3 answers in the same style that state a value which **does appear on the page but belongs to a different subject or row** (another household size, another sub-code, another degree level, the extension value instead of the first grant…). Each `{"text": "...", "value": {...}, "mixed_with": "what row/subject that value really belongs to", "kind": "household|status_code|row|other"}`. Write them as confident, fluent answers — the kind of mistake that reads plausibly. Do not use a value that is not on the page.
- `expect`, in this exact shape:
```json
{"status": ["answered", "partial"], "must_cite": ["<page_id>"],
 "answer_must_contain_any_of_each": [["<right value notation 1>", "<notation 2>", "..."]],
 "answer_must_not_contain": ["<each wrong_answers text, verbatim>"]}
```
  The first list holds every reasonable notation of the right value (e.g. "2년", "24개월", "2 년"). Keep it to the value; do not require other words.

## File shape
```json
{"version": "heldout-v9", "created": "2026-10-28", "authorship": "written by an agent that saw only pages.json and this brief",
 "notice": "실제 2026-10-19 매뉴얼 쪽으로 쓴 독립 문항. 라벨은 쪽 원문에 맞춘 것이며 법률 검증이나 사람 검토가 아니다.",
 "cases": [{"id": "V-01-<short-slug>", "group": "V", "purpose": "<Korean: which two rows could be confused>",
            "question": "...", "evidence": [{"id": "<page_id>", "source_id": "<page_id before #>", "page": <page number>, "domain": "<visa_issuance|stay>"}],
            "right": {...}, "right_answers": [...], "wrong_answers": [...], "expect": {...}}]}
```
`source_id` is the part of `page_id` before `#`, and `page` is the number after `#p`. Evidence is only the one page.

## Self-check before you finish (python3 -I)
24 cases; ids unique; every `right.amount` and every wrong `value.amount` appears on that page (compare digits after removing commas; 만/천 units and "N년 M개월" count); right and wrong values differ; each `expect.answer_must_not_contain` equals the wrong texts; every right answer contains one entry of `answer_must_contain_any_of_each[0]`, and no wrong answer does. Report in four lines: case count and pages used, counts of `kind`, the self-check result, and one example question.
