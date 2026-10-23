"""Tests for Fly-in application exceptions."""

from pathlib import Path

from fly_in.errors import (
    DroneStateError,
    FlyInError,
    MapDefinitionError,
    MapParseError,
)


def test_map_parse_error_is_a_fly_in_error() -> None:
    """Parser errors can be caught through the common base class."""
    error = MapParseError(Path("maps/example.txt"), "Invalid map")

    assert isinstance(error, FlyInError)


def test_drone_state_error_is_a_fly_in_error() -> None:
    """Drone state failures can be caught through the common base class."""
    assert isinstance(DroneStateError("Invalid transition"), FlyInError)


def test_map_errors_are_sibling_classes() -> None:
    """Parsing and definition failures share only the common base."""
    parse_error = MapParseError(Path("map.txt"), "Invalid syntax")
    definition_error = MapDefinitionError("Invalid structure")

    assert isinstance(parse_error, FlyInError)
    assert isinstance(definition_error, FlyInError)
    assert not isinstance(parse_error, MapDefinitionError)
    assert not isinstance(definition_error, MapParseError)


def test_map_parse_error_displays_line_context() -> None:
    """Line-specific errors show their file, line, message, and input."""
    error = MapParseError(
        file_path=Path("maps/example.txt"),
        message="nb_drones must be a positive integer",
        line_number=4,
        line_text="nb_drones: -3\t",
    )

    assert error.file_path == Path("maps/example.txt")
    assert error.message == "nb_drones must be a positive integer"
    assert error.line_number == 4
    assert error.line_text == "nb_drones: -3\t"
    assert str(error) == (
        "maps/example.txt:4: nb_drones must be a positive integer\n"
        "  > 'nb_drones: -3\\t'"
    )


def test_map_parse_error_displays_file_level_error() -> None:
    """File-wide errors omit unavailable line context."""
    error = MapParseError(
        file_path=Path("maps/empty.txt"),
        message="Map file contains no definitions",
    )

    assert str(error) == (
        "maps/empty.txt: Map file contains no definitions"
    )
