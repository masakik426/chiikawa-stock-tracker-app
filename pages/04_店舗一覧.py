import html as _html
import streamlit as st
from dotenv import load_dotenv
from utils.style import apply_global_styles, page_banner
from utils.db import get_all_stores

load_dotenv()

st.set_page_config(page_title="店舗一覧 | ちいかわグッズ情報", page_icon="🏪", layout="wide")
apply_global_styles()
page_banner("🏪 店舗一覧", "ちいかわグッズが購入できる店舗の一覧です")

# ── データ取得 ────────────────────────────────────────
try:
    stores = get_all_stores()
except Exception as e:
    st.error(f"データの取得に失敗しました: {e}")
    st.stop()

# ── フィルター ────────────────────────────────────────
col1, col2 = st.columns(2)
with col1:
    store_types = ["すべて", "100均", "コンビニ", "百貨店", "EC", "その他"]
    selected_type = st.selectbox("店舗種別", store_types)
with col2:
    regions = ["すべて"] + sorted({s.get("region", "") for s in stores if s.get("region")})
    selected_region = st.selectbox("地域（都道府県）", regions)

filtered = stores
if selected_type != "すべて":
    filtered = [s for s in filtered if s.get("store_type") == selected_type]
if selected_region != "すべて":
    filtered = [s for s in filtered if s.get("region") == selected_region]

st.markdown(f"<div style='color:#888;font-size:0.9em;margin:8px 0 16px;'>"
            f"<b>{len(filtered)}</b> 件の店舗が見つかりました</div>",
            unsafe_allow_html=True)

# ── 店舗カードを 3 カラムで表示 ──────────────────────
_TYPE_COLORS = {
    "100均":   ("#00695C", "#E0F2F1"),
    "コンビニ": ("#1565C0", "#E3F2FD"),
    "百貨店":  ("#6A1B9A", "#F3E5F5"),
    "EC":      ("#E65100", "#FFF3E0"),
    "その他":  ("#555555", "#EEEEEE"),
}

cols = st.columns(3)
for i, store in enumerate(filtered):
    stype       = store.get("store_type", "その他")
    color, bg   = _TYPE_COLORS.get(stype, ("#555", "#EEE"))
    name        = _html.escape(store.get("name", ""))
    region      = _html.escape(store.get("region") or "")
    address     = _html.escape(store.get("address") or "")
    x_account   = store.get("x_account", "")
    website_url = store.get("website_url", "")

    type_badge = (f'<span style="background:{bg};color:{color};padding:2px 10px;'
                  f'border-radius:12px;font-size:0.78em;font-weight:bold;">'
                  f'{_html.escape(stype)}</span>')
    address_html = (f'<div style="color:#888;font-size:0.82em;margin-top:4px;">🗺️ {address}</div>'
                    if address else "")
    x_html = (f'<div style="color:#1DA1F2;font-size:0.82em;margin-top:2px;">'
              f'𝕏 @{_html.escape(x_account)}</div>' if x_account else "")
    btn_html = ""
    if website_url:
        btn_html = (f'<a href="{_html.escape(website_url)}" target="_blank" '
                    f'style="display:block;margin-top:10px;text-align:center;'
                    f'background:#FCE4EC;color:#E91E8C;padding:7px;border-radius:8px;'
                    f'text-decoration:none;font-size:0.85em;font-weight:bold;">🌐 公式サイト</a>')

    card_html = f"""
<div style="background:white;border-radius:14px;padding:16px 18px;margin-bottom:14px;
            box-shadow:0 2px 10px rgba(0,0,0,0.06);border-top:3px solid {color};">
    <div style="font-weight:700;color:#2D2D2D;font-size:0.97em;margin-bottom:6px;">{name}</div>
    <div>{type_badge}&nbsp;<span style="color:#888;font-size:0.85em;">📍 {region}</span></div>
    {address_html}
    {x_html}
    {btn_html}
</div>"""

    with cols[i % 3]:
        st.markdown(card_html, unsafe_allow_html=True)
