"""Application-specific exceptions for the Fly-in project."""

from pathlib import Path


class FlyInError(Exception):
    """Base class for expected Fly-in errors."""


class MapParseError(FlyInError):
    """Report invalid content found while parsing a map file."""

    def __init__(
        self,
        file_path: Path,
        message: str,
        line_number: int | None = None,
        line_text: str | None = None,
    ) -> None:
        """Store the location and cause of a map parsing error."""
        super().__init__(message)
        self.file_path = file_path
        self.message = message
        self.line_number = line_number
        self.line_text = line_text

    def __str__(self) -> str:
        """Return a readable message including available source context."""
        location = str(self.file_path)
        if self.line_number is not None:
            location += f":{self.line_number}"

        result = f"{location}: {self.message}"
        if self.line_text is not None:
            result += f"\n  > {self.line_text!r}"
        return result
