"""Value objects describing movements planned for one turn."""

from dataclasses import dataclass


def _validate_positive_integer(value: int, field_name: str) -> None:
    """Require an integer identifier greater than zero."""
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 1
    ):
        raise ValueError(f"{field_name} must be a positive integer")


@dataclass(frozen=True)
class MoveIntent:
    """Describe one drone's intention to start moving this turn."""

    drone_id: int
    destination_zone_id: int

    def __post_init__(self) -> None:
        """Validate the drone and destination identifiers."""
        _validate_positive_integer(self.drone_id, "drone_id")
        _validate_positive_integer(
            self.destination_zone_id,
            "destination_zone_id",
        )


@dataclass(frozen=True)
class TurnPlan:
    """Collect every new movement intended for one simulation turn."""

    moves: tuple[MoveIntent, ...]

    def __post_init__(self) -> None:
        """Require an immutable collection with one move per drone."""
        if not isinstance(self.moves, tuple):
            raise ValueError("moves must be a tuple")
        if not all(isinstance(move, MoveIntent) for move in self.moves):
            raise ValueError("moves must contain only MoveIntent objects")

        drone_ids = [move.drone_id for move in self.moves]
        if len(drone_ids) != len(set(drone_ids)):
            raise ValueError("TurnPlan cannot contain duplicate drone IDs")
