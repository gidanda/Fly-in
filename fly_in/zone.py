"""Zone definitions for a Fly-in map."""

from dataclasses import dataclass
from enum import Enum


class ZoneRole(str, Enum):
    """Describe a zone's role within the whole map."""

    START = "start"
    END = "end"
    REGULAR = "regular"


class ZoneType(str, Enum):
    """Describe the movement behavior of a zone."""

    NORMAL = "normal"
    PRIORITY = "priority"
    RESTRICTED = "restricted"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class Zone:
    """Store the static definition of one map zone."""

    id: int
    name: str
    x: int
    y: int
    role: ZoneRole
    zone_type: ZoneType
    max_drones: int | None
    color: str | None

    def is_accessible(self) -> bool:
        """Return whether drones are allowed to enter this zone."""
        return self.zone_type is not ZoneType.BLOCKED

    def movement_cost(self) -> int | None:
        """Return the turns required to enter, or None when blocked."""
        if not self.is_accessible():
            return None
        if self.zone_type is ZoneType.RESTRICTED:
            return 2
        return 1

    def has_unlimited_capacity(self) -> bool:
        """Return whether this zone has no occupancy limit."""
        return self.max_drones is None
