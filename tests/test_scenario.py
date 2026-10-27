"""Tests for scenario data and validation."""

from dataclasses import FrozenInstanceError

import pytest

from fly_in.connection import Connection
from fly_in.drone_map import DroneMap
from fly_in.scenario import Scenario
from fly_in.zone import Zone, ZoneRole, ZoneType


def make_map() -> DroneMap:
    """Create the smallest valid map for scenario tests."""
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
            "end",
            1,
            0,
            ZoneRole.END,
            ZoneType.NORMAL,
            None,
            None,
        ),
    ]
    return DroneMap(zones, [Connection(1, 1, 2, 1)])


def test_scenario_stores_map_and_drone_count() -> None:
    """A scenario keeps the supplied map and positive drone count."""
    drone_map = make_map()

    scenario = Scenario(drone_map, 3)

    assert scenario.drone_map is drone_map
    assert scenario.drone_count == 3


@pytest.mark.parametrize("drone_count", [0, -1, True, 1.5])
def test_scenario_rejects_invalid_drone_count(
    drone_count: object,
) -> None:
    """A scenario requires a positive integer count, excluding booleans."""
    with pytest.raises(ValueError, match="positive integer"):
        Scenario(make_map(), drone_count)  # type: ignore[arg-type]


def test_scenario_is_immutable() -> None:
    """Scenario fields cannot be replaced after construction."""
    scenario = Scenario(make_map(), 3)

    with pytest.raises(FrozenInstanceError):
        setattr(scenario, "drone_count", 4)
