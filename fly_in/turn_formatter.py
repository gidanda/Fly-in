"""Format the movements produced by one simulation turn."""

from fly_in.drone import AtZone, Drone, Finished, InTransit
from fly_in.drone_map import DroneMap
from fly_in.simulation_state import SimulationState
from fly_in.turn_projection import TurnProjection


class TurnFormatter:
    """Build one output line from the state change of a turn."""

    def format_turn(
        self,
        source_state: SimulationState,
        projection: TurnProjection,
    ) -> str:
        """Return the movements in a turn as one space-separated line."""
        movements: list[str] = []

        for drone_id in sorted(source_state.drones):
            before = source_state.drones[drone_id]
            after = projection.next_state.drones[drone_id]
            movement = self._format_drone_movement(
                before,
                after,
                source_state.drone_map,
            )
            if movement is not None:
                movements.append(movement)

        return " ".join(movements)

    def _format_drone_movement(
        self,
        before: Drone,
        after: Drone,
        drone_map: DroneMap,
    ) -> str | None:
        """Return one drone's movement, or None when it did not move."""
        if before.state == after.state:
            return None

        if isinstance(before.state, AtZone):
            if isinstance(after.state, AtZone):
                return self._format_zone_arrival(
                    after.id,
                    after.state.zone_id,
                    drone_map,
                )
            if isinstance(after.state, Finished):
                return self._format_zone_arrival(
                    after.id,
                    drone_map.end_zone_id,
                    drone_map,
                )
            if isinstance(after.state, InTransit):
                return f"D{after.id}-C{after.state.connection_id}"

        if isinstance(before.state, InTransit):
            if isinstance(after.state, AtZone):
                return self._format_zone_arrival(
                    after.id,
                    after.state.zone_id,
                    drone_map,
                )
            if isinstance(after.state, Finished):
                return self._format_zone_arrival(
                    after.id,
                    before.state.destination_zone_id,
                    drone_map,
                )

        raise ValueError(
            f"Unsupported state transition for drone {before.id}: "
            f"{type(before.state).__name__} -> "
            f"{type(after.state).__name__}"
        )

    def _format_zone_arrival(
        self,
        drone_id: int,
        zone_id: int,
        drone_map: DroneMap,
    ) -> str:
        """Return one drone's arrival using the destination zone name."""
        zone = drone_map.get_zone(zone_id)
        return f"D{drone_id}-{zone.name}"
