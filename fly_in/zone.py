"""Fly-inマップのゾーン定義。"""

from dataclasses import dataclass
from enum import Enum


class ZoneRole(str, Enum):
    """マップ全体におけるゾーンの役割を表す。"""

    START = "start"
    END = "end"
    REGULAR = "regular"


class ZoneType(str, Enum):
    """移動コストや進入可否を決めるゾーン種別を表す。"""

    NORMAL = "normal"
    PRIORITY = "priority"
    RESTRICTED = "restricted"
    BLOCKED = "blocked"


@dataclass(frozen=True)
class Zone:
    """1つのゾーンの静的な定義を保持する。"""

    id: int
    name: str
    x: int
    y: int
    role: ZoneRole
    zone_type: ZoneType
    max_drones: int | None
    color: str | None

    def is_accessible(self) -> bool:
        """このゾーンにドローンが進入できるかを返す。"""
        return self.zone_type is not ZoneType.BLOCKED

    def movement_cost(self) -> int | None:
        """進入に必要なターン数を返し、進入禁止ならNoneを返す。"""
        if not self.is_accessible():
            return None
        if self.zone_type is ZoneType.RESTRICTED:
            return 2
        return 1

    def has_unlimited_capacity(self) -> bool:
        """このゾーンの滞在容量が無制限かを返す。"""
        return self.max_drones is None
