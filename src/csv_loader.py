from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, Iterator, Tuple


def iter_csv_rows(csv_path: Path) -> Iterator[Tuple[int, Dict[str, str]]]:
    """
    CSVを1行ずつ dict で返す。
    戻り値: (行番号(2開始), 行データ{列名:値})
    """
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader, start=2):  # 1行目はヘッダーなので2から
            # DictReaderは欠損列があると None キーを作ることがあるので除去
            row = {k: (v if v is not None else "") for k, v in row.items() if k is not None}
            yield i, row


def list_input_csvs(input_dir: Path, month: str) -> list[Path]:
    """
    input_dir配下から `*_YYYY_MM.csv` のようなCSVを探す。
    例: month="2026-01" -> suffix "2026_01"
    """
    month_suffix = month.replace("-", "_")
    if not input_dir.exists():
        return []

    return sorted(input_dir.glob(f"*_{month_suffix}.csv"))


def infer_store_name(csv_path: Path) -> str:
    """
    ファイル名から店舗名っぽいものを作る。
    例: store_a_2026_01.csv -> store_a
    """
    name = csv_path.stem  # store_a_2026_01
    parts = name.split("_")
    if len(parts) >= 3:
        return "_".join(parts[:-2])  # 後ろの 2026_01 を落とす
    return name