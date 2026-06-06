# Source Status Taxonomy

Paradiso uses these statuses to describe how much official evidence supports a data record or AI claim. The status is not a confidence vibe; it is a traceability state.

## `source_confirmed`

| Field | Guidance |
|---|---|
| Definition | Official source evidence directly supports the exact claim and exact scope. |
| When to use | Manual, law, HiKorea, or other competent official source has a precise locator and quote or section reference. |
| When not to use | The source only supports a parent status, adjacent procedure, similar document, old manual, or internal normalized copy. |
| Paradiso example | D-2 registration required-document claim with current stay manual version, printed page, section heading, and quote for the D-2 registration document list. |
| Recommended AI/UI behavior | May show as official-source supported, with locator visible. Still include general non-advice framing for legal content. |

## `source_partial`

| Field | Guidance |
|---|---|
| Definition | Official source supports part of the claim, but some material part remains unsupported. |
| When to use | Source confirms procedure but not fee; confirms parent status but not sub-code; confirms one required document but not the full list. |
| When not to use | No official source exists at all, or the source is only background context. |
| Paradiso example | A manual page confirms E-7 extension procedure generally but does not confirm a specific sub-code exception. |
| Recommended AI/UI behavior | Narrow the claim to the supported portion or label the unsupported portion for manual confirmation. Do not use official certainty wording for the full claim. |

## `source_contextual`

| Field | Guidance |
|---|---|
| Definition | Official source is relevant background but does not directly prove the claim. |
| When to use | A service portal shows where a reservation happens, while the claim is about eligibility; a law article establishes general authority but not the specific document list. |
| When not to use | The source directly states the claim, or no source is available. |
| Paradiso example | HiKorea reservation page supports link guidance for office booking, but not whether a specific applicant must book before filing. |
| Recommended AI/UI behavior | Present as contextual guidance. Avoid "officially confirmed" labels. Pair with a warning to confirm exact requirements. |

## `official_unavailable`

| Field | Guidance |
|---|---|
| Definition | No usable official source evidence was available in the audit context. |
| When to use | Source retrieval failed, no locator exists, source is unofficial, or the official source does not cover the claim. |
| When not to use | A source exists but is partial or contextual; use those narrower statuses instead. |
| Paradiso example | A FAQ-style helper says a niche overstay scenario has a special exception, but no official manual, law, notice, or HiKorea locator is present. |
| Recommended AI/UI behavior | Do not state as official fact. Omit, soften, or explicitly mark as requiring official confirmation. |

## `needs_manual_review`

| Field | Guidance |
|---|---|
| Definition | Human source review is required before the claim or record can be promoted or presented with confidence. |
| When to use | Evidence is stale, broad, conflicting, machine-extracted, generated from a matrix, or not mapped to the exact scenario. |
| When not to use | A reviewer has already confirmed direct official support for every in-scope claim and recorded required locator/quote metadata. |
| Paradiso example | A candidate record generated from a manual crosswalk has page ranges but no reviewer quote tying each document to the exact status/sub-code/procedure. |
| Recommended AI/UI behavior | Keep user-facing language cautious. Preserve manual-review flags until a reviewer documents direct support. |
