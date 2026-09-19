from typing import Annotated

from pydantic import AfterValidator

ID_ERROR_MESSAGE = "IDの値が正しくありません"
_ID_MAX = 2**63 - 1


def _check_id(value: int) -> int:
    if value < 1 or value > _ID_MAX:
        raise ValueError(ID_ERROR_MESSAGE)
    return value


# SQLite INTEGER(64bit符号付き)に収まる正の整数。範囲外のID入力がDB層で
# OverflowError(500)にならず、日本語メッセージの入力検証エラー(422)になるようにする。
EntityId = Annotated[int, AfterValidator(_check_id)]
