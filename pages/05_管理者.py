import os
import streamlit as st
from utils.db import (
    get_all_products, insert_product, update_product, delete_product,
    get_all_stores,   insert_store,   update_store,   delete_store,
    get_inventory_reports, soft_delete_report,
    get_release_schedule,  insert_release_schedule, delete_release_schedule,
)
from utils.geocoder import address_to_coords
from utils.style import apply_global_styles, page_banner
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="管理者 | ちいかわグッズ情報", page_icon="🔧", layout="wide")
apply_global_styles()

# ── パスワード認証 ────────────────────────────────────
if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

if not st.session_state.admin_authenticated:
    st.title("🔒 管理者ログイン")
    password = st.text_input("パスワード", type="password")
    if st.button("ログイン", type="primary"):
        correct = os.environ.get("ADMIN_PASSWORD", "")
        if correct and password == correct:
            st.session_state.admin_authenticated = True
            st.rerun()
        else:
            st.error("パスワードが正しくありません。")
    st.stop()

# ── 管理者ダッシュボード ──────────────────────────────
st.title("🔧 管理者ダッシュボード")
if st.button("ログアウト", type="secondary"):
    st.session_state.admin_authenticated = False
    st.rerun()

tab_product, tab_store, tab_schedule, tab_report = st.tabs(
    ["🐰 商品管理", "🏪 店舗管理", "📅 発売スケジュール管理", "📦 報告管理"]
)

# ──────────────────────────────────────────────────────
# タブ1: 商品管理
# ──────────────────────────────────────────────────────
with tab_product:
    st.subheader("商品の登録・編集")

    # 新規登録フォーム
    with st.expander("➕ 新しい商品を登録", expanded=False):
        with st.form("new_product"):
            p_name     = st.text_input("商品名 *")
            p_category = st.selectbox("カテゴリ", ["ぬいぐるみ", "ガチャ", "食玩", "コラボ", "その他"])
            col1, col2 = st.columns(2)
            with col1:
                p_date  = st.date_input("公式発売日")
                p_price = st.number_input("定価（円）", min_value=0, step=100)
            with col2:
                p_site_url = st.text_input("公式サイトURL")
                p_img_url  = st.text_input("商品画像URL")
            p_amazon  = st.text_input("Amazonアフィリエイト URL")
            p_rakuten = st.text_input("楽天アフィリエイト URL")
            p_notes   = st.text_area("備考")
            if st.form_submit_button("登録する", type="primary"):
                if not p_name:
                    st.error("商品名は必須です。")
                else:
                    try:
                        insert_product({
                            "name": p_name, "category": p_category,
                            "official_release_date": p_date.isoformat(),
                            "official_price": p_price if p_price > 0 else None,
                            "official_site_url": p_site_url or None,
                            "image_url": p_img_url or None,
                            "affiliate_amazon": p_amazon or None,
                            "affiliate_rakuten": p_rakuten or None,
                            "notes": p_notes or None,
                        })
                        st.success(f"✅ 「{p_name}」を登録しました。")
                        st.rerun()
                    except Exception as e:
                        st.error(f"登録に失敗しました: {e}")

    # 商品一覧と削除
    st.write("**登録済み商品一覧**")
    try:
        products = get_all_products()
    except Exception as e:
        st.error(f"データ取得エラー: {e}")
        products = []

    for p in products:
        with st.container(border=True):
            c1, c2 = st.columns([5, 1])
            with c1:
                st.write(f"**{p['name']}**　｜　{p.get('category', '')}　｜　{p.get('official_release_date', '')}　｜　¥{p.get('official_price', '不明')}")
            with c2:
                if st.button("🗑️ 削除", key=f"del_p_{p['id']}"):
                    delete_product(p["id"])
                    st.success("削除しました。")
                    st.rerun()

# ──────────────────────────────────────────────────────
# タブ2: 店舗管理
# ──────────────────────────────────────────────────────
with tab_store:
    st.subheader("店舗の登録・編集")

    with st.expander("➕ 新しい店舗を登録", expanded=False):
        with st.form("new_store"):
            s_name = st.text_input("店舗名 *")
            col1, col2 = st.columns(2)
            with col1:
                s_type   = st.selectbox("店舗種別", ["100均", "コンビニ", "スーパー", "ガチャガチャ", "百貨店", "雑貨", "ちいかわ公式", "EC", "その他"])
                s_region = st.text_input("地域（都道府県）")
            with col2:
                s_site = st.text_input("公式サイトURL")
                s_x    = st.text_input("Xアカウント名（@なし）")
            s_address = st.text_input("住所（入力すると座標を自動取得します）")
            if st.form_submit_button("登録する", type="primary"):
                if not s_name:
                    st.error("店舗名は必須です。")
                else:
                    lat, lon = None, None
                    if s_address:
                        with st.spinner("住所から座標を取得中..."):
                            lat, lon = address_to_coords(s_address)
                        if lat:
                            st.info(f"座標を取得しました: 緯度 {lat:.4f}, 経度 {lon:.4f}")
                        else:
                            st.warning("座標の自動取得に失敗しました。住所を確認してください。")
                    try:
                        insert_store({
                            "name": s_name, "store_type": s_type,
                            "region": s_region or None, "address": s_address or None,
                            "latitude": lat, "longitude": lon,
                            "website_url": s_site or None, "x_account": s_x or None,
                        })
                        st.success(f"✅ 「{s_name}」を登録しました。")
                        st.rerun()
                    except Exception as e:
                        st.error(f"登録に失敗しました: {e}")

    st.write("**登録済み店舗一覧**")
    try:
        stores = get_all_stores()
    except Exception as e:
        st.error(f"データ取得エラー: {e}")
        stores = []

    for s in stores:
        with st.container(border=True):
            c1, c2 = st.columns([5, 1])
            with c1:
                coords = f"📍 ({s['latitude']:.3f}, {s['longitude']:.3f})" if s.get("latitude") else "📍 座標なし"
                st.write(f"**{s['name']}**　｜　{s.get('store_type', '')}　｜　{s.get('region', '')}　｜　{coords}")
            with c2:
                if st.button("🗑️ 削除", key=f"del_s_{s['id']}"):
                    delete_store(s["id"])
                    st.success("削除しました。")
                    st.rerun()

