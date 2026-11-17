"""1ターン分の移動計画を表す値オブジェクト。"""

from dataclasses import dataclass


from fly_in.validation import validate_positive_integer


@dataclass(frozen=True)
class MoveIntent:
    """そのターンに1機のドローンが移動を開始する指示を表す。"""

    drone_id: int
    destination_zone_id: int

    def __post_init__(self) -> None:
        """ドローンIDと移動先ゾーンIDを検証する。"""
        validate_positive_integer(self.drone_id, "drone_id")
        validate_positive_integer(
            self.destination_zone_id,
            "destination_zone_id",
        )


@dataclass(frozen=True)
class TurnPlan:
    """実行ターン番号と、そのターンに新しく開始する全移動を保持する。"""

    execution_turn: int
    moves: tuple[MoveIntent, ...]

    def __post_init__(self) -> None:
        """実行ターンと、機体ごとに重複のない変更不能な移動列を検証する。"""
        validate_positive_integer(self.execution_turn, "execution_turn")
        if not isinstance(self.moves, tuple):
            raise ValueError("moves must be a tuple")
        if not all(isinstance(move, MoveIntent) for move in self.moves):
            raise ValueError("moves must contain only MoveIntent objects")

        drone_ids = [move.drone_id for move in self.moves]
        if len(drone_ids) != len(set(drone_ids)):
            raise ValueError("TurnPlan cannot contain duplicate drone IDs")
