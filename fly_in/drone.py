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


@dataclass(frozen=True)
class Drone:
    """Represent one drone at one immutable point in time."""

    id: int
    state: DroneState

    def __post_init__(self) -> None:
        """Validate the drone identifier and state."""
        _validate_positive_integer(self.id, "id")
        if not isinstance(self.state, (AtZone, InTransit, Finished)):
            raise ValueError("state must be a valid drone state")

    def start_move(
        self,
        connection_id: int,
        destination_zone_id: int,
        travel_turns: int,
    ) -> "Drone":
        """Return this zone-bound drone in a new in-transit state."""
        if not isinstance(self.state, AtZone):
            raise DroneStateError(
                "Only a drone at a zone can start moving"
            )
        if destination_zone_id == self.state.zone_id:
            raise ValueError("destination zone must differ from current zone")

        return Drone(
            id=self.id,
            state=InTransit(
                connection_id=connection_id,
                destination_zone_id=destination_zone_id,
                remaining_turns=travel_turns,
            ),
        )

    def advance_one_turn(self, destination_is_goal: bool) -> "Drone":
        """Return this in-transit drone after one turn of travel."""
        if not isinstance(self.state, InTransit):
            raise DroneStateError(
                "Only an in-transit drone can advance one turn"
            )

        if self.state.remaining_turns > 1:
            return Drone(
                id=self.id,
                state=InTransit(
                    connection_id=self.state.connection_id,
                    destination_zone_id=self.state.destination_zone_id,
                    remaining_turns=self.state.remaining_turns - 1,
                ),
            )

        if destination_is_goal:
            return Drone(self.id, Finished())
        return Drone(self.id, AtZone(self.state.destination_zone_id))
