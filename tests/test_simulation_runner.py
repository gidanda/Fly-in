"""Tests for running a complete simulation."""

import pytest

from fly_in.connection import Connection
from fly_in.drone_map import DroneMap
from fly_in.errors import PlanningError
from fly_in.pathfinder import Pathfinder
from fly_in.scenario import Scenario
from fly_in.simulation_runner import SimulationRunner
from fly_in.simulation_state import SimulationState
from fly_in.turn_formatter import TurnFormatter
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
    """Create a zone with defaults suited to runner tests."""
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


def make_runner(drone_map: DroneMap) -> SimulationRunner:
    """Create a runner configured for one map."""
    return SimulationRunner(
        TurnPlanner(Pathfinder(drone_map)),
        TurnFormatter(),
    )


def test_runs_until_all_drones_finish(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Every planned turn is printed before advancing to the next state."""
    drone_map = DroneMap(
        zones=(
            make_zone(1, "start", ZoneRole.START),
            make_zone(2, "middle"),
            make_zone(3, "goal", ZoneRole.END),
        ),
        connections=(
            Connection(1, 1, 2, 1),
            Connection(2, 2, 3, 1),
        ),
    )
    initial_state = SimulationState(Scenario(drone_map, 2))

    final_state = make_runner(drone_map).run(initial_state)

    assert capsys.readouterr().out == (
        "D1-middle\n"
        "D1-goal D2-middle\n"
        "D2-goal\n"
    )
    assert final_state.all_drones_finished()
    assert final_state.current_turn == 3
    assert initial_state.current_turn == 0


def test_prints_both_restricted_movement_turns(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A restricted journey prints its connection and later its arrival."""
    drone_map = DroneMap(
        zones=(
            make_zone(1, "start", ZoneRole.START),
            make_zone(
                2,
                "restricted_area",
                zone_type=ZoneType.RESTRICTED,
            ),
            make_zone(3, "goal", ZoneRole.END),
        ),
        connections=(
            Connection(1, 1, 2, 1),
            Connection(2, 2, 3, 1),
        ),
    )
    initial_state = SimulationState(Scenario(drone_map, 1))

    final_state = make_runner(drone_map).run(initial_state)

    assert capsys.readouterr().out == (
        "D1-C1\n"
        "D1-restricted_area\n"
        "D1-goal\n"
    )
    assert final_state.all_drones_finished()
    assert final_state.current_turn == 3


def test_completed_initial_state_returns_without_output(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A completed state does not enter the simulation loop."""
    drone_map = DroneMap(
        zones=(
            make_zone(1, "start", ZoneRole.START),
            make_zone(2, "goal", ZoneRole.END),
        ),
        connections=(Connection(1, 1, 2, 1),),
    )
    state = SimulationState(Scenario(drone_map, 1))
    completed_state = state.preview_turn(
        TurnPlan((MoveIntent(1, 2),))
    ).next_state

    final_state = make_runner(drone_map).run(completed_state)

    assert capsys.readouterr().out == ""
    assert final_state is completed_state


def test_propagates_planning_errors() -> None:
    """The runner leaves simulation failures for its caller to handle."""
    drone_map = DroneMap(
        zones=(
            make_zone(1, "start", ZoneRole.START),
            make_zone(2, "goal", ZoneRole.END),
        ),
        connections=(),
    )
    state = SimulationState(Scenario(drone_map, 1))

    with pytest.raises(PlanningError, match="turn 0"):
        make_runner(drone_map).run(state)
