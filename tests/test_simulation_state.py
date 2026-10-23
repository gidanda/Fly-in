"""Tests for aggregate simulation state and derived facts."""

from typing import cast

import pytest

from fly_in.connection import Connection
from fly_in.drone import Drone, Finished
from fly_in.drone_map import DroneMap
from fly_in.scenario import Scenario
from fly_in.simulation_state import SimulationState
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

    simulation.drones[1].start_move(1, 2, 2)
    simulation.drones[2].start_move(1, 2, 2)

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
    for drone in simulation.drones.values():
        drone.start_move(1, 3, 1)
        drone.advance_one_turn(destination_is_goal=True)

    assert simulation.all_drones_finished()
