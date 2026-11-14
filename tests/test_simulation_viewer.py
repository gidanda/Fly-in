"""Test viewer playback and drawing without requiring a display server."""

import tkinter as tk
from collections.abc import Iterator
from typing import cast
from unittest.mock import MagicMock, patch

import pytest

from fly_in.connection import Connection
from fly_in.drone_map import DroneMap
from fly_in.errors import VisualizationError
from fly_in.scenario import Scenario
from fly_in.simulation_state import SimulationState
from fly_in.simulation_viewer import SimulationViewer
from fly_in.turn_plan import MoveIntent, TurnPlan
from fly_in.zone import Zone, ZoneRole, ZoneType


def make_history() -> list[SimulationState]:
    """Build initial, in-transit, and delivered snapshots."""
    drone_map = DroneMap(
        [
            Zone(1, "start", -3, 0, ZoneRole.START,
                 ZoneType.NORMAL, None, "green"),
            Zone(2, "goal", 3, 0, ZoneRole.END,
                 ZoneType.RESTRICTED, None, "banana"),
            Zone(3, "isolated", 0, 2, ZoneRole.REGULAR,
                 ZoneType.NORMAL, 1, None),
        ],
        [Connection(1, 1, 2, 2)],
    )
    initial = SimulationState(Scenario(drone_map, 2))
    moving = initial.preview_turn(
        TurnPlan(1, (MoveIntent(1, 2), MoveIntent(2, 2)))
    ).next_state
    finished = moving.preview_turn(TurnPlan(2, ())).next_state
    return [initial, moving, finished]


@pytest.fixture
def widgets() -> Iterator[MagicMock]:
    """Replace Tk widgets with mocks so tests never create real windows."""
    canvas = MagicMock()
    canvas.winfo_width.return_value = 700
    canvas.winfo_height.return_value = 700
    with (
        patch("fly_in.simulation_viewer.tk.Tk"),
        patch("fly_in.simulation_viewer.tk.Canvas", return_value=canvas),
        patch("fly_in.simulation_viewer.ttk.Label"),
        patch("fly_in.simulation_viewer.ttk.Frame"),
        patch(
            "fly_in.simulation_viewer.ttk.Button",
            side_effect=lambda *args, **kwargs: MagicMock(),
        ),
    ):
        yield canvas


def test_rejects_empty_history_before_opening_window() -> None:
    """An empty history is a domain error even without a Tk display."""
    with patch("fly_in.simulation_viewer.tk.Tk") as root:
        with pytest.raises(VisualizationError, match="must not be empty"):
            SimulationViewer([])
        root.assert_not_called()


def test_reports_unavailable_display() -> None:
    """A Tk startup failure is translated into an application error."""
    with patch("fly_in.simulation_viewer.tk.Tk", side_effect=tk.TclError):
        with pytest.raises(VisualizationError, match="Cannot open"):
            SimulationViewer(make_history())


def test_replays_history_without_changing_snapshots(
    widgets: MagicMock,
) -> None:
    """Next steps display transit and arrival, then stop at the last state."""
    history = make_history()
    viewer = SimulationViewer(history)
    assert viewer._current_index == 0
    assert len(viewer._get_positions()) == 3
    viewer._next_turn()
    texts = [call.kwargs.get("text")
             for call in widgets.create_text.call_args_list]
    assert "2/2" in texts
    viewer._next_turn()
    assert viewer._current_index == 2
    cast(MagicMock, viewer._next_button).configure.assert_called_with(
        state=tk.DISABLED,
    )
    texts = [call.kwargs.get("text")
             for call in widgets.create_text.call_args_list]
    assert "2/∞" in texts
    viewer._next_turn()
    assert viewer._current_index == 2
    assert [state.current_turn for state in history] == [0, 1, 2]
    assert not history[0].all_drones_finished()


def test_back_and_reset_update_controls(widgets: MagicMock) -> None:
    """Playback can go back or reset without changing recorded states."""
    history = make_history()
    viewer = SimulationViewer(history)
    reset = cast(MagicMock, viewer._reset_button)
    back = cast(MagicMock, viewer._back_button)
    next_button = cast(MagicMock, viewer._next_button)
    reset.configure.assert_called_with(state=tk.DISABLED)
    back.configure.assert_called_with(state=tk.DISABLED)
    viewer._previous_turn()
    assert viewer._current_index == 0
    viewer._next_turn()
    viewer._next_turn()
    next_button.configure.assert_called_with(state=tk.DISABLED)
    viewer._previous_turn()
    assert viewer._current_index == 1
    next_button.configure.assert_called_with(state=tk.NORMAL)
    reset.configure.assert_called_with(state=tk.NORMAL)
    back.configure.assert_called_with(state=tk.NORMAL)
    viewer._reset()
    assert viewer._current_index == 0
    reset.configure.assert_called_with(state=tk.DISABLED)
    back.configure.assert_called_with(state=tk.DISABLED)
    next_button.configure.assert_called_with(state=tk.NORMAL)
    viewer._next_turn()
    viewer._previous_turn()
    assert viewer._current_index == 0
    back.configure.assert_called_with(state=tk.DISABLED)
    assert [state.current_turn for state in history] == [0, 1, 2]


def test_color_fallback_and_marker_limit(widgets: MagicMock) -> None:
    """Unknown colors are white and large groups use five diamonds."""
    viewer = SimulationViewer(make_history())
    assert viewer._resolve_color(None) == "white"
    assert viewer._resolve_color("green") == "green"
    widgets.winfo_rgb.side_effect = tk.TclError
    assert viewer._resolve_color("banana") == "white"
    widgets.create_polygon.reset_mock()
    viewer._draw_markers(100, 100, 50)
    assert widgets.create_polygon.call_count == 5


def test_positions_fit_resized_canvas(widgets: MagicMock) -> None:
    """Negative coordinates fit within margins without distorting scale."""
    viewer = SimulationViewer(make_history())
    widgets.winfo_width.return_value = 900
    widgets.winfo_height.return_value = 500
    positions = viewer._get_positions()
    for x, y in positions.values():
        assert 70 <= x <= 830
        assert 70 <= y <= 430
    assert positions[3][1] < positions[1][1]


def test_handles_horizontal_and_coincident_coordinates(
    widgets: MagicMock,
) -> None:
    """A zero span on one or both axes never causes division by zero."""
    for end_x in (0, 3):
        drone_map = DroneMap(
            [
                Zone(1, "start", 0, 0, ZoneRole.START,
                     ZoneType.NORMAL, None, None),
                Zone(2, "goal", end_x, 0, ZoneRole.END,
                     ZoneType.NORMAL, None, None),
            ],
            [Connection(1, 1, 2, 1)],
        )
        viewer = SimulationViewer([
            SimulationState(Scenario(drone_map, 1)),
        ])
        assert all(y == 350 for _, y in viewer._get_positions().values())
        cast(MagicMock, viewer._next_button).configure.assert_called_with(
            state=tk.DISABLED,
        )
        cast(MagicMock, viewer._back_button).configure.assert_called_with(
            state=tk.DISABLED,
        )
        cast(MagicMock, viewer._reset_button).configure.assert_called_with(
            state=tk.DISABLED,
        )
