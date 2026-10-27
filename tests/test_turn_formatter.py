"""Tests for formatting one turn of drone movements."""

import pytest

from fly_in.connection import Connection
from fly_in.drone import AtZone, Drone, Finished
from fly_in.drone_map import DroneMap
from fly_in.scenario import Scenario
from fly_in.simulation_state import SimulationState
from fly_in.turn_formatter import TurnFormatter
from fly_in.turn_plan import MoveIntent, TurnPlan
from fly_in.turn_projection import TurnProjection
from fly_in.zone import Zone, ZoneRole, ZoneType


def make_map() -> DroneMap:
    """Return a map containing normal and restricted movements."""
    return DroneMap(
        zones=(
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
                "restricted_area",
                2,
                0,
                ZoneRole.REGULAR,
                ZoneType.RESTRICTED,
                3,
                None,
            ),
            Zone(
                4,
                "goal",
                3,
                0,
                ZoneRole.END,
                ZoneType.NORMAL,
                None,
                None,
            ),
        ),
        connections=(
            Connection(1, 1, 2, 3),
            Connection(2, 2, 3, 3),
            Connection(3, 3, 4, 3),
        ),
    )


def test_formats_normal_moves_in_drone_id_order() -> None:
    """Normal arrivals use zone names and waiting drones are omitted."""
    state = SimulationState(Scenario(make_map(), 3))
    projection = state.preview_turn(
        TurnPlan((MoveIntent(2, 2), MoveIntent(1, 2)))
    )

    result = TurnFormatter().format_turn(state, projection)

    assert result == "D1-middle D2-middle"


def test_formats_restricted_departure_with_connection_id() -> None:
    """The first restricted turn displays the occupied connection."""
    state = SimulationState(Scenario(make_map(), 1))
    state = state.preview_turn(
        TurnPlan((MoveIntent(1, 2),))
    ).next_state
    projection = state.preview_turn(
        TurnPlan((MoveIntent(1, 3),))
    )

    result = TurnFormatter().format_turn(state, projection)

    assert result == "D1-C2"


def test_formats_restricted_arrival_with_zone_name() -> None:
    """The second restricted turn displays the destination zone."""
    state = SimulationState(Scenario(make_map(), 1))
    state = state.preview_turn(
        TurnPlan((MoveIntent(1, 2),))
    ).next_state
    state = state.preview_turn(
        TurnPlan((MoveIntent(1, 3),))
    ).next_state
    projection = state.preview_turn(TurnPlan(()))

    result = TurnFormatter().format_turn(state, projection)

    assert result == "D1-restricted_area"


def test_formats_goal_arrival_with_goal_zone_name() -> None:
    """A Finished state is displayed as an arrival at the goal zone."""
    state = SimulationState(Scenario(make_map(), 1))
    state = state.preview_turn(
        TurnPlan((MoveIntent(1, 2),))
    ).next_state
    state = state.preview_turn(
        TurnPlan((MoveIntent(1, 3),))
    ).next_state
    state = state.preview_turn(TurnPlan(())).next_state
    projection = state.preview_turn(
        TurnPlan((MoveIntent(1, 4),))
    )

    result = TurnFormatter().format_turn(state, projection)

    assert result == "D1-goal"


def test_returns_empty_string_when_no_drone_moves() -> None:
    """A turn containing only waiting drones has no movement text."""
    state = SimulationState(Scenario(make_map(), 1))
    projection = state.preview_turn(TurnPlan(()))

    result = TurnFormatter().format_turn(state, projection)

    assert result == ""


def test_rejects_an_unsupported_state_transition() -> None:
    """An impossible transition is not silently represented as movement."""
    drone_map = make_map()
    source_state = SimulationState._from_snapshot(
        drone_map,
        {1: Drone(1, Finished())},
        4,
    )
    next_state = SimulationState._from_snapshot(
        drone_map,
        {1: Drone(1, AtZone(2))},
        5,
    )
    projection = TurnProjection(4, TurnPlan(()), next_state, {})

    with pytest.raises(ValueError, match="Finished -> AtZone"):
        TurnFormatter().format_turn(source_state, projection)
