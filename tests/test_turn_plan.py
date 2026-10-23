"""Tests for one-turn movement plan value objects."""

from dataclasses import FrozenInstanceError

import pytest

from fly_in.turn_plan import MoveIntent, TurnPlan


def test_move_intent_stores_drone_and_destination_ids() -> None:
    """A move intent identifies one drone and its intended destination."""
    intent = MoveIntent(drone_id=2, destination_zone_id=5)

    assert intent.drone_id == 2
    assert intent.destination_zone_id == 5


@pytest.mark.parametrize(
    ("drone_id", "destination_zone_id", "field_name"),
    [
        (0, 1, "drone_id"),
        (-1, 1, "drone_id"),
        (1, 0, "destination_zone_id"),
        (1, -1, "destination_zone_id"),
    ],
)
def test_move_intent_rejects_non_positive_ids(
    drone_id: int,
    destination_zone_id: int,
    field_name: str,
) -> None:
    """Move intent identifiers must be positive integers."""
    with pytest.raises(ValueError, match=field_name):
        MoveIntent(drone_id, destination_zone_id)


def test_move_intent_is_immutable() -> None:
    """A move intent cannot change after creation."""
    intent = MoveIntent(1, 2)

    with pytest.raises(FrozenInstanceError):
        setattr(intent, "destination_zone_id", 3)


def test_turn_plan_stores_an_immutable_move_tuple() -> None:
    """A turn plan keeps its supplied movements in order."""
    moves = (MoveIntent(1, 2), MoveIntent(3, 4))

    plan = TurnPlan(moves)

    assert plan.moves == moves


def test_turn_plan_allows_no_new_movements() -> None:
    """An empty plan represents a turn with no newly started movement."""
    assert TurnPlan(()).moves == ()


def test_turn_plan_rejects_duplicate_drone_ids() -> None:
    """One drone cannot start multiple movements in the same turn."""
    moves = (MoveIntent(1, 2), MoveIntent(1, 3))

    with pytest.raises(ValueError, match="duplicate drone IDs"):
        TurnPlan(moves)


def test_turn_plan_rejects_mutable_move_collection() -> None:
    """A mutable list cannot be used as a turn plan's move collection."""
    moves = [MoveIntent(1, 2)]

    with pytest.raises(ValueError, match="must be a tuple"):
        TurnPlan(moves)  # type: ignore[arg-type]


def test_turn_plan_rejects_non_move_intent_elements() -> None:
    """Every turn plan element must be a MoveIntent."""
    with pytest.raises(ValueError, match="only MoveIntent"):
        TurnPlan((object(),))  # type: ignore[arg-type]


def test_turn_plan_is_immutable() -> None:
    """A turn plan cannot replace its move collection after creation."""
    plan = TurnPlan((MoveIntent(1, 2),))

    with pytest.raises(FrozenInstanceError):
        setattr(plan, "moves", ())
