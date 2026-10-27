"""Tests for ANSI terminal color conversion."""

from fly_in.terminal_colors import colorize


def test_colorize_uses_true_color_ansi_codes() -> None:
    """A supported name wraps text in its RGB color and a reset code."""
    assert colorize("movement", "orange") == (
        "\033[38;2;255;165;0mmovement\033[0m"
    )


def test_colorize_accepts_color_names_case_insensitively() -> None:
    """Map colors do not depend on letter case for display."""
    assert colorize("movement", "BLUE") == (
        "\033[38;2;0;102;255mmovement\033[0m"
    )


def test_colorize_leaves_missing_colors_unchanged() -> None:
    """A zone without color metadata keeps the terminal default."""
    assert colorize("movement", None) == "movement"


def test_colorize_uses_a_visible_fallback_for_unknown_colors() -> None:
    """Every specified color still provides visible terminal feedback."""
    assert colorize("movement", "rainbow") == (
        "\033[38;2;255;0;255mmovement\033[0m"
    )
