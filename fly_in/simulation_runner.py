"""Run a Fly-in simulation from an initial state to completion."""

from fly_in.simulation_state import SimulationState
from fly_in.turn_formatter import TurnFormatter
from fly_in.turn_planner import TurnPlanner


class SimulationRunner:
    """Coordinate planning, state transitions, and terminal output."""

    def __init__(
        self,
        planner: TurnPlanner,
        formatter: TurnFormatter,
    ) -> None:
        """Store the collaborators used for every simulation turn."""
        self._planner = planner
        self._formatter = formatter

    def run(
        self,
        initial_state: SimulationState,
    ) -> SimulationState:
        """Print each turn and return the completed simulation state."""
        state = initial_state

        while not state.all_drones_finished():
            plan = self._planner.create_plan(state)
            projection = state.preview_turn(plan)
            print(self._formatter.format_turn(state, projection))
            state = projection.next_state

        return state
