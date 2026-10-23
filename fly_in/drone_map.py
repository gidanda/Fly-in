"""Container and lookup operations for a Fly-in map."""

from collections.abc import Iterable

from fly_in.connection import Connection
from fly_in.errors import MapDefinitionError
from fly_in.zone import Zone, ZoneRole


class DroneMap:
    """Own zones and connections and provide graph lookups."""

    def __init__(
        self,
        zones: Iterable[Zone],
        connections: Iterable[Connection],
    ) -> None:
        """Build lookup indexes from zones and connections."""
        self._zones: dict[int, Zone] = {}
        self._zone_ids_by_name: dict[str, int] = {}
        self._connections: dict[int, Connection] = {}
        self._connection_ids_by_zone: dict[int, list[int]] = {}
        self._connection_ids_by_pair: dict[frozenset[int], int] = {}

        for zone in zones:
            self._register_zone(zone)
        for connection in connections:
            self._register_connection(connection)

        self.start_zone_id = self._find_unique_role(ZoneRole.START)
        self.end_zone_id = self._find_unique_role(ZoneRole.END)

    def has_zone(self, zone_id: int) -> bool:
        """Return whether a zone ID exists in this map."""
        return zone_id in self._zones

    def get_zone(self, zone_id: int) -> Zone:
        """Return a zone by ID.

        Raises:
            KeyError: If the zone ID does not exist.
        """
        try:
            return self._zones[zone_id]
        except KeyError as error:
            raise KeyError(f"Unknown zone ID: {zone_id}") from error

    def get_zone_id_by_name(self, name: str) -> int | None:
        """Return the ID for a zone name, or None when not found."""
        return self._zone_ids_by_name.get(name)

    def has_connection(self, connection_id: int) -> bool:
        """Return whether a connection ID exists in this map."""
        return connection_id in self._connections

    def get_connection(self, connection_id: int) -> Connection:
        """Return a connection by ID.

        Raises:
            KeyError: If the connection ID does not exist.
        """
        try:
            return self._connections[connection_id]
        except KeyError as error:
            raise KeyError(
                f"Unknown connection ID: {connection_id}"
            ) from error

    def get_connection_between(
        self,
        zone_a_id: int,
        zone_b_id: int,
    ) -> Connection | None:
        """Return the connection between two zones, if one exists."""
        if not self.has_zone(zone_a_id):
            raise KeyError(f"Unknown zone ID: {zone_a_id}")
        if not self.has_zone(zone_b_id):
            raise KeyError(f"Unknown zone ID: {zone_b_id}")

        connection_id = self._connection_ids_by_pair.get(
            frozenset((zone_a_id, zone_b_id))
        )
        if connection_id is None:
            return None
        return self._connections[connection_id]

    def get_connections_from(self, zone_id: int) -> list[Connection]:
        """Return every connection incident to a zone."""
        if not self.has_zone(zone_id):
            raise KeyError(f"Unknown zone ID: {zone_id}")
        return [
            self._connections[connection_id]
            for connection_id in self._connection_ids_by_zone[zone_id]
        ]

    def get_neighbor_ids(self, zone_id: int) -> list[int]:
        """Return IDs of all directly connected zones."""
        return [
            connection.other_zone(zone_id)
            for connection in self.get_connections_from(zone_id)
        ]

    def _register_zone(self, zone: Zone) -> None:
        """Add one zone to the internal indexes."""
        if zone.id in self._zones:
            raise MapDefinitionError(f"Duplicate zone ID: {zone.id}")
        if zone.name in self._zone_ids_by_name:
            raise MapDefinitionError(
                f"Duplicate zone name: {zone.name}"
            )

        self._zones[zone.id] = zone
        self._zone_ids_by_name[zone.name] = zone.id
        self._connection_ids_by_zone[zone.id] = []

    def _register_connection(self, connection: Connection) -> None:
        """Add one connection to the internal indexes."""
        if connection.id in self._connections:
            raise MapDefinitionError(
                f"Duplicate connection ID: {connection.id}"
            )
        if not self.has_zone(connection.zone_a_id):
            raise MapDefinitionError(
                f"Unknown zone ID in connection: {connection.zone_a_id}"
            )
        if not self.has_zone(connection.zone_b_id):
            raise MapDefinitionError(
                f"Unknown zone ID in connection: {connection.zone_b_id}"
            )

        pair = frozenset((connection.zone_a_id, connection.zone_b_id))
        if pair in self._connection_ids_by_pair:
            raise MapDefinitionError(
                "Duplicate connection between zones "
                f"{connection.zone_a_id} and {connection.zone_b_id}"
            )

        self._connections[connection.id] = connection
        self._connection_ids_by_pair[pair] = connection.id
        self._connection_ids_by_zone[connection.zone_a_id].append(
            connection.id
        )
        self._connection_ids_by_zone[connection.zone_b_id].append(
            connection.id
        )

    def _find_unique_role(self, role: ZoneRole) -> int:
        """Return the sole zone ID with the requested role."""
        matching_ids = [
            zone.id for zone in self._zones.values() if zone.role is role
        ]
        if len(matching_ids) != 1:
            raise MapDefinitionError(
                f"Map must contain exactly one {role.value} zone"
            )
        return matching_ids[0]
