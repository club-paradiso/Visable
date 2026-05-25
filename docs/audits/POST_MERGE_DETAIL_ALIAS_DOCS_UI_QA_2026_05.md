# Post-Merge QA - Detail-Code Alias and Document UI

## Scope

This report checks the merged detail-code alias and document-section unification work on `main`.

## Automated checks

- `visa_data.json` and `backend/data/visas.json` identical: `True`
- Visa records: `58`
- Backend records: `58`
- Scenario/help shadow records: `17`

## Index markers

- `DETAIL_CODE_RESOLVER_SHIM_2026_05`: `True`
- `DOC_SECTION_UNIFICATION_SHIM_2026_05`: `True`
- `DOC_SECTION_UNIFICATION_CSS_2026_05`: `True`

## Watched detail-code aliases

- `F-1-6`: F-1, SCN-4
- `E-7-4`: E-7
- `F-2-7`: F-2, F-5
- `D-10-T`: D-10
- `F-2-R`: NO_ALIAS_FOUND
- `F-4-R`: NO_ALIAS_FOUND
- `F-5-T`: F-5

## Resolver parity

- Union equals visa_data: `True`
- Union count: `58`
- visa_data count: `58`
- Simulated E-4B counts match: `True`
- Simulated E-4B user-facing content parity: `True`

## Manual QA still required

- [ ] Search `F-1-6`.
- [ ] Search `f-1-6`.
- [ ] Search `F-1`.
- [ ] Search `E-7-4`.
- [ ] Search `F-2-7`.
- [ ] Search `제주 무사증`.
- [ ] Open a result card with document sections.
- [ ] Confirm duplicate top-level `필수서류` summary is hidden when `구비서류` exists.
- [ ] Confirm `구비서류` tabs still render.

## Result

Automated post-merge checks passed. Visual/manual QA is still required for rendered search result cards and document tabs.

