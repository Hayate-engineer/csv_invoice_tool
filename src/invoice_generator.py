# src/invoice_generator.py
from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import List

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

# ★追加（日本語フォント登録用）
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib import colors

from .config import (
    LOGO_PATH,
    FONT_PATH,
    LOGO_WIDTH,
    ISSUER_NAME,
    ISSUER_ADDRESS,
    ISSUER_TEL,
    ISSUER_EMAIL,
    PAYMENT_DUE_DAYS,
    BANK_NAME,
    BANK_BRANCH,
    BANK_ACCOUNT,
    BANK_ACCOUNT_NAME,
    NOTES,
)


@dataclass(frozen=True)
class Invoice:
    invoice_no: str
    issue_date: str          # YYYY-MM-DD
    bill_to: str             # 店舗名
    subtotal: int            # 税抜
    tax_rate: float          # 0.10 など
    tax: int                 # 税額
    total: int               # 税込合計


def _yen(n: int) -> str:
    """3桁カンマの円表示（日本語フォントで表示できる文字にする）"""
    return f"{n:,} 円"


def _calc_tax(subtotal: int, tax_rate: float) -> int:
    """税額（四捨五入）"""
    return int(round(subtotal * tax_rate))


def _make_invoice_no(store: str, month: str) -> str:
    """請求書番号（例）INV-202601-store_a"""
    yyyymm = month.replace("-", "")
    safe = store.replace(" ", "_")
    return f"INV-{yyyymm}-{safe}"


def load_summary_by_store(summary_csv: Path) -> List[tuple[str, int]]:
    """
    summary_by_store.csv を読み込む
    形式: store,total_amount
    """
    rows: List[tuple[str, int]] = []
    with summary_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            store = (row.get("store") or "").strip()
            total_amount = (row.get("total_amount") or "").strip()
            if store == "" or total_amount == "":
                continue
            rows.append((store, int(total_amount)))
    return rows


def build_invoices(
    summary_rows: List[tuple[str, int]],
    month: str,
    tax_rate: float = 0.10
) -> List[Invoice]:
    """
    店舗別合計から請求書データを作る
    """
    issue = date.today().strftime("%Y-%m-%d")

    invoices: List[Invoice] = []
    for store, subtotal in summary_rows:
        inv_no = _make_invoice_no(store, month)
        tax = _calc_tax(subtotal, tax_rate)
        total = subtotal + tax

        invoices.append(
            Invoice(
                invoice_no=inv_no,
                issue_date=issue,
                bill_to=store,
                subtotal=subtotal,
                tax_rate=tax_rate,
                tax=tax,
                total=total,
            )
        )
    return invoices


# ★追加：日本語フォント登録（1回だけ）
_FONT_REGISTERED = False


def _ensure_japanese_font_registered() -> None:
    """
    assets/fonts/NotoSansJP-Regular.otf を登録して、
    PDFで日本語が '■' にならないようにする。
    """
    global _FONT_REGISTERED
    if _FONT_REGISTERED:
        return

    font_path = FONT_PATH

    if not font_path.exists():
        raise FileNotFoundError(
            f"日本語フォントが見つかりません: {font_path}\n"
            "assets/fonts/ に NotoSansJP-Regular.otf を置いてください。"
        )

    pdfmetrics.registerFont(TTFont("NotoSansJP", str(font_path)))
    _FONT_REGISTERED = True


