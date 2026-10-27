"""Tests for aggregate simulation state and derived facts."""

from typing import cast

import pytest

from fly_in.connection import Connection
from fly_in.drone import AtZone, Drone, Finished, InTransit
from fly_in.drone_map import DroneMap
from fly_in.errors import TurnValidationError
from fly_in.scenario import Scenario
from fly_in.simulation_state import SimulationState
from fly_in.turn_plan import MoveIntent, TurnPlan
from fly_in.zone import Zone, ZoneRole, ZoneType


def make_scenario(drone_count: int = 3) -> Scenario:
    """Create a small scenario for dynamic-state tests."""
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
            ZoneType.RESTRICTED,
            2,
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
        Connection(1, 1, 2, 2),
        Connection(2, 2, 3, 1),
    ]
    return Scenario(DroneMap(zones, connections), drone_count)


def make_preview_scenario(drone_count: int = 3) -> Scenario:
    """Create a map covering preview movement and validation rules."""
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
            "normal",
            1,
            0,
            ZoneRole.REGULAR,
            ZoneType.NORMAL,
            1,
            None,
        ),
        Zone(
            3,
            "restricted",
            1,
            1,
            ZoneRole.REGULAR,
            ZoneType.RESTRICTED,
            2,
            None,
        ),
        Zone(
            4,
            "end",
            2,
            0,
            ZoneRole.END,
            ZoneType.NORMAL,
            None,
            None,
        ),
        Zone(
            5,
            "blocked",
            0,
            1,
            ZoneRole.REGULAR,
            ZoneType.BLOCKED,
            1,
            None,
        ),
        Zone(
            6,
            "isolated",
            3,
            0,
            ZoneRole.REGULAR,
            ZoneType.NORMAL,
            1,
            None,
        ),
    ]
    connections = [
        Connection(1, 1, 2, 2),
        Connection(2, 1, 3, 2),
        Connection(3, 2, 4, 2),
        Connection(4, 3, 4, 1),
        Connection(5, 1, 5, 1),
    ]
    return Scenario(DroneMap(zones, connections), drone_count)


def replace_drone_for_test(
    simulation: SimulationState,
    drone: Drone,
) -> None:
    """Install a snapshot to exercise aggregate behavior not yet public."""
    simulation._drones[drone.id] = drone


def test_initializes_every_drone_at_start_on_turn_zero() -> None:
    """A scenario creates sequential drones at its start zone."""
    scenario = make_scenario()

    simulation = SimulationState(scenario)

    assert simulation.drone_map is scenario.drone_map
    assert list(simulation.drones) == [1, 2, 3]
    assert [drone.id for drone in simulation.drones.values()] == [1, 2, 3]
    assert simulation.get_zone_occupancy(1) == 3
    assert simulation.current_turn == 0


def test_drones_mapping_is_read_only() -> None:
    """Callers cannot add or replace entries in the drone index."""
    simulation = SimulationState(make_scenario())
    drones = cast(dict[int, Drone], simulation.drones)

    with pytest.raises(TypeError):
        drones[4] = Drone(4, Finished())


def test_occupancy_is_derived_from_current_drone_states() -> None:
    """Zone and connection occupancy reflect current drone states."""
    simulation = SimulationState(make_scenario())

    replace_drone_for_test(
        simulation,
        simulation.drones[1].start_move(1, 2, 2),
    )
    replace_drone_for_test(
        simulation,
        simulation.drones[2].start_move(1, 2, 2),
    )

    assert simulation.get_zone_occupancy(1) == 1
    assert simulation.get_zone_occupancy(2) == 0
    assert simulation.get_connection_occupancy(1) == 2
    assert simulation.get_connection_occupancy(2) == 0


def test_occupancy_rejects_unknown_map_ids() -> None:
    """Occupancy queries reject zones and connections outside the map."""
    simulation = SimulationState(make_scenario())

    with pytest.raises(KeyError, match="Unknown zone ID: 99"):
        simulation.get_zone_occupancy(99)
    with pytest.raises(KeyError, match="Unknown connection ID: 99"):
        simulation.get_connection_occupancy(99)


