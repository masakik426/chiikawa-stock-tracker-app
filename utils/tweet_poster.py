"""
毎日2種類のツイートを @chiikawa_track に投稿するスクリプト。

① 週間サマリーツイート
   今後7日間の発売予定をまとめて投稿する。

② 本日発売ツイート（引用ツイート＋商品画像）
   本日発売の商品を1件ずつ公式ツイートを引用しながら投稿する。
   元ツイートに画像があればダウンロードして一緒に添付する。

GitHub Actions の daily_tweet.yml から毎日 JST 12:00 に呼び出される。
"""

import os
import re
import time
import tempfile
from datetime import date, timedelta

import requests
import tweepy
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

# 曜日を日本語に変換するリスト（0=月曜日 〜 6=日曜日）
WEEKDAYS_JP = ["月", "火", "水", "木", "金", "土", "日"]

# ハッシュタグ（末尾に付ける）
HASHTAGS = "#ちいかわ #ちいかわグッズ"


# ──────────────────────────────────────────────
# データ取得
# ──────────────────────────────────────────────

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


def get_today_releases(db) -> list:
    """本日発売の商品を取得する。"""
    today = date.today()
    res = (
        db.table("release_schedule")
        .select("*, products(name, category), stores(name)")
        .eq("scheduled_date", today.isoformat())
        .execute()
    )
    return res.data


# ──────────────────────────────────────────────
# ツイート文章の生成
# ──────────────────────────────────────────────

def format_weekly_tweet(releases: list) -> str:
    """
    今後7日間の発売情報を週間サマリーとしてフォーマットする。

    例:
      🐰 今週のちいかわグッズ発売情報

      📅 6/23（月）
      ・ちいかわぬいぐるみ @ ローソン

      📅 6/25（水）
      ・ちいかわガチャ

      #ちいかわ #ちいかわグッズ
    """
    if not releases:
        return ""

    by_date: dict[str, list] = {}
    for r in releases:
        by_date.setdefault(r["scheduled_date"], []).append(r)

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

        lines.append("")

    lines.append(HASHTAGS)
    tweet_text = "\n".join(lines)

    # 270文字を超えたら末尾を省略してハッシュタグを残す
    if len(tweet_text) > 270:
        max_body = 270 - len(HASHTAGS) - 5
        tweet_text = tweet_text[:max_body] + "...\n" + HASHTAGS

    return tweet_text


def format_today_tweet(release: dict) -> str:
    """
    本日発売の商品を1件フォーマットする。
    このツイートは公式ツイートの引用ツイートとして投稿される。

    例:
      🎉 本日発売！

      📦 ちいかわぬいぐるみ（Mサイズ）
      🏪 ちいかわらんど

      #ちいかわ #ちいかわグッズ
    """
    product    = release.get("products") or {}
    store      = release.get("stores") or {}
    name       = product.get("name", "（商品名不明）")
    store_name = store.get("name", "") if store else ""

    lines = ["🎉 本日発売！", ""]
    lines.append(f"📦 {name}")
    if store_name:
        lines.append(f"🏪 {store_name}")
    lines.append("")
    lines.append(HASHTAGS)
    return "\n".join(lines)


# ──────────────────────────────────────────────
# 画像取得・アップロード
# ──────────────────────────────────────────────

def extract_tweet_id(source_url: str) -> str | None:
    """source_url（例: https://x.com/xxx/status/123）からツイートIDを取り出す。"""
    match = re.search(r"/status/(\d+)", source_url or "")
    return match.group(1) if match else None


def fetch_tweet_image_url(tweet_id: str, bearer_token: str) -> str | None:
    """X API v2 を使って元ツイートの最初の画像 URL を取得する。"""
    try:
        client = tweepy.Client(bearer_token=bearer_token)
        response = client.get_tweet(
            tweet_id,
            expansions=["attachments.media_keys"],
            media_fields=["url", "type"],
        )
        if response.includes and "media" in response.includes:
            for media in response.includes["media"]:
                if media.type == "photo" and media.url:
                    return media.url
    except Exception as e:
        print(f"  画像URL取得エラー: {e}")
    return None


