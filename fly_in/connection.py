"""Fly-inマップの接続定義。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Connection:
    """2つのゾーンを結ぶ双方向の接続を保持する。"""

    id: int
    zone_a_id: int
    zone_b_id: int
    max_capacity: int

    def connects(self, zone_id: int) -> bool:
        """指定ゾーンがこの接続の端点に含まれるかを返す。"""
        return zone_id in (self.zone_a_id, self.zone_b_id)

    def other_zone(self, zone_id: int) -> int:
        """指定ゾーンと反対側の端点のゾーンIDを返す。

        Raises:
            ValueError: 指定ゾーンがこの接続の端点ではない場合。
        """
        if zone_id == self.zone_a_id:
            return self.zone_b_id
        if zone_id == self.zone_b_id:
            return self.zone_a_id
        raise ValueError(
            f"Zone {zone_id} is not part of connection {self.id}"
        )
