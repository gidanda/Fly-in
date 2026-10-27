"""Tests for drone states and local state transitions."""

from dataclasses import FrozenInstanceError

import pytest

from fly_in.drone import AtZone, Drone, Finished, InTransit
from fly_in.errors import DroneStateError


@pytest.mark.parametrize(
    ("state_factory", "field_name"),
    [
        (lambda: AtZone(0), "zone_id"),
        (lambda: InTransit(0, 2, 1), "connection_id"),
        (lambda: InTransit(1, 0, 1), "destination_zone_id"),
        (lambda: InTransit(1, 2, 0), "remaining_turns"),
    ],
)
def test_states_reject_non_positive_values(
    state_factory: object,
    field_name: str,
) -> None:
    """State identifiers and remaining turns must be positive."""
    assert callable(state_factory)
    with pytest.raises(ValueError, match=field_name):
        state_factory()


def test_states_are_immutable() -> None:
    """A state object cannot be changed after creation."""
    state = InTransit(1, 2, 2)

    with pytest.raises(FrozenInstanceError):
        setattr(state, "remaining_turns", 1)


def test_drone_rejects_invalid_id_and_state() -> None:
    """A drone requires a positive ID and one supported state."""
    with pytest.raises(ValueError, match="id"):
        Drone(0, AtZone(1))
    with pytest.raises(ValueError, match="valid drone state"):
        Drone(1, object())  # type: ignore[arg-type]


def test_drone_is_immutable() -> None:
    """Callers can observe but cannot replace either drone field."""
    drone = Drone(1, AtZone(2))

    assert drone.id == 1
    assert drone.state == AtZone(2)
    with pytest.raises(AttributeError):
        setattr(drone, "id", 2)
    with pytest.raises(AttributeError):
        setattr(drone, "state", Finished())


def test_start_move_returns_new_in_transit_drone() -> None:
    """Moving returns a new snapshot and preserves the original."""
    drone = Drone(1, AtZone(2))

    moved_drone = drone.start_move(3, 4, 2)

    assert moved_drone == Drone(1, InTransit(3, 4, 2))
    assert drone == Drone(1, AtZone(2))


@pytest.mark.parametrize("state", [InTransit(1, 2, 1), Finished()])
def test_start_move_requires_at_zone_state(
    state: InTransit | Finished,
) -> None:
    """Moving and finished drones cannot start another movement."""
    drone = Drone(1, state)

    with pytest.raises(DroneStateError, match="at a zone"):
        drone.start_move(1, 2, 1)


def test_start_move_rejects_current_zone_as_destination() -> None:
    """A movement must lead to a different zone."""
    drone = Drone(1, AtZone(2))

    with pytest.raises(ValueError, match="differ"):
        drone.start_move(1, 2, 1)


def test_advance_one_turn_decrements_remaining_turns() -> None:
    """A non-arriving drone remains in transit for one fewer turn."""
    drone = Drone(1, InTransit(3, 4, 2))

    advanced_drone = drone.advance_one_turn(destination_is_goal=False)

    assert advanced_drone == Drone(1, InTransit(3, 4, 1))
    assert drone == Drone(1, InTransit(3, 4, 2))


def test_advance_one_turn_arrives_at_regular_zone() -> None:
    """A final travel turn places a drone at its destination zone."""
    drone = Drone(1, InTransit(3, 4, 1))

    advanced_drone = drone.advance_one_turn(destination_is_goal=False)

    assert advanced_drone == Drone(1, AtZone(4))
    assert drone == Drone(1, InTransit(3, 4, 1))


def test_advance_one_turn_finishes_at_goal() -> None:
    """A final travel turn marks a drone whose destination is the goal."""
    drone = Drone(1, InTransit(3, 4, 1))

    advanced_drone = drone.advance_one_turn(destination_is_goal=True)

    assert advanced_drone == Drone(1, Finished())
    assert drone == Drone(1, InTransit(3, 4, 1))


@pytest.mark.parametrize("state", [AtZone(1), Finished()])
def test_advance_one_turn_requires_in_transit_state(
    state: AtZone | Finished,
) -> None:
    """Only a moving drone can advance a travel turn."""
    drone = Drone(1, state)

    with pytest.raises(DroneStateError, match="in-transit"):
        drone.advance_one_turn(destination_is_goal=False)
