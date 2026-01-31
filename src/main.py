# src/main.py
from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Dict, List

from .csv_loader import infer_store_name, iter_csv_rows, list_input_csvs
from .normalizer import NormalizedRow, normalize_row
from .aggregator import aggregate
from .invoice_generator import generate_invoices_from_summary


def write_csv(path: Path, header: List[str], rows: List[Dict[str, str]]) -> None:
    """
    CSVを書き出す共通関数
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def main() -> int:
    # --------------------------------------------------
    # 0. コマンドライン引数を受け取る
    # --------------------------------------------------
    parser = argparse.ArgumentParser()
    parser.add_argument("--month", required=True, help="例: 2026-01")
    parser.add_argument("--debug", action="store_true")
    args = parser.parse_args()

    # --------------------------------------------------
    # フォルダの場所を決める
    # --------------------------------------------------
    base_dir = Path(__file__).resolve().parents[1]  # csv_invoice_tool/
    input_dir = base_dir / "input"
    output_dir = base_dir / "output"
    invoices_dir = output_dir / "invoices"

    # ==================================================
    # ① 全部のCSVを開いて（対象ファイルを集める）
    # ==================================================
    csv_paths = list_input_csvs(input_dir, args.month)

    if not csv_paths:
        print(f"[WARN] 対象CSVが見つかりません: {input_dir}")
        return 1

    # 正規化に成功した行を入れる箱
    normalized: List[NormalizedRow] = []

    # エラーになった行を入れる箱
    error_rows: List[Dict[str, str]] = []

    # CSVファイルを1つずつ処理
    for csv_path in csv_paths:
        store = infer_store_name(csv_path)

        # ==================================================
        # ① CSVを開いて、1行ずつ読む
        # ==================================================
        for line_no, raw_row in iter_csv_rows(csv_path):

            # ==================================================
            # ② 同じ形（ルール）に並べ直して
            #    ・列名をそろえる
            #    ・日付を統一する
            #    ・数字に変換する
            # ==================================================
            row, err = normalize_row(raw_row, store=store)

            # ==================================================
            # ③ おかしい行は別にメモして
            # ==================================================
            if err:
                error_rows.append({
                    "file": csv_path.name,
                    "line": str(line_no),
                    "store": store,
                    "reason": err,
                    "raw": str(raw_row),
                })
                continue  # 次の行へ

            # ==================================================
            # ④ OKな行だけで合計を出すために集める
            # ==================================================
            normalized.append(row)

    # ==================================================
    # ⑤ 結果をファイルにして保存して
    # ==================================================

    # ⑤-1 正規化されたデータ一覧
    write_csv(
        output_dir / "normalized.csv",
        header=["date", "store", "item", "quantity", "amount"],
        rows=[{
            "date": r.date,
            "store": r.store,
            "item": r.item,
            "quantity": str(r.quantity),
            "amount": str(r.amount),
        } for r in normalized],
    )

    # ⑤-2 エラー一覧
    write_csv(
        output_dir / "errors.csv",
        header=["file", "line", "store", "reason", "raw"],
        rows=error_rows,
    )

    # ==================================================
    # ④（続き） OKな行だけを使って合計を出す
    # ==================================================
    result = aggregate(normalized)

    # ⑤-3 店舗別合計
    summary_by_store_path = output_dir / "summary_by_store.csv"
    write_csv(
        output_dir / "summary_by_store.csv",
        header=["store", "total_amount"],
        rows=[{"store": k, "total_amount": str(v)}
              for k, v in sorted(result.by_store.items())],
    )

    # ⑤-4 商品別合計
    write_csv(
        output_dir / "summary_by_item.csv",
        header=["item", "total_amount"],
        rows=[{"item": k, "total_amount": str(v)}
              for k, v in sorted(result.by_item.items())],
    )

    print("[OK] STEP1 完了しました")


# ==================================================
# STEP2: summary_by_store.csv から請求書PDFを生成
# ==================================================
    created_pdfs = generate_invoices_from_summary(
        summary_csv=summary_by_store_path,
        out_dir=invoices_dir,
        month=args.month,
        tax_rate=0.10,
    )

    print("[OK] STEP1 + STEP2 完了しました")
    print(f" - invoices: {invoices_dir}")
    if args.debug:
        for p in created_pdfs:
            print(f"   - {p.name}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())