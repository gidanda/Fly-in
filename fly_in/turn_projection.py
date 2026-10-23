"""Immutable result of previewing one simulation turn."""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from fly_in.drone import AtZone, DroneState, Finished, InTransit
from fly_in.turn_plan import TurnPlan


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
    projected_drone_states: Mapping[int, DroneState]
    connection_users: Mapping[int, frozenset[int]]

    def __post_init__(self) -> None:
        """Validate local consistency and protect supplied mappings."""
        _validate_non_negative_integer(self.source_turn, "source_turn")
        if not isinstance(self.plan, TurnPlan):
            raise ValueError("plan must be a TurnPlan")
        if not isinstance(self.projected_drone_states, Mapping):
            raise ValueError("projected_drone_states must be a mapping")
        if not isinstance(self.connection_users, Mapping):
            raise ValueError("connection_users must be a mapping")

        drone_states = dict(self.projected_drone_states)
        if not drone_states:
            raise ValueError("projected_drone_states must not be empty")
        for drone_id, state in drone_states.items():
            _validate_positive_integer(drone_id, "drone_id")
            if not isinstance(state, (AtZone, InTransit, Finished)):
                raise ValueError("projected state must be a DroneState")

        connection_users: dict[int, frozenset[int]] = {}
        seen_user_ids: set[int] = set()
        for connection_id, user_ids in self.connection_users.items():
            _validate_positive_integer(connection_id, "connection_id")
            if not isinstance(user_ids, frozenset):
                raise ValueError("connection users must be a frozenset")
            for drone_id in user_ids:
                _validate_positive_integer(drone_id, "drone_id")
                if drone_id not in drone_states:
                    raise ValueError(
                        "connection user must exist in projected drone states"
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
        if not planned_drone_ids.issubset(drone_states):
            raise ValueError(
                "planned drone must exist in projected drone states"
            )
        if not planned_drone_ids.issubset(seen_user_ids):
            raise ValueError(
                "planned drone must use a connection in the projection"
            )

        object.__setattr__(
            self,
            "projected_drone_states",
            MappingProxyType(drone_states),
        )
        object.__setattr__(
            self,
            "connection_users",
            MappingProxyType(connection_users),
        )
