import streamlit as st
from dotenv import load_dotenv
from utils.style import apply_global_styles, page_banner, report_card_html
from utils.db import get_inventory_reports, get_all_products, get_all_stores, insert_inventory_report

load_dotenv()

st.set_page_config(page_title="在庫状況 | ちいかわグッズ情報", page_icon="📦", layout="wide")
apply_global_styles()
page_banner("📦 在庫状況", "ユーザーから報告された在庫情報をリアルタイム表示しています")

st.warning("掲載情報はユーザーからの報告です。公式情報ではなく、在庫は変動する場合があります。", icon="ℹ️")

# ── データ取得 ────────────────────────────────────────
try:
    products = get_all_products()
    stores   = get_all_stores()
except Exception as e:
    st.error(f"データの取得に失敗しました: {e}")
    st.stop()

# ── フィルター ────────────────────────────────────────
with st.expander("🔍 絞り込む", expanded=True):
    col1, col2, col3 = st.columns(3)
    with col1:
        product_options = {"すべての商品": None} | {p["name"]: p["id"] for p in products}
        selected_product_name = st.selectbox("商品", list(product_options.keys()))
        selected_product_id = product_options[selected_product_name]
    with col2:
        store_types = ["すべての店舗種別", "100均", "コンビニ", "百貨店", "EC", "その他"]
        selected_type = st.selectbox("店舗種別", store_types)
    with col3:
        status_options = {
            "すべてのステータス": None,
            "🟢 在庫あり": "in_stock",
            "🟡 残りわずか": "limited",
            "🔴 在庫なし": "out_of_stock",
        }
        selected_status_name = st.selectbox("ステータス", list(status_options.keys()))
        selected_status = status_options[selected_status_name]

# ── 在庫報告一覧 ──────────────────────────────────────
try:
    reports = get_inventory_reports(limit=50, product_id=selected_product_id, status=selected_status)
except Exception as e:
    st.error(f"在庫報告の取得に失敗しました: {e}")
    reports = []

if selected_type != "すべての店舗種別":
    reports = [r for r in reports if r.get("stores") and r["stores"].get("store_type") == selected_type]

st.markdown(f"<div style='color:#888;font-size:0.9em;margin-bottom:8px;'>"
            f"<b>{len(reports)}</b> 件の報告が見つかりました</div>",
            unsafe_allow_html=True)

if reports:
    st.markdown("".join(report_card_html(r) for r in reports), unsafe_allow_html=True)
else:
    st.info("条件に合う在庫報告はありません。")

st.divider()

# ── Webフォームで在庫報告 ─────────────────────────────
st.markdown("### 📝 在庫情報を報告する")
st.caption("XアカウントがなくてもWebフォームから報告できます。")

with st.form("inventory_form", clear_on_submit=True):
    col_f1, col_f2 = st.columns(2)
    with col_f1:
        form_product = st.selectbox("商品名 *", ["（選択してください）"] + [p["name"] for p in products])
    with col_f2:
        form_store = st.selectbox("店舗名 *", ["（選択してください）"] + [s["name"] for s in stores])

    form_status = st.radio("在庫状況 *", ["在庫あり", "残りわずか", "在庫なし"], horizontal=True)
    submitted = st.form_submit_button("📤 報告する", type="primary", use_container_width=True)

if submitted:
    if form_product == "（選択してください）" or form_store == "（選択してください）":
        st.error("商品名と店舗名を選択してください。")
    else:
        status_map = {"在庫あり": "in_stock", "残りわずか": "limited", "在庫なし": "out_of_stock"}
        p_id = next(p["id"] for p in products if p["name"] == form_product)
        s_id = next(s["id"] for s in stores   if s["name"] == form_store)
        try:
            insert_inventory_report({"product_id": p_id, "store_id": s_id,
                                     "status": status_map[form_status], "source": "web_form"})
            st.success("✅ 報告を受け付けました！ありがとうございます。")
            st.rerun()
        except Exception as e:
            st.error(f"報告の登録に失敗しました: {e}")
