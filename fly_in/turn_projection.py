"""Immutable result of previewing one simulation turn."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING

from fly_in.turn_plan import TurnPlan

if TYPE_CHECKING:
    from fly_in.simulation_state import SimulationState


def _validate_non_negative_integer(value: int, field_name: str) -> None:
    """Require an integer value greater than or equal to zero."""
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
    ):
        raise ValueError(f"{field_name} must be a non-negative integer")


def _validate_positive_integer(value: int, field_name: str) -> None:
    """Require an integer identifier greater than zero."""
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 1
    ):
        raise ValueError(f"{field_name} must be a positive integer")


@dataclass(frozen=True)
class TurnProjection:
    """Store the immutable calculated outcome of one proposed turn."""

    source_turn: int
    plan: TurnPlan
    next_state: "SimulationState"
    connection_users: Mapping[int, frozenset[int]]

    def __post_init__(self) -> None:
        """Validate local consistency and protect supplied mappings."""
        _validate_non_negative_integer(self.source_turn, "source_turn")
        if not isinstance(self.plan, TurnPlan):
            raise ValueError("plan must be a TurnPlan")
        from fly_in.simulation_state import SimulationState

        if not isinstance(self.next_state, SimulationState):
            raise ValueError("next_state must be a SimulationState")
        if self.next_state.current_turn != self.source_turn + 1:
            raise ValueError(
                "next_state must be exactly one turn after source_turn"
            )
        if not isinstance(self.connection_users, Mapping):
            raise ValueError("connection_users must be a mapping")

        drone_ids = self.next_state.drones.keys()

        connection_users: dict[int, frozenset[int]] = {}
        seen_user_ids: set[int] = set()
        for connection_id, user_ids in self.connection_users.items():
            _validate_positive_integer(connection_id, "connection_id")
            if not isinstance(user_ids, frozenset):
                raise ValueError("connection users must be a frozenset")
            for drone_id in user_ids:
                _validate_positive_integer(drone_id, "drone_id")
                if drone_id not in drone_ids:
                    raise ValueError(
                        "connection user must exist in next state"
                    )
            duplicate_ids = seen_user_ids.intersection(user_ids)
            if duplicate_ids:
                raise ValueError(
                    "a drone cannot use multiple connections in one turn"
                )
            seen_user_ids.update(user_ids)
            connection_users[connection_id] = user_ids

        planned_drone_ids = {
            move.drone_id for move in self.plan.moves
        }
        if not planned_drone_ids.issubset(drone_ids):
            raise ValueError(
                "planned drone must exist in next state"
            )
        if not planned_drone_ids.issubset(seen_user_ids):
            raise ValueError(
                "planned drone must use a connection in the projection"
            )

        object.__setattr__(
            self,
            "connection_users",
            MappingProxyType(connection_users),
        )
