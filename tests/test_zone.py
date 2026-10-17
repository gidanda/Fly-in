"""Tests for zone behavior."""

import pytest

from fly_in.zone import Zone, ZoneRole, ZoneType


@pytest.mark.parametrize(
    ("zone_type", "expected_accessible", "expected_cost"),
    [
        (ZoneType.NORMAL, True, 1),
        (ZoneType.PRIORITY, True, 1),
        (ZoneType.RESTRICTED, True, 2),
        (ZoneType.BLOCKED, False, None),
    ],
)
def test_zone_movement_behavior(
    zone_type: ZoneType,
    expected_accessible: bool,
    expected_cost: int | None,
) -> None:
    """Each zone type exposes the expected movement behavior."""
    zone = Zone(
        id=1,
        name="zone",
        x=0,
        y=0,
        role=ZoneRole.REGULAR,
        zone_type=zone_type,
        max_drones=1,
        color=None,
    )

    assert zone.is_accessible() is expected_accessible
    assert zone.movement_cost() == expected_cost


def test_unlimited_capacity_uses_none() -> None:
    """None represents a zone without an occupancy limit."""
    zone = Zone(
        id=1,
        name="start",
        x=0,
        y=0,
        role=ZoneRole.START,
        zone_type=ZoneType.NORMAL,
        max_drones=None,
        color="green",
    )

    assert zone.has_unlimited_capacity()
