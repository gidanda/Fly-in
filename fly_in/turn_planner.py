"""Greedy movement planning for one Fly-in simulation turn."""

from fly_in.drone import AtZone, Drone, InTransit
from fly_in.errors import PlanningError, TurnValidationError
from fly_in.pathfinder import Pathfinder
from fly_in.simulation_state import SimulationState
from fly_in.turn_plan import MoveIntent, TurnPlan
from fly_in.zone import ZoneType


class TurnPlanner:
    """Build one safe turn using static goal costs and greedy choices."""

    def __init__(self, pathfinder: Pathfinder) -> None:
        """Store the static analysis used to order movement choices."""
        self._pathfinder = pathfinder

    def create_plan(self, state: SimulationState) -> TurnPlan:
        """Return a greedy, capacity-aware plan for the current turn."""
        if state.drone_map is not self._pathfinder.drone_map:
            raise ValueError(
                "Pathfinder and simulation state use different maps"
            )

        accepted_moves: list[MoveIntent] = []

        for drone in self._get_ordered_drones(state):
            drone_state = drone.state
            if not isinstance(drone_state, AtZone):
                continue

            destination_ids = self._get_ordered_destination_ids(
                drone_state.zone_id
            )
            for destination_id in destination_ids:
                intent = MoveIntent(drone.id, destination_id)
                candidate_plan = TurnPlan(
                    tuple(accepted_moves + [intent])
                )

                try:
                    projection = state.preview_turn(candidate_plan)
                except TurnValidationError:
                    continue

                if not self._has_safe_arrival_reservations(
                    projection.next_state
                ):
                    continue

                accepted_moves.append(intent)
                break

        plan = TurnPlan(tuple(accepted_moves))
        if (
            accepted_moves
            or state.all_drones_finished()
            or any(
                isinstance(drone.state, InTransit)
                for drone in state.drones.values()
            )
        ):
            return plan

        raise PlanningError(
            f"No progressing turn plan exists at turn "
            f"{state.current_turn}"
        )

    def _get_ordered_drones(
        self,
        state: SimulationState,
    ) -> list[Drone]:
        """Return reachable zone-bound drones from downstream to upstream."""
        ordered: list[tuple[int, int, Drone]] = []

        for drone in state.drones.values():
            drone_state = drone.state
            if not isinstance(drone_state, AtZone):
                continue

            goal_cost = self._pathfinder.get_goal_cost(
                drone_state.zone_id
            )
            if goal_cost is None:
                continue

            ordered.append((goal_cost, drone.id, drone))

        ordered.sort(key=lambda item: (item[0], item[1]))
        return [item[2] for item in ordered]

    def _get_ordered_destination_ids(
        self,
        current_zone_id: int,
    ) -> list[int]:
        """Return accessible, strictly goalward neighboring zone IDs."""
        drone_map = self._pathfinder.drone_map
        current_goal_cost = self._pathfinder.get_goal_cost(
            current_zone_id
        )
        if current_goal_cost is None:
            return []

        ordered: list[tuple[int, int, int]] = []

        for destination_id in drone_map.get_neighbor_ids(
            current_zone_id
        ):
            destination = drone_map.get_zone(destination_id)
            entry_cost = destination.movement_cost()
            destination_goal_cost = self._pathfinder.get_goal_cost(
                destination_id
            )

            if entry_cost is None or destination_goal_cost is None:
                continue
            if destination_goal_cost >= current_goal_cost:
                continue

            priority_rank = (
                0
                if destination.zone_type is ZoneType.PRIORITY
                else 1
            )
            ordered.append(
                (
                    entry_cost + destination_goal_cost,
                    priority_rank,
                    destination_id,
                )
            )

        ordered.sort()
        return [item[2] for item in ordered]

    def _has_safe_arrival_reservations(
        self,
        next_state: SimulationState,
    ) -> bool:
        """Return whether every forced next-turn arrival has capacity."""
        arrival_counts: dict[int, int] = {}

        for drone in next_state.drones.values():
            drone_state = drone.state
            if not isinstance(drone_state, InTransit):
                continue
            if drone_state.remaining_turns != 1:
                continue

            destination_id = drone_state.destination_zone_id
            arrival_counts[destination_id] = (
                arrival_counts.get(destination_id, 0) + 1
            )

        for zone_id, arrival_count in arrival_counts.items():
            zone = next_state.drone_map.get_zone(zone_id)
            max_drones = zone.max_drones
            if zone_id in (
                next_state.drone_map.start_zone_id,
                next_state.drone_map.end_zone_id,
            ) or max_drones is None:
                continue

            occupancy = next_state.get_zone_occupancy(zone_id)
            if occupancy + arrival_count > max_drones:
                return False

        return True
