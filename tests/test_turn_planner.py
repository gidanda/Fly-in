"""Tests for greedy one-turn movement planning."""

import pytest

from fly_in.connection import Connection
from fly_in.drone import AtZone, Drone, InTransit
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

    assert first_plan.execution_turn == 1
    assert second_plan.execution_turn == 2
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
    assert planner._required_plan == TurnPlan(2, ())

    following_plan = planner.create_plan(next_state)
    assert following_plan.moves == (MoveIntent(2, 2),)
    saved_plan = planner._required_plan
    assert saved_plan is not None
    assert saved_plan.execution_turn == 3
    assert MoveIntent(1, 3) in saved_plan.moves
    arrival_state = next_state.preview_turn(following_plan).next_state
    third_plan = planner.create_plan(arrival_state)
    assert all(move in third_plan.moves for move in saved_plan.moves)
    final_state = arrival_state.preview_turn(third_plan).next_state
    assert final_state.drones[2].state == AtZone(2)


def test_next_plan_includes_supporting_downstream_departure() -> None:
    """A full saved plan keeps the move needed to free an exit destination."""
    zones = [
        make_zone(1, "start", ZoneRole.START),
        make_zone(2, "restricted", zone_type=ZoneType.RESTRICTED),
        make_zone(3, "middle"),
        make_zone(4, "goal", ZoneRole.END),
    ]
    initial = make_state(
        zones,
        [Connection(1, 1, 2, 1), Connection(2, 2, 3, 1),
         Connection(3, 3, 4, 1)],
        3,
    )
    state = SimulationState._from_snapshot(
        initial.drone_map,
        {1: Drone(1, AtZone(3)), 2: Drone(2, AtZone(2)),
         3: Drone(3, InTransit(1, 2, 1))},
        3,
    )
    planner = TurnPlanner(Pathfinder(state.drone_map))

    plan = planner._build_required_next_plan(state)

    assert plan == TurnPlan(4, (MoveIntent(1, 4), MoveIntent(2, 3)))
    assert planner._required_plan is None
    result = state.preview_turn(plan).next_state
    assert result.drones[3].state == AtZone(2)


def test_next_plan_rejects_exit_requiring_restricted_movement() -> None:
    """A future restricted departure cannot support a new arrival promise."""
    initial = make_state(
        [make_zone(1, "start", ZoneRole.START),
         make_zone(2, "first", zone_type=ZoneType.RESTRICTED),
         make_zone(3, "second", zone_type=ZoneType.RESTRICTED),
         make_zone(4, "goal", ZoneRole.END)],
        [Connection(1, 1, 2, 1), Connection(2, 2, 3, 1),
         Connection(3, 3, 4, 1)],
        2,
    )
    state = SimulationState._from_snapshot(
        initial.drone_map,
        {1: Drone(1, AtZone(2)), 2: Drone(2, InTransit(1, 2, 1))},
        2,
    )
    planner = TurnPlanner(Pathfinder(state.drone_map))
    assert planner._build_required_next_plan(state) is None
    assert planner._required_plan is None


def test_planner_rejects_saved_plan_for_another_turn() -> None:
    """A stored promise cannot silently run at a different time."""
    state = make_state(
        [make_zone(1, "start", ZoneRole.START),
         make_zone(2, "goal", ZoneRole.END)],
        [Connection(1, 1, 2, 1)],
        1,
    )
    planner = TurnPlanner(Pathfinder(state.drone_map))
    planner._required_plan = TurnPlan(2, (MoveIntent(1, 2),))
    with pytest.raises(PlanningError, match="different turn"):
        planner.create_plan(state)


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
        TurnPlan(1, (MoveIntent(1, 2),))
    ).next_state

    assert state.all_drones_finished()
    assert planner.create_plan(state).moves == ()
