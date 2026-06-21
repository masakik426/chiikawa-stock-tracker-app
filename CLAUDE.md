# chiikawa-stock-tracker - Claude への説明書

## プロジェクト概要

ちいかわグッズの在庫情報・発売情報を自動収集し、Webアプリと X（Twitter）で公開するシステム。

- **Webアプリ**: Streamlit で構築、Supabase にデータを蓄積して表示
- **自動収集**: GitHub Actions で毎日自動実行
- **自動ツイート**: 専用 X アカウント（@chiikawa_track）が毎日12時に発売情報を投稿

---

## X アカウント

| 用途 | アカウント名 | 備考 |
|---|---|---|
| 情報収集（読み取り） | 既存の個人アカウント | Bearer Token で読み取りのみ |
| 自動投稿（書き込み） | @chiikawa_track（ちいかわグッズ速報） | OAuth 1.0a で投稿 |

`@chiikawa_track` のメールアドレスは `masaki.kariya.0426+chiikawa@gmail.com`（Gmailエイリアス）。

---

## GitHub Secrets 一覧

| 変数名 | 用途 |
|---|---|
| `SUPABASE_URL` | Supabase の接続URL |
| `SUPABASE_KEY` | Supabase の API キー |
| `X_BEARER_TOKEN` | X API 読み取り用トークン（既存アカウント） |
| `POST_X_ACCESS_TOKEN` | @chiikawa_track の アクセストークン |
| `POST_X_ACCESS_TOKEN_SECRET` | @chiikawa_track の アクセストークンシークレット |
| `POST_X_API_KEY` | @chiikawa_track の API Key（Consumer Key） |
| `POST_X_API_SECRET` | @chiikawa_track の API Key Secret |
| `SITE_URL` | Streamlit アプリの URL（ツイートに貼るリンク） |

---

## GitHub Actions ワークフロー

### `collect_data.yml`（毎日 JST 9:00）
- 公式 X アカウントの投稿を収集（`x_official_watcher.py`）
- ハッシュタグ検索で在庫情報を収集（`x_harvester.py`、週1回・月曜日のみ）
- 主要チェーン店舗を一括登録（`store_seeder.py`、毎月1日のみ）

### `daily_tweet.yml`（毎日 JST 12:00）
- 今後7日間の発売情報を @chiikawa_track に自動投稿（`tweet_poster.py`）
- ~~公式サイトのスクレイピング（`web_scraper.py`）~~ → **現在無効**（下記参照）

---

## スクレイピングについて（重要）

`web_scraper.py` はちいかわ公式サイトから発売情報を収集するスクリプトだが、**現在は動作しない**。

| 対象サイト | 設定URL | 状態 |
|---|---|---|
| ちいかわ公式情報サイト | `https://chiikawa-info.jp/news/` | 404エラー（パスが存在しない） |
| ちいかわランド公式サイト | `https://www.chiikawa-land.com/contents/news/` | DNS解決失敗（ドメインが存在しない） |

また `chiikawa-info.jp/` のトップページは 403（ボット拒否）のため、正しいURLが分かっても
スクレイピング自体ができない可能性が高い。

**現状の対応**: `daily_tweet.yml` からスクレイピングステップを除外済み。
発売情報は X 公式アカウント監視（`x_official_watcher.py`）と手動登録で賄う。

---

## データの流れ

```
公式Xアカウント（@chiikawa_kouhou 等）
    ↓ x_official_watcher.py（毎日 9:00）
Supabase（release_schedule テーブル）
    ↓ tweet_poster.py（毎日 12:00）
@chiikawa_track に自動ツイート
```

---

## 主要ファイル

| ファイル | 役割 |
|---|---|
| `utils/x_official_watcher.py` | 公式Xアカウントを監視して発売情報を収集 |
| `utils/x_harvester.py` | ハッシュタグ検索で在庫情報を収集 |
| `utils/store_seeder.py` | 主要チェーン店舗を一括登録 |
| `utils/text_parser.py` | テキストから商品名・店舗名・日付を抽出するユーティリティ |
| `utils/tweet_poster.py` | 今後7日間の発売情報を X に投稿 |
| `utils/web_scraper.py` | 公式サイトのスクレイピング（現在無効） |
| `utils/db.py` | Supabase へのデータ取得関数 |
| `utils/geocoder.py` | 住所→座標変換 |

---

## 開発環境

- Python 3.12
- Supabase（データベース）
- Streamlit（Web アプリ）
- GitHub Actions（自動実行）
- GitHub Desktop でコミット・プッシュ（git CLI は使用不可）
