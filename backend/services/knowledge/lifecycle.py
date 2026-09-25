"""Centralized knowledge lifecycle transition rules.

The same whitelist is enforced twice, deliberately:

* here, so callers get a clear ``KnowledgeError(TRANSITION_FORBIDDEN)`` before
  touching the database, with the actor rules below; and
* in the database (``lifecycle_transitions`` + trigger), so no code path — a
  script, a future endpoint, a hand-written UPDATE — can skip review.

``test_knowledge_platform`` asserts the two tables are identical.

Epistemic rule: review and verification are human acts. An AI extractor or a
system process may create proposals and move them INTO review; it can never be
the actor that marks a fact reviewed, verified or published. The pre-platform
repository verification (``legacy_import``) is recorded as its own reviewer
kind so the operator can tell it apart from a Knowledge Studio review.
"""
from __future__ import annotations

from typing import Dict, FrozenSet, Tuple

from .models import ActorKind, KnowledgeError, LifecycleState, PipelineError

S = LifecycleState

TRANSITIONS: Dict[LifecycleState, FrozenSet[LifecycleState]] = {
    S.DRAFT: frozenset({S.HUMAN_REVIEW_REQUIRED, S.REJECTED}),
    S.AI_EXTRACTED: frozenset({S.HUMAN_REVIEW_REQUIRED, S.REJECTED}),
    S.HUMAN_REVIEW_REQUIRED: frozenset({S.HUMAN_REVIEWED, S.REJECTED}),
    S.HUMAN_REVIEWED: frozenset({S.VERIFIED, S.HUMAN_REVIEW_REQUIRED, S.REJECTED}),
    S.VERIFIED: frozenset({S.PUBLISHED, S.HUMAN_REVIEW_REQUIRED, S.REJECTED}),
    S.PUBLISHED: frozenset({S.SUPERSEDED, S.WITHDRAWN}),
    S.SUPERSEDED: frozenset(),
    S.WITHDRAWN: frozenset(),
    S.REJECTED: frozenset(),
}

#: Target states that encode a human judgement.
HUMAN_JUDGEMENT_TARGETS = frozenset({S.HUMAN_REVIEWED, S.VERIFIED, S.PUBLISHED, S.WITHDRAWN})

#: Actor kinds allowed to move a fact into each target state.
_ALLOWED_ACTORS: Dict[LifecycleState, FrozenSet[str]] = {
    S.HUMAN_REVIEW_REQUIRED: frozenset({a.value for a in ActorKind}),
    S.HUMAN_REVIEWED: frozenset({ActorKind.HUMAN_OPERATOR.value, ActorKind.LEGACY_IMPORT.value}),
    S.VERIFIED: frozenset({ActorKind.HUMAN_OPERATOR.value, ActorKind.LEGACY_IMPORT.value}),
    S.PUBLISHED: frozenset({ActorKind.HUMAN_OPERATOR.value, ActorKind.LEGACY_IMPORT.value}),
    S.WITHDRAWN: frozenset({ActorKind.HUMAN_OPERATOR.value}),
    # Supersession is a consequence of publishing a successor, which already
    # required a human; the system performs the bookkeeping inside that transaction.
    S.SUPERSEDED: frozenset({ActorKind.HUMAN_OPERATOR.value, ActorKind.LEGACY_IMPORT.value, ActorKind.SYSTEM.value}),
    # Rejection may be automatic (e.g. a validation failure) or human.
    S.REJECTED: frozenset({ActorKind.HUMAN_OPERATOR.value, ActorKind.SYSTEM.value}),
}


def transition_pairs() -> FrozenSet[Tuple[str, str]]:
    return frozenset((a.value, b.value) for a, targets in TRANSITIONS.items() for b in targets)


def can_transition(current: str, target: str) -> bool:
    try:
        return S(target) in TRANSITIONS[S(current)]
    except (ValueError, KeyError):
        return False


def assert_transition(current: str, target: str, actor_kind: str) -> None:
    if not can_transition(current, target):
        raise KnowledgeError(
            PipelineError.TRANSITION_FORBIDDEN,
            f"{current} -> {target} is not a permitted lifecycle transition",
            detail={"from": current, "to": target},
        )
    allowed = _ALLOWED_ACTORS.get(S(target))
    if allowed is not None and actor_kind not in allowed:
        raise KnowledgeError(
            PipelineError.TRANSITION_FORBIDDEN,
            f"actor kind {actor_kind!r} may not move a fact to {target}",
            detail={"from": current, "to": target, "actor_kind": actor_kind},
        )


def reviewer_kind_for(actor_kind: str) -> str:
    """Reviewer-of-record kind stored on the fact. Never 'ai'."""
    if actor_kind == ActorKind.HUMAN_OPERATOR.value:
        return "human_operator"
    if actor_kind == ActorKind.LEGACY_IMPORT.value:
        return "legacy_repository_verification"
    raise KnowledgeError(
        PipelineError.TRANSITION_FORBIDDEN,
        f"actor kind {actor_kind!r} cannot be a reviewer of record",
    )
