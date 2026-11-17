"""Fly-inシミュレーション1回分のシナリオ定義。"""

from dataclasses import dataclass

from fly_in.drone_map import DroneMap


@dataclass(frozen=True)
class Scenario:
    """呼び出し側で検証済みのマップとドローン数を保持する。"""

    drone_map: DroneMap
    drone_count: int
