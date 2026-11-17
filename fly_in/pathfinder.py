"""Fly-inマップの静的な最短コスト計算。"""

from heapq import heappop, heappush

from fly_in.drone_map import DroneMap


class Pathfinder:
    """各ゾーンからゴールまでの最小移動コストを提供する。"""

    def __init__(self, drone_map: DroneMap) -> None:
        """マップを一度解析し、ゴールまでの最短コストを保持する。"""
        self._drone_map = drone_map
        self._goal_costs = self._calculate_goal_costs()

    @property
    def drone_map(self) -> DroneMap:
        """最短コストの計算対象のマップを返す。"""
        return self._drone_map

    def get_goal_cost(self, zone_id: int) -> int | None:
        """指定ゾーンからゴールまでの最短ターン数を返す。

        到達できない場合はNoneを返す。

        Raises:
            KeyError: 指定ゾーンIDがマップに存在しない場合。
        """
        self._drone_map.get_zone(zone_id)
        return self._goal_costs.get(zone_id)

    def _calculate_goal_costs(self) -> dict[int, int]:
        """ゴールを起点とする逆向きのダイクストラ法を実行する。"""
        end_zone_id = self._drone_map.end_zone_id
        goal_costs = {end_zone_id: 0}
        queue = [(0, end_zone_id)]

        while queue:
            current_cost, current_id = heappop(queue)
            if current_cost != goal_costs[current_id]:
                continue

            current_zone = self._drone_map.get_zone(current_id)
            entry_cost = current_zone.movement_cost()
            if entry_cost is None:
                continue

            for neighbor_id in self._drone_map.get_neighbor_ids(current_id):
                neighbor = self._drone_map.get_zone(neighbor_id)
                if not neighbor.is_accessible():
                    continue

                candidate_cost = current_cost + entry_cost
                known_cost = goal_costs.get(neighbor_id)
                if known_cost is not None and candidate_cost >= known_cost:
                    continue

                goal_costs[neighbor_id] = candidate_cost
                heappush(queue, (candidate_cost, neighbor_id))

        return goal_costs
