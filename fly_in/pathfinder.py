"""Static shortest-cost analysis for a Fly-in map."""

from heapq import heappop, heappush

from fly_in.drone_map import DroneMap


class Pathfinder:
    """Provide minimum movement costs from zones to the end zone."""

    def __init__(self, drone_map: DroneMap) -> None:
        """Analyze the map once and retain its goal costs."""
        self._drone_map = drone_map
        self._goal_costs = self._calculate_goal_costs()

    @property
    def drone_map(self) -> DroneMap:
        """Return the map used to calculate these goal costs."""
        return self._drone_map

    def get_goal_cost(self, zone_id: int) -> int | None:
        """Return the minimum turns from a zone to the end, if reachable.

        Raises:
            KeyError: If the zone ID does not exist in the map.
        """
        self._drone_map.get_zone(zone_id)
        return self._goal_costs.get(zone_id)

    def _calculate_goal_costs(self) -> dict[int, int]:
        """Run reverse Dijkstra analysis from the end zone."""
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
