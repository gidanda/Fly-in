"""シミュレーションの値オブジェクトで共用する整数検証。"""


def validate_positive_integer(value: int, field_name: str) -> None:
    """真偽値を除く、0より大きい整数であることを確認する。"""
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 1
    ):
        raise ValueError(f"{field_name} must be a positive integer")


def validate_non_negative_integer(value: int, field_name: str) -> None:
    """真偽値を除く、0以上の整数であることを確認する。"""
    if (
        not isinstance(value, int)
        or isinstance(value, bool)
        or value < 0
    ):
        raise ValueError(f"{field_name} must be a non-negative integer")
