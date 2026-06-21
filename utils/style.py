import html as _html
import streamlit as st

# ── カラーパレット ──────────────────────────────────────
PINK_PRIMARY  = "#E91E8C"
PINK_LIGHT    = "#F48FB1"
PINK_PALE     = "#FCE4EC"
CREAM_BG      = "#FFF8F5"
CARD_BG       = "#FFFFFF"
BORDER_COLOR  = "#FFD1DC"
TEXT_DARK     = "#2D2D2D"
TEXT_MUTED    = "#888888"


def apply_global_styles():
    """全ページ共通のCSS を注入する"""
    st.markdown(f"""
    <style>
    /* ── 全体背景 ── */
    .stApp {{ background-color: {CREAM_BG}; }}

    /* ── メインエリア幅・余白 ── */
    .block-container {{
        padding-top: 1rem !important;
        padding-bottom: 3rem !important;
        max-width: 1020px !important;
    }}

    /* ── サイドバー ── */
    [data-testid="stSidebar"] {{
        background: linear-gradient(180deg, #FFF0F5 0%, #FFE0EE 100%) !important;
    }}
    [data-testid="stSidebarNav"] a {{
        color: #AD1457 !important;
        border-radius: 8px !important;
        font-weight: 500;
    }}
    [data-testid="stSidebarNav"] a:hover {{
        background-color: {PINK_PALE} !important;
    }}

    /* ── 見出し ── */
    h1 {{ color: #AD1457 !important; font-weight: 700 !important; }}
    h2 {{ color: #AD1457 !important; }}
    h3 {{ color: #C2185B !important; }}

    /* ── ボーダー付きコンテナ ── */
    [data-testid="stVerticalBlockBorderWrapper"] {{
        border-radius: 14px !important;
        border-color: {BORDER_COLOR} !important;
        background: {CARD_BG} !important;
        box-shadow: 0 2px 10px rgba(233,30,140,0.07) !important;
    }}

    /* ── タブ ── */
    .stTabs [data-baseweb="tab-list"] {{
        background-color: {PINK_PALE};
        border-radius: 12px;
        gap: 4px;
        padding: 5px;
    }}
    .stTabs [data-baseweb="tab"] {{
        border-radius: 8px;
        color: #AD1457 !important;
        font-weight: 600;
    }}
    .stTabs [aria-selected="true"] {{
        background-color: white !important;
        color: {PINK_PRIMARY} !important;
    }}

    /* ── ボタン ── */
    [data-testid="stButton"] > button[kind="primary"] {{
        background: linear-gradient(135deg, {PINK_LIGHT}, {PINK_PRIMARY}) !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: bold !important;
        box-shadow: 0 2px 8px rgba(233,30,140,0.3);
    }}
    [data-testid="stButton"] > button[kind="secondary"] {{
        border-color: {PINK_PRIMARY} !important;
        color: {PINK_PRIMARY} !important;
        border-radius: 8px !important;
    }}

    /* ── エクスパンダー ── */
    details {{ border-color: {BORDER_COLOR} !important; border-radius: 10px !important; }}

    /* ── 区切り線 ── */
    hr {{ border-color: {BORDER_COLOR} !important; }}

    /* ── 入力フィールド ── */
    [data-testid="stTextInput"] input,
    [data-testid="stTextArea"] textarea {{
        border-radius: 8px !important;
        border-color: {BORDER_COLOR} !important;
    }}
    [data-testid="stTextInput"] input:focus,
    [data-testid="stTextArea"] textarea:focus {{
        border-color: {PINK_PRIMARY} !important;
        box-shadow: 0 0 0 2px rgba(233,30,140,0.15) !important;
    }}

    /* ── アラート ── */
    [data-testid="stAlert"] {{ border-radius: 10px !important; }}

    /* ── リンクボタン ── */
    [data-testid="stLinkButton"] a {{
        border-radius: 8px !important;
    }}

    /* ── キャプション ── */
    [data-testid="stCaptionContainer"] {{ color: {TEXT_MUTED} !important; }}
    </style>
    """, unsafe_allow_html=True)


