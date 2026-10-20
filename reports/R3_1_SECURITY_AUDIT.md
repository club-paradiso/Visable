# VISABLE R3.1: Security & Access Control Audit Report
## Role-Based Access Control, Four-Eyes Principle & Administrative Hardening

- **Milestone**: VISABLE R3.1 (Production Publishing Recovery, Data Integrity & Operational Readiness)
- **Branch**: `feat/visable-r3-1-publishing-recovery`
- **Date**: 2026-10-20
- **Auditor**: Security Architect & Compliance Team
- **Status**: Production Audit Ready

---

## 1. Executive Summary

Administrative systems managing regulatory data require rigorous safeguards against privilege escalation, unauthorized mutations, unilateral publishing, and data leakage. R3.1 reinforces security across the entire Content Operations Studio with four core controls:

1. **Strict Role-Based Access Control (RBAC)** across four distinct operator personas.
2. **Mandatory Four-Eyes Principle (Separation of Duties)** preventing single-operator draft creation and approval.
3. **Least-Privilege Fallback** ensuring untrusted or unconfigured sessions default to read-only `VIEWER` access.
4. **Client-Side Safe DOM Construction** eliminating stored and reflected XSS vectors.

---

## 2. Role-Based Access Control (RBAC) Matrix

| Permission / Capability | Viewer (`viewer`) | Editor (`editor`) | Reviewer (`reviewer`) | Publisher (`publisher`) |
|---|:---:|:---:|:---:|:---:|
| View Scenarios & Statistics | ✅ | ✅ | ✅ | ✅ |
| View Diffs & Audit Logs | ✅ | ✅ | ✅ | ✅ |
| View Candidate Release Previews | ✅ | ✅ | ✅ | ✅ |
| Create & Update Drafts | ❌ | ✅ | ❌ | ❌ |
| Create Office Overrides | ❌ | ✅ | ❌ | ❌ |
| Approve / Reject Drafts | ❌ | ❌ | ✅ | ❌ |
| Run Pre-Publish Validation Gate | ❌ | ❌ | ❌ | ✅ |
| Execute Production Release | ❌ | ❌ | ❌ | ✅ |
| Execute Emergency Rollback | ❌ | ❌ | ❌ | ✅ |

### Least-Privilege Role Fallback
In previous iterations, parsing an unknown token or missing role assignment could lead to undefined state. In R3.1:
```python
# backend/services/knowledge/checklist_repository.py
def _resolve_operator_role(self, token: str) -> OperatorRole:
    # ...
    # Fallback to least-privilege VIEWER role if token unrecognized
    return OperatorRole.VIEWER
```
If an unauthenticated request or unrecognized token reaches the service, the actor is restricted to `OperatorRole.VIEWER`. Any attempt to draft, review, publish, or rollback returns `HTTP 403 Forbidden`.

---

## 3. Four-Eyes Principle (Separation of Duties)

### Threat Vector
A single operator acting maliciously or negligently could draft a fabricated document rule and immediately approve it without secondary peer review, potentially bypassing editorial scrutiny.

### Technical Enforcement
In `checklist_repository.py:act_on_draft`:
```python
# Four-eyes principle: draft author cannot approve their own draft unless emergency override
if action == DraftAction.APPROVE and draft.author == actor:
    if not action_in.allow_self_approval:
        raise HTTPException(
            status_code=409,
            detail=f"Four-eyes principle violation: operator '{actor}' cannot approve draft '{draft_id}' authored by themselves. Peer review required.",
        )
```

### Emergency Override Governance
In disaster recovery or emergency maintenance scenarios where only a single designated lead is available, self-approval can be permitted only when:
1. The operator holds explicit `REVIEWER` privileges.
2. The request explicitly includes `allow_self_approval: true`.
3. An auditable `comment` or `rationale` is submitted.
4. The audit log permanently records that an emergency self-approval occurred with the operator's identity.

In `assets/js/content-studio.js`, attempting to approve one's own draft triggers an interactive modal dialog warning the operator of the Four-Eyes violation and demanding confirmation and rationale before proceeding.

---

## 4. Token Hygiene & Web Security Posture

### Constant-Time Secret Verification
Token comparison utilizes `hmac.compare_digest` in `backend/services/knowledge/api.py` to prevent timing attacks when authenticating administrative tokens.

### Client-Side Session Storage & Zero-Leakage
- Operator tokens are stored solely in `sessionStorage` in the active browser tab.
- Tokens are never written to `localStorage`, cookies, or browser history.
- The `content-studio.html` header includes:
  ```html
  <meta name="robots" content="noindex, nofollow">
  <meta name="referrer" content="no-referrer">
  ```
- All outbound requests to non-API destinations omit referrer headers to avoid token leakage.

### XSS Prevention via DOM Sanitization
Dynamic strings from backend databases (scenario names, required document text, exceptions, operator notes) are rendered in `content-studio.js` exclusively via `document.createTextNode()` and `element.textContent`:
```javascript
function h(tag, attrs, children) {
  var el = document.createElement(tag);
  if (attrs.text) el.textContent = attrs.text;
  // ...
  return el;
}
```
Zero instances of `innerHTML` or `eval()` are present in `content-studio.js`, fully preventing stored XSS injection.

---

## 5. Security Test Suite Verification

The security controls are validated by the following tests:

1. `test_role_permissions_rbac`:
   Confirms that `viewer` cannot mutate data, `editor` cannot approve drafts, and `reviewer` cannot trigger production releases.
2. `test_four_eyes_self_approval_prevented`:
   Confirms that a draft author attempting approval receives `HTTP 409 Conflict`.
3. `test_least_privilege_viewer_fallback`:
   Confirms that unrecognized tokens default to `OperatorRole.VIEWER`.
4. Playwright E2E security test (`tests/e2e/content-studio.spec.mjs`):
   - Verifies 503 rejection when backend token is unset.
   - Verifies 401 rejection for invalid tokens.
   - Confirms token absence in `localStorage`.
