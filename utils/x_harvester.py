"""
X (Twitter) のハッシュタグ検索で既存の在庫報告ツイートを収集し、
Supabase に登録するスクリプト。

GitHub Actions から毎週1回呼び出される。
X API 無料枠の節約のため、週1回・最大50件に制限している。
"""

import os
import tweepy
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# 収集対象のキーワード（在庫情報が含まれそうなツイートを検索する）
SEARCH_QUERIES = [
    "#ダイソーちいかわ (在庫あり OR 入荷) -is:retweet",
    "#セリアちいかわ (在庫あり OR 入荷) -is:retweet",
    "#キャンドゥちいかわ (在庫あり OR 入荷) -is:retweet",
    "#ちいかわ コンビニ (在庫あり OR 入荷) -is:retweet",
]

# 在庫ステータスを判定するキーワード
IN_STOCK_KEYWORDS  = ["在庫あり", "入荷", "ありました", "見つけた", "買えた", "GET"]
OUT_STOCK_KEYWORDS = ["在庫なし", "売り切れ", "なかった", "完売"]
LIMITED_KEYWORDS   = ["残りわずか", "残り少ない", "あと少し", "ラスト"]


def detect_status(text: str) -> str:
    """ツイート本文から在庫ステータスを判定する。"""
    for kw in OUT_STOCK_KEYWORDS:
        if kw in text:
            return "out_of_stock"
    for kw in LIMITED_KEYWORDS:
        if kw in text:
            return "limited"
    for kw in IN_STOCK_KEYWORDS:
        if kw in text:
            return "in_stock"
    return "in_stock"  # キーワードが見つからない場合は在庫ありとみなす


def run():
    """ハッシュタグ検索を実行してデータを収集・登録する。"""
    bearer_token = os.environ.get("X_BEARER_TOKEN")
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")

    if not all([bearer_token, supabase_url, supabase_key]):
        print("環境変数が設定されていません。.env ファイルを確認してください。")
        return

    client = tweepy.Client(bearer_token=bearer_token)
    db = create_client(supabase_url, supabase_key)

    total_saved = 0

    for query in SEARCH_QUERIES:
        print(f"検索中: {query}")
        try:
            # 直近7日間のツイートを最大10件取得（週1回実行なので十分な量）
            response = client.search_recent_tweets(
                query=query,
                max_results=10,
                tweet_fields=["created_at", "author_id"],
            )
        except tweepy.TooManyRequests:
            print("API レート制限に達しました。今回はここまでで終了します。")
            break

        if not response.data:
            print("  → 結果なし")
            continue

        for tweet in response.data:
            post_url = f"https://x.com/i/web/status/{tweet.id}"

            # 同じURLの報告がすでに登録されていれば重複登録しない
            existing = db.table("inventory_reports").select("id").eq("x_post_url", post_url).execute()
            if existing.data:
                continue

            status = detect_status(tweet.text)
            db.table("inventory_reports").insert({
                "status":       status,
                "source":       "x_hashtag",
                "x_post_url":   post_url,
                "x_post_date":  tweet.created_at.isoformat() if tweet.created_at else None,
                "reporter_x_id": str(tweet.author_id),
                # product_id / store_id は管理者が後から紐付ける（自動解析は将来対応）
            }).execute()
            total_saved += 1
            print(f"  → 保存: {tweet.text[:60]}...")

    print(f"\n完了: {total_saved} 件を新規登録しました。")


if __name__ == "__main__":
    run()
