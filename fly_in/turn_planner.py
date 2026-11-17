"""Fly-inの1ターン分の移動を貪欲法と先読みで計画する。"""

from typing import cast

from fly_in.drone import AtZone, Drone, InTransit
from fly_in.errors import PlanningError, TurnValidationError
from fly_in.pathfinder import Pathfinder
from fly_in.simulation_state import SimulationState
from fly_in.turn_plan import MoveIntent, TurnPlan
from fly_in.zone import ZoneType


class TurnPlanner:
    """静的なゴールコストと貪欲な選択で、安全な移動計画を作る。"""

    def __init__(self, pathfinder: Pathfinder) -> None:
        """移動候補の優先順位に使う静的解析と、保存済み計画の保持先を用意する。"""
        self._pathfinder = pathfinder
        self._required_plan: TurnPlan | None = None

    def create_plan(self, state: SimulationState) -> TurnPlan:
        """現在の状態から実行する、容量と次ターンの安全性を考慮した計画を返す。"""
        if state.drone_map is not self._pathfinder.drone_map:
            raise ValueError(
                "Pathfinder and simulation state use different maps"
            )

        accepted_moves: list[MoveIntent] = []
        if self._required_plan is not None:
            if self._required_plan.execution_turn != state.current_turn + 1:
                raise PlanningError("Saved plan is for a different turn")
            accepted_moves.extend(self._required_plan.moves)
        base_plan = TurnPlan(state.current_turn + 1, tuple(accepted_moves))
        base_projection = state.preview_turn(base_plan)
        next_plan = self._build_required_next_plan(base_projection.next_state)
        required_drone_ids = {
            move.drone_id for move in accepted_moves
        }

        for drone in self._get_ordered_drones(state):
            if drone.id in required_drone_ids:
                continue
            drone_state = drone.state
            if not isinstance(drone_state, AtZone):
                continue

            destination_ids = self._get_ordered_destination_ids(
                drone_state.zone_id
            )
            for destination_id in destination_ids:
                intent = MoveIntent(drone.id, destination_id)
                candidate_plan = TurnPlan(
                    execution_turn=state.current_turn + 1,
                    moves=tuple(accepted_moves + [intent]),
                )

                try:
                    projection = state.preview_turn(candidate_plan)
                except TurnValidationError:
                    continue

                candidate_next_plan = self._build_required_next_plan(
                    projection.next_state
                )
                if candidate_next_plan is None:
                    continue

                accepted_moves.append(intent)
                next_plan = candidate_next_plan
                break

        plan = TurnPlan(
            execution_turn=state.current_turn + 1,
            moves=tuple(accepted_moves),
        )
        if (
            accepted_moves
            or state.all_drones_finished()
            or any(
                isinstance(drone.state, InTransit)
                for drone in state.drones.values()
            )
        ):
            if next_plan is None:
                raise PlanningError("Cannot secure a safe next-turn plan")
            self._required_plan = next_plan
            return plan

        raise PlanningError(
            f"No progressing turn plan exists at turn "
            f"{state.current_turn}"
        )

    def _get_ordered_drones(
        self,
        state: SimulationState,
    ) -> list[Drone]:
        """ゴールに到達可能なゾーン滞在中の機体を、ゴールコストの小さい順に返す。"""
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
        """進入可能でゴールコストが現在地より小さい隣接ゾーンIDを優先順に返す。"""
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

    def _build_required_next_plan(
        self,
        next_state: SimulationState,
    ) -> TurnPlan | None:
        """今ターンの仮実行後の状態から、次ターンの安全な計画全体を確保する。

        新規移動は1ターンで到着できるものに限定する。
        強制到着を先に数え、ゴール側から退出を選ぶ。
        集計途中の容量超過は退出で解消できる場合があるため、
        最後に計画全体を仮実行して全ゾーンをまとめて検証する。
        成立すれば計画を返し、確保できなければNoneを返す。保存は呼び出し側が行う。
        """
        drone_map = next_state.drone_map
        zone_counts = {
            zone.id: next_state.get_zone_occupancy(zone.id)
            for zone in drone_map.get_zones()
        }
        connection_counts: dict[int, int] = {}
        for drone in next_state.drones.values():
            transit = drone.state
            if not isinstance(transit, InTransit):
                continue
            if transit.remaining_turns == 1:
                zone_counts[transit.destination_zone_id] += 1
            else:
                connection_id = transit.connection_id
                connection_counts[connection_id] = (
                    connection_counts.get(connection_id, 0) + 1
                )

        moves: list[MoveIntent] = []
        for drone in self._get_ordered_drones(next_state):
            at_zone = drone.state
            if not isinstance(at_zone, AtZone):
                continue
            for destination_id in self._get_ordered_destination_ids(
                at_zone.zone_id
            ):
                destination = drone_map.get_zone(destination_id)
                if destination.movement_cost() != 1:
                    continue
                if (
                    not destination.has_unlimited_capacity()
                    and zone_counts[destination_id]
                    >= cast(int, destination.max_drones)
                ):
                    continue
                connection = drone_map.get_connection_between(
                    at_zone.zone_id, destination_id,
                )
                if connection is None:
                    continue
                if (
                    connection_counts.get(connection.id, 0)
                    >= connection.max_capacity
                ):
                    continue
                moves.append(MoveIntent(drone.id, destination_id))
                zone_counts[at_zone.zone_id] -= 1
                zone_counts[destination_id] += 1
                connection_counts[connection.id] = (
                    connection_counts.get(connection.id, 0) + 1
                )
                break

        plan = TurnPlan(next_state.current_turn + 1, tuple(moves))
        try:
            projection = next_state.preview_turn(plan)
        except TurnValidationError:
            return None
        if not self._has_safe_arrival_reservations(projection.next_state):
            return None
        return plan

    def _has_safe_arrival_reservations(
        self,
        next_state: SimulationState,
    ) -> bool:
        """渡された状態の滞在数に、さらに次ターンの強制到着を加えて容量を確認する。"""
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
            if zone.has_unlimited_capacity():
                continue
            max_drones = cast(int, zone.max_drones)

            occupancy = next_state.get_zone_occupancy(zone_id)
            if occupancy + arrival_count > max_drones:
                return False

        return True
