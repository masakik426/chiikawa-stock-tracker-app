"""
公式Xアカウントの過去ツイートを遡り、
今日以降の発売日が含まれるツイートを release_schedule に一括登録するスクリプト。

通常の x_official_watcher.py は最新10件しか取得しないが、
このスクリプトは1アカウントあたり最大100件を取得する。

GitHub Actions の手動実行（workflow_dispatch）から呼び出す。
初回データ投入や、しばらくデータが空だったときのリカバリに使う。
"""

import os
from datetime import date

import tweepy
from supabase import create_client
from dotenv import load_dotenv
from utils.text_parser import find_or_create_product, extract_date

load_dotenv()

# 監視対象の公式アカウント（x_official_watcher.py と同じ）
OFFICIAL_ACCOUNTS = {
    "chiikawa_land":   "ちいかわらんど・ポップアップ店舗",
    "chiikawa_market": "オンラインショップ",
    "chiikawa_kouhou": "グッズ全般",
    "gtchiikawa":      "ご当地ちいかわ",
}

# 発売情報として拾うキーワード（is_product_announcement より広め）
RELEASE_KEYWORDS = [
    "新発売", "発売決定", "発売予定", "新商品", "発売開始",
    "登場", "販売開始", "販売予定", "発売", "販売",
]


def is_release_related(text: str) -> bool:
    """ツイートに発売情報キーワードが含まれるか判定する。"""
    return any(kw in text for kw in RELEASE_KEYWORDS)


def run():
    """公式アカウントの過去ツイートから未来の発売情報を一括登録する。"""
    bearer_token = os.environ.get("X_BEARER_TOKEN")
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")

    if not all([bearer_token, supabase_url, supabase_key]):
        print("環境変数 X_BEARER_TOKEN / SUPABASE_URL / SUPABASE_KEY が設定されていません。")
        return

    client = tweepy.Client(bearer_token=bearer_token)
    db     = create_client(supabase_url, supabase_key)

    today      = date.today()
    total_new  = 0

    for username, description in OFFICIAL_ACCOUNTS.items():
        print(f"\n📡 取得中: @{username}（{description}）")

        try:
            user = client.get_user(username=username)
            if not user.data:
                print(f"  → ユーザーが見つかりません")
                continue

            # 最大100件のツイートを取得（リツイート・リプライは除外）
            response = client.get_users_tweets(
                id=user.data.id,
                max_results=100,
                tweet_fields=["created_at"],
                exclude=["retweets", "replies"],
            )
        except tweepy.TooManyRequests:
            print("  ⚠️ API レート制限に達しました。今回はここまでで終了します。")
            break
        except tweepy.TweepyException as e:
            print(f"  ❌ API エラー: {e}")
            continue

        if not response.data:
            print("  → ツイートなし")
            continue

        print(f"  → {len(response.data)} 件取得")

        for tweet in response.data:
            text = tweet.text

            # 発売情報キーワードがなければスキップ
            if not is_release_related(text):
                continue

            # 日付を抽出
            release_date = extract_date(text)
            if not release_date:
                continue

            # 過去の日付はスキップ（今日以降のみ登録）
            if release_date < today:
                continue

            # 商品を特定（未登録なら自動作成）
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

            # release_schedule に登録
            db.table("release_schedule").insert({
                "product_id":     product_id,
                "scheduled_date": release_date.isoformat(),
                "is_confirmed":   True,
                "notes":          f"公式X (@{username}) より一括取得",
            }).execute()

            total_new += 1
            print(f"  ✅ 登録: {release_date} | {text[:60]}...")

    print(f"\n🎉 完了: 合計 {total_new} 件を新規登録しました。")


if __name__ == "__main__":
    run()
