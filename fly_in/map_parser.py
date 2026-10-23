"""Parse Fly-in map files into validated scenarios."""

import re
from collections.abc import Mapping
from pathlib import Path

from fly_in.connection import Connection
from fly_in.drone_map import DroneMap
from fly_in.errors import MapParseError
from fly_in.scenario import Scenario
from fly_in.zone import Zone, ZoneRole, ZoneType


_DRONE_COUNT_PATTERN = re.compile(
    r"nb_drones: (?P<count>\S+)"
)
_ZONE_PATTERN = re.compile(
    r"(?P<kind>start_hub|end_hub|hub): "
    r"(?P<name>[^\s-]+) "
    r"(?P<x>\S+) "
    r"(?P<y>\S+)"
    r"(?: (?P<metadata>.+))?"
)
_CONNECTION_PATTERN = re.compile(
    r"connection: "
    r"(?P<zone_a>[^\s-]+)-(?P<zone_b>[^\s-]+)"
    r"(?: (?P<metadata>.+))?"
)


class MapParser:
    """Convert one map file into a Scenario without retaining state."""

    def parse_file(self, file_path: str | Path) -> Scenario:
        """Parse and validate a map file.

        Args:
            file_path: Path to the UTF-8 encoded map file.

        Returns:
            A scenario containing the parsed map and drone count.

        Raises:
            FileNotFoundError: If the map file does not exist.
            PermissionError: If the map file cannot be read.
            UnicodeDecodeError: If the map file is not valid UTF-8.
            MapParseError: If the file content is invalid.
        """
        path = Path(file_path)
        drone_count: int | None = None
        zones: list[Zone] = []
        connections: list[Connection] = []
        zone_ids_by_name: dict[str, int] = {}
        connection_pairs: set[tuple[int, int]] = set()
        start_seen = False
        end_seen = False
        definition_seen = False

        with path.open(encoding="utf-8") as map_file:
            for line_number, raw_line in enumerate(map_file, start=1):
                line = raw_line.removesuffix("\n")
                if line == "" or line.startswith("#"):
                    continue

                if "\t" in line:
                    raise MapParseError(
                        path,
                        "Tab characters are not allowed",
                        line_number,
                        line,
                    )
                if any(
                    character.isspace() and character != " "
                    for character in line
                ):
                    raise MapParseError(
                        path,
                        "Only ASCII spaces are allowed between elements",
                        line_number,
                        line,
                    )
                if line != line.strip():
                    raise MapParseError(
                        path,
                        "Leading and trailing spaces are not allowed",
                        line_number,
                        line,
                    )
                if "  " in line:
                    raise MapParseError(
                        path,
                        "Elements must be separated by exactly one "
                        "ASCII space",
                        line_number,
                        line,
                    )
                definition_seen = True

                if drone_count is None:
                    if not line.startswith("nb_drones"):
                        raise MapParseError(
                            path,
                            "The first definition must be "
                            "'nb_drones: <positive_integer>'",
                            line_number,
                            line,
                        )
                    drone_count = self._parse_drone_count(
                        path,
                        line_number,
                        line,
                    )
                    continue

                if line.startswith("nb_drones"):
                    raise MapParseError(
                        path,
                        "nb_drones must be defined exactly once",
                        line_number,
                        line,
                    )

                if line.startswith(("start_hub", "end_hub", "hub")):
                    zone = self._parse_zone(
                        path,
                        line_number,
                        line,
                        len(zones) + 1,
                    )
                    if zone.name in zone_ids_by_name:
                        raise MapParseError(
                            path,
                            f"Duplicate zone name: {zone.name!r}",
                            line_number,
                            line,
                        )
                    if zone.role is ZoneRole.START:
                        if start_seen:
                            raise MapParseError(
                                path,
                                "start_hub must be defined exactly once",
                                line_number,
                                line,
                            )
                        start_seen = True
                    elif zone.role is ZoneRole.END:
                        if end_seen:
                            raise MapParseError(
                                path,
                                "end_hub must be defined exactly once",
                                line_number,
                                line,
                            )
                        end_seen = True

                    zones.append(zone)
                    zone_ids_by_name[zone.name] = zone.id
                    continue

                if line.startswith("connection"):
                    connection = self._parse_connection(
                        path,
                        line_number,
                        line,
                        len(connections) + 1,
                        zone_ids_by_name,
                    )
                    if connection.zone_a_id < connection.zone_b_id:
                        pair = (
                            connection.zone_a_id,
                            connection.zone_b_id,
                        )
                    else:
                        pair = (
                            connection.zone_b_id,
                            connection.zone_a_id,
                        )
                    if pair in connection_pairs:
                        zone_a_name = zones[pair[0] - 1].name
                        zone_b_name = zones[pair[1] - 1].name
                        raise MapParseError(
                            path,
                            "Duplicate connection between "
                            f"{zone_a_name!r} and {zone_b_name!r}",
                            line_number,
                            line,
                        )
                    connection_pairs.add(pair)
                    connections.append(connection)
                    continue

                raise MapParseError(
                    path,
                    "Unknown definition; expected nb_drones, "
                    "start_hub, end_hub, hub, or connection",
                    line_number,
                    line,
                )

        if not definition_seen:
            raise MapParseError(path, "Map file contains no definitions")
        if not start_seen:
            raise MapParseError(
                path,
                "Map must contain exactly one start_hub definition",
            )
        if not end_seen:
            raise MapParseError(
                path,
                "Map must contain exactly one end_hub definition",
            )

        if drone_count is None:
            raise MapParseError(
                path,
                "Missing required nb_drones definition",
            )

        drone_map = DroneMap(zones, connections)
        return Scenario(drone_map, drone_count)

    def _parse_drone_count(
        self,
        file_path: Path,
        line_number: int,
        line: str,
    ) -> int:
        """Parse one drone-count definition."""
        match = _DRONE_COUNT_PATTERN.fullmatch(line)
        if match is None:
            raise MapParseError(
                file_path,
                "Invalid nb_drones definition; expected "
                "'nb_drones: <positive_integer>'",
                line_number,
                line,
            )

        try:
            drone_count = int(match.group("count"))
        except ValueError as error:
            raise MapParseError(
                file_path,
                "nb_drones must be an integer",
                line_number,
                line,
            ) from error
        if drone_count < 1:
            raise MapParseError(
                file_path,
                "nb_drones must be a positive integer",
                line_number,
                line,
            )
        return drone_count

    def _parse_zone(
        self,
        file_path: Path,
        line_number: int,
        line: str,
        zone_id: int,
    ) -> Zone:
        """Parse one zone definition into a Zone."""
        match = _ZONE_PATTERN.fullmatch(line)
        if match is None:
            raise MapParseError(
                file_path,
                "Invalid zone definition; expected "
                "'<kind>: <name> <x> <y> [metadata]'",
                line_number,
                line,
            )

        try:
            x = int(match.group("x"))
            y = int(match.group("y"))
        except ValueError as error:
            raise MapParseError(
                file_path,
                "Zone coordinates must be integers",
                line_number,
                line,
            ) from error

        role_by_kind = {
            "start_hub": ZoneRole.START,
            "end_hub": ZoneRole.END,
            "hub": ZoneRole.REGULAR,
        }
        role = role_by_kind[match.group("kind")]
        metadata = self._parse_metadata(
            file_path,
            line_number,
            line,
            match.group("metadata"),
        )

        allowed_keys = {"zone", "color", "max_drones"}
        unknown_keys = sorted(metadata.keys() - allowed_keys)
        if unknown_keys:
            raise MapParseError(
                file_path,
                f"Unknown zone metadata key: {unknown_keys[0]!r}",
                line_number,
                line,
            )

        zone_type_text = metadata.get("zone", ZoneType.NORMAL.value)
        try:
            zone_type = ZoneType(zone_type_text)
        except ValueError as error:
            raise MapParseError(
                file_path,
                f"Invalid zone type {zone_type_text!r}; expected "
                "normal, blocked, restricted, or priority",
                line_number,
                line,
            ) from error

        color = metadata.get("color")
        max_drones: int | None
        if role in (ZoneRole.START, ZoneRole.END):
            max_drones = None
        else:
            max_drones_text = metadata.get("max_drones", "1")
            try:
                max_drones = int(max_drones_text)
            except ValueError as error:
                raise MapParseError(
                    file_path,
                    "max_drones must be an integer",
                    line_number,
                    line,
                ) from error
            if max_drones < 1:
                raise MapParseError(
                    file_path,
                    "max_drones must be a positive integer",
                    line_number,
                    line,
                )

        return Zone(
            id=zone_id,
            name=match.group("name"),
            x=x,
            y=y,
            role=role,
            zone_type=zone_type,
            max_drones=max_drones,
            color=color,
        )

    def _parse_connection(
        self,
        file_path: Path,
        line_number: int,
        line: str,
        connection_id: int,
        zone_ids_by_name: Mapping[str, int],
    ) -> Connection:
        """Parse one connection definition into a Connection."""
        match = _CONNECTION_PATTERN.fullmatch(line)
        if match is None:
            raise MapParseError(
                file_path,
                "Invalid connection definition; expected "
                "'connection: <name1>-<name2> [metadata]'",
                line_number,
                line,
            )

        zone_a_name = match.group("zone_a")
        zone_b_name = match.group("zone_b")
        if zone_a_name == zone_b_name:
            raise MapParseError(
                file_path,
                "Connection endpoints must be different",
                line_number,
                line,
            )
        for zone_name in (zone_a_name, zone_b_name):
            if zone_name not in zone_ids_by_name:
                raise MapParseError(
                    file_path,
                    f"Connection references zone {zone_name!r} "
                    "before it is defined",
                    line_number,
                    line,
                )

        metadata = self._parse_metadata(
            file_path,
            line_number,
            line,
            match.group("metadata"),
        )
        allowed_keys = {"max_link_capacity"}
        unknown_keys = sorted(metadata.keys() - allowed_keys)
        if unknown_keys:
            raise MapParseError(
                file_path,
                f"Unknown connection metadata key: {unknown_keys[0]!r}",
                line_number,
                line,
            )

        capacity_text = metadata.get("max_link_capacity", "1")
        try:
            max_capacity = int(capacity_text)
        except ValueError as error:
            raise MapParseError(
                file_path,
                "max_link_capacity must be an integer",
                line_number,
                line,
            ) from error
        if max_capacity < 1:
            raise MapParseError(
                file_path,
                "max_link_capacity must be a positive integer",
                line_number,
                line,
            )

        return Connection(
            id=connection_id,
            zone_a_id=zone_ids_by_name[zone_a_name],
            zone_b_id=zone_ids_by_name[zone_b_name],
            max_capacity=max_capacity,
        )

    def _parse_metadata(
        self,
        file_path: Path,
        line_number: int,
        line: str,
        metadata_text: str | None,
    ) -> dict[str, str]:
        """Parse a shared key-value metadata block."""
        if metadata_text is None:
            return {}

        match = re.fullmatch(r"\[(?P<content>.*)\]", metadata_text)
        if match is None:
            raise MapParseError(
                file_path,
                "Invalid metadata; expected '[key=value ...]'",
                line_number,
                line,
            )

        content = match.group("content")
        if not content or "[" in content or "]" in content:
            raise MapParseError(
                file_path,
                "Invalid metadata; expected '[key=value ...]'",
                line_number,
                line,
            )

        metadata: dict[str, str] = {}
        for item in content.split(" "):
            if item.count("=") != 1:
                raise MapParseError(
                    file_path,
                    "Invalid metadata; expected '[key=value ...]'",
                    line_number,
                    line,
                )
            key, value = item.split("=", 1)
            if not key or not value:
                raise MapParseError(
                    file_path,
                    "Metadata keys and values must not be empty",
                    line_number,
                    line,
                )
            if key in metadata:
                raise MapParseError(
                    file_path,
                    f"Duplicate metadata key: {key!r}",
                    line_number,
                    line,
                )
            metadata[key] = value
        return metadata
