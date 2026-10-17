"""Tests for connection behavior."""

import pytest

from fly_in.connection import Connection


def test_connection_recognizes_both_endpoints() -> None:
    """A bidirectional connection contains both endpoint zones."""
    connection = Connection(1, 10, 20, 2)

    assert connection.connects(10)
    assert connection.connects(20)
    assert not connection.connects(30)


def test_other_zone_returns_opposite_endpoint() -> None:
    """The opposite endpoint is returned for either direction."""
    connection = Connection(1, 10, 20, 2)

    assert connection.other_zone(10) == 20
    assert connection.other_zone(20) == 10


def test_other_zone_rejects_unrelated_zone() -> None:
    """An unrelated zone ID is a programming error."""
    connection = Connection(1, 10, 20, 2)

    with pytest.raises(ValueError, match="Zone 30"):
        connection.other_zone(30)