def render_invoice_pdf(invoice: Invoice, out_path: Path) -> None:
    """
    ヘッダー2カラム + 発行者/支払情報つきの請求書PDF（業務向け）
    """
    out_path.parent.mkdir(parents=True, exist_ok=True)
    _ensure_japanese_font_registered()

    # 支払期限（発行日 + N日）
    issue_dt = date.fromisoformat(invoice.issue_date)
    due_dt = issue_dt + timedelta(days=PAYMENT_DUE_DAYS)
    due_str = due_dt.strftime("%Y-%m-%d")

    doc = SimpleDocTemplate(
        str(out_path),
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40,
    )

    styles = getSampleStyleSheet()
    styles["Normal"].fontName = "NotoSansJP"
    styles["Normal"].fontSize = 10
    styles["Normal"].leading = 14

    title_style = ParagraphStyle(
        "Title",
        parent=styles["Normal"],
        fontSize=20,
        leading=24,
    )

    right_style = ParagraphStyle(
        "Right",
        parent=styles["Normal"],
        alignment=TA_RIGHT,
    )

    section_title = ParagraphStyle(
        "SectionTitle",
        parent=styles["Normal"],
        fontSize=11,
        leading=16,
    )

    elements: list = []

    # ==================================================
    # STEP3-① ヘッダー2カラム
    # 左：ロゴ（任意）＋発行者情報 / 右：INVOICE・番号・日付
    # ==================================================

    # ★ロゴパス（assets/logo.png）
    logo_path = LOGO_PATH

    left_header = []

    # ★ロゴが存在すれば表示（無ければスキップ）
    if logo_path.exists():
        # ロゴは幅だけ指定（縦横比は自動）
        logo_img = Image(str(logo_path), width=LOGO_WIDTH, height=None)
        left_header.append(logo_img)
        left_header.append(Spacer(1, 6))  # ロゴと文字の間に余白

    # 発行者情報
    left_header.extend([
        Paragraph(f"<b>{ISSUER_NAME}</b>", styles["Normal"]),
        Paragraph(ISSUER_ADDRESS, styles["Normal"]),
        Paragraph(ISSUER_TEL, styles["Normal"]),
        Paragraph(ISSUER_EMAIL, styles["Normal"]),
    ])

    right_header = [
        Paragraph("INVOICE", title_style),
        Paragraph(f"<b>Invoice No:</b> {invoice.invoice_no}", right_style),
        Paragraph(f"<b>Issue Date:</b> {invoice.issue_date}", right_style),
        Paragraph(f"<b>Due Date:</b> {due_str}", right_style),
    ]

    header_table = Table(
        [[left_header, right_header]],
        colWidths=[280, 170],
        hAlign="LEFT",
    )
    header_table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )

    elements.append(header_table)
    elements.append(Spacer(1, 10))

    # 仕切り線
    line = Table([[""]], colWidths=[450], rowHeights=[1])
    line.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 1, colors.grey)]))
    elements.append(line)
    elements.append(Spacer(1, 14))

    # 請求先
    elements.append(Paragraph("<b>Bill To</b>", section_title))
    elements.append(Paragraph(f"{invoice.bill_to} 御中", styles["Normal"]))
    elements.append(Spacer(1, 14))

    # ==================================================
    # 金額テーブル
    # ==================================================
    table_data = [
        ["項目", "金額"],
        ["小計（税抜）", _yen(invoice.subtotal)],
        [f"消費税（{int(invoice.tax_rate * 100)}%）", _yen(invoice.tax)],
        ["合計（税込）", _yen(invoice.total)],
    ]

    money_table = Table(
        table_data,
        colWidths=[300, 150],
        hAlign="RIGHT",
    )
    money_table.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), "NotoSansJP"),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("BACKGROUND", (0, -1), (-1, -1), colors.whitesmoke),
                ("FONTSIZE", (0, -1), (-1, -1), 12),
                ("LINEABOVE", (0, -1), (-1, -1), 1, colors.grey),
            ]
        )
    )

    elements.append(money_table)
    elements.append(Spacer(1, 18))

    # ==================================================
    # STEP3-② 支払情報（振込先・備考）
    # ==================================================
    elements.append(Paragraph("<b>Payment Information</b>", section_title))
    pay_rows = [
        ["支払期限", due_str],
        ["振込先", f"{BANK_NAME} {BANK_BRANCH} / {BANK_ACCOUNT}"],
        ["口座名義", BANK_ACCOUNT_NAME],
    ]
    pay_table = Table(pay_rows, colWidths=[90, 360], hAlign="LEFT")
    pay_table.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), "NotoSansJP"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.grey),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    elements.append(pay_table)
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(NOTES, styles["Normal"]))

    # フッター
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("Generated by csv_invoice_tool (Python)", right_style))

    doc.build(elements)


def generate_invoices_from_summary(
    summary_csv: Path,
    out_dir: Path,
    month: str,
    tax_rate: float = 0.10
) -> List[Path]:
    """
    summary_by_store.csv から 店舗別の請求書PDFを一括生成する
    """
    rows = load_summary_by_store(summary_csv)
    invoices = build_invoices(rows, month=month, tax_rate=tax_rate)

    created: List[Path] = []
    yyyymm = month.replace("-", "")

    for inv in invoices:
        pdf_name = f"invoice_{inv.bill_to}_{yyyymm}.pdf"
        pdf_path = out_dir / pdf_name
        render_invoice_pdf(inv, pdf_path)
        created.append(pdf_path)

    return created