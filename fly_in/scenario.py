"""Scenario definition for one Fly-in simulation."""

from dataclasses import dataclass

from fly_in.drone_map import DroneMap


@dataclass(frozen=True)
class Scenario:
    """Combine a static map with the number of drones to simulate."""

    drone_map: DroneMap
    drone_count: int

    def __post_init__(self) -> None:
        """Ensure every scenario contains at least one drone."""
        if self.drone_count < 1:
            raise ValueError("drone_count must be at least 1")
