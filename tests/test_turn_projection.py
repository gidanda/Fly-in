"""Tests for immutable one-turn projection results."""

from dataclasses import FrozenInstanceError
from typing import cast

import pytest

from fly_in.connection import Connection
from fly_in.drone import AtZone, Drone
from fly_in.drone_map import DroneMap
from fly_in.scenario import Scenario
from fly_in.simulation_state import SimulationState
from fly_in.turn_plan import MoveIntent, TurnPlan
from fly_in.turn_projection import TurnProjection
from fly_in.zone import Zone, ZoneRole, ZoneType


def make_state() -> SimulationState:
    """Create a state suitable for projection validation tests."""
    zones = [
        Zone(
            1,
            "start",
            0,
            0,
            ZoneRole.START,
            ZoneType.NORMAL,
            None,
            None,
        ),
        Zone(
            2,
            "middle",
            1,
            0,
            ZoneRole.REGULAR,
            ZoneType.NORMAL,
            3,
            None,
        ),
        Zone(
            3,
            "end",
            2,
            0,
            ZoneRole.END,
            ZoneType.NORMAL,
            None,
            None,
        ),
    ]
    connections = [
        Connection(1, 1, 2, 3),
        Connection(2, 2, 3, 3),
    ]
    scenario = Scenario(DroneMap(zones, connections), 3)
    return SimulationState(scenario)


def make_projection() -> TurnProjection:
    """Create a valid projection shared by basic tests."""
    state = make_state()
    return state.preview_turn(TurnPlan((MoveIntent(1, 2),)))


def test_stores_valid_projection_data() -> None:
    """A projection stores its transition data and complete next state."""
    projection = make_projection()

    assert projection.source_turn == 0
    assert projection.plan == TurnPlan((MoveIntent(1, 2),))
    assert projection.next_state.current_turn == 1
    assert projection.next_state.drones[1] == Drone(1, AtZone(2))
    assert projection.connection_users == {1: frozenset({1})}


@pytest.mark.parametrize("source_turn", [-1, True])
def test_rejects_invalid_source_turn(source_turn: int) -> None:
    """The source turn must be a non-negative integer, excluding booleans."""
    projection = make_projection()

    with pytest.raises(ValueError, match="source_turn"):
        TurnProjection(
            source_turn,
            TurnPlan(()),
            projection.next_state,
            {},
        )


def test_rejects_non_turn_plan() -> None:
    """The recorded plan must be a TurnPlan."""
    projection = make_projection()

    with pytest.raises(ValueError, match="plan must be a TurnPlan"):
        TurnProjection(
            0,
            object(),  # type: ignore[arg-type]
            projection.next_state,
            {},
        )


def test_rejects_non_simulation_next_state() -> None:
    """The next state must be a complete SimulationState."""
    with pytest.raises(ValueError, match="next_state"):
        TurnProjection(
            0,
            TurnPlan(()),
            object(),  # type: ignore[arg-type]
            {},
        )


def test_rejects_next_state_at_wrong_turn() -> None:
    """The next state must immediately follow the source turn."""
    with pytest.raises(ValueError, match="exactly one turn"):
        TurnProjection(0, TurnPlan(()), make_state(), {})


@pytest.mark.parametrize("connection_id", [0, -1, True])
def test_rejects_invalid_connection_id(connection_id: int) -> None:
    """Connection identifiers must be positive integers."""
    projection = make_projection()

    with pytest.raises(ValueError, match="connection_id"):
        TurnProjection(
            0,
            TurnPlan(()),
            projection.next_state,
            {connection_id: frozenset({1})},
        )


def test_rejects_mutable_connection_user_set() -> None:
    """Connection users must be supplied as an immutable set."""
    projection = make_projection()
    users = cast(dict[int, frozenset[int]], {1: {1}})

    with pytest.raises(ValueError, match="must be a frozenset"):
        TurnProjection(0, TurnPlan(()), projection.next_state, users)


@pytest.mark.parametrize("drone_id", [0, -1, True])
def test_rejects_invalid_connection_user_id(drone_id: int) -> None:
    """Connection user identifiers must be positive integers."""
    projection = make_projection()

    with pytest.raises(ValueError, match="drone_id"):
        TurnProjection(
            0,
            TurnPlan(()),
            projection.next_state,
            {1: frozenset({drone_id})},
        )


def test_rejects_connection_user_missing_from_next_state() -> None:
    """Every connection user must exist in the next state."""
    projection = make_projection()

    with pytest.raises(ValueError, match="connection user must exist"):
        TurnProjection(
            0,
            TurnPlan(()),
            projection.next_state,
            {1: frozenset({99})},
        )


def test_rejects_drone_using_multiple_connections() -> None:
    """One drone cannot use two connections in the same turn."""
    projection = make_projection()

    with pytest.raises(ValueError, match="multiple connections"):
        TurnProjection(
            0,
            TurnPlan(()),
            projection.next_state,
            {1: frozenset({1}), 2: frozenset({1})},
        )


def test_rejects_planned_drone_missing_from_next_state() -> None:
    """Every planned drone must exist in the next state."""
    projection = make_projection()

    with pytest.raises(ValueError, match="planned drone must exist"):
        TurnProjection(
            0,
            TurnPlan((MoveIntent(99, 2),)),
            projection.next_state,
            {},
        )


def test_rejects_planned_drone_without_connection_usage() -> None:
    """Every planned movement must use exactly one connection."""
    projection = make_projection()

    with pytest.raises(ValueError, match="must use a connection"):
        TurnProjection(
            0,
            TurnPlan((MoveIntent(1, 2),)),
            projection.next_state,
            {},
        )


def test_copies_supplied_connection_mapping() -> None:
    """Later source mapping changes cannot alter a projection."""
    projection = make_projection()
    users: dict[int, frozenset[int]] = {}
    copied_projection = TurnProjection(
        0,
        TurnPlan(()),
        projection.next_state,
        users,
    )

    users[1] = frozenset({1})

    assert copied_projection.connection_users == {}


def test_exposed_connection_mapping_is_read_only() -> None:
    """Callers cannot alter connection usage through a projection."""
    projection = make_projection()
    users = cast(
        dict[int, frozenset[int]],
        projection.connection_users,
    )

    with pytest.raises(TypeError):
        users[4] = frozenset({1})


def test_projection_fields_cannot_be_replaced() -> None:
    """A frozen projection cannot replace any top-level field."""
    projection = make_projection()

    with pytest.raises(FrozenInstanceError):
        setattr(projection, "source_turn", 2)
