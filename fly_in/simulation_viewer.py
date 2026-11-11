"""Display a precomputed simulation history in a Tk window."""

import tkinter as tk
from collections.abc import Sequence
from tkinter import ttk

from fly_in.drone import AtZone, Finished, InTransit
from fly_in.errors import VisualizationError
from fly_in.simulation_state import SimulationState
from fly_in.zone import ZoneRole


class SimulationViewer:
    """Replay state snapshots without changing or running the simulation."""

    def __init__(self, states: Sequence[SimulationState]) -> None:
        """Create the window and show the first recorded state."""
        if not states:
            raise VisualizationError("State history must not be empty")
        self._states = states
        self._current_index = 0
        try:
            self._window = tk.Tk()
        except tk.TclError as error:
            raise VisualizationError(
                f"Cannot open the graphical viewer: {error}"
            ) from error
        self._window.title("Fly-in")
        self._canvas = tk.Canvas(
            self._window, width=700, height=700,
            background="#20242b", highlightthickness=0,
        )
        self._canvas.pack(fill=tk.BOTH, expand=True)
        self._turn_label = ttk.Label(self._window)
        self._turn_label.pack(pady=6)
        controls = ttk.Frame(self._window)
        controls.pack(pady=(0, 10))
        self._reset_button = ttk.Button(
            controls, text="Reset", command=self._reset,
        )
        self._reset_button.pack(side=tk.LEFT, padx=4)
        self._back_button = ttk.Button(
            controls, text="Previous turn", command=self._previous_turn,
        )
        self._back_button.pack(side=tk.LEFT, padx=4)
        self._next_button = ttk.Button(
            controls, text="Next turn", command=self._next_turn,
        )
        self._next_button.pack(side=tk.LEFT, padx=4)
        self._canvas.bind("<Configure>", self._on_resize)
        self._draw_state()

    def run(self) -> None:
        """Handle window events until the viewer is closed."""
        self._window.mainloop()

    def _next_turn(self) -> None:
        """Select the next snapshot, if available, and redraw it."""
        if self._current_index < len(self._states) - 1:
            self._current_index += 1
            self._draw_state()

    def _previous_turn(self) -> None:
        """Select the preceding snapshot without going before the first."""
        if self._current_index > 0:
            self._current_index -= 1
            self._draw_state()

    def _reset(self) -> None:
        """Return to the first recorded snapshot without recalculation."""
        self._current_index = 0
        self._draw_state()

    def _on_resize(self, event: tk.Event[tk.Misc]) -> None:
        """Fit the current map again after the canvas changes size."""
        self._draw_state()

    def _get_positions(self) -> dict[int, tuple[float, float]]:
        """Fit map coordinates into the canvas with a shared scale."""
        zones = self._states[self._current_index].drone_map.get_zones()
        min_x = min(zone.x for zone in zones)
        max_x = max(zone.x for zone in zones)
        min_y = min(zone.y for zone in zones)
        max_y = max(zone.y for zone in zones)
        # Before the first layout event, use the requested canvas dimensions.
        width = self._canvas.winfo_width()
        height = self._canvas.winfo_height()
        if width <= 1:
            width = int(self._canvas.cget("width"))
        if height <= 1:
            height = int(self._canvas.cget("height"))
        span_x = max_x - min_x
        span_y = max_y - min_y
        scales = [
            max(width - 140, 1) / span_x if span_x else float("inf"),
            max(height - 140, 1) / span_y if span_y else float("inf"),
        ]
        scale = min(scales)
        if scale == float("inf"):
            scale = 1.0
        return {
            zone.id: (
                width / 2 + (zone.x - (min_x + max_x) / 2) * scale,
                height / 2 - (zone.y - (min_y + max_y) / 2) * scale,
            )
            for zone in zones
        }

    def _draw_state(self) -> None:
        """Redraw edges, zones, drones, and playback controls."""
        state = self._states[self._current_index]
        positions = self._get_positions()
        self._canvas.delete("all")
        self._draw_connections(state, positions)
        self._draw_zones(state, positions)
        self._draw_drones(state, positions)
        self._turn_label.configure(text=f"Turn: {state.current_turn}")
        backward_state = tk.DISABLED if self._current_index == 0 else tk.NORMAL
        self._reset_button.configure(state=backward_state)
        self._back_button.configure(state=backward_state)
        self._next_button.configure(
            state=(
                tk.DISABLED
                if self._current_index == len(self._states) - 1
                else tk.NORMAL
            )
        )

    def _draw_connections(
        self,
        state: SimulationState,
        positions: dict[int, tuple[float, float]],
    ) -> None:
        """Draw connections behind the zone and drone markers."""
        for connection in state.drone_map.get_connections():
            self._canvas.create_line(
                *positions[connection.zone_a_id],
                *positions[connection.zone_b_id],
                fill="#8a95a5", width=2,
            )

    def _draw_zones(
        self,
        state: SimulationState,
        positions: dict[int, tuple[float, float]],
    ) -> None:
        """Draw fixed-size zone markers, names, and capacity labels."""
        for zone in state.drone_map.get_zones():
            x, y = positions[zone.id]
            color = self._resolve_color(zone.color)
            self._canvas.create_oval(
                x - 20, y - 20, x + 20, y + 20,
                fill=color, outline="white", width=2,
            )
            if zone.role in (ZoneRole.START, ZoneRole.END):
                self._canvas.create_oval(
                    x - 25, y - 25, x + 25, y + 25,
                    outline=color, width=2,
                )
            self._canvas.create_text(
                x, y - 38, text=zone.name, fill="white",
            )
            count = state.get_zone_occupancy(zone.id)
            if zone.role is ZoneRole.END:
                count += sum(
                    isinstance(drone.state, Finished)
                    for drone in state.drones.values()
                )
            capacity = (
                "∞" if zone.has_unlimited_capacity() else str(zone.max_drones)
            )
            self._canvas.create_text(
                x, y + 38, text=f"{count}/{capacity}", fill="white",
            )

    def _draw_drones(
        self,
        state: SimulationState,
        positions: dict[int, tuple[float, float]],
    ) -> None:
        """Group drones by location and draw at most five per group."""
        zone_counts: dict[int, int] = {}
        connection_counts: dict[int, int] = {}
        for drone in state.drones.values():
            if isinstance(drone.state, InTransit):
                key = drone.state.connection_id
                connection_counts[key] = connection_counts.get(key, 0) + 1
            else:
                zone_id = (
                    drone.state.zone_id if isinstance(drone.state, AtZone)
                    else state.drone_map.end_zone_id
                )
                zone_counts[zone_id] = zone_counts.get(zone_id, 0) + 1
        for zone_id, count in zone_counts.items():
            self._draw_markers(*positions[zone_id], count)
        for connection in state.drone_map.get_connections():
            count = connection_counts.get(connection.id, 0)
            ax, ay = positions[connection.zone_a_id]
            bx, by = positions[connection.zone_b_id]
            x, y = (ax + bx) / 2, (ay + by) / 2
            self._draw_markers(x, y, count)
            self._canvas.create_text(
                x, y + 18, text=f"{count}/{connection.max_capacity}",
                fill="#66e6ff",
            )

    def _draw_markers(self, x: float, y: float, count: int) -> None:
        """Draw a centered row of small, offset diamond markers."""
        visible = min(count, 5)
        for index in range(visible):
            marker_x = x + (index - (visible - 1) / 2) * 8
            self._canvas.create_polygon(
                marker_x, y - 5, marker_x + 4, y,
                marker_x, y + 5, marker_x - 4, y,
                fill="#ffcf40", outline="black",
            )

    def _resolve_color(self, color: str | None) -> str:
        """Use Tk-recognized colors and fall back to white otherwise."""
        if not color:
            return "white"
        try:
            self._canvas.winfo_rgb(color)
        except tk.TclError:
            return "white"
        return color
