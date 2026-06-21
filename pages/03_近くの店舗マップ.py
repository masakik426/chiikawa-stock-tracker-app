import streamlit as st
import folium
from streamlit_folium import st_folium
from streamlit_js_eval import get_geolocation
from geopy.distance import geodesic
from dotenv import load_dotenv
from utils.style import apply_global_styles, page_banner
from utils.db import get_stores_with_stock, get_all_products, CATEGORY_COLORS

load_dotenv()

st.set_page_config(page_title="近くの店舗マップ | ちいかわグッズ情報", page_icon="🗺️", layout="wide")
apply_global_styles()
page_banner("🗺️ 近くの在庫店舗を探す", "現在地から近い順に、在庫ありの店舗を地図で表示します")

# ── アイテムフィルター ────────────────────────────────
st.subheader("① 探している商品を選ぶ")

try:
    products = get_all_products()
except Exception as e:
    st.error(f"商品データの取得に失敗しました: {e}")
    st.stop()

col1, col2, col3 = st.columns(3)
with col1:
    categories = ["すべて"] + list(CATEGORY_COLORS.keys())
    selected_category = st.selectbox("カテゴリ", categories)

# カテゴリ選択に応じて商品リストを絞り込む
if selected_category == "すべて":
    filtered_products = products
else:
    filtered_products = [p for p in products if p.get("category") == selected_category]

with col2:
    product_names = ["（すべての商品）"] + [p["name"] for p in filtered_products]
    selected_product_name = st.selectbox("商品名", product_names)
    selected_product = next(
        (p for p in filtered_products if p["name"] == selected_product_name), None
    )

with col3:
    hours_options = {"6時間以内": 6, "24時間以内": 24, "3日以内": 72, "期限なし": 9999}
    selected_hours_label = st.selectbox("報告期限（情報の新しさ）", list(hours_options.keys()), index=1)
    selected_hours = hours_options[selected_hours_label]

st.divider()

# ── 現在地の取得 ──────────────────────────────────────
st.subheader("② 現在地を取得する")
st.caption("「現在地を取得」ボタンを押すと、ブラウザが位置情報の許可を求めます。")

# get_geolocation() はブラウザのGPS機能を呼び出して緯度・経度を返す
location = get_geolocation()

if not location:
    st.info("👆 上の「Locate me」または位置情報の許可ダイアログで「許可」を選択してください。")
    # 現在地が取得できない場合は東京駅を中心に表示
    user_lat, user_lon = 35.6812, 139.7671
    show_user_marker = False
else:
    user_lat  = location["coords"]["latitude"]
    user_lon  = location["coords"]["longitude"]
    show_user_marker = True
    st.success(f"✅ 現在地を取得しました（緯度: {user_lat:.4f}, 経度: {user_lon:.4f}）")

st.divider()

# ── 在庫あり店舗を取得・距離順に並べる ────────────────
st.subheader("③ 在庫あり店舗の地図")

try:
    if selected_product:
        reports = get_stores_with_stock(selected_product["id"], hours=selected_hours)
    else:
        # 商品を選んでいない場合はすべての在庫あり報告を取得
        from utils.db import get_inventory_reports
        reports = get_inventory_reports(limit=100, status="in_stock")
except Exception as e:
    st.error(f"在庫データの取得に失敗しました: {e}")
    reports = []

# 座標情報がある店舗のみ抽出し、距離を計算して近い順に並べる
stores_with_distance = []
for r in reports:
    store = r.get("stores") or {}
    lat = store.get("latitude")
    lon = store.get("longitude")
    if lat and lon:
        dist_km = geodesic((user_lat, user_lon), (lat, lon)).km
        stores_with_distance.append({**r, "_distance_km": dist_km})

stores_with_distance.sort(key=lambda x: x["_distance_km"])

# ── Folium マップを作成 ───────────────────────────────
m = folium.Map(location=[user_lat, user_lon], zoom_start=13)

# 現在地マーカー（青）
if show_user_marker:
    folium.Marker(
        location=[user_lat, user_lon],
        popup="📍 現在地",
        icon=folium.Icon(color="blue", icon="user", prefix="fa"),
    ).add_to(m)

# 在庫あり店舗マーカー（赤）
for r in stores_with_distance:
    store = r.get("stores") or {}
    product = r.get("products") or {}
    lat = store["latitude"]
    lon = store["longitude"]
    dist = r["_distance_km"]
    created = r.get("created_at", "")[:16].replace("T", " ") if r.get("created_at") else ""

    popup_html = (
        f"<b>{store.get('name', '不明')}</b><br>"
        f"🐰 {product.get('name', '（商品未設定）')}<br>"
        f"📍 {store.get('address', '')}<br>"
        f"🕐 {created} 報告<br>"
        f"📏 現在地から約 {dist:.1f} km"
    )
    folium.Marker(
        location=[lat, lon],
        popup=folium.Popup(popup_html, max_width=250),
        icon=folium.Icon(color="red", icon="shopping-cart", prefix="fa"),
    ).add_to(m)

# マップを表示
st_folium(m, width="100%", height=500)

# ── 距離順リスト ──────────────────────────────────────
if stores_with_distance:
    st.divider()
    st.subheader(f"📋 近い順リスト（{len(stores_with_distance)} 件）")
    for i, r in enumerate(stores_with_distance, 1):
        store   = r.get("stores") or {}
        product = r.get("products") or {}
        dist    = r["_distance_km"]
        created = r.get("created_at", "")[:16].replace("T", " ") if r.get("created_at") else ""

        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            with c1:
                st.write(f"**{i}位　{store.get('name', '不明')}**　📏 約 {dist:.1f} km")
                st.caption(
                    f"🐰 {product.get('name', '（商品未設定）')}　｜　"
                    f"📍 {store.get('address', store.get('region', ''))}　｜　"
                    f"🕐 {created} 報告"
                )
            with c2:
                if r.get("x_post_url"):
                    st.link_button("元の投稿", r["x_post_url"], use_container_width=True)
elif show_user_marker:
    st.info("現在地周辺に条件に合う在庫情報が見つかりませんでした。絞り込み条件を変えてみてください。")
