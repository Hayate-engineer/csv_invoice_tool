from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional, Tuple


# 列名ゆれ対応（ここが実務で超大事）
COLUMN_MAP = {
    "date": "date",
    "day": "date",
    "日付": "date",

    "product": "item",
    "item_name": "item",
    "商品名": "item",

    "price": "price",
    "単価": "price",

    "quantity": "quantity",
    "数量": "quantity",

    "amount": "amount",
    "金額": "amount",
}


@dataclass(frozen=True)
class NormalizedRow:
    date: str        # YYYY-MM-DD
    store: str
    item: str
    quantity: int
    amount: int


def _to_int(value: str) -> Optional[int]:
    value = (value or "").strip()
    if value == "":
        return None
    # カンマや全角数字が混ざる想定もあるが、最小版なのでまずはカンマだけ除去
    value = value.replace(",", "")
    try:
        return int(value)
    except ValueError:
        return None


def _parse_date(value: str) -> Optional[str]:
    value = (value or "").strip()
    if value == "":
        return None

    patterns = ["%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d"]
    for p in patterns:
        try:
            dt = datetime.strptime(value, p)
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            continue
    return None


def normalize_row(raw: Dict[str, str], store: str) -> Tuple[Optional[NormalizedRow], Optional[str]]:
    """
    生のrow(dict)を正規化する。
    戻り値: (正規化成功ならNormalizedRow, 失敗ならエラーメッセージ)
    """
    # 1) 列名を揃える（必要なキーだけにする）
    unified: Dict[str, str] = {}
    for k, v in raw.items():
        key = COLUMN_MAP.get(k.strip())
        if key:
            unified[key] = (v or "").strip()

    date = _parse_date(unified.get("date", ""))
    item = unified.get("item", "").strip()

    qty = _to_int(unified.get("quantity", ""))
    amount = _to_int(unified.get("amount", ""))

    price = _to_int(unified.get("price", ""))

    # 2) 必須チェック
    if date is None:
        return None, "dateが不正/空です"
    if item == "":
        return None, "itemが空です"

    # quantityは必須
    if qty is None:
        return None, "quantityが不正/空です"

    # 3) amountが無ければ price×quantity で作る
    if amount is None:
        if price is None:
            return None, "amountもpriceも不正/空です（計算できません）"
        amount = price * qty

    # 4) 正規化結果
    return NormalizedRow(
        date=date,
        store=store,
        item=item,
        quantity=qty,
        amount=amount,
    ), None