def upload_image_to_x(image_url: str, api_v1) -> str | None:
    """画像 URL からダウンロードし、X にアップロードして media_id を返す。"""
    try:
        r = requests.get(image_url, timeout=10)
        r.raise_for_status()
        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            f.write(r.content)
            tmp_path = f.name
        media = api_v1.media_upload(tmp_path)
        os.unlink(tmp_path)
        return str(media.media_id)
    except Exception as e:
        print(f"  画像アップロードエラー: {e}")
    return None


# ──────────────────────────────────────────────
# X クライアント構築
# ──────────────────────────────────────────────

def build_clients():
    """
    X API クライアントを2種類構築して返す。
    - client_v2 : v2 API（ツイート投稿）
    - api_v1    : v1.1 API（メディアアップロード専用）
    どちらも OAuth 1.0a の4つのシークレットを使う。
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
        return None, None

    client_v2 = tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_secret,
    )
    auth   = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_secret)
    api_v1 = tweepy.API(auth)
    return client_v2, api_v1


def post_tweet(client, text: str, quote_tweet_id: str | None = None, media_ids: list | None = None) -> str | None:
    """
    ツイートを投稿する。
    quote_tweet_id を指定すると引用ツイートになる。
    media_ids を指定すると画像が添付される。
    """
    try:
        kwargs = {"text": text}
        if quote_tweet_id:
            kwargs["quote_tweet_id"] = quote_tweet_id
        if media_ids:
            kwargs["media_ids"] = media_ids
        response = client.create_tweet(**kwargs)
        return response.data["id"]
    except tweepy.TweepyException as e:
        print(f"❌ X API エラー: {e}")
        return None


# ──────────────────────────────────────────────
# メイン処理
# ──────────────────────────────────────────────

def run():
    """週間サマリーと本日発売ツイートを投稿する。"""
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    bearer_token = os.environ.get("X_BEARER_TOKEN")

    if not all([supabase_url, supabase_key]):
        print("環境変数 SUPABASE_URL / SUPABASE_KEY が設定されていません。")
        return

    db                = create_client(supabase_url, supabase_key)
    client_v2, api_v1 = build_clients()
    if not client_v2:
        return

    # ① 週間サマリーを投稿する
    print("=== ① 週間サマリー ===")
    weekly_releases = get_next_week_releases(db)
    if weekly_releases:
        tweet_text = format_weekly_tweet(weekly_releases)
        print(tweet_text)
        print(f"文字数: {len(tweet_text)}\n")
        tweet_id = post_tweet(client_v2, tweet_text)
        if tweet_id:
            print(f"✅ 投稿完了！ https://x.com/i/web/status/{tweet_id}\n")
    else:
        print("今後7日間に発売予定の商品はありません。スキップします。\n")

    # ② 本日発売の商品を引用ツイートで投稿する（最大3件）
    print("=== ② 本日発売ツイート ===")
    today_releases = get_today_releases(db)
    if not today_releases:
        print("本日発売の商品はありません。スキップします。")
        return

    print(f"本日発売: {len(today_releases)} 件\n")
    for release in today_releases[:3]:
        tweet_text   = format_today_tweet(release)
        source_url   = release.get("source_url", "")
        tweet_id_str = extract_tweet_id(source_url)

        # 元ツイートの画像を取得してアップロードする（失敗しても投稿は続ける）
        media_ids = None
        if tweet_id_str and bearer_token and api_v1:
            image_url = fetch_tweet_image_url(tweet_id_str, bearer_token)
            if image_url:
                media_id = upload_image_to_x(image_url, api_v1)
                if media_id:
                    media_ids = [media_id]

        name = (release.get("products") or {}).get("name", "（商品名不明）")
        print(f"--- {name} ---")
        print(tweet_text)
        print(f"引用元: {source_url}")
        print(f"画像: {'あり ✅' if media_ids else 'なし（引用ツイートで代替）'}\n")

        tweet_id = post_tweet(client_v2, tweet_text, quote_tweet_id=tweet_id_str, media_ids=media_ids)
        if tweet_id:
            print(f"✅ 投稿完了！ https://x.com/i/web/status/{tweet_id}\n")

        time.sleep(3)  # 連続投稿の間に少し間隔を空ける


if __name__ == "__main__":
    run()
