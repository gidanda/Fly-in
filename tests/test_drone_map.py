"""Tests for map lookup operations."""

import pytest

from fly_in.connection import Connection
from fly_in.drone_map import DroneMap
from fly_in.errors import MapDefinitionError
from fly_in.zone import Zone, ZoneRole, ZoneType


def make_map() -> DroneMap:
    """Create a small map shared by lookup tests."""
    zones = [
        Zone(
            1,
            "start",
            0,
            0,
            ZoneRole.START,
            ZoneType.NORMAL,
            None,
            "green",
        ),
        Zone(
            2,
            "middle",
            1,
            0,
            ZoneRole.REGULAR,
            ZoneType.RESTRICTED,
            1,
            None,
        ),
        Zone(
            3,
            "goal",
            2,
            0,
            ZoneRole.END,
            ZoneType.NORMAL,
            None,
            "yellow",
        ),
    ]
    connections = [
        Connection(1, 1, 2, 1),
        Connection(2, 2, 3, 2),
    ]
    return DroneMap(zones, connections)


def test_zone_lookups() -> None:
    """Zones can be checked and retrieved by ID or name."""
    drone_map = make_map()

    assert drone_map.has_zone(2)
    assert not drone_map.has_zone(99)
    assert drone_map.get_zone(2).name == "middle"
    assert drone_map.get_zone_id_by_name("goal") == 3
    assert drone_map.get_zone_id_by_name("missing") is None
    assert drone_map.start_zone_id == 1
    assert drone_map.end_zone_id == 3


def test_connection_lookups() -> None:
    """Connections can be checked and retrieved in either direction."""
    drone_map = make_map()

    assert drone_map.has_connection(2)
    assert not drone_map.has_connection(99)
    assert drone_map.get_connection(2).max_capacity == 2
    assert drone_map.get_connection_between(1, 2) is not None
    assert drone_map.get_connection_between(2, 1) is not None
    assert drone_map.get_connection_between(1, 3) is None


def test_adjacency_lookups() -> None:
    """Incident connections and neighboring zones are available."""
    drone_map = make_map()

    assert [
        connection.id
        for connection in drone_map.get_connections_from(2)
    ] == [1, 2]
    assert drone_map.get_neighbor_ids(2) == [1, 3]


def test_unknown_ids_raise_clear_errors() -> None:
    """Lookup operations reject unknown identifiers."""
    drone_map = make_map()

    with pytest.raises(KeyError, match="Unknown zone ID: 99"):
        drone_map.get_zone(99)
    with pytest.raises(KeyError, match="Unknown connection ID: 99"):
        drone_map.get_connection(99)


def test_duplicate_connection_pair_is_rejected() -> None:
    """Connections are unique regardless of endpoint order."""
    original = make_map()
    zones = [original.get_zone(zone_id) for zone_id in (1, 2, 3)]
    connections = [
        Connection(1, 1, 2, 1),
        Connection(2, 2, 1, 1),
    ]

    with pytest.raises(MapDefinitionError, match="Duplicate connection"):
        DroneMap(zones, connections)