def page_banner(title: str, subtitle: str = ""):
    """ページ上部のグラデーションバナーを表示する"""
    sub_html = (f'<div style="font-size:0.92em;opacity:0.92;margin-top:5px;">'
                f'{_html.escape(subtitle)}</div>') if subtitle else ""
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, {PINK_LIGHT} 0%, {PINK_PRIMARY} 100%);
        padding: 22px 28px; border-radius: 18px; margin-bottom: 22px;
        color: white; box-shadow: 0 4px 18px rgba(233,30,140,0.22);
    ">
        <div style="font-size:1.65em;font-weight:700;">{_html.escape(title)}</div>
        {sub_html}
    </div>
    """, unsafe_allow_html=True)


# ── バッジ・タグ HTML ───────────────────────────────────

_STATUS_STYLE = {
    "in_stock":     ("#E8F5E9", "#2E7D32", "🟢 在庫あり"),
    "out_of_stock": ("#FFEBEE", "#C62828", "🔴 在庫なし"),
    "limited":      ("#FFFDE7", "#F57F17", "🟡 残りわずか"),
}
_BORDER_COLORS = {
    "in_stock":     "#66BB6A",
    "out_of_stock": "#EF5350",
    "limited":      "#FFA726",
}
_CAT_COLORS = {
    "ぬいぐるみ": ("#E91E8C", "#FCE4EC"),
    "ガチャ":     ("#1565C0", "#E3F2FD"),
    "食玩":       ("#E65100", "#FFF3E0"),
    "コラボ":     ("#6A1B9A", "#F3E5F5"),
    "その他":     ("#00695C", "#E0F2F1"),
}


def status_badge(status: str) -> str:
    """在庫ステータスのバッジHTMLを返す"""
    bg, color, label = _STATUS_STYLE.get(status, ("#EEE", "#555", status))
    return (f'<span style="background:{bg};color:{color};padding:4px 13px;'
            f'border-radius:20px;font-size:0.83em;font-weight:bold;'
            f'white-space:nowrap;display:inline-block;">{label}</span>')


def category_tag(category: str) -> str:
    """カテゴリタグのHTMLを返す"""
    color, bg = _CAT_COLORS.get(category, ("#555", "#EEE"))
    return (f'<span style="background:{bg};color:{color};padding:2px 9px;'
            f'border-radius:12px;font-size:0.78em;font-weight:bold;">'
            f'{_html.escape(category)}</span>')


def report_card_html(r: dict) -> str:
    """在庫報告1件分のカードHTMLを返す"""
    product    = r.get("products") or {}
    store      = r.get("stores") or {}
    status     = r.get("status", "")
    border_col = _BORDER_COLORS.get(status, "#DDD")
    created    = r.get("created_at", "")[:16].replace("T", " ") if r.get("created_at") else ""

    name       = _html.escape(product.get("name", "（商品未設定）"))
    store_name = _html.escape(store.get("name", "（店舗未設定）"))
    region     = _html.escape(store.get("region", ""))
    stype      = _html.escape(store.get("store_type", ""))
    cat        = product.get("category", "")

    link_html = ""
    if r.get("x_post_url"):
        url = _html.escape(r["x_post_url"])
        link_html = (f' · <a href="{url}" target="_blank" '
                     f'style="color:#1DA1F2;text-decoration:none;font-size:0.8em;">𝕏 投稿を見る</a>')

    return f"""
<div style="background:white;border-radius:14px;padding:14px 18px;
            margin-bottom:10px;box-shadow:0 2px 10px rgba(0,0,0,0.05);
            border-left:4px solid {border_col};">
  <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px;">
    <div style="flex:1;min-width:0;">
      <div style="font-weight:700;color:{TEXT_DARK};font-size:0.97em;margin-bottom:4px;">
        {name} &nbsp;{category_tag(cat)}
      </div>
      <div style="color:#666;font-size:0.87em;">
        📍 {store_name}{"　" + region if region else ""}{"　｜ " + stype if stype else ""}
      </div>
      <div style="margin-top:5px;color:{TEXT_MUTED};font-size:0.8em;">
        🕐 {created}{link_html}
      </div>
    </div>
    <div style="flex-shrink:0;margin-top:2px;">{status_badge(status)}</div>
  </div>
</div>"""


def release_card_html(sc: dict) -> str:
    """発売スケジュール1件分のカードHTMLを返す"""
    product = sc.get("products") or {}
    store   = sc.get("stores") or {}
    name    = _html.escape(product.get("name", "（不明）"))
    date    = _html.escape(sc.get("scheduled_date", ""))
    cat     = product.get("category", "")
    store_name = _html.escape(store.get("name", "全国")) if store else "全国"
    confirmed  = "✅ 確定" if sc.get("is_confirmed") else "📌 予定"
    notes_html = ""
    if sc.get("notes"):
        notes_html = f'<div style="color:#888;font-size:0.8em;margin-top:3px;">📝 {_html.escape(sc["notes"])}</div>'

    amazon_html = ""
    if product.get("affiliate_amazon"):
        url = _html.escape(product["affiliate_amazon"])
        amazon_html = (f'<a href="{url}" target="_blank" '
                       f'style="font-size:0.82em;color:#E47911;text-decoration:none;'
                       f'background:#FFF8EE;padding:2px 8px;border-radius:6px;">'
                       f'🛒 Amazon</a>')

    return f"""
<div style="background:white;border-radius:14px;padding:13px 16px;
            margin-bottom:9px;box-shadow:0 2px 8px rgba(0,0,0,0.05);
            border-top:3px solid {_CAT_COLORS.get(cat, ('#E91E8C', '#FFF'))[0]};">
  <div style="font-weight:700;color:{TEXT_DARK};font-size:0.95em;margin-bottom:4px;">
    {name} &nbsp;{category_tag(cat)}
  </div>
  <div style="color:#555;font-size:0.87em;">
    📅 {date}　{confirmed}　｜　🏪 {store_name}
  </div>
  {notes_html}
  {"<div style='margin-top:6px;'>" + amazon_html + "</div>" if amazon_html else ""}
</div>"""
