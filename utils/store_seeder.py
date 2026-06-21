"""
ちいかわグッズを取り扱う主要チェーン店を stores テーブルに一括登録するスクリプト。

GitHub Actions から月1回（毎月1日）呼び出される。
すでに同名の店舗が登録されている場合はスキップする（重複防止）。
"""

import os
import time
from supabase import create_client
from dotenv import load_dotenv
from utils.geocoder import address_to_coords

load_dotenv()

# ちいかわグッズを取り扱う主要チェーン店マスタ
# address を設定した店舗は geopy で座標を自動取得する
STORE_MASTER = [
    # ── 100均 ──────────────────────────────────────────
    {"name": "ダイソー（全国）",   "store_type": "100均",  "region": None, "address": None, "website_url": "https://www.daiso-sangyo.co.jp/"},
    {"name": "セリア（全国）",     "store_type": "100均",  "region": None, "address": None, "website_url": "https://www.seria-group.com/"},
    {"name": "キャンドゥ（全国）", "store_type": "100均",  "region": None, "address": None, "website_url": "https://www.cando-web.co.jp/"},
    {"name": "Watts（全国）",      "store_type": "100均",  "region": None, "address": None, "website_url": "https://www.watts.jp/"},

    # ── コンビニ ───────────────────────────────────────
    {"name": "ローソン（全国）",           "store_type": "コンビニ", "region": None, "address": None, "website_url": "https://www.lawson.co.jp/"},
    {"name": "ファミリーマート（全国）",   "store_type": "コンビニ", "region": None, "address": None, "website_url": "https://www.family.co.jp/"},
    {"name": "セブンイレブン（全国）",     "store_type": "コンビニ", "region": None, "address": None, "website_url": "https://www.sej.co.jp/"},

    # ── スーパー ───────────────────────────────────────
    {"name": "イオン（全国）",             "store_type": "スーパー", "region": None, "address": None, "website_url": "https://www.aeon.com/"},
    {"name": "イトーヨーカドー（全国）",   "store_type": "スーパー", "region": None, "address": None, "website_url": "https://www.itoyokado.co.jp/"},
    {"name": "ライフ（全国）",             "store_type": "スーパー", "region": None, "address": None, "website_url": "https://www.lifecorp.jp/"},
    {"name": "マルエツ（全国）",           "store_type": "スーパー", "region": None, "address": None, "website_url": "https://www.maruetsu.co.jp/"},
    {"name": "西友（全国）",               "store_type": "スーパー", "region": None, "address": None, "website_url": "https://www.seiyu.co.jp/"},
    {"name": "マックスバリュ（全国）",     "store_type": "スーパー", "region": None, "address": None, "website_url": "https://www.maxvalu.co.jp/"},

    # ── ガチャガチャ ───────────────────────────────────
    {"name": "ガチャガチャの森（全国）",                 "store_type": "ガチャガチャ", "region": None, "address": None, "website_url": "https://www.gachaforest.com/"},
    {"name": "ガシャポンバンダイオフィシャルショップ",   "store_type": "ガチャガチャ", "region": "東京都", "address": "東京都豊島区東池袋3-1-3", "website_url": "https://gashapon.jp/"},
    {"name": "トイズキャビン（全国）",                   "store_type": "ガチャガチャ", "region": None, "address": None, "website_url": None},
    {"name": "エムアールマックス（全国）",               "store_type": "ガチャガチャ", "region": None, "address": None, "website_url": None},

    # ── 雑貨 ───────────────────────────────────────────
    {"name": "ドン・キホーテ（全国）",         "store_type": "雑貨", "region": None, "address": None, "website_url": "https://www.donki.com/"},
    {"name": "ヴィレッジヴァンガード（全国）", "store_type": "雑貨", "region": None, "address": None, "website_url": "https://www.village-v.co.jp/"},

    # ── 百貨店 ─────────────────────────────────────────
    {"name": "伊勢丹新宿店",   "store_type": "百貨店", "region": "東京都", "address": "東京都新宿区新宿3-14-1",   "website_url": "https://www.isetan.mistore.jp/shinjuku.html"},
    {"name": "高島屋東京店",   "store_type": "百貨店", "region": "東京都", "address": "東京都中央区日本橋2-4-1",  "website_url": "https://www.takashimaya.co.jp/tokyo/"},
    {"name": "阪急うめだ本店", "store_type": "百貨店", "region": "大阪府", "address": "大阪府大阪市北区角田町8-7", "website_url": "https://www.hankyu-dept.co.jp/honten/"},
    {"name": "大丸東京店",     "store_type": "百貨店", "region": "東京都", "address": "東京都千代田区丸の内1-9-1", "website_url": "https://www.daimaru.co.jp/tokyo/"},

    # ── ちいかわ公式 ───────────────────────────────────
    {"name": "ちいかわらんど 原宿店",   "store_type": "ちいかわ公式", "region": "東京都", "address": "東京都渋谷区神宮前1-7-1",   "website_url": "https://chiikawa-land.com/"},
    {"name": "ちいかわらんど 池袋店",   "store_type": "ちいかわ公式", "region": "東京都", "address": "東京都豊島区東池袋3-1-3",   "website_url": "https://chiikawa-land.com/"},
    {"name": "ちいかわらんど 大阪店",   "store_type": "ちいかわ公式", "region": "大阪府", "address": "大阪府大阪市浪速区難波中2-10-70", "website_url": "https://chiikawa-land.com/"},
    {"name": "ちいかわマーケット（公式EC）", "store_type": "EC", "region": None, "address": None, "website_url": "https://chiikawa-market.com/"},

    # ── EC ─────────────────────────────────────────────
    {"name": "Amazon ちいかわ公式ストア", "store_type": "EC", "region": None, "address": None, "website_url": "https://www.amazon.co.jp/stores/chiikawa/"},
    {"name": "楽天 ちいかわ公式ショップ", "store_type": "EC", "region": None, "address": None, "website_url": "https://www.rakuten.co.jp/"},
]


def run():
    """店舗マスタを Supabase に一括登録する。"""
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    if not all([supabase_url, supabase_key]):
        print("環境変数 SUPABASE_URL / SUPABASE_KEY が設定されていません。")
        return

    db = create_client(supabase_url, supabase_key)

    inserted = 0
    skipped = 0

    for store in STORE_MASTER:
        # 同名の店舗がすでに登録されている場合はスキップ
        existing = db.table("stores").select("id").eq("name", store["name"]).execute()
        if existing.data:
            print(f"  スキップ（登録済み）: {store['name']}")
            skipped += 1
            continue

        # 住所がある場合は座標を自動取得（Nominatim の Rate Limit に合わせて1秒待機）
        lat, lon = None, None
        if store.get("address"):
            lat, lon = address_to_coords(store["address"])
            time.sleep(1)
            if lat:
                print(f"  座標取得: {store['name']} → ({lat:.4f}, {lon:.4f})")
            else:
                print(f"  座標取得失敗: {store['name']}")

        db.table("stores").insert({
            "name":        store["name"],
            "store_type":  store["store_type"],
            "region":      store.get("region"),
            "address":     store.get("address"),
            "latitude":    lat,
            "longitude":   lon,
            "website_url": store.get("website_url"),
        }).execute()
        print(f"  登録: {store['name']}（{store['store_type']}）")
        inserted += 1

    print(f"\n完了: {inserted} 件登録、{skipped} 件スキップ")


if __name__ == "__main__":
    run()
