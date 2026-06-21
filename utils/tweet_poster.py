"""
Supabase の release_schedule から今後7日間の発売情報を取得し、
専用Xアカウントに毎日1回つぶやくスクリプト。

GitHub Actions から daily_tweet.yml に呼び出される（毎日 JST 12:00）。

【重要】X への投稿には OAuth 1.0a 認証が必要。
Bearer Token（読み取り専用）とは別に、以下の4つの環境変数が必要：
  POST_X_API_KEY             : API Key（Consumer Key）
  POST_X_API_SECRET          : API Key Secret（Consumer Secret）
  POST_X_ACCESS_TOKEN        : Access Token
  POST_X_ACCESS_TOKEN_SECRET : Access Token Secret
これらは GitHub Secrets に設定しておくこと。
"""

import os
from datetime import date, timedelta

import tweepy
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# 曜日を日本語に変換するリスト（0=月曜日 〜 6=日曜日）
WEEKDAYS_JP = ["月", "火", "水", "木", "金", "土", "日"]

# ツイートに貼るサイトURL
# GitHub Secrets に SITE_URL を設定するか、直接書き換えてください
SITE_URL = os.environ.get("SITE_URL", "https://chiikawa-goods-info.streamlit.app")

# ハッシュタグ（末尾に付ける）
HASHTAGS = "#ちいかわ #ちいかわグッズ"


def get_next_week_releases(db) -> list:
    """今日から7日間の発売スケジュールを取得する。"""
    today = date.today()
    end   = today + timedelta(days=7)

    res = (
        db.table("release_schedule")
        .select("*, products(name, category), stores(name)")
        .gte("scheduled_date", today.isoformat())
        .lte("scheduled_date", end.isoformat())
        .order("scheduled_date")
        .execute()
    )
    return res.data


def format_tweet(releases: list) -> str:
    """
    発売情報リストをシンプルなツイートテキストに整形する。

    フォーマット例:
      🐰 今週のちいかわグッズ発売情報

      📅 6/23（月）
      ・ちいかわぬいぐるみ新作 @ ローソン

      📅 6/25（水）
      ・ちいかわガチャ

      詳細→ https://...
      #ちいかわ #ちいかわグッズ
    """
    if not releases:
        return ""

    # 日付ごとにグループ化する
    by_date: dict[str, list] = {}
    for r in releases:
        d_str = r["scheduled_date"]
        by_date.setdefault(d_str, []).append(r)

    lines = ["🐰 今週のちいかわグッズ発売情報", ""]

    for d_str in sorted(by_date.keys()):
        d    = date.fromisoformat(d_str)
        wday = WEEKDAYS_JP[d.weekday()]
        lines.append(f"📅 {d.month}/{d.day}（{wday}）")

        for r in by_date[d_str]:
            product    = r.get("products") or {}
            store      = r.get("stores") or {}
            name       = product.get("name", "（商品情報取得中）")
            store_name = store.get("name", "") if store else ""

            if store_name:
                lines.append(f"・{name} @ {store_name}")
            else:
                lines.append(f"・{name}")

        lines.append("")  # 日付ブロックの間に空行を入れる

    lines.append(f"詳細→ {SITE_URL}")
    lines.append(HASHTAGS)

    tweet_text = "\n".join(lines)

    # X の文字数上限は280文字（日本語は1文字2文字カウントされる場合もある）
    # 270文字を超えたら末尾を省略してリンクとタグを残す
    if len(tweet_text) > 270:
        # ハッシュタグとリンクを確保した上で本文を切り詰める
        footer = f"\n詳細→ {SITE_URL}\n{HASHTAGS}"
        max_body = 270 - len(footer) - 3  # "..." の分
        tweet_text = tweet_text[:max_body] + "..." + footer

    return tweet_text


def post_tweet(text: str) -> str | None:
    """
    X API v2 を使ってツイートを投稿する。
    成功した場合はツイートIDを返し、失敗した場合は None を返す。
    """
    api_key       = os.environ.get("POST_X_API_KEY")
    api_secret    = os.environ.get("POST_X_API_SECRET")
    access_token  = os.environ.get("POST_X_ACCESS_TOKEN")
    access_secret = os.environ.get("POST_X_ACCESS_TOKEN_SECRET")

    if not all([api_key, api_secret, access_token, access_secret]):
        print(
            "❌ X 投稿用の環境変数が不足しています。\n"
            "   POST_X_API_KEY / POST_X_API_SECRET / "
            "POST_X_ACCESS_TOKEN / POST_X_ACCESS_TOKEN_SECRET\n"
            "   を GitHub Secrets に設定してください。"
        )
        return None

    # OAuth 1.0a で認証（投稿にはこの形式が必要）
    client = tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_secret,
    )

    try:
        response = client.create_tweet(text=text)
        tweet_id = response.data["id"]
        return tweet_id
    except tweepy.TweepyException as e:
        print(f"❌ X API エラー: {e}")
        return None


def run():
    """発売情報を取得してXに投稿する。"""
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")

    if not all([supabase_url, supabase_key]):
        print("環境変数 SUPABASE_URL / SUPABASE_KEY が設定されていません。")
        return

    db       = create_client(supabase_url, supabase_key)
    releases = get_next_week_releases(db)

    if not releases:
        print("今後7日間に発売予定の商品はありません。ツイートをスキップします。")
        return

    tweet_text = format_tweet(releases)
    print("━━━ 投稿予定のツイート ━━━")
    print(tweet_text)
    print(f"━━━ 文字数: {len(tweet_text)} ━━━\n")

    tweet_id = post_tweet(tweet_text)
    if tweet_id:
        print(f"✅ 投稿完了！ https://x.com/i/web/status/{tweet_id}")
    else:
        print("投稿に失敗しました。")


if __name__ == "__main__":
    run()
