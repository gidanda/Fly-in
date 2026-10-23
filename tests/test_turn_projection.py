"""Tests for immutable one-turn projection results."""

from collections.abc import Mapping
from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from fly_in.drone import AtZone, DroneState, Finished, InTransit
from fly_in.turn_plan import MoveIntent, TurnPlan
from fly_in.turn_projection import TurnProjection


def make_projection() -> TurnProjection:
    """Create a valid projection shared by basic tests."""
    plan = TurnPlan((MoveIntent(1, 2),))
    states: dict[int, DroneState] = {
        1: AtZone(2),
        2: InTransit(3, 4, 1),
        3: Finished(),
    }
    users = {
        1: frozenset({1}),
        3: frozenset({2, 3}),
    }
    return TurnProjection(0, plan, states, users)


def test_stores_valid_projection_data() -> None:
    """A projection stores its source, plan, states, and connection users."""
    projection = make_projection()

    assert projection.source_turn == 0
    assert projection.plan == TurnPlan((MoveIntent(1, 2),))
    assert projection.projected_drone_states[1] == AtZone(2)
    assert projection.connection_users[3] == frozenset({2, 3})


@pytest.mark.parametrize("source_turn", [-1, True])
def test_rejects_invalid_source_turn(source_turn: int) -> None:
    """The source turn must be a non-negative integer, excluding booleans."""
    with pytest.raises(ValueError, match="source_turn"):
        TurnProjection(
            source_turn,
            TurnPlan(()),
            {1: AtZone(1)},
            {},
        )


def test_rejects_non_turn_plan() -> None:
    """The recorded plan must be a TurnPlan."""
    with pytest.raises(ValueError, match="plan must be a TurnPlan"):
        TurnProjection(
            0,
            object(),  # type: ignore[arg-type]
            {1: AtZone(1)},
            {},
        )


def test_rejects_empty_projected_drone_states() -> None:
    """Every projection must describe at least one drone."""
    with pytest.raises(ValueError, match="must not be empty"):
        TurnProjection(0, TurnPlan(()), {}, {})


@pytest.mark.parametrize("drone_id", [0, -1, True])
def test_rejects_invalid_projected_drone_id(drone_id: int) -> None:
    """Projected drone identifiers must be positive integers."""
    with pytest.raises(ValueError, match="drone_id"):
        TurnProjection(
            0,
            TurnPlan(()),
            {drone_id: AtZone(1)},
            {},
        )


def test_rejects_invalid_projected_state() -> None:
    """Every projected value must be a supported drone state."""
    states = cast(Mapping[int, DroneState], {1: object()})

    with pytest.raises(ValueError, match="must be a DroneState"):
        TurnProjection(0, TurnPlan(()), states, {})


@pytest.mark.parametrize("connection_id", [0, -1, True])
def test_rejects_invalid_connection_id(connection_id: int) -> None:
    """Connection identifiers must be positive integers."""
    with pytest.raises(ValueError, match="connection_id"):
        TurnProjection(
            0,
            TurnPlan(()),
            {1: AtZone(1)},
            {connection_id: frozenset({1})},
        )


def test_rejects_mutable_connection_user_set() -> None:
    """Connection users must be supplied as an immutable set."""
    users = cast(Mapping[int, frozenset[int]], {1: {1}})

    with pytest.raises(ValueError, match="must be a frozenset"):
        TurnProjection(0, TurnPlan(()), {1: AtZone(1)}, users)


@pytest.mark.parametrize("drone_id", [0, -1, True])
def test_rejects_invalid_connection_user_id(drone_id: int) -> None:
    """Connection user identifiers must be positive integers."""
    with pytest.raises(ValueError, match="drone_id"):
        TurnProjection(
            0,
            TurnPlan(()),
            {1: AtZone(1)},
            {1: frozenset({drone_id})},
        )


def test_rejects_connection_user_missing_from_states() -> None:
    """Every connection user must also have a projected state."""
    with pytest.raises(ValueError, match="connection user must exist"):
        TurnProjection(
            0,
            TurnPlan(()),
            {1: AtZone(1)},
            {1: frozenset({2})},
        )


def test_rejects_drone_using_multiple_connections() -> None:
    """One drone cannot use two connections in the same turn."""
    with pytest.raises(ValueError, match="multiple connections"):
        TurnProjection(
            0,
            TurnPlan(()),
            {1: AtZone(2)},
            {1: frozenset({1}), 2: frozenset({1})},
        )


def test_rejects_planned_drone_missing_from_states() -> None:
    """Every planned drone must have a projected state."""
    with pytest.raises(ValueError, match="planned drone must exist"):
        TurnProjection(
            0,
            TurnPlan((MoveIntent(2, 3),)),
            {1: AtZone(1)},
            {},
        )


def test_rejects_planned_drone_without_connection_usage() -> None:
    """Every planned movement must use exactly one connection."""
    with pytest.raises(ValueError, match="must use a connection"):
        TurnProjection(
            0,
            TurnPlan((MoveIntent(1, 2),)),
            {1: AtZone(2)},
            {},
        )


def test_copies_supplied_mappings() -> None:
    """Later changes to source dictionaries cannot alter a projection."""
    states: dict[int, DroneState] = {1: AtZone(1)}
    users: dict[int, frozenset[int]] = {}
    projection = TurnProjection(0, TurnPlan(()), states, users)

    states[1] = Finished()
    users[1] = frozenset({1})

    assert projection.projected_drone_states[1] == AtZone(1)
    assert projection.connection_users == {}


def test_exposed_mappings_are_read_only() -> None:
    """Callers cannot alter a projection through exposed mappings."""
    projection = make_projection()
    states = cast(
        dict[int, DroneState],
        projection.projected_drone_states,
    )
    users = cast(
        dict[int, frozenset[int]],
        projection.connection_users,
    )

    with pytest.raises(TypeError):
        states[4] = AtZone(1)
    with pytest.raises(TypeError):
        users[4] = frozenset({1})


def test_projection_fields_cannot_be_replaced() -> None:
    """A frozen projection cannot replace any top-level field."""
    projection = make_projection()

    with pytest.raises(FrozenInstanceError):
        setattr(projection, "source_turn", 2)
