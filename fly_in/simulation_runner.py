"""Fly-inシミュレーションを初期状態から全機到着まで実行する。"""

from fly_in.simulation_state import SimulationState
from fly_in.turn_formatter import TurnFormatter
from fly_in.turn_planner import TurnPlanner


class SimulationRunner:
    """移動計画の作成・状態遷移・ターミナル出力を連携させる。"""

    def __init__(
        self,
        planner: TurnPlanner,
        formatter: TurnFormatter,
    ) -> None:
        """各ターンで使用する計画作成・文字列整形の担当オブジェクトを保持する。"""
        self._planner = planner
        self._formatter = formatter

    def run(
        self,
        initial_state: SimulationState,
    ) -> list[SimulationState]:
        """各ターンの移動を出力し、初期状態を含む状態履歴を返す。"""
        state = initial_state
        states = [initial_state]

        while not state.all_drones_finished():
            plan = self._planner.create_plan(state)
            projection = state.preview_turn(plan)
            print(self._formatter.format_turn(state, projection))
            state = projection.next_state
            states.append(state)

        return states
