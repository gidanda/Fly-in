"""Apply ANSI true-color codes to terminal text."""

RGBColor = tuple[int, int, int]

COLOR_RGB: dict[str, RGBColor] = {
    "black": (128, 128, 128),
    "blue": (0, 102, 255),
    "brown": (165, 90, 42),
    "crimson": (220, 20, 60),
    "cyan": (0, 255, 255),
    "darkred": (139, 0, 0),
    "gold": (255, 215, 0),
    "green": (0, 200, 0),
    "lime": (0, 255, 0),
    "magenta": (255, 0, 255),
    "maroon": (128, 0, 0),
    "orange": (255, 165, 0),
    "purple": (160, 80, 200),
    "red": (255, 0, 0),
    "violet": (238, 130, 238),
    "white": (255, 255, 255),
    "yellow": (255, 255, 0),
}

_RESET = "\033[0m"
_FALLBACK_RGB: RGBColor = (255, 0, 255)


def colorize(text: str, color_name: str | None) -> str:
    """Use a named color, magenta for unknown names, or no color for None."""
    if color_name is None:
        return text

    rgb = COLOR_RGB.get(color_name.lower(), _FALLBACK_RGB)

    red, green, blue = rgb
    prefix = f"\033[38;2;{red};{green};{blue}m"
    return f"{prefix}{text}{_RESET}"
