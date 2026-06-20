"""Lead lifecycle state machine.

A lead moves through a guarded set of transitions. Anything not in the map is
rejected, which keeps the funnel honest and makes invalid states impossible.
"""
from __future__ import annotations

from app.domain.enums import LeadStatus

_S = LeadStatus

# from-status -> set of allowed next statuses
TRANSITIONS: dict[LeadStatus, set[LeadStatus]] = {
    _S.NEW: {_S.CONTACTED, _S.ENGAGED, _S.UNREACHABLE, _S.OPTED_OUT},
    _S.CONTACTED: {_S.ENGAGED, _S.UNREACHABLE, _S.OPTED_OUT, _S.LOST},
    _S.ENGAGED: {
        _S.TEST_DRIVE_REQUESTED,
        _S.FEEDBACK_GIVEN,
        _S.HANDED_OFF,
        _S.OPTED_OUT,
        _S.LOST,
    },
    _S.TEST_DRIVE_REQUESTED: {
        _S.HANDED_OFF,
        _S.FEEDBACK_GIVEN,
        _S.WON,
        _S.OPTED_OUT,
        _S.LOST,
    },
    _S.FEEDBACK_GIVEN: {_S.HANDED_OFF, _S.ENGAGED, _S.OPTED_OUT, _S.LOST},
    _S.HANDED_OFF: {_S.WON, _S.LOST, _S.OPTED_OUT},
    _S.UNREACHABLE: {_S.CONTACTED, _S.OPTED_OUT, _S.LOST},
    _S.WON: set(),
    _S.LOST: set(),
    _S.OPTED_OUT: set(),
}

TERMINAL_STATES: frozenset[LeadStatus] = frozenset({_S.WON, _S.LOST, _S.OPTED_OUT})


class InvalidTransition(Exception):
    """Raised when an attempted lead status change is not allowed."""


def can_transition(src: LeadStatus, dst: LeadStatus) -> bool:
    return dst in TRANSITIONS.get(src, set())


def assert_transition(src: LeadStatus, dst: LeadStatus) -> None:
    if not can_transition(src, dst):
        raise InvalidTransition(f"Cannot move lead from {src.value!r} to {dst.value!r}")


def next_states(src: LeadStatus) -> set[LeadStatus]:
    return set(TRANSITIONS.get(src, set()))
