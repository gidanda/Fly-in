"""Tests for parsing map files into scenarios."""

from pathlib import Path

import pytest

from fly_in.errors import MapParseError
from fly_in.map_parser import MapParser
from fly_in.zone import ZoneRole, ZoneType


def write_map(tmp_path: Path, content: str) -> Path:
    """Write one temporary map and return its path."""
    map_path = tmp_path / "map.txt"
    map_path.write_text(content, encoding="utf-8")
    return map_path


def test_all_distributed_maps_parse() -> None:
    """Every distributed map follows the supported format."""
    parser = MapParser()
    map_paths = sorted(Path("maps").rglob("*.txt"))

    assert len(map_paths) == 10
    for map_path in map_paths:
        scenario = parser.parse_file(map_path)
        assert scenario.drone_count > 0


def test_parser_builds_expected_scenario(tmp_path: Path) -> None:
    """Definitions, defaults, and metadata become domain objects."""
    map_path = write_map(
        tmp_path,
        "# example\n"
        "nb_drones: 3\n"
        "\n"
        "start_hub: start 0 0 [color=green max_drones=invalid]\n"
        "hub: middle 1 -2 [zone=restricted color=light-green "
        "max_drones=2]\n"
        "connection: start-middle [max_link_capacity=3]\n"
        "end_hub: goal 2 0\n"
        "connection: middle-goal\n",
    )

    scenario = MapParser().parse_file(map_path)
    drone_map = scenario.drone_map
    middle = drone_map.get_zone(2)

    assert scenario.drone_count == 3
    assert drone_map.start_zone_id == 1
    assert drone_map.end_zone_id == 3
    assert middle.name == "middle"
    assert middle.role is ZoneRole.REGULAR
    assert middle.zone_type is ZoneType.RESTRICTED
    assert middle.max_drones == 2
    assert middle.color == "light-green"
    assert drone_map.get_connection(1).max_capacity == 3
    assert drone_map.get_connection(2).max_capacity == 1


@pytest.mark.parametrize(
    ("content", "message", "line_number"),
    [
        (
            "hub: a 0 0\n",
            "first definition",
            1,
        ),
        (
            "nb_drones: 0\n",
            "positive integer",
            1,
        ),
        (
            "nb_drones: two\n",
            "must be an integer",
            1,
        ),
        (
            "nb_drones: 1\nnb_drones: 2\n",
            "exactly once",
            2,
        ),
        (
            "nb_drones: 1\nstart_hub: same 0 0\n"
            "end_hub: same 1 0\n",
            "Duplicate zone name",
            3,
        ),
        (
            "nb_drones: 1\nstart_hub: a 0 0\n"
            "start_hub: b 1 0\nend_hub: c 2 0\n",
            "start_hub must be defined exactly once",
            3,
        ),
        (
            "nb_drones: 1\nstart_hub: a 0 0\n"
            "end_hub: b 1 0\nconnection: a-c\n",
            "before it is defined",
            4,
        ),
        (
            "nb_drones: 1\nstart_hub: a 0 0\n"
            "end_hub: b 1 0\nconnection: a-a\n",
            "endpoints must be different",
            4,
        ),
        (
            "nb_drones: 1\nstart_hub: a 0 0\n"
            "end_hub: b 1 0\nconnection: a-b\n"
            "connection: b-a\n",
            "Duplicate connection",
            5,
        ),
        (
            "nb_drones: 1\nstart_hub: a 0 0 [zone=unknown]\n"
            "end_hub: b 1 0\n",
            "Invalid zone type",
            2,
        ),
        (
            "nb_drones: 1\nstart_hub: a 0 0 [color=red color=blue]\n"
            "end_hub: b 1 0\n",
            "Duplicate metadata key",
            2,
        ),
        (
            "nb_drones: 1\nstart_hub: a 0 0 [unknown=value]\n"
            "end_hub: b 1 0\n",
            "Unknown zone metadata key",
            2,
        ),
        (
            "nb_drones: 1\nstart_hub: a 0 0\n"
            "hub: c 1 0 [max_drones=-1]\nend_hub: b 2 0\n",
            "max_drones must be a positive integer",
            3,
        ),
        (
            "nb_drones: 1\nstart_hub: a 0 0\n"
            "end_hub: b 1 0\n"
            "connection: a-b [max_link_capacity=0]\n",
            "max_link_capacity must be a positive integer",
            4,
        ),
        (
            "nb_drones: 1\nstart_hub:  a 0 0\nend_hub: b 1 0\n",
            "exactly one ASCII space",
            2,
        ),
    ],
)
def test_invalid_map_reports_source_line(
    tmp_path: Path,
    content: str,
    message: str,
    line_number: int,
) -> None:
    """Invalid definitions report their path, line, text, and cause."""
    map_path = write_map(tmp_path, content)

    with pytest.raises(MapParseError, match=message) as error_info:
        MapParser().parse_file(map_path)

    error = error_info.value
    assert error.file_path == map_path
    assert error.line_number == line_number
    assert error.line_text == content.splitlines()[line_number - 1]


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("# comment only\n\n", "contains no definitions"),
        (
            "nb_drones: 1\nend_hub: goal 1 0\n",
            "exactly one start_hub",
        ),
        (
            "nb_drones: 1\nstart_hub: start 0 0\n",
            "exactly one end_hub",
        ),
    ],
)
def test_file_level_errors_have_no_line_context(
    tmp_path: Path,
    content: str,
    message: str,
) -> None:
    """Missing whole-file requirements report no invented source line."""
    map_path = write_map(tmp_path, content)

    with pytest.raises(MapParseError, match=message) as error_info:
        MapParser().parse_file(map_path)

    assert error_info.value.line_number is None
    assert error_info.value.line_text is None
