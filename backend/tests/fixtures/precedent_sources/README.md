# Precedent-family scaffold fixtures

These are **synthetic, sanitized scaffold fixtures** that mirror the *shapes* the
National Law Information Open API (`open.law.go.kr` / `www.law.go.kr` DRF
endpoints) is expected to return for the precedent-related source families:

| file | family | result kind | notes |
|------|--------|-------------|-------|
| `precedent_list.json` | precedent (판례) | list search | mirrors `DRF/lawSearch.do?target=prec` — the **confirmed** target |
| `precedent_body.json` | precedent (판례) | body/detail | mirrors `DRF/lawService.do?target=prec&ID=…` — the two-step body lookup |
| `administrative_appeal_list.json` | administrative_appeal (행정심판례) | list search | **scaffold only** — official target not confirmed yet |
| `legal_interpretation_list.json` | legal_interpretation (법령해석례) | list search | **scaffold only** — official target not confirmed yet |
| `constitutional_decision_list.json` | constitutional_decision (헌재결정례) | list search | **scaffold only** — official target not confirmed yet |
| `official_error.json` | precedent | error | official API error object → public-safe unavailable |
| `html_service_page.txt` | precedent | bad response | HTML/login page → public-safe unavailable, never echoed |

They contain **no `OC` / API-key values and no real response bodies**. Case
numbers, decision numbers, dates, courts and agencies in these files are
**invented for shape testing only** and must never be cited as real authority.

Only `precedent` has a confirmed list-search target (`prec`). The
administrative-appeal / legal-interpretation / constitutional-decision shapes
are conservative scaffolds; their official targets and field names remain a
follow-up verification item (see
`docs/data/LAW_OPEN_DATA_PRECEDENT_SOURCE_SCAFFOLD_2026_06.md`).

To capture **real** sanitized shape metadata (never raw bodies, never secrets)
for the confirmed precedent target, an operator with `LAW_API_OC` configured can
run:

```
python3 scripts/capture_law_api_shape.py --family precedent --query "출입국관리 체류자격 판례"
```
