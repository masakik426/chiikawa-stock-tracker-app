import os
from supabase import create_client, Client
from dotenv import load_dotenv

# .env ファイルから環境変数を読み込む（ローカル開発用）
load_dotenv()

# カテゴリと表示色の対応表
CATEGORY_COLORS = {
    "ぬいぐるみ": "#FF69B4",
    "ガチャ":     "#4169E1",
    "食玩":       "#FF8C00",
    "コラボ":     "#9370DB",
    "その他":     "#20B2AA",
}

# 在庫ステータスの日本語ラベル
STATUS_LABELS = {
    "in_stock":    "在庫あり",
    "out_of_stock": "在庫なし",
    "limited":     "残りわずか",
}

# 情報ソースの日本語ラベル
SOURCE_LABELS = {
    "x_mention":  "Xメンション",
    "x_hashtag":  "Xハッシュタグ",
    "x_official": "X公式アカウント",
    "web_form":   "Webフォーム",
}


def get_client() -> Client:
    """Supabase クライアントを返す。環境変数が未設定の場合はエラーを表示する。"""
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        raise EnvironmentError(
            "環境変数 SUPABASE_URL と SUPABASE_KEY を設定してください。"
            ".env.example を参考に .env ファイルを作成してください。"
        )
    return create_client(url, key)


# ── 商品 ──────────────────────────────────────────────

def get_all_products():
    """全商品を取得する。"""
    db = get_client()
    res = db.table("products").select("*").order("official_release_date", desc=True).execute()
    return res.data


def get_product(product_id: int):
    """指定IDの商品を1件取得する。"""
    db = get_client()
    res = db.table("products").select("*").eq("id", product_id).single().execute()
    return res.data


def insert_product(data: dict):
    """商品を1件登録する。"""
    db = get_client()
    db.table("products").insert(data).execute()


def update_product(product_id: int, data: dict):
    """商品情報を更新する。"""
    db = get_client()
    db.table("products").update(data).eq("id", product_id).execute()


def delete_product(product_id: int):
    """商品を削除する（関連する在庫報告・発売スケジュールも CASCADE で削除）。"""
    db = get_client()
    db.table("products").delete().eq("id", product_id).execute()


# ── 店舗 ──────────────────────────────────────────────

def get_all_stores():
    """全店舗を取得する。"""
    db = get_client()
    res = db.table("stores").select("*").order("name").execute()
    return res.data


def insert_store(data: dict):
    """店舗を1件登録する。"""
    db = get_client()
    db.table("stores").insert(data).execute()


def update_store(store_id: int, data: dict):
    """店舗情報を更新する。"""
    db = get_client()
    db.table("stores").update(data).eq("id", store_id).execute()


def delete_store(store_id: int):
    """店舗を削除する。"""
    db = get_client()
    db.table("stores").delete().eq("id", store_id).execute()


# ── 在庫報告 ──────────────────────────────────────────

def get_inventory_reports(limit: int = 100, product_id: int = None, store_id: int = None, status: str = None):
    """在庫報告を取得する。フィルター条件を指定できる。"""
    db = get_client()
    query = (
        db.table("inventory_reports")
        .select("*, products(name, category), stores(name, region, store_type)")
        .eq("is_deleted", False)
        .order("created_at", desc=True)
        .limit(limit)
    )
    if product_id:
        query = query.eq("product_id", product_id)
    if store_id:
        query = query.eq("store_id", store_id)
    if status:
        query = query.eq("status", status)
    return query.execute().data


def get_stores_with_stock(product_id: int, hours: int = 24):
    """指定商品の在庫あり報告がある店舗を、指定時間以内の報告で絞り込んで取得する。"""
    from datetime import datetime, timedelta, timezone
    since = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
    db = get_client()
    res = (
        db.table("inventory_reports")
        .select("*, stores(id, name, address, latitude, longitude, store_type, region)")
        .eq("product_id", product_id)
        .eq("status", "in_stock")
        .eq("is_deleted", False)
        .gte("created_at", since)
        .order("created_at", desc=True)
        .execute()
    )
    return res.data


def insert_inventory_report(data: dict):
    """在庫報告を1件登録する。"""
    db = get_client()
    db.table("inventory_reports").insert(data).execute()


def soft_delete_report(report_id: int):
    """在庫報告を論理削除する（実際には is_deleted フラグを立てるだけ）。"""
    db = get_client()
    db.table("inventory_reports").update({"is_deleted": True}).eq("id", report_id).execute()


# ── 発売スケジュール ──────────────────────────────────

def get_release_schedule(months_ahead: int = 3):
    """今後の発売スケジュールを取得する。"""
    from datetime import date, timedelta
    today = date.today().isoformat()
    until = (date.today() + timedelta(days=30 * months_ahead)).isoformat()
    db = get_client()
    res = (
        db.table("release_schedule")
        .select("*, products(name, category, official_price, affiliate_amazon, affiliate_rakuten), stores(name)")
        .gte("scheduled_date", today)
        .lte("scheduled_date", until)
        .order("scheduled_date")
        .execute()
    )
    return res.data


def insert_release_schedule(data: dict):
    """発売スケジュールを1件登録する。"""
    db = get_client()
    db.table("release_schedule").insert(data).execute()


def delete_release_schedule(schedule_id: int):
    """発売スケジュールを削除する。"""
    db = get_client()
    db.table("release_schedule").delete().eq("id", schedule_id).execute()
