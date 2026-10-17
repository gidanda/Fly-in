"""Connection definitions for a Fly-in map."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Connection:
    """Store a bidirectional connection between two zones."""

    id: int
    zone_a_id: int
    zone_b_id: int
    max_capacity: int

    def connects(self, zone_id: int) -> bool:
        """Return whether this connection contains the given zone."""
        return zone_id in (self.zone_a_id, self.zone_b_id)

    def other_zone(self, zone_id: int) -> int:
        """Return the zone at the opposite end of this connection.

        Raises:
            ValueError: If the given zone is not part of this connection.
        """
        if zone_id == self.zone_a_id:
            return self.zone_b_id
        if zone_id == self.zone_b_id:
            return self.zone_a_id
        raise ValueError(
            f"Zone {zone_id} is not part of connection {self.id}"
        )
