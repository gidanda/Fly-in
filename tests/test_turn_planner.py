"""Tests for greedy one-turn movement planning."""

import pytest

from fly_in.connection import Connection
from fly_in.drone import AtZone, InTransit
from fly_in.drone_map import DroneMap
from fly_in.errors import PlanningError
from fly_in.pathfinder import Pathfinder
from fly_in.scenario import Scenario
from fly_in.simulation_state import SimulationState
from fly_in.turn_plan import MoveIntent, TurnPlan
from fly_in.turn_planner import TurnPlanner
from fly_in.zone import Zone, ZoneRole, ZoneType


def make_zone(
    zone_id: int,
    name: str,
    role: ZoneRole = ZoneRole.REGULAR,
    zone_type: ZoneType = ZoneType.NORMAL,
    max_drones: int | None = 1,
) -> Zone:
    """Create a zone with defaults suited to planning tests."""
    if role is not ZoneRole.REGULAR:
        max_drones = None
    return Zone(
        zone_id,
        name,
        zone_id,
        0,
        role,
        zone_type,
        max_drones,
        None,
    )


def make_state(
    zones: list[Zone],
    connections: list[Connection],
    drone_count: int,
) -> SimulationState:
    """Create a fresh simulation for a planning test."""
    drone_map = DroneMap(zones, connections)
    return SimulationState(Scenario(drone_map, drone_count))


def test_planner_moves_downstream_drones_first() -> None:
    """A downstream departure frees capacity for an upstream arrival."""
    zones = [
        make_zone(1, "start", ZoneRole.START),
        make_zone(2, "middle"),
        make_zone(3, "goal", ZoneRole.END),
    ]
    connections = [
        Connection(1, 1, 2, 1),
        Connection(2, 2, 3, 1),
    ]
    state = make_state(zones, connections, 2)
    planner = TurnPlanner(Pathfinder(state.drone_map))

    first_plan = planner.create_plan(state)
    state = state.preview_turn(first_plan).next_state
    second_plan = planner.create_plan(state)

    assert first_plan.moves == (MoveIntent(1, 2),)
    assert second_plan.moves == (
        MoveIntent(1, 3),
        MoveIntent(2, 2),
    )


def test_planner_uses_priority_then_an_alternative_route() -> None:
    """Priority wins a tie, while capacity sends another drone elsewhere."""
    zones = [
        make_zone(1, "start", ZoneRole.START),
        make_zone(2, "priority", zone_type=ZoneType.PRIORITY),
        make_zone(3, "normal"),
        make_zone(4, "goal", ZoneRole.END),
    ]
    connections = [
        Connection(1, 1, 2, 1),
        Connection(2, 2, 4, 1),
        Connection(3, 1, 3, 1),
        Connection(4, 3, 4, 1),
    ]
    state = make_state(zones, connections, 2)
    planner = TurnPlanner(Pathfinder(state.drone_map))

    plan = planner.create_plan(state)

    assert plan.moves == (
        MoveIntent(1, 2),
        MoveIntent(2, 3),
    )


def test_planner_reserves_capacity_for_restricted_arrivals() -> None:
    """Only one drone enters transit toward a one-capacity zone."""
    zones = [
        make_zone(1, "start", ZoneRole.START),
        make_zone(
            2,
            "restricted",
            zone_type=ZoneType.RESTRICTED,
        ),
        make_zone(3, "goal", ZoneRole.END),
    ]
    connections = [
        Connection(1, 1, 2, 2),
        Connection(2, 2, 3, 1),
    ]
    state = make_state(zones, connections, 2)
    planner = TurnPlanner(Pathfinder(state.drone_map))

    first_plan = planner.create_plan(state)
    next_state = state.preview_turn(first_plan).next_state

    assert first_plan.moves == (MoveIntent(1, 2),)
    assert isinstance(next_state.drones[1].state, InTransit)
    assert isinstance(next_state.drones[2].state, AtZone)

    waiting_plan = planner.create_plan(next_state)
    assert waiting_plan.moves == ()


def test_planner_raises_when_no_progress_is_possible() -> None:
    """An unfinished state without movement or transit is a deadlock."""
    zones = [
        make_zone(1, "start", ZoneRole.START),
        make_zone(2, "goal", ZoneRole.END),
    ]
    state = make_state(zones, [], 1)
    planner = TurnPlanner(Pathfinder(state.drone_map))

    with pytest.raises(
        PlanningError,
        match="No progressing turn plan exists at turn 0",
    ):
        planner.create_plan(state)


def test_planner_rejects_a_pathfinder_for_another_map() -> None:
    """Static costs from another map cannot plan this state."""
    zones = [
        make_zone(1, "start", ZoneRole.START),
        make_zone(2, "goal", ZoneRole.END),
    ]
    connections = [Connection(1, 1, 2, 1)]
    state = make_state(zones, connections, 1)
    other_map = DroneMap(zones, connections)
    planner = TurnPlanner(Pathfinder(other_map))

    with pytest.raises(ValueError, match="different maps"):
        planner.create_plan(state)


def test_planner_returns_an_empty_plan_when_every_drone_finished() -> None:
    """Calling the planner after completion remains harmless."""
    zones = [
        make_zone(1, "start", ZoneRole.START),
        make_zone(2, "goal", ZoneRole.END),
    ]
    connections = [Connection(1, 1, 2, 1)]
    state = make_state(zones, connections, 1)
    planner = TurnPlanner(Pathfinder(state.drone_map))
    state = state.preview_turn(
        TurnPlan((MoveIntent(1, 2),))
    ).next_state

    assert state.all_drones_finished()
    assert planner.create_plan(state).moves == ()
