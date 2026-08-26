# Visable Immigration Intelligence Architecture

## The invariant

> The LLM reasons. Visable retrieves. Official sources prove.
> Deterministic code constrains. The user can see the difference.

Every decision below follows from that sentence. Where a rule looks strict, it
is because the alternative produces a confident, fluent, wrong answer about
someone's legal status.

---

## 1. What the model is and is not

The model is a **reasoning and language layer**. It may:

* read retrieved evidence and explain it,
* translate, summarize, and restructure,
* classify a question's intent, and
* say clearly that it does not know.

It may **not**:

* supply a legal fact from memory,
* invent evidence to fill a retrieval gap,
* decide whether a source is approved,
* decide whether a rule is currently in force, or
* convert "we could not check" into "there is no rule".

The last two are enforced structurally rather than by prompt text, because a
prompt is a request and a type is a constraint.

---

## 2. Layers

```
question
   |
   v
extract_immigration_facts          deterministic; reports only what was stated
   |
   v
missing_decisive_facts             asks rather than guesses
   |
   v
tool selection                     capabilities, not call sites
   |
   v
ImmigrationToolRegistry            services.immigration_tools
   |
   +-- lookup_status               Visable structured data
   +-- search_manual               approval state from the registry
   +-- search_law                  Open Law API, posture-aware
   +-- search_precedent            contextual only, never statutory authority
   +-- calculate_deadline          only periods Visable can cite
   +-- analyze_enforcement_rules   rule range, never a probability
   |
   v
EvidencePack                       ranked, with its gaps still visible
   |
   v
AIRuntime.complete(role=...)       services.ai_runtime
   |
   v
citation + safety validation       statute guard, safety review
   |
   v
answer + evidence + limitations
```

---

## 3. The two states that must never merge

```
RETRIEVAL_FAILED   we could not look
NO_RESULTS         we looked and found nothing
```

Only the second says anything about Korean immigration law.

Flattening them lets "our index is down" reach a user as "there is no such
rule" — the most dangerous sentence this system could emit, because it sounds
like an answer and licenses the user to act.

`ToolResult.is_inconclusive` and `EvidencePack.unavailable_reasons()` keep the
distinction reportable end to end, so an answer can say *"we could not check the
statute"* instead of implying there is no statute. `NOT_CONFIGURED` is separated
further still: an operator problem must not read as a legal finding.

---

## 4. Approval is deterministic

`EvidenceItem.usable_for_direct_assertion` is computed from the registry and the
retrieval outcome. No model output is an input to it.

An item may back a "you must / you may" statement only if **all** hold:

1. its authority type is in `DIRECT_ASSERTION_AUTHORITIES`;
2. if it is manual content, its `approval_state` is `APPROVED` — a human
   reviewer is on record;
3. its verification state is not `AUDIT_ONLY` or `CONFLICTING`;
4. its status is not `repealed`.

Consequences worth stating plainly:

* **Confidence is a ranking signal, never an approval mechanism.** An
  unapproved extraction with confidence 1.0 is still context.
* **Precedent is excluded.** A decision shows how a provision was read once; it
  is not the provision.
* **Audit-posture law retrieval cannot be cited.** That posture exists so
  article numbers are not trusted before the pipeline is proven end to end.
* **A repealed statute stays visible.** Hiding it would suggest the current rule
  was never found.

---

## 5. Evidence hierarchy

Encoded as `AUTHORITY_RANK`, so ranking is a property of the system rather than
a habit of whoever wrote the last prompt.

| Rank | Authority | Direct assertion? |
|---|---|---|
| 1 | Statute / decree / rule | yes |
| 2 | Approved official manual | yes, if human-reviewed |
| 3 | Official MOJ / HiKorea guidance | yes |
| 4 | Consular guidance | context |
| 5 | Administrative source | context |
| 6 | Precedent / 재결례 | context only |
| 7 | Visable structured data | yes |
| 8 | Unapproved extraction | context, clearly labelled |

Private blogs, legal marketing sites and forums are not in this table and are
not reachable by any tool.

---

## 6. Structural rules the code enforces

**Parent and sub-status stay distinct.** `lookup_status` returns a parent with
its subcodes listed and an explicit `subcodeRulesAreNotParentRules` marker. A
D-2-1 requirement rendered as a universal D-2 requirement is the most
consequential rendering error this dataset can produce.

**Visa and stay procedures never mix.** Manual sources are family-scoped;
사증발급 requirements never migrate into 체류 procedures or the reverse.

**Classification is not authorization.** The employment interpreter extracts
facts. Codes come only from official tables, via the deterministic analyzer.
"Reportable employment category" and "employment permitted under this status"
are different questions and the layers that answer them are different.

**Enforcement produces a range, not a likelihood.** The deterministic baseline
is primary. No AI-manufactured probability, and every enforcement fact carries
`isPrediction: false` / `isDeterministicRuleOutput: true`.

**A computed date is a preparation date.** `calculate_deadline` refuses periods
it cannot cite, marks arbitrary intervals with no statutory basis and low
confidence, and labels every result `isOfficialDeadline: false`.

**Refugee/asylum handling stays procedural.** Neutral procedure and official
document categories only — never narrative coaching.

---

## 7. Why the tool layer is transport-neutral

`services.immigration_tools` imports no FastAPI, performs no HTTP of its own,
and holds no provider SDK or credential. A tool is a plain callable over plain
data.

That is what lets the same registry back the HTTP API today and an MCP server
tomorrow without either owning it. Every tool already declares its stable
`visable.*` MCP name, so exposure is an adapter rather than a rename — callers,
logs and tests keep their identifiers.

MCP is deliberately **not** a dependency. Internal reliability comes first; the
public service must never require it.

---

## 8. Why `AIResult` is a dataclass

The defect this architecture was built after was a caller writing:

```python
text, meta = await _openrouter_complete_with_candidates(prompt)
```

against a 16-key dict. Python unpacks the *keys* and raises `ValueError`, which
a broad `except` turned into a permanent fake outage across two features.

A dataclass raises `TypeError: cannot unpack non-iterable AIResult` on the same
mistake — a failure no reasonable handler mistakes for a provider fault. The
type does the work the review did not.

A static rule in `check_ai_architecture.py` catches the shape as well, because
the runtime failure looked like ordinary degradation.

---

## 9. What survives a model change

Everything except the wording. Retrieval, approval, ranking, the two-state
distinction, the safety gates and the tool contracts are all deterministic
Python. Swapping every model id would change how answers *read*, not what
Visable is willing to assert.

That is the measure of whether this architecture is working.
