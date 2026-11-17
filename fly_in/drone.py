"""1機のドローンの動的な状態と状態遷移。"""

from dataclasses import dataclass

from fly_in.errors import DroneStateError
from fly_in.validation import validate_positive_integer


@dataclass(frozen=True)
class AtZone:
    """ゾーンに滞在している状態を表す。"""

    zone_id: int

    def __post_init__(self) -> None:
        """滞在先のゾーンIDを検証する。"""
        validate_positive_integer(self.zone_id, "zone_id")


@dataclass(frozen=True)
class InTransit:
    """接続上を移動している状態を表す。"""

    connection_id: int
    destination_zone_id: int
    remaining_turns: int

    def __post_init__(self) -> None:
        """接続・到着先のIDと到着までの残りターン数を検証する。"""
        validate_positive_integer(self.connection_id, "connection_id")
        validate_positive_integer(
            self.destination_zone_id,
            "destination_zone_id",
        )
        validate_positive_integer(self.remaining_turns, "remaining_turns")


@dataclass(frozen=True)
class Finished:
    """ゴールに到着済みの状態を表す。"""


DroneState = AtZone | InTransit | Finished


@dataclass(frozen=True)
class Drone:
    """ある時点の1機のドローンを、変更不能な値として表す。"""

    id: int
    state: DroneState

    def __post_init__(self) -> None:
        """ドローンIDと状態を検証する。"""
        validate_positive_integer(self.id, "id")
        if not isinstance(self.state, (AtZone, InTransit, Finished)):
            raise ValueError("state must be a valid drone state")

    def start_move(
        self,
        connection_id: int,
        destination_zone_id: int,
        travel_turns: int,
    ) -> "Drone":
        """呼び出し側の移動検証を前提に、移動中の新しいドローンを返す。"""
        return Drone(
            id=self.id,
            state=InTransit(
                connection_id=connection_id,
                destination_zone_id=destination_zone_id,
                remaining_turns=travel_turns,
            ),
        )

    def advance_one_turn(self, destination_is_goal: bool) -> "Drone":
        """移動中のドローンを1ターン進めた新しいドローンを返す。"""
        if not isinstance(self.state, InTransit):
            raise DroneStateError(
                "Only an in-transit drone can advance one turn"
            )

        if self.state.remaining_turns > 1:
            return Drone(
                id=self.id,
                state=InTransit(
                    connection_id=self.state.connection_id,
                    destination_zone_id=self.state.destination_zone_id,
                    remaining_turns=self.state.remaining_turns - 1,
                ),
            )

        if destination_is_goal:
            return Drone(self.id, Finished())
        return Drone(self.id, AtZone(self.state.destination_zone_id))