def test_all_drones_finished_reflects_drone_states() -> None:
    """Completion is true only after every drone reaches the goal."""
    simulation = SimulationState(make_scenario(drone_count=2))

    assert not simulation.all_drones_finished()
    for drone in tuple(simulation.drones.values()):
        finished_drone = drone.start_move(1, 3, 1).advance_one_turn(
            destination_is_goal=True
        )
        replace_drone_for_test(simulation, finished_drone)

    assert simulation.all_drones_finished()


def test_preview_empty_plan_keeps_zone_drones_in_place() -> None:
    """An empty plan is valid and leaves zone-bound drones waiting."""
    simulation = SimulationState(make_preview_scenario())

    projection = simulation.preview_turn(TurnPlan(()))

    assert projection.source_turn == 0
    assert projection.next_state.drones == {
        1: Drone(1, AtZone(1)),
        2: Drone(2, AtZone(1)),
        3: Drone(3, AtZone(1)),
    }
    assert projection.connection_users == {}
    assert simulation.current_turn == 0
    assert projection.next_state.current_turn == 1
    assert projection.next_state.drone_map is simulation.drone_map
    assert all(
        drone.state == AtZone(1)
        for drone in simulation.drones.values()
    )


def test_preview_treats_start_zone_capacity_as_unlimited() -> None:
    """Start capacity metadata cannot invalidate the initial occupancy."""
    zones = [
        Zone(
            1,
            "start",
            0,
            0,
            ZoneRole.START,
            ZoneType.NORMAL,
            1,
            None,
        ),
        Zone(
            2,
            "end",
            1,
            0,
            ZoneRole.END,
            ZoneType.NORMAL,
            1,
            None,
        ),
    ]
    scenario = Scenario(
        DroneMap(zones, [Connection(1, 1, 2, 1)]),
        drone_count=3,
    )

    projection = SimulationState(scenario).preview_turn(TurnPlan(()))

    assert projection.next_state.drones == {
        1: Drone(1, AtZone(1)),
        2: Drone(2, AtZone(1)),
        3: Drone(3, AtZone(1)),
    }


def test_preview_projects_one_turn_move_without_mutating_drone() -> None:
    """A cost-one move arrives while the real drone stays unchanged."""
    simulation = SimulationState(make_preview_scenario())
    plan = TurnPlan((MoveIntent(1, 2),))

    projection = simulation.preview_turn(plan)

    assert projection.next_state.drones[1] == Drone(1, AtZone(2))
    assert projection.connection_users == {1: frozenset({1})}
    assert simulation.drones[1].state == AtZone(1)


def test_next_state_can_preview_following_turn() -> None:
    """A projected next state can become the source of another turn."""
    initial_state = SimulationState(make_preview_scenario())

    first_projection = initial_state.preview_turn(
        TurnPlan((MoveIntent(1, 2),))
    )
    second_projection = first_projection.next_state.preview_turn(
        TurnPlan((MoveIntent(1, 4),))
    )

    assert initial_state.current_turn == 0
    assert initial_state.drones[1] == Drone(1, AtZone(1))
    assert first_projection.next_state.current_turn == 1
    assert first_projection.next_state.drones[1] == Drone(1, AtZone(2))
    assert second_projection.next_state.current_turn == 2
    assert second_projection.next_state.drones[1] == Drone(1, Finished())


def test_preview_projects_two_turn_move_onto_connection() -> None:
    """A new restricted move ends its first turn in transit."""
    simulation = SimulationState(make_preview_scenario())
    plan = TurnPlan((MoveIntent(1, 3),))

    projection = simulation.preview_turn(plan)

    assert projection.next_state.drones[1] == Drone(
        1,
        InTransit(2, 3, 1),
    )
    assert projection.connection_users == {2: frozenset({1})}


