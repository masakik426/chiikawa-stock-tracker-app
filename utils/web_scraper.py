"""
ちいかわの公式ウェブサイトから商品発売情報を収集し、
Supabase の release_schedule テーブルに登録するスクリプト。

GitHub Actions から daily_tweet.yml に呼び出される（毎日実行）。
requests + BeautifulSoup でサイトのHTML を解析して日付・商品名を抽出する。
"""

import os
import re
import time
from datetime import date, timedelta

import requests
from bs4 import BeautifulSoup
from supabase import create_client
from dotenv import load_dotenv
from utils.text_parser import find_or_create_product, extract_date

load_dotenv()

# ── スクレイピング対象サイト ──────────────────────────────
# url: アクセスするページのURL（ニュース・新着情報のページを指定）
TARGET_SITES = [
    {
        "name":     "ちいかわ公式情報サイト",
        "url":      "https://chiikawa-info.jp/news/",
        "encoding": "utf-8",
    },
    {
        "name":     "ちいかわランド公式サイト",
        "url":      "https://www.chiikawa-land.com/contents/news/",
        "encoding": "utf-8",
    },
]

# 発売情報を示すキーワード（このキーワードを含む要素だけ処理する）
RELEASE_KEYWORDS = ["発売", "販売", "新発売", "発売予定", "入荷", "登場", "リリース"]

# ブラウザに偽装したリクエストヘッダー（bot と判定されて弾かれないように）
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}


def fetch_page(url: str, encoding: str = "utf-8") -> BeautifulSoup | None:
    """指定URLのHTMLを取得してパースする。失敗した場合は None を返す。"""
    try:
        resp = requests.get(url, headers=REQUEST_HEADERS, timeout=20)
        resp.raise_for_status()
        resp.encoding = encoding
        return BeautifulSoup(resp.text, "html.parser")
    except Exception as e:
        print(f"  → ページ取得失敗: {e}")
        return None


def extract_news_items(soup: BeautifulSoup) -> list[str]:
    """
    HTML からニュース・お知らせの本文テキストを抽出する。
    サイトによって HTML 構造が違うため、複数のパターンを試みる。
    """
    texts = []

    # パターン1: <article> タグ（一般的なブログ・ニュースサイト）
    for elem in soup.find_all("article"):
        t = elem.get_text(" ", strip=True)
        if t:
            texts.append(t)

    # パターン2: class 名に "news" "article" "post" を含む要素
    if not texts:
        for elem in soup.find_all(
            class_=re.compile(r"news|article|post|entry|item|release", re.I)
        ):
            t = elem.get_text(" ", strip=True)
            if len(t) > 20:  # 短すぎる断片は除外
                texts.append(t)

    # パターン3: <li> タグの中にある日付＋テキスト（一覧ページ形式）
    if not texts:
        for elem in soup.find_all("li"):
            t = elem.get_text(" ", strip=True)
            if len(t) > 20 and "月" in t:
                texts.append(t)

    # パターン4: 上記すべて失敗した場合は、<p> タグを総当たり
    if not texts:
        for elem in soup.find_all("p"):
            t = elem.get_text(" ", strip=True)
            if len(t) > 20:
                texts.append(t)

    return texts


def scrape_site(site: dict, db) -> int:
    """
    1サイトをスクレイピングして発売情報を Supabase に登録する。
    新規登録した件数を返す。
    """
    print(f"\n📡 スクレイピング中: {site['name']}")
    print(f"   URL: {site['url']}")

    soup = fetch_page(site["url"], site.get("encoding", "utf-8"))
    if soup is None:
        return 0

    items = extract_news_items(soup)
    print(f"   → {len(items)} 件の要素を検出")

    saved = 0
    for text in items[:30]:  # 最大30件処理（APIコスト節約）

        # ちいかわに関係しないテキストはスキップ
        if "ちいかわ" not in text:
            continue

        # 発売情報キーワードがないテキストはスキップ
        if not any(kw in text for kw in RELEASE_KEYWORDS):
            continue

        # テキストから日付を抽出
        release_date = extract_date(text)
        if not release_date:
            continue

        # 過去30日以上前の情報はスキップ（ある程度の古い情報は許容）
        if release_date < date.today() - timedelta(days=30):
            continue

        # テキストから商品を特定（未登録なら自動作成）
        product_id = find_or_create_product(text, db)
        if not product_id:
            continue

        # 同じ商品・同じ日付がすでに登録されていれば重複登録しない
        existing = (
            db.table("release_schedule")
            .select("id")
            .eq("product_id", product_id)
            .eq("scheduled_date", release_date.isoformat())
            .execute()
        )
        if existing.data:
            continue

        db.table("release_schedule").insert({
            "product_id":     product_id,
            "scheduled_date": release_date.isoformat(),
            "is_confirmed":   False,  # ウェブサイト情報は「予定」扱い
            "notes":          f"{site['name']} より自動取得",
        }).execute()
        saved += 1
        print(f"   → 登録: {text[:60]}... （{release_date}）")

    return saved


def run():
    """全サイトをスクレイピングして発売情報を Supabase に登録する。"""
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")

    if not all([supabase_url, supabase_key]):
        print("環境変数 SUPABASE_URL / SUPABASE_KEY が設定されていません。")
        return

    db = create_client(supabase_url, supabase_key)
    total = 0

    for site in TARGET_SITES:
        total += scrape_site(site, db)
        time.sleep(3)  # サーバーへの負荷を減らすため3秒待機

    print(f"\n✅ 完了: 合計 {total} 件を新規登録しました。")


if __name__ == "__main__":
    run()
