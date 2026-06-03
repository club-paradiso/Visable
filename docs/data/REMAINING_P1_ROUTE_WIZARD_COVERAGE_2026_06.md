# Remaining P1 route-wizard coverage: E-7, D-4, and F-1

PR #250 is stale and conflicted and must not be merged directly. PR #249 already
landed the reusable `ROUTE_WIZARD_CONFIG` baseline, AI-modal/document-tab i18n,
and the live AI smoke baseline. PR #251 already landed the F-2, D-10, and H-2
route expansion. PR #252 already fixed the broad-route scenario-selection bug by
removing unsafe subtype preselection and resetting broad routes to **Show all**.

This follow-up carries forward only the remaining useful P1 route-wizard coverage
from PR #250:

- **E-7**: foreigner registration, the source-backed registered-workplace
  addition/change report, and broad extension guidance.
- **D-4**: the three existing source-backed status-change variants and broad
  extension guidance.
- **F-1**: the existing source-backed family/status-change and Korea-born-child
  status-grant variants, plus broad extension guidance.

Broad routes intentionally omit `variantId`. Selecting one activates the relevant
procedure tab and resets the scenario selector to **Show all**, preserving the
PR #252 safety behavior. Exact routes use only procedure variants that already
exist in `visa_data.json` and `backend/data/visas.json`; this change adds no new
procedure records, documents, or raw source metadata to the UI.
