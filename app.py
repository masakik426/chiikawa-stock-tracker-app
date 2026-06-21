import streamlit as st
from dotenv import load_dotenv
from utils.style import apply_global_styles, page_banner, report_card_html, release_card_html
from utils.db import get_inventory_reports, get_release_schedule

load_dotenv()

st.set_page_config(
    page_title="ちいかわグッズ情報 | 在庫・発売スケジュール",
    page_icon="🐰",
    layout="wide",
    initial_sidebar_state="expanded",
)

apply_global_styles()

page_banner(
    "🐰 ちいかわグッズ情報",
    "発売スケジュール・在庫状況をリアルタイムでまとめてチェック",
)

# ── メインコンテンツ（左: 在庫 / 右: 発売） ──────────────
col_left, col_right = st.columns([3, 2], gap="large")

with col_left:
    st.markdown("### 📦 新着在庫情報")
    try:
        reports = get_inventory_reports(limit=10)
        if not reports:
            st.info("まだ在庫情報がありません。以下のフォームから報告してみましょう！")
        else:
            cards_html = "".join(report_card_html(r) for r in reports)
            st.markdown(cards_html, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"データの取得に失敗しました: {e}")

    st.caption("👉 [在庫状況ページで絞り込み検索](pages/02_在庫状況.py)")

with col_right:
    st.markdown("### 📅 今後の発売予定")
    try:
        schedules = get_release_schedule(months_ahead=2)
        if not schedules:
            st.info("登録されている発売予定はありません。")
        else:
            cards_html = "".join(release_card_html(sc) for sc in schedules)
            st.markdown(cards_html, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"データの取得に失敗しました: {e}")

    st.caption("👉 [カレンダーで月別表示](pages/01_発売カレンダー.py)")

st.divider()

# ── 在庫報告の案内 ────────────────────────────────────
st.markdown("### 📣 在庫情報を報告する")
st.write("店舗でちいかわグッズを見かけたら、ぜひ教えてください！")

tab_x, tab_form = st.tabs(["　𝕏 X（旧Twitter）でメンション　", "　📝 Webフォームから報告　"])

with tab_x:
    st.markdown("""
    <div style="background:white;border-radius:14px;padding:20px 24px;
                border:1px solid #FFD1DC;box-shadow:0 2px 8px rgba(0,0,0,0.05);">
        <div style="font-weight:700;font-size:1em;margin-bottom:10px;color:#333;">
            報告フォーマット（コピーしてお使いください）
        </div>
        <div style="background:#F8F8F8;border-radius:10px;padding:14px 18px;
                    font-family:monospace;font-size:0.95em;color:#1A1A1A;">
            @chiikawa_stock セリア渋谷店 ぬいぐるみはちわれ 在庫あり
        </div>
        <div style="margin-top:12px;color:#666;font-size:0.88em;">
            ✅ 「在庫あり」「残りわずか」「在庫なし」の3種類で報告できます<br>
            ✅ 写真を添付するだけでもOK！<br>
            ✅ 報告はサイト上にユーザー報告情報として掲載されます
        </div>
    </div>
    """, unsafe_allow_html=True)

with tab_form:
    st.page_link("pages/02_在庫状況.py", label="📝 在庫状況ページのWebフォームから報告する →", icon="📦")
    st.caption("XアカウントがなくてもWebフォームから在庫情報を報告できます。")

st.divider()

# ── サービスについて ──────────────────────────────────
c1, c2, c3 = st.columns(3)
with c1:
    st.markdown("""
    <div style="background:white;border-radius:14px;padding:18px;text-align:center;
                border:1px solid #FFD1DC;height:130px;display:flex;flex-direction:column;
                align-items:center;justify-content:center;">
        <div style="font-size:2em;">📅</div>
        <div style="font-weight:700;color:#AD1457;margin-top:6px;">発売カレンダー</div>
        <div style="font-size:0.85em;color:#666;margin-top:4px;">月別で発売日をチェック</div>
    </div>
    """, unsafe_allow_html=True)
with c2:
    st.markdown("""
    <div style="background:white;border-radius:14px;padding:18px;text-align:center;
                border:1px solid #FFD1DC;height:130px;display:flex;flex-direction:column;
                align-items:center;justify-content:center;">
        <div style="font-size:2em;">🗺️</div>
        <div style="font-weight:700;color:#AD1457;margin-top:6px;">近くの在庫を探す</div>
        <div style="font-size:0.85em;color:#666;margin-top:4px;">現在地から最寄り店舗を検索</div>
    </div>
    """, unsafe_allow_html=True)
with c3:
    st.markdown("""
    <div style="background:white;border-radius:14px;padding:18px;text-align:center;
                border:1px solid #FFD1DC;height:130px;display:flex;flex-direction:column;
                align-items:center;justify-content:center;">
        <div style="font-size:2em;">👥</div>
        <div style="font-weight:700;color:#AD1457;margin-top:6px;">みんなで更新</div>
        <div style="font-size:0.85em;color:#666;margin-top:4px;">Xメンション・Webフォームで報告</div>
    </div>
    """, unsafe_allow_html=True)
