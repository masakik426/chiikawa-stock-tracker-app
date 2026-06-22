"""
ツイートテキストから店舗名・商品名・価格・日付を抽出するユーティリティ。

x_harvester.py と x_official_watcher.py から呼び出して
store_id / product_id を自動リンクするために使う。
"""

import os
import re
import time
from datetime import date, datetime
from utils.geocoder import address_to_coords

# ちいかわグッズを取り扱う主要チェーン名（長い名前から先に照合する）
CHAIN_NAMES = [
    "ガチャガチャの森", "ガシャポンバンダイオフィシャルショップ", "トイズキャビン",
    "エムアールマックス", "ファミリーマート", "ファミマ",
    "イトーヨーカドー", "ヨーカドー", "マックスバリュ",
    "ドン・キホーテ", "ドンキホーテ", "ドンキ",
    "ヴィレッジヴァンガード", "ヴィレヴァン",
    "ちいかわらんど", "ちいかわマーケット",
    "セブンイレブン", "セブン",
    "ローソン", "セリア", "キャンドゥ", "Watts", "ワッツ",
    "ダイソー", "イオン", "ライフ", "マルエツ", "西友",
    "伊勢丹", "高島屋", "阪急", "大丸",
]

# チェーン名 → store_type のマッピング
CHAIN_TO_TYPE = {
    "ダイソー": "100均", "セリア": "100均", "キャンドゥ": "100均",
    "Watts": "100均", "ワッツ": "100均",
    "ローソン": "コンビニ", "ファミリーマート": "コンビニ", "ファミマ": "コンビニ",
    "セブンイレブン": "コンビニ", "セブン": "コンビニ",
    "イオン": "スーパー", "イトーヨーカドー": "スーパー", "ヨーカドー": "スーパー",
    "ライフ": "スーパー", "マルエツ": "スーパー", "西友": "スーパー",
    "マックスバリュ": "スーパー",
    "ガチャガチャの森": "ガチャガチャ", "ガシャポンバンダイオフィシャルショップ": "ガチャガチャ",
    "トイズキャビン": "ガチャガチャ", "エムアールマックス": "ガチャガチャ",
    "ドン・キホーテ": "雑貨", "ドンキホーテ": "雑貨", "ドンキ": "雑貨",
    "ヴィレッジヴァンガード": "雑貨", "ヴィレヴァン": "雑貨",
    "伊勢丹": "百貨店", "高島屋": "百貨店", "阪急": "百貨店", "大丸": "百貨店",
    "ちいかわらんど": "ちいかわ公式", "ちいかわマーケット": "EC",
}

# 商品カテゴリのキーワード
CATEGORY_KEYWORDS = {
    "ぬいぐるみ": ["ぬいぐるみ", "ぬい", "봉제인형"],
    "ガチャ":     ["ガチャ", "ガシャ", "カプセルトイ", "ガチャポン"],
    "食玩":       ["食玩", "チョコエッグ", "グミ", "お菓子"],
    "コラボ":     ["コラボ", "限定", "コラボグッズ"],
}

# 商品発表を示すキーワード
ANNOUNCEMENT_KEYWORDS = ["新発売", "発売決定", "発売予定", "新商品", "発売開始", "登場", "販売開始"]


def extract_chain_name(text: str) -> str | None:
    """テキストからチェーン名を返す。"""
    for chain in CHAIN_NAMES:
        if chain in text:
            return chain
    return None


def extract_store_fullname(text: str) -> str | None:
    """
    テキストから「セリア渋谷店」のような店舗フルネームを抽出する。
    チェーン名＋（任意の文字）＋「店」のパターンで探す。
    """
    for chain in CHAIN_NAMES:
        if chain not in text:
            continue
        # チェーン名の後に続く店舗名（例：渋谷、池袋、〇〇SC内）を抽出
        pattern = rf"{re.escape(chain)}[\w\s（）()ー〜・]*?店"
        match = re.search(pattern, text)
        if match:
            return match.group(0).strip()
        # 「〇〇店」が見つからない場合はチェーン名だけ返す
        return chain
    return None


def extract_product_category(text: str) -> str:
    """テキストから商品カテゴリを推定する。"""
    for category, keywords in CATEGORY_KEYWORDS.items():
        for kw in keywords:
            if kw in text:
                return category
    return "その他"


