"""Tests for static shortest-cost map analysis."""

import pytest

from fly_in.connection import Connection
from fly_in.drone_map import DroneMap
from fly_in.pathfinder import Pathfinder
from fly_in.zone import Zone, ZoneRole, ZoneType


def make_zone(
    zone_id: int,
    name: str,
    role: ZoneRole = ZoneRole.REGULAR,
    zone_type: ZoneType = ZoneType.NORMAL,
) -> Zone:
    """Create a zone with defaults suited to pathfinder tests."""
    max_drones = None if role is not ZoneRole.REGULAR else 1
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


def test_goal_costs_use_destination_zone_movement_costs() -> None:
    """Reverse search charges the cost of the forward destination."""
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
        Connection(1, 1, 2, 1),
        Connection(2, 2, 3, 1),
    ]

    pathfinder = Pathfinder(DroneMap(zones, connections))

    assert pathfinder.get_goal_cost(1) == 3
    assert pathfinder.get_goal_cost(2) == 1
    assert pathfinder.get_goal_cost(3) == 0


def test_pathfinder_exposes_the_analyzed_map() -> None:
    """The exact analyzed map is available for consistency checks."""
    zones = [
        make_zone(1, "start", ZoneRole.START),
        make_zone(2, "goal", ZoneRole.END),
    ]
    drone_map = DroneMap(zones, [Connection(1, 1, 2, 1)])

    pathfinder = Pathfinder(drone_map)

    assert pathfinder.drone_map is drone_map


def test_shortest_cost_is_selected_from_multiple_routes() -> None:
    """The cheaper complete route wins regardless of definition order."""
    zones = [
        make_zone(1, "start", ZoneRole.START),
        make_zone(
            2,
            "slow",
            zone_type=ZoneType.RESTRICTED,
        ),
        make_zone(3, "fast"),
        make_zone(4, "goal", ZoneRole.END),
    ]
    connections = [
        Connection(1, 1, 2, 1),
        Connection(2, 2, 4, 1),
        Connection(3, 1, 3, 1),
        Connection(4, 3, 4, 1),
    ]

    pathfinder = Pathfinder(DroneMap(zones, connections))

    assert pathfinder.get_goal_cost(1) == 2
    assert pathfinder.get_goal_cost(2) == 1
    assert pathfinder.get_goal_cost(3) == 1


def test_priority_does_not_change_static_movement_cost() -> None:
    """Priority and normal zones both retain their one-turn cost."""
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

    pathfinder = Pathfinder(DroneMap(zones, connections))

    assert pathfinder.get_goal_cost(2) == 1
    assert pathfinder.get_goal_cost(3) == 1


def test_blocked_and_disconnected_zones_are_unreachable() -> None:
    """Blocked zones cannot form paths and disconnected zones return None."""
    zones = [
        make_zone(1, "start", ZoneRole.START),
        make_zone(2, "blocked", zone_type=ZoneType.BLOCKED),
        make_zone(3, "disconnected"),
        make_zone(4, "goal", ZoneRole.END),
    ]
    connections = [
        Connection(1, 1, 2, 1),
        Connection(2, 2, 4, 1),
    ]

    pathfinder = Pathfinder(DroneMap(zones, connections))

    assert pathfinder.get_goal_cost(1) is None
    assert pathfinder.get_goal_cost(2) is None
    assert pathfinder.get_goal_cost(3) is None
    assert pathfinder.get_goal_cost(4) == 0


def test_unknown_zone_id_raises_key_error() -> None:
    """A missing zone ID is distinguished from an unreachable zone."""
    zones = [
        make_zone(1, "start", ZoneRole.START),
        make_zone(2, "goal", ZoneRole.END),
    ]
    pathfinder = Pathfinder(
        DroneMap(zones, [Connection(1, 1, 2, 1)])
    )

    with pytest.raises(KeyError, match="Unknown zone ID: 99"):
        pathfinder.get_goal_cost(99)