def test_preview_advances_existing_transit_and_records_usage() -> None:
    """An existing transit progresses and still uses its connection."""
    simulation = SimulationState(make_preview_scenario())
    replace_drone_for_test(
        simulation,
        simulation.drones[1].start_move(2, 3, 2),
    )

    projection = simulation.preview_turn(TurnPlan(()))

    assert projection.next_state.drones[1] == Drone(
        1,
        InTransit(2, 3, 1),
    )
    assert projection.connection_users == {2: frozenset({1})}
    assert simulation.drones[1].state == InTransit(2, 3, 2)


def test_preview_arrives_at_goal_as_finished() -> None:
    """A cost-one move to the end projects a finished drone."""
    simulation = SimulationState(make_preview_scenario())
    at_middle = simulation.drones[1].start_move(
        1,
        2,
        1,
    ).advance_one_turn(destination_is_goal=False)
    replace_drone_for_test(simulation, at_middle)

    projection = simulation.preview_turn(
        TurnPlan((MoveIntent(1, 4),))
    )

    assert projection.next_state.drones[1] == Drone(1, Finished())
    assert projection.connection_users == {3: frozenset({1})}


@pytest.mark.parametrize(
    ("plan", "message"),
    [
        (TurnPlan((MoveIntent(99, 2),)), "Unknown drone ID"),
        (TurnPlan((MoveIntent(1, 99),)), "Unknown destination zone"),
        (TurnPlan((MoveIntent(1, 1),)), "already at zone"),
        (TurnPlan((MoveIntent(1, 6),)), "not connected"),
        (TurnPlan((MoveIntent(1, 5),)), "blocked zone"),
    ],
)
def test_preview_rejects_invalid_individual_move(
    plan: TurnPlan,
    message: str,
) -> None:
    """A move must match an existing drone, destination, and connection."""
    simulation = SimulationState(make_preview_scenario())

    with pytest.raises(TurnValidationError, match=message):
        simulation.preview_turn(plan)


def test_preview_rejects_move_for_in_transit_drone() -> None:
    """A drone already on a connection cannot start another move."""
    simulation = SimulationState(make_preview_scenario())
    replace_drone_for_test(
        simulation,
        simulation.drones[1].start_move(2, 3, 2),
    )

    with pytest.raises(TurnValidationError, match="not at a zone"):
        simulation.preview_turn(TurnPlan((MoveIntent(1, 2),)))


def test_preview_rejects_connection_capacity_excess() -> None:
    """Current and newly entering users share the connection capacity."""
    simulation = SimulationState(make_preview_scenario())
    replace_drone_for_test(
        simulation,
        simulation.drones[1].start_move(1, 2, 1),
    )
    plan = TurnPlan((MoveIntent(2, 2), MoveIntent(3, 2)))

    with pytest.raises(TurnValidationError, match="Connection 1 capacity"):
        simulation.preview_turn(plan)

    assert simulation.drones[1].state == InTransit(1, 2, 1)
    assert simulation.drones[2].state == AtZone(1)
    assert simulation.drones[3].state == AtZone(1)


def test_preview_rejects_projected_zone_capacity_excess() -> None:
    """Arriving and newly moving drones share destination capacity."""
    simulation = SimulationState(make_preview_scenario(drone_count=2))
    replace_drone_for_test(
        simulation,
        simulation.drones[1].start_move(1, 2, 1),
    )
    plan = TurnPlan((MoveIntent(2, 2),))

    with pytest.raises(TurnValidationError, match="Zone 2 capacity"):
        simulation.preview_turn(plan)


def test_preview_counts_same_turn_departure_before_zone_capacity() -> None:
    """A departing drone frees its zone for another arrival that turn."""
    simulation = SimulationState(make_preview_scenario(drone_count=2))
    at_middle = simulation.drones[1].start_move(
        1,
        2,
        1,
    ).advance_one_turn(destination_is_goal=False)
    replace_drone_for_test(simulation, at_middle)
    plan = TurnPlan((MoveIntent(1, 4), MoveIntent(2, 2)))

    projection = simulation.preview_turn(plan)

    assert projection.next_state.drones[1] == Drone(1, Finished())
    assert projection.next_state.drones[2] == Drone(2, AtZone(2))
    assert projection.connection_users == {
        3: frozenset({1}),
        1: frozenset({2}),
    }
