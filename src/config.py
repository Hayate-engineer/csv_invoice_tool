# src/config.py
from pathlib import Path

# プロジェクト直下（csv_invoice_tool/）を取得
BASE_DIR = Path(__file__).resolve().parents[1]

# ===== アセット =====
LOGO_PATH = BASE_DIR / "assets" / "logo.png"
FONT_PATH = BASE_DIR / "assets" / "fonts" / "NotoSansJP-Regular.otf"

# ===== 発行者情報 =====
ISSUER_NAME = "サンプル株式会社"
ISSUER_ADDRESS = "〒100-0001 東京都千代田区サンプル1-2-3"
ISSUER_TEL = "TEL: 03-0000-0000"
ISSUER_EMAIL = "Email: example@example.com"

# ===== 支払・振込情報 =====
PAYMENT_DUE_DAYS = 14
BANK_NAME = "サンプル銀行"
BANK_BRANCH = "本店"
BANK_ACCOUNT = "普通 1234567"
BANK_ACCOUNT_NAME = "サンプル（カ"
NOTES = "※振込手数料は貴社ご負担にてお願いいたします。"

# ===== 表示調整（デザイン用）=====
LOGO_WIDTH = 70  # ロゴの表示幅（pt相当）