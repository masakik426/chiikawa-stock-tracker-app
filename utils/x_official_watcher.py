"""
ちいかわの公式Xアカウントの最新ツイートを収集し、
発売・再入荷情報として Supabase に記録するスクリプト。

GitHub Actions から毎日1回呼び出される。
"""

import os
import tweepy
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# 監視対象の公式アカウント（ユーザーID形式。名前変更に影響されない）
# 実際のユーザーIDは X Developer Portal または
# https://tweeterid.com/ で調べることができる
OFFICIAL_ACCOUNTS = {
    "chiikawa_land":    "ちいかわらんど・ポップアップ店舗の在庫・再入荷",
    "chiikawa_market":  "オンラインショップの新商品・再入荷",
    "chiikawa_kouhou":  "グッズ全般の新情報",
    "gtchiikawa":       "ご当地ちいかわ情報",
}

# 入荷・発売に関連するキーワード
STOCK_KEYWORDS = ["入荷", "再入荷", "発売", "販売開始", "新発売", "在庫", "お知らせ"]


def is_stock_related(text: str) -> bool:
    """ツイート本文が在庫・発売情報に関係するか判定する。"""
    return any(kw in text for kw in STOCK_KEYWORDS)


def run():
    """公式アカウントの最新ツイートを収集・登録する。"""
    bearer_token = os.environ.get("X_BEARER_TOKEN")
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")

    if not all([bearer_token, supabase_url, supabase_key]):
        print("環境変数が設定されていません。")
        return

    client = tweepy.Client(bearer_token=bearer_token)
    db = create_client(supabase_url, supabase_key)

    total_saved = 0

    for username, description in OFFICIAL_ACCOUNTS.items():
        print(f"監視中: @{username} ({description})")
        try:
            # ユーザーの最新10件のツイートを取得
            user = client.get_user(username=username)
            if not user.data:
                print(f"  → ユーザーが見つかりません: @{username}")
                continue

            response = client.get_users_tweets(
                id=user.data.id,
                max_results=10,
                tweet_fields=["created_at"],
                exclude=["retweets", "replies"],
            )
        except tweepy.TooManyRequests:
            print("API レート制限に達しました。")
            break

        if not response.data:
            continue

        for tweet in response.data:
            if not is_stock_related(tweet.text):
                continue

            post_url = f"https://x.com/{username}/status/{tweet.id}"

            # 重複チェック
            existing = db.table("inventory_reports").select("id").eq("x_post_url", post_url).execute()
            if existing.data:
                continue

            db.table("inventory_reports").insert({
                "status":       "in_stock",
                "source":       "x_official",
                "x_post_url":   post_url,
                "x_post_date":  tweet.created_at.isoformat() if tweet.created_at else None,
                "reporter_x_id": username,
            }).execute()
            total_saved += 1
            print(f"  → 保存: {tweet.text[:60]}...")

    print(f"\n完了: {total_saved} 件を新規登録しました。")


if __name__ == "__main__":
    run()
