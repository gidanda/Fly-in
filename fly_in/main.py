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
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the requested map and return a process exit code."""
    arguments = _parse_arguments(argv)

    try:
        scenario = MapParser().parse_file(arguments.map_file)
        state = SimulationState(scenario)
        pathfinder = Pathfinder(scenario.drone_map)
        planner = TurnPlanner(pathfinder)
        formatter = TurnFormatter()
        runner = SimulationRunner(planner, formatter)
        runner.run(state)
    except (FlyInError, OSError, UnicodeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    return 0
