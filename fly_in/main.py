"""Command-line entry point for the Fly-in simulation."""

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from fly_in.errors import FlyInError
from fly_in.map_parser import MapParser
from fly_in.pathfinder import Pathfinder
from fly_in.simulation_runner import SimulationRunner
from fly_in.simulation_state import SimulationState
from fly_in.turn_formatter import TurnFormatter
from fly_in.turn_planner import TurnPlanner


def _parse_arguments(
    argv: Sequence[str] | None = None,
) -> argparse.Namespace:
    """Parse command-line arguments for one simulation run."""
    parser = argparse.ArgumentParser(
        prog="python -m fly_in",
        description="Simulate drone movement through a Fly-in map.",
    )
    parser.add_argument(
        "map_file",
        type=Path,
        help="path to the map file to simulate",
    )
    parser.add_argument(
        "--gui",
        action="store_true",
        help="Open the graphical simulation viewer",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the requested map and return a process exit code."""
    arguments = _parse_arguments(argv)

    try:
        scenario = MapParser().parse_file(arguments.map_file)
        state = SimulationState(scenario)
        pathfinder = Pathfinder(scenario.drone_map)
        planner = TurnPlanner(pathfinder)
        formatter = TurnFormatter(use_color=sys.stdout.isatty())
        runner = SimulationRunner(planner, formatter)
        states = runner.run(state)
        if arguments.gui:
            # Keep terminal-only runs independent of the optional Tk runtime.
            try:
                from fly_in.simulation_viewer import SimulationViewer
            except ImportError as error:
                from fly_in.errors import VisualizationError

                raise VisualizationError(
                    "GUI requires a Python installation with tkinter/Tk"
                ) from error
            SimulationViewer(states).run()
    except (FlyInError, OSError, UnicodeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    return 0
