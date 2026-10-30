"""Scenario definition for one Fly-in simulation."""

from dataclasses import dataclass

from fly_in.drone_map import DroneMap


@dataclass(frozen=True)
class Scenario:
    """Store a map and drone count validated by the caller."""

    drone_map: DroneMap
    drone_count: int