# ──────────────────────────────────────────────────────
# タブ3: 発売スケジュール管理
# ──────────────────────────────────────────────────────
with tab_schedule:
    st.subheader("発売スケジュールの登録・削除")

    try:
        products = get_all_products()
        stores   = get_all_stores()
    except Exception as e:
        st.error(f"データ取得エラー: {e}")
        products, stores = [], []

    with st.expander("➕ 発売スケジュールを登録", expanded=False):
        with st.form("new_schedule"):
            sc_product = st.selectbox("商品", [p["name"] for p in products] if products else ["（商品なし）"])
            col1, col2 = st.columns(2)
            with col1:
                sc_date      = st.date_input("発売予定日")
                sc_confirmed = st.checkbox("発売確定（チェックなし = 予定）")
            with col2:
                sc_store = st.selectbox("販売店（全国発売の場合は選択不要）", ["（全国）"] + [s["name"] for s in stores])
            sc_notes = st.text_input("備考（ポップアップ限定・数量限定 など）")
            if st.form_submit_button("登録する", type="primary"):
                p_id = next((p["id"] for p in products if p["name"] == sc_product), None)
                s_id = next((s["id"] for s in stores if s["name"] == sc_store), None)
                if not p_id:
                    st.error("商品を選択してください。")
                else:
                    try:
                        insert_release_schedule({
                            "product_id": p_id, "store_id": s_id,
                            "scheduled_date": sc_date.isoformat(),
                            "is_confirmed": sc_confirmed,
                            "notes": sc_notes or None,
                        })
                        st.success("✅ 登録しました。")
                        st.rerun()
                    except Exception as e:
                        st.error(f"登録に失敗しました: {e}")

    st.write("**登録済み発売スケジュール**")
    try:
        schedules = get_release_schedule(months_ahead=6)
    except Exception as e:
        st.error(f"データ取得エラー: {e}")
        schedules = []

    for sc in schedules:
        product = sc.get("products") or {}
        store   = sc.get("stores") or {}
        with st.container(border=True):
            c1, c2 = st.columns([5, 1])
            with c1:
                confirmed = "✅ 確定" if sc.get("is_confirmed") else "📌 予定"
                st.write(f"**{product.get('name', '（不明）')}**　｜　{sc['scheduled_date']}　{confirmed}　｜　{store.get('name', '全国') if store else '全国'}")
            with c2:
                if st.button("🗑️ 削除", key=f"del_sc_{sc['id']}"):
                    delete_release_schedule(sc["id"])
                    st.success("削除しました。")
                    st.rerun()

# ──────────────────────────────────────────────────────
# タブ4: 在庫報告管理
# ──────────────────────────────────────────────────────
with tab_report:
    st.subheader("在庫報告の確認・削除")
    st.caption("問題のある報告（スパム・虚偽情報）はここから削除できます。")

    try:
        reports = get_inventory_reports(limit=50)
    except Exception as e:
        st.error(f"データ取得エラー: {e}")
        reports = []

    for r in reports:
        product = r.get("products") or {}
        store   = r.get("stores") or {}
        with st.container(border=True):
            c1, c2 = st.columns([5, 1])
            with c1:
                st.write(
                    f"**{product.get('name', '（商品未設定）')}**　at　{store.get('name', '（店舗未設定）')}"
                    f"　｜　{r.get('status', '')}　｜　{r.get('source', '')}"
                )
                created = r.get("created_at", "")[:16].replace("T", " ")
                st.caption(f"報告日時: {created}")
                if r.get("x_post_url"):
                    st.caption(f"元の投稿: {r['x_post_url']}")
            with c2:
                if st.button("🗑️ 削除", key=f"del_r_{r['id']}"):
                    soft_delete_report(r["id"])
                    st.success("削除しました。")
                    st.rerun()
