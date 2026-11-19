"""計算済みのシミュレーション履歴をTkウィンドウに表示する。"""

from __future__ import annotations

import tkinter as tk
from collections.abc import Sequence
from tkinter import ttk

from fly_in.drone import AtZone, Finished, InTransit
from fly_in.errors import VisualizationError
from fly_in.simulation_state import SimulationState
from fly_in.zone import ZoneRole


class SimulationViewer:
    """シミュレーションを実行・変更せず、記録済みの状態を再生する。"""

    def __init__(self, states: Sequence[SimulationState]) -> None:
        """ウィンドウを作成し、履歴の先頭の状態を表示する。"""
        # statesの確認
        if not states:
            raise VisualizationError("State history must not be empty")
        self._states = states
        self._current_index = 0
        # ウィンドウ・描画エリア作成
        try:
            self._window = tk.Tk()
        except tk.TclError as error:
            raise VisualizationError(
                f"Cannot open the graphical viewer: {error}"
            ) from error
        self._window.title("Fly-in")
        self._canvas = tk.Canvas(
            self._window, width=700, height=700,
            background="#20242b", highlightthickness=0,
        )
        # ウィンドウサイズに合わせて描画エリアを配置
        self._canvas.pack(fill=tk.BOTH, expand=True)
        # ターン数表示の作成・配置
        self._turn_label = ttk.Label(self._window)
        self._turn_label.pack(pady=6)
        # ボタンのフレーム作成・配置
        controls = ttk.Frame(self._window)
        controls.pack(pady=(0, 10))
        # メソッドを登録した各種ボタンをフレーム内に作成・左から配置
        self._reset_button = ttk.Button(
            controls, text="Reset", command=self._reset,
        )
        self._reset_button.pack(side=tk.LEFT, padx=4)
        self._back_button = ttk.Button(
            controls, text="Previous turn", command=self._previous_turn,
        )
        self._back_button.pack(side=tk.LEFT, padx=4)
        self._next_button = ttk.Button(
            controls, text="Next turn", command=self._next_turn,
        )
        self._next_button.pack(side=tk.LEFT, padx=4)
        # サイズ変更イベントに対応するメソッドの登録
        self._canvas.bind("<Configure>", self._on_resize)
        # 最初の描画
        self._draw_state()

    def run(self) -> None:
        """ウィンドウが閉じられるまで操作イベントを処理する。"""
        self._window.mainloop()

    def _next_turn(self) -> None:
        """次の状態があれば表示位置を進め、再描画する。"""
        if self._current_index < len(self._states) - 1:
            self._current_index += 1
            self._draw_state()

    def _previous_turn(self) -> None:
        """先頭より前には戻らず、1つ前の状態へ表示を切り替える。"""
        if self._current_index > 0:
            self._current_index -= 1
            self._draw_state()

    def _reset(self) -> None:
        """再計算せず、表示を履歴の先頭へ戻す。"""
        self._current_index = 0
        self._draw_state()

    def _on_resize(self, event: tk.Event[tk.Misc]) -> None:
        """Canvasのサイズ変更に合わせ、マップを再描画する。"""
        # bindで指定されたメソッドはイベントを受け取る
        self._draw_state()

    def _get_positions(self) -> dict[int, tuple[float, float]]:
        """縦横共通の倍率で、マップ座標をCanvas内に収める。"""
        # zone座標の最大最小を取得
        zones = self._states[self._current_index].drone_map.get_zones()
        min_x = min(zone.x for zone in zones)
        max_x = max(zone.x for zone in zones)
        min_y = min(zone.y for zone in zones)
        max_y = max(zone.y for zone in zones)
        # Canvasのサイズを取得
        # 初回の配置が確定する前は、Canvas作成時に指定したサイズを使う。
        width = self._canvas.winfo_width()
        height = self._canvas.winfo_height()
        if width <= 1:
            width = int(self._canvas.cget("width"))
        if height <= 1:
            height = int(self._canvas.cget("height"))
        # 座標の縦横幅・倍率取得→値の小さい方を倍率として採用
        span_x = max_x - min_x
        span_y = max_y - min_y
        scales = [
            max(width - 140, 1) / span_x if span_x else float("inf"),
            max(height - 140, 1) / span_y if span_y else float("inf"),
        ]
        scale = min(scales)
        if scale == float("inf"):
            scale = 1.0
        # 各ゾーンに対し、画面の中心＋マップの中心からの距離×倍率を辞書形式で返す
        return {
            zone.id: (
                width / 2 + (zone.x - (min_x + max_x) / 2) * scale,
                height / 2 - (zone.y - (min_y + max_y) / 2) * scale,
            )
            for zone in zones
        }

    def _draw_state(self) -> None:
        """接続・ゾーン・ドローンを再描画し、表示と操作部品を更新する。"""
        # ゾーンの座標情報を取得し、各パーツを描画
        state = self._states[self._current_index]
        positions = self._get_positions()
        self._canvas.delete("all")
        self._draw_connections(state, positions)
        self._draw_zones(state, positions)
        self._draw_drones(state, positions)
        # ターン数表示のパーツにテキスト設定追加
        self._turn_label.configure(
            text=(
                f"Turn: {state.current_turn}/"
                f"{self._states[-1].current_turn}"
            )
        )
        # 履歴の先頭（通常はターン0の初期状態）では、リセット・戻るを無効化する
        backward_state = tk.DISABLED if self._current_index == 0 else tk.NORMAL
        self._reset_button.configure(state=backward_state)
        self._back_button.configure(state=backward_state)
        # 最終ターンの場合無効化する設定を、次へボタンに適用し作成
        self._next_button.configure(
            state=(
                tk.DISABLED
                if self._current_index == len(self._states) - 1
                else tk.NORMAL
            )
        )

    def _draw_connections(
        self,
        state: SimulationState,
        positions: dict[int, tuple[float, float]],
    ) -> None:
        """ゾーンやドローンの背後に接続の線を描く。"""
        for connection in state.drone_map.get_connections():
            self._canvas.create_line(
                *positions[connection.zone_a_id],
                *positions[connection.zone_b_id],
                fill="#8a95a5", width=2,
            )

    def _draw_zones(
        self,
        state: SimulationState,
        positions: dict[int, tuple[float, float]],
    ) -> None:
        """固定サイズのゾーン記号、名前、機数と容量の表示を描く。"""
        for zone in state.drone_map.get_zones():
            # zone情報取得
            x, y = positions[zone.id]
            color = self._resolve_color(zone.color)
            # 指定したサイズの四角に収まる楕円を描画（この場合は正円）
            self._canvas.create_oval(
                x - 20, y - 20, x + 20, y + 20,
                fill=color, outline="white", width=2,
            )
            # スタート・エンドの場合は二重丸に描画
            if zone.role in (ZoneRole.START, ZoneRole.END):
                self._canvas.create_oval(
                    x - 25, y - 25, x + 25, y + 25,
                    outline=color, width=2,
                )
            # zone上方にzone_name描画
            self._canvas.create_text(
                x, y - 38, text=zone.name, fill="white",
            )
            # zone容量および滞在機体数を取得して表示
            count = state.get_zone_occupancy(zone.id)
            if zone.role is ZoneRole.END:
                count += sum(
                    isinstance(drone.state, Finished)
                    for drone in state.drones.values()
                )
            capacity = (
                "∞" if zone.has_unlimited_capacity() else str(zone.max_drones)
            )
            self._canvas.create_text(
                x, y + 38, text=f"{count}/{capacity}", fill="white",
            )

    def _draw_drones(
        self,
        state: SimulationState,
        positions: dict[int, tuple[float, float]],
    ) -> None:
        """機体を位置ごとにまとめ、各位置に最大5個の記号を描く。"""
        # 位置ごとに機体数を集計する。未登録なら0として、機体ごとに1を加える
        zone_counts: dict[int, int] = {}
        connection_counts: dict[int, int] = {}
        for drone in state.drones.values():
            if isinstance(drone.state, InTransit):
                key = drone.state.connection_id
                connection_counts[key] = connection_counts.get(key, 0) + 1
            else:
                zone_id = (
                    drone.state.zone_id if isinstance(drone.state, AtZone)
                    else state.drone_map.end_zone_id
                )
                zone_counts[zone_id] = zone_counts.get(zone_id, 0) + 1
        for zone_id, count in zone_counts.items():
            self._draw_markers(*positions[zone_id], count)
        # 接続の中点にドローンを描画
        for connection in state.drone_map.get_connections():
            count = connection_counts.get(connection.id, 0)
            ax, ay = positions[connection.zone_a_id]
            bx, by = positions[connection.zone_b_id]
            x, y = (ax + bx) / 2, (ay + by) / 2
            self._draw_markers(x, y, count)
            self._canvas.create_text(
                x, y + 18, text=f"{count}/{connection.max_capacity}",
                fill="#66e6ff",
            )

    def _draw_markers(self, x: float, y: float, count: int) -> None:
        """中心を基準に少しずつ横へずらした、小さな菱形を描く。"""
        visible = min(count, 5)
        # 中央揃えで８ピクセル間隔で配置
        for index in range(visible):
            marker_x = x + (index - (visible - 1) / 2) * 8
            # 指定した座標のポリゴンを描画
            self._canvas.create_polygon(
                marker_x, y - 5, marker_x + 4, y,
                marker_x, y + 5, marker_x - 4, y,
                fill="#ffcf40", outline="black",
            )

    def _resolve_color(self, color: str | None) -> str:
        """Tkが認識できる指定色を使用し、未指定・未対応なら白にする。"""
        if not color:
            return "white"
        try:
            self._canvas.winfo_rgb(color)
        except tk.TclError:
            return "white"
        return color
