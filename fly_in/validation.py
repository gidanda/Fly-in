"""Shared integer validation for simulation value objects."""


def validate_positive_integer(value: int, field_name: str) -> None:
    """Require an integer greater than zero, excluding booleans."""
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 1
    ):
        raise ValueError(f"{field_name} must be a positive integer")


def validate_non_negative_integer(value: int, field_name: str) -> None:
    """Require an integer at least zero, excluding booleans."""
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
    ):
        raise ValueError(f"{field_name} must be a non-negative integer")
