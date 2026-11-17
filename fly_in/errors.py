"""Fly-in固有の例外。"""

from pathlib import Path


class FlyInError(Exception):
    """Fly-inで想定するエラーの共通親クラス。"""


class DroneStateError(FlyInError):
    """ドローンの現在状態では実行できない操作を報告する。"""


class TurnValidationError(FlyInError):
    """現在の状態から実行できないターン計画を報告する。"""


class PlanningError(FlyInError):
    """シミュレーションを進められる移動計画を作成できないことを報告する。"""


class VisualizationError(FlyInError):
    """GUIでシミュレーションを表示できないことを報告する。"""


class MapParseError(FlyInError):
    """マップファイルの解析中に見つかった不正な内容を報告する。"""

    def __init__(
        self,
        file_path: Path,
        message: str,
        line_number: int | None = None,
        line_text: str | None = None,
    ) -> None:
        """マップ解析エラーの発生箇所と原因を保持する。"""
        super().__init__(message)
        self.file_path = file_path
        self.message = message
        self.line_number = line_number
        self.line_text = line_text

    def __str__(self) -> str:
        """取得できたファイル・行情報を含む、読みやすいメッセージを返す。"""
        location = str(self.file_path)
        if self.line_number is not None:
            location += f":{self.line_number}"

        result = f"{location}: {self.message}"
        if self.line_text is not None:
            result += f"\n  > {self.line_text!r}"
        return result
