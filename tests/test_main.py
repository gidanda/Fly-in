"""Tests for the Fly-in command-line entry point."""

from pathlib import Path

import pytest

from fly_in.main import main


def write_map(tmp_path: Path, content: str) -> Path:
    """Write a temporary map for a CLI test."""
    map_path = tmp_path / "map.txt"
    map_path.write_text(content, encoding="utf-8")
    return map_path


def test_main_runs_a_map_to_completion(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A valid map prints every movement and exits successfully."""
    map_path = write_map(
        tmp_path,
        "nb_drones: 2\n"
        "start_hub: start 0 0\n"
        "hub: middle 1 0 [max_drones=1]\n"
        "end_hub: goal 2 0\n"
        "connection: start-middle [max_link_capacity=1]\n"
        "connection: middle-goal [max_link_capacity=1]\n",
    )

    exit_code = main([str(map_path)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert captured.out == (
        "D1-middle\n"
        "D1-goal D2-middle\n"
        "D2-goal\n"
    )
    assert captured.err == ""


def test_main_reports_invalid_map_content(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Domain errors are written to stderr with a failing exit code."""
    map_path = write_map(tmp_path, "nb_drones: 0\n")

    exit_code = main([str(map_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert str(map_path) in captured.err
    assert "positive integer" in captured.err


def test_main_reports_an_unreadable_path(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """File-system errors are reported instead of escaping uncaught."""
    missing_path = tmp_path / "missing.txt"

    exit_code = main([str(missing_path)])

    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert str(missing_path) in captured.err


def test_main_uses_argparse_for_missing_arguments(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Missing required arguments produce argparse's usage error."""
    with pytest.raises(SystemExit) as error:
        main([])

    captured = capsys.readouterr()
    assert error.value.code == 2
    assert captured.out == ""
    assert "usage: python -m fly_in" in captured.err
