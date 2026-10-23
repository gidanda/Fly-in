"""Dynamic state and state transitions for one drone."""

from dataclasses import dataclass

from fly_in.errors import DroneStateError


def _validate_positive_integer(value: int, field_name: str) -> None:
    """Require an integer identifier or count greater than zero."""
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 1
    ):
        raise ValueError(f"{field_name} must be a positive integer")


@dataclass(frozen=True)
class AtZone:
    """Represent a drone currently occupying one zone."""

    zone_id: int

    def __post_init__(self) -> None:
        """Validate the occupied zone identifier."""
        _validate_positive_integer(self.zone_id, "zone_id")


@dataclass(frozen=True)
class InTransit:
    """Represent a drone currently traveling along one connection."""

    connection_id: int
    destination_zone_id: int
    remaining_turns: int

    def __post_init__(self) -> None:
        """Validate identifiers and the remaining travel duration."""
        _validate_positive_integer(self.connection_id, "connection_id")
        _validate_positive_integer(
            self.destination_zone_id,
            "destination_zone_id",
        )
        _validate_positive_integer(self.remaining_turns, "remaining_turns")


@dataclass(frozen=True)
class Finished:
    """Represent a drone that has reached the end zone."""


DroneState = AtZone | InTransit | Finished


class Drone:
    """Keep one drone's immutable identity and current dynamic state."""

    def __init__(self, id: int, state: DroneState) -> None:
        """Create a drone with a positive ID and a valid state."""
        _validate_positive_integer(id, "id")
        if not isinstance(state, (AtZone, InTransit, Finished)):
            raise ValueError("state must be a valid drone state")
        self._id = id
        self._state = state

    @property
    def id(self) -> int:
        """Return this drone's immutable identifier."""
        return self._id

    @property
    def state(self) -> DroneState:
        """Return this drone's current state."""
        return self._state

    def start_move(
        self,
        connection_id: int,
        destination_zone_id: int,
        travel_turns: int,
    ) -> None:
        """Change a zone-bound drone into an in-transit state."""
        if not isinstance(self._state, AtZone):
            raise DroneStateError(
                "Only a drone at a zone can start moving"
            )
        if destination_zone_id == self._state.zone_id:
            raise ValueError("destination zone must differ from current zone")

        self._state = InTransit(
            connection_id=connection_id,
            destination_zone_id=destination_zone_id,
            remaining_turns=travel_turns,
        )

    def advance_one_turn(self, destination_is_goal: bool) -> None:
        """Advance an in-transit drone by one turn, including arrival."""
        if not isinstance(self._state, InTransit):
            raise DroneStateError(
                "Only an in-transit drone can advance one turn"
            )

        if self._state.remaining_turns > 1:
            self._state = InTransit(
                connection_id=self._state.connection_id,
                destination_zone_id=self._state.destination_zone_id,
                remaining_turns=self._state.remaining_turns - 1,
            )
            return

        if destination_is_goal:
            self._state = Finished()
        else:
            self._state = AtZone(self._state.destination_zone_id)
