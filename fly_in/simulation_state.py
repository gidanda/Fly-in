"""Dynamic state shared by one Fly-in simulation."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from fly_in.drone import AtZone, Drone, Finished, InTransit
from fly_in.drone_map import DroneMap
from fly_in.errors import TurnValidationError
from fly_in.scenario import Scenario
from fly_in.turn_plan import TurnPlan
from fly_in.turn_projection import TurnProjection


@dataclass(frozen=True)
class _ResolvedMove:
    """Store one map-resolved move during a turn preview."""

    destination_zone_id: int
    connection_id: int
    travel_turns: int


class SimulationState:
    """Own every drone and expose facts about the current simulation."""

    def __init__(self, scenario: Scenario) -> None:
        """Place all scenario drones at the start zone on turn zero."""
        self._drone_map = scenario.drone_map
        self._drones = {
            drone_id: Drone(
                id=drone_id,
                state=AtZone(self._drone_map.start_zone_id),
            )
            for drone_id in range(1, scenario.drone_count + 1)
        }
        self._drones_view = MappingProxyType(self._drones)
        self._current_turn = 0

    @classmethod
    def _from_snapshot(
        cls,
        drone_map: DroneMap,
        drones: Mapping[int, Drone],
        current_turn: int,
    ) -> "SimulationState":
        """Build a next-turn snapshot from caller-validated data."""
        simulation = cls.__new__(cls)
        simulation._drone_map = drone_map
        simulation._drones = dict(drones)
        simulation._drones_view = MappingProxyType(simulation._drones)
        simulation._current_turn = current_turn
        return simulation

    @property
    def drone_map(self) -> DroneMap:
        """Return the static map used by this simulation."""
        return self._drone_map

    @property
    def drones(self) -> Mapping[int, Drone]:
        """Return a read-only view of drones indexed by ID."""
        return self._drones_view

    @property
    def current_turn(self) -> int:
        """Return the current turn number."""
        return self._current_turn

    def get_zone_occupancy(self, zone_id: int) -> int:
        """Return the number of drones currently occupying a zone."""
        self._drone_map.get_zone(zone_id)
        return sum(
            isinstance(drone.state, AtZone)
            and drone.state.zone_id == zone_id
            for drone in self._drones.values()
        )

    def get_connection_occupancy(self, connection_id: int) -> int:
        """Return the number of drones currently using a connection."""
        self._drone_map.get_connection(connection_id)
        return sum(
            isinstance(drone.state, InTransit)
            and drone.state.connection_id == connection_id
            for drone in self._drones.values()
        )

    def all_drones_finished(self) -> bool:
        """Return whether every drone has reached the end zone."""
        return all(
            isinstance(drone.state, Finished)
            for drone in self._drones.values()
        )

    def preview_turn(self, plan: TurnPlan) -> TurnProjection:
        """Return a validated next-turn projection without changing state."""
        resolved_moves = self._resolve_moves(plan)
        connection_users = self._collect_connection_users(resolved_moves)
        self._validate_connection_capacities(connection_users)
        projected_drones = self._project_drones(resolved_moves)
        self._validate_zone_capacities(projected_drones)
        next_state = self._from_snapshot(
            drone_map=self._drone_map,
            drones=projected_drones,
            current_turn=self._current_turn + 1,
        )

        return TurnProjection(
            source_turn=self._current_turn,
            plan=plan,
            next_state=next_state,
            connection_users=connection_users,
        )

    def _resolve_moves(
        self,
        plan: TurnPlan,
    ) -> dict[int, _ResolvedMove]:
        """Validate and enrich every newly planned movement."""
        resolved_moves: dict[int, _ResolvedMove] = {}

        for move in plan.moves:
            drone = self._drones.get(move.drone_id)
            if drone is None:
                raise TurnValidationError(
                    f"Unknown drone ID: {move.drone_id}"
                )
            if not isinstance(drone.state, AtZone):
                raise TurnValidationError(
                    f"Drone {move.drone_id} is not at a zone"
                )

            source_zone_id = drone.state.zone_id
            if not self._drone_map.has_zone(move.destination_zone_id):
                raise TurnValidationError(
                    f"Unknown destination zone ID: "
                    f"{move.destination_zone_id}"
                )
            if source_zone_id == move.destination_zone_id:
                raise TurnValidationError(
                    f"Drone {move.drone_id} is already at zone "
                    f"{source_zone_id}"
                )

            destination = self._drone_map.get_zone(
                move.destination_zone_id
            )
            travel_turns = destination.movement_cost()
            if travel_turns is None:
                raise TurnValidationError(
                    f"Drone {move.drone_id} cannot enter blocked zone "
                    f"{move.destination_zone_id}"
                )

            connection = self._drone_map.get_connection_between(
                source_zone_id,
                move.destination_zone_id,
            )
            if connection is None:
                raise TurnValidationError(
                    f"Zones {source_zone_id} and "
                    f"{move.destination_zone_id} are not connected"
                )

            resolved_moves[move.drone_id] = _ResolvedMove(
                destination_zone_id=move.destination_zone_id,
                connection_id=connection.id,
                travel_turns=travel_turns,
            )

        return resolved_moves

    def _collect_connection_users(
        self,
        resolved_moves: Mapping[int, _ResolvedMove],
    ) -> dict[int, frozenset[int]]:
        """Collect connection users, trusting validated existing transit."""
        mutable_users: dict[int, set[int]] = {}

        for drone in self._drones.values():
            state = drone.state
            if not isinstance(state, InTransit):
                continue
            mutable_users.setdefault(state.connection_id, set()).add(
                drone.id
            )

        for drone_id, move in resolved_moves.items():
            mutable_users.setdefault(move.connection_id, set()).add(
                drone_id
            )

        return {
            connection_id: frozenset(drone_ids)
            for connection_id, drone_ids in mutable_users.items()
        }

    def _validate_connection_capacities(
        self,
        connection_users: Mapping[int, frozenset[int]],
    ) -> None:
        """Reject a turn that overuses any connection."""
        for connection_id, drone_ids in connection_users.items():
            connection = self._drone_map.get_connection(connection_id)
            if len(drone_ids) > connection.max_capacity:
                raise TurnValidationError(
                    f"Connection {connection_id} capacity exceeded: "
                    f"{len(drone_ids)} > {connection.max_capacity}"
                )

    def _project_drones(
        self,
        resolved_moves: Mapping[int, _ResolvedMove],
    ) -> dict[int, Drone]:
        """Return every drone after one complete simulated turn."""
        projected_drones = dict(self._drones)

        for drone_id, drone in self._drones.items():
            move = resolved_moves.get(drone_id)
            if move is not None:
                destination_is_goal = (
                    move.destination_zone_id
                    == self._drone_map.end_zone_id
                )
                projected_drones[drone_id] = drone.start_move(
                    connection_id=move.connection_id,
                    destination_zone_id=move.destination_zone_id,
                    travel_turns=move.travel_turns,
                ).advance_one_turn(destination_is_goal)
                continue

            state = drone.state
            if isinstance(state, InTransit):
                destination_is_goal = (
                    state.destination_zone_id
                    == self._drone_map.end_zone_id
                )
                projected_drones[drone_id] = drone.advance_one_turn(
                    destination_is_goal
                )

        return projected_drones

    def _validate_zone_capacities(
        self,
        projected_drones: Mapping[int, Drone],
    ) -> None:
        """Reject a turn whose end state overfills any zone."""
        occupancy: dict[int, int] = {}

        for drone in projected_drones.values():
            state = drone.state
            if not isinstance(state, AtZone):
                continue
            occupancy[state.zone_id] = occupancy.get(state.zone_id, 0) + 1

        for zone_id, drone_count in occupancy.items():
            zone = self._drone_map.get_zone(zone_id)
            if zone_id in (
                self._drone_map.start_zone_id,
                self._drone_map.end_zone_id,
            ) or zone.max_drones is None:
                continue
            if drone_count > zone.max_drones:
                raise TurnValidationError(
                    f"Zone {zone_id} capacity exceeded: "
                    f"{drone_count} > {zone.max_drones}"
                )
