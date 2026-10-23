"""Dynamic state shared by one Fly-in simulation."""

from collections.abc import Mapping
from types import MappingProxyType

from fly_in.drone import AtZone, Drone, Finished, InTransit
from fly_in.drone_map import DroneMap
from fly_in.scenario import Scenario


class SimulationState:
    """Own every drone and expose facts about the current simulation."""

    def __init__(self, scenario: Scenario) -> None:
        """Place all scenario drones at the start zone on turn zero."""
        self._drone_map = scenario.drone_map
        self._drones = {
            drone_id: Drone(
                id=drone_id,
                state=AtZone(self._drone_map.start_zone_id),
            )
            for drone_id in range(1, scenario.drone_count + 1)
        }
        self._drones_view = MappingProxyType(self._drones)
        self._current_turn = 0

    @property
    def drone_map(self) -> DroneMap:
        """Return the static map used by this simulation."""
        return self._drone_map

    @property
    def drones(self) -> Mapping[int, Drone]:
        """Return a read-only view of drones indexed by ID."""
        return self._drones_view

    @property
    def current_turn(self) -> int:
        """Return the current turn number."""
        return self._current_turn

    def get_zone_occupancy(self, zone_id: int) -> int:
        """Return the number of drones currently occupying a zone."""
        self._drone_map.get_zone(zone_id)
        return sum(
            isinstance(drone.state, AtZone)
            and drone.state.zone_id == zone_id
            for drone in self._drones.values()
        )

    def get_connection_occupancy(self, connection_id: int) -> int:
        """Return the number of drones currently using a connection."""
        self._drone_map.get_connection(connection_id)
        return sum(
            isinstance(drone.state, InTransit)
            and drone.state.connection_id == connection_id
            for drone in self._drones.values()
        )

    def all_drones_finished(self) -> bool:
        """Return whether every drone has reached the end zone."""
        return all(
            isinstance(drone.state, Finished)
            for drone in self._drones.values()
        )