def extract_price(text: str) -> int | None:
    """テキストから価格（円）を抽出する。"""
    # ¥1,650 / 1650円 / 165円（税抜）などのパターン
    patterns = [
        r"¥([\d,]+)",
        r"([\d,]+)円",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            try:
                return int(match.group(1).replace(",", ""))
            except ValueError:
                pass
    return None


def extract_date(text: str) -> date | None:
    """テキストから発売日を抽出する。複数の表記形式に対応。"""
    current_year = datetime.now().year
    today = date.today()

    def _adjust_year(m: int, d: int) -> date | None:
        # 年なし日付で90日以上過去なら翌年として扱う
        try:
            candidate = date(current_year, m, d)
            if (today - candidate).days > 90:
                candidate = date(current_year + 1, m, d)
            return candidate
        except ValueError:
            return None

    # YYYY年M月D日
    match = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", text)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            pass

    # YYYY/M/D または YYYY-M-D
    match = re.search(r"(\d{4})[/\-](\d{1,2})[/\-](\d{1,2})", text)
    if match:
        try:
            return date(int(match.group(1)), int(match.group(2)), int(match.group(3)))
        except ValueError:
            pass

    # M月D日（年なし）
    match = re.search(r"(\d{1,2})月(\d{1,2})日", text)
    if match:
        result = _adjust_year(int(match.group(1)), int(match.group(2)))
        if result:
            return result

    # M/D（年なし、前後に別の数字が続かない場合のみ）
    match = re.search(r"(?<!\d)(\d{1,2})/(\d{1,2})(?!\d)", text)
    if match:
        m, d = int(match.group(1)), int(match.group(2))
        if 1 <= m <= 12 and 1 <= d <= 31:
            result = _adjust_year(m, d)
            if result:
                return result

    return None


def is_product_announcement(text: str) -> bool:
    """テキストが新商品発表かどうかを判定する。"""
    return any(kw in text for kw in ANNOUNCEMENT_KEYWORDS)


def extract_product_name_with_ai(tweet_text: str) -> str | None:
    """
    Claude Haiku API を使ってツイートから商品名を抽出する。
    環境変数 ANTHROPIC_API_KEY が設定されていない場合は None を返す。
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=60,
            messages=[{
                "role": "user",
                "content": (
                    "以下のちいかわ公式ツイートから、発売・販売される商品名を簡潔に抽出してください。\n"
                    "商品名だけを返してください（25文字以内）。商品名が分からない場合は「不明」とだけ返してください。\n\n"
                    f"ツイート:\n{tweet_text[:300]}"
                ),
            }],
        )
        result = message.content[0].text.strip()
        return None if result == "不明" else result
    except Exception as e:
        print(f"  AI抽出エラー: {e}")
        return None


def find_or_create_store(text: str, db) -> int | None:
    """
    テキストから店舗を特定し、未登録なら自動挿入して store_id を返す。
    店舗名が抽出できない場合は None を返す。
    """
    store_name = extract_store_fullname(text)
    if not store_name:
        return None

    # 既存の店舗と照合（部分一致）
    existing = db.table("stores").select("id, name").execute()
    for s in existing.data:
        if store_name in s["name"] or s["name"] in store_name:
            return s["id"]

    # 未登録 → 新しい店舗を自動作成
    chain = extract_chain_name(text)
    store_type = CHAIN_TO_TYPE.get(chain, "その他") if chain else "その他"

    # 座標取得（店舗名で検索してみる）
    lat, lon = None, None
    lat, lon = address_to_coords(f"日本 {store_name}")
    time.sleep(1)

    result = db.table("stores").insert({
        "name":       store_name,
        "store_type": store_type,
        "latitude":   lat,
        "longitude":  lon,
    }).execute()

    if result.data:
        print(f"  新規店舗を自動登録: {store_name}（{store_type}）")
        return result.data[0]["id"]
    return None


def find_or_create_product(text: str, db, name_override: str | None = None) -> int | None:
    """
    テキストから商品を特定し、未登録なら自動挿入して product_id を返す。
    name_override が指定された場合（AI抽出）はその名前を優先して使う。
    商品名が抽出できない場合は None を返す。
    """
    if name_override:
        candidate = name_override
    else:
        # 「ちいかわ ○○」パターンで商品名を抽出（正規表現フォールバック）
        match = re.search(r"ちいかわ[\s　]*([\w\s（）()ー〜・「」]+?)(?=[にをがはでと、。\s]|$)", text)
        if not match:
            return None
        candidate = f"ちいかわ {match.group(1).strip()}"
        if len(candidate) > 50:
            return None

    # 既存の商品と照合
    existing = db.table("products").select("id, name").execute()
    for p in existing.data:
        if candidate in p["name"] or p["name"] in candidate:
            return p["id"]

    # カテゴリ推定
    category = extract_product_category(text)
    price = extract_price(text)

    result = db.table("products").insert({
        "name":     candidate,
        "category": category,
        "official_price": price,
    }).execute()

    if result.data:
        print(f"  新規商品を自動登録: {candidate}（{category}）")
        return result.data[0]["id"]
    return None
