import pytest

from app.domain.enums import LeadStatus as S
from app.domain.lead_state import (
    InvalidTransition,
    assert_transition,
    can_transition,
    next_states,
)


def test_allowed_transitions() -> None:
    assert can_transition(S.NEW, S.CONTACTED)
    assert can_transition(S.ENGAGED, S.TEST_DRIVE_REQUESTED)
    assert can_transition(S.HANDED_OFF, S.WON)


def test_disallowed_transitions() -> None:
    assert not can_transition(S.NEW, S.WON)
    assert not can_transition(S.WON, S.LOST)


def test_assert_raises() -> None:
    with pytest.raises(InvalidTransition):
        assert_transition(S.NEW, S.WON)


def test_terminal_states_have_no_exits() -> None:
    assert next_states(S.WON) == set()
    assert next_states(S.OPTED_OUT) == set()
