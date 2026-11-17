"""Fly-inマップの保持と各要素の検索処理。"""

from collections.abc import Iterable

from fly_in.connection import Connection
from fly_in.zone import Zone, ZoneRole


class DroneMap:
    """ゾーンと接続を保持し、グラフの検索機能を提供する。"""

    def __init__(
        self,
        zones: Iterable[Zone],
        connections: Iterable[Connection],
    ) -> None:
        """呼び出し側で検証済みのマップ定義から索引を構築する。"""
        self._zones: dict[int, Zone] = {}
        self._connections: dict[int, Connection] = {}
        self._connection_ids_by_zone: dict[int, list[int]] = {}
        self._connection_ids_by_pair: dict[frozenset[int], int] = {}

        for zone in zones:
            self._register_zone(zone)
        for connection in connections:
            self._register_connection(connection)

        self.start_zone_id = self._find_role(ZoneRole.START)
        self.end_zone_id = self._find_role(ZoneRole.END)

    def get_zones(self) -> list[Zone]:
        """内部索引を公開せず、全ゾーン定義を新しいリストで返す。"""
        return list(self._zones.values())

    def get_connections(self) -> list[Connection]:
        """内部索引を公開せず、全接続を新しいリストで返す。"""
        return list(self._connections.values())

    def has_zone(self, zone_id: int) -> bool:
        """指定ゾーンIDがマップに存在するかを返す。"""
        return zone_id in self._zones

    def get_zone(self, zone_id: int) -> Zone:
        """指定IDのゾーンを返す。

        Raises:
            KeyError: 指定ゾーンIDが存在しない場合。
        """
        try:
            return self._zones[zone_id]
        except KeyError as error:
            raise KeyError(f"Unknown zone ID: {zone_id}") from error

    def has_connection(self, connection_id: int) -> bool:
        """指定接続IDがマップに存在するかを返す。"""
        return connection_id in self._connections

    def get_connection(self, connection_id: int) -> Connection:
        """指定IDの接続を返す。

        Raises:
            KeyError: 指定接続IDが存在しない場合。
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
        """2つのゾーン間の接続を返し、接続がなければNoneを返す。"""
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
        """指定ゾーンを端点に持つ全接続を返す。"""
        if not self.has_zone(zone_id):
            raise KeyError(f"Unknown zone ID: {zone_id}")
        return [
            self._connections[connection_id]
            for connection_id in self._connection_ids_by_zone[zone_id]
        ]

    def get_neighbor_ids(self, zone_id: int) -> list[int]:
        """直接接続している全ゾーンのIDを返す。"""
        return [
            connection.other_zone(zone_id)
            for connection in self.get_connections_from(zone_id)
        ]

    def _register_zone(self, zone: Zone) -> None:
        """1つのゾーンを内部索引に登録する。"""
        self._zones[zone.id] = zone
        self._connection_ids_by_zone[zone.id] = []

    def _register_connection(self, connection: Connection) -> None:
        """1つの接続を内部索引に登録する。"""
        pair = frozenset((connection.zone_a_id, connection.zone_b_id))
        self._connections[connection.id] = connection
        self._connection_ids_by_pair[pair] = connection.id
        self._connection_ids_by_zone[connection.zone_a_id].append(
            connection.id
        )
        self._connection_ids_by_zone[connection.zone_b_id].append(
            connection.id
        )

    def _find_role(self, role: ZoneRole) -> int:
        """存在と一意性が検証済みの役割に対応するゾーンIDを取得する。"""
        return next(
            zone.id for zone in self._zones.values() if zone.role is role
        )
