import streamlit as st
from streamlit_calendar import calendar
from dotenv import load_dotenv
from utils.style import apply_global_styles, page_banner, category_tag
from utils.db import get_release_schedule, CATEGORY_COLORS

load_dotenv()

st.set_page_config(page_title="発売カレンダー | ちいかわグッズ情報", page_icon="📅", layout="wide")
apply_global_styles()
page_banner("📅 発売カレンダー", "今後の発売予定をカレンダーで確認できます。イベントをクリックすると詳細が表示されます。")

# ── フィルター ────────────────────────────────────────
with st.expander("🔍 絞り込む", expanded=False):
    col1, col2 = st.columns(2)
    with col1:
        selected_category = st.selectbox("カテゴリ", ["すべて", "ぬいぐるみ", "ガチャ", "食玩", "コラボ", "その他"])
    with col2:
        months = st.slider("表示期間（ヶ月）", min_value=1, max_value=6, value=3)

# ── データ取得 ────────────────────────────────────────
try:
    schedules = get_release_schedule(months_ahead=months)
except Exception as e:
    st.error(f"データの取得に失敗しました: {e}")
    st.stop()

if selected_category != "すべて":
    schedules = [s for s in schedules if s.get("products", {}).get("category") == selected_category]

# ── カレンダー用イベントデータを組み立てる ─────────────
events = []
event_details = {}

for s in schedules:
    product    = s.get("products") or {}
    store      = s.get("stores") or {}
    category   = product.get("category", "その他")
    color      = CATEGORY_COLORS.get(category, "#20B2AA")
    store_name = store.get("name", "全国") if store else "全国"
    event_id   = str(s["id"])

    events.append({
        "id":              event_id,
        "title":           product.get("name", "（商品名なし）"),
        "start":           s["scheduled_date"],
        "end":             s["scheduled_date"],
        "backgroundColor": color,
        "borderColor":     color,
        "extendedProps": {
            "store":        store_name,
            "price":        product.get("official_price"),
            "confirmed":    s.get("is_confirmed", False),
            "notes":        s.get("notes", ""),
            "amazon":       product.get("affiliate_amazon", ""),
            "rakuten":      product.get("affiliate_rakuten", ""),
            "official_url": product.get("official_site_url", ""),
        },
    })
    event_details[event_id] = s

# ── カレンダー表示 ────────────────────────────────────
calendar_options = {
    "headerToolbar": {
        "left":   "today prev,next",
        "center": "title",
        "right":  "dayGridMonth,timeGridWeek,listMonth",
    },
    "initialView": "dayGridMonth",
    "locale": "ja",
    "height": 600,
    "eventDisplay": "block",
}

result = calendar(events=events, options=calendar_options, key="release_calendar")

# ── クリックされたイベントの詳細パネル ────────────────
if result and result.get("eventClick"):
    clicked_id = result["eventClick"]["event"]["id"]
    s = event_details.get(clicked_id)
    if s:
        product = s.get("products") or {}
        store   = s.get("stores") or {}
        st.divider()

        st.markdown(f"""
        <div style="background:white;border-radius:16px;padding:20px 24px;
                    border:1px solid #FFD1DC;box-shadow:0 2px 12px rgba(0,0,0,0.07);
                    margin-bottom:16px;">
            <div style="font-size:1.2em;font-weight:700;color:#AD1457;margin-bottom:12px;">
                🏷️ {product.get('name', '（商品名なし）')}
                &nbsp;{category_tag(product.get('category', ''))}
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px;font-size:0.93em;color:#444;">
                <div>📅 <b>発売日</b>　{s['scheduled_date']}</div>
                <div>🏪 <b>販売店</b>　{store.get('name', '全国') if store else '全国'}</div>
                <div>💰 <b>定価</b>　¥{product.get('official_price', '不明')}</div>
                <div>{"✅ <b>発売確定</b>" if s.get('is_confirmed') else "📌 <b>発売予定（未確定）</b>"}</div>
                {f"<div colspan='2'>📝 {s['notes']}</div>" if s.get('notes') else ""}
            </div>
        </div>
        """, unsafe_allow_html=True)

        btn_cols = st.columns(3)
        with btn_cols[0]:
            if product.get("affiliate_amazon"):
                st.link_button("🛒 Amazonで購入", product["affiliate_amazon"], use_container_width=True)
        with btn_cols[1]:
            if product.get("affiliate_rakuten"):
                st.link_button("🛒 楽天で購入", product["affiliate_rakuten"], use_container_width=True)
        with btn_cols[2]:
            if product.get("official_site_url"):
                st.link_button("🌐 公式サイト", product["official_site_url"], use_container_width=True)

# ── カテゴリ凡例 ─────────────────────────────────────
st.divider()
legend_html = "　".join(
    f'<span style="color:{color};font-size:1.1em;">■</span>'
    f'<span style="font-size:0.85em;color:#555;margin-left:3px;">{name}</span>'
    for name, color in CATEGORY_COLORS.items()
)
st.markdown(f"<div style='color:#888;'>カテゴリ凡例　{legend_html}</div>",
            unsafe_allow_html=True)
