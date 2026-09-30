import streamlit as st
import pandas as pd
from pyproj import Transformer
import urllib.request
import json

# ==========================================
# 画面全体の設定
# ==========================================
st.set_page_config(page_title="ICT Earthworks | 座標変換ツール", page_icon="🌍", layout="wide", initial_sidebar_state="expanded")

# --- カスタムCSS（ボタンやタブのデザイン調整） ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&display=swap');
    html, body, [class*="css"]  {
        font-family: 'Noto Sans JP', sans-serif;
    }
    .block-container { padding-top: 2rem; }
    header {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* ボタンをグラデーションに */
    .stButton>button {
        background: linear-gradient(135deg, #0052D4 0%, #4364F7 50%, #6FB1FC 100%);
        color: white;
        border: none;
        border-radius: 8px;
        padding: 10px 24px;
        font-weight: 700;
        width: 100%;
        box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.1);
    }
    .stButton>button:hover {
        box-shadow: 0px 8px 15px rgba(67, 100, 247, 0.3);
        transform: translateY(-2px);
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# サイドバー（共通設定メニュー）
# ==========================================
with st.sidebar:
    st.markdown("<h2 style='text-align: center;'>⚙️ 共通設定</h2>", unsafe_allow_html=True)
    st.write("アプリ全体に適用される設定です。")
    st.divider()
    
    zone_global = st.selectbox("📍 平面直角座標系の系番号", list(range(1, 20)), index=11)
    st.info(f"現在の設定: **{zone_global}系**")
    
    st.divider()
    st.caption("© 2026 ICT Group Coordinate Tool")

# ==========================================
# メイン画面
# ==========================================
st.title("🌍 座標・ジオイド一括変換ツール")

tab1, tab2 = st.tabs(["📝 手入力（単一座標・ジオイド計算）", "📁 CSV一括変換"])

# ==========================================
# タブ1：手入力モード
# ==========================================
with tab1:
    col_in, col_out = st.columns([1, 1.2])
    
    with col_in:
        st.markdown("### 📥 座標入力")
        x_input = st.number_input("X座標 (北方向, m)", value=-97319.006, format="%.3f")
        y_input = st.number_input("Y座標 (東方向, m)", value=-47020.992, format="%.3f")
        z_input = st.number_input("標高 (m)", value=8.467, format="%.3f")
        
        st.markdown("### 📡 アンテナ設定")
        ant_input = st.number_input("アンテナ高 (m)", value=1.500, format="%.3f")
        
        with st.expander("💡 主要な機器のアンテナ高参考値"):
            st.write("- **DJI D-RTK2**: 1.8019 m")
            st.write("- **DJI D-RTK3**: 任意のポール高 + 0.1 m")
        
        st.write("")
        calc_btn = st.button("🚀 座標変換を実行する")

    with col_out:
        if calc_btn:
            epsg_latlon = 6668
            epsg_xy = 6668 + zone_global
            transformer = Transformer.from_crs(epsg_xy, epsg_latlon, always_xy=True)
            lon, lat = transformer.transform(y_input, x_input)
            
            geoid = None
            geoid_err = False
            
            with st.spinner('🌐 国土地理院サーバーからジオイド高を取得中...'):
                try:
                    url = f"https://vldb.gsi.go.jp/sokuchi/surveycalc/geoid/calcgh/cgi/geoidcalc.pl?outputType=json&latitude={lat}&longitude={lon}"
                    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                    with urllib.request.urlopen(req) as response:
                        data = json.loads(response.read().decode('utf-8'))
                        if 'OutputData' in data and 'geoidHeight' in data['OutputData']:
                            geoid = float(data['OutputData']['geoidHeight'])
                        else:
                            geoid_err = True
                except Exception as e:
                    geoid_err = True
            
            if not geoid_err and geoid is not None:
                ellipsoid_height = z_input + geoid
                total_height = ellipsoid_height + ant_input
                
                def to_dms(deg):
                    d = int(deg)
                    m = int((deg - d) * 60)
                    s = (deg - d - m/60) * 3600
                    return f"{d}° {m:02d}' {s:.5f}\""

                # Streamlitの標準コンポーネントで美しくダッシュボード風に表示
                st.markdown(f"### 🎯 変換結果 (JGD2011 / {zone_global}系)")
                
                res_col1, res_col2 = st.columns(2)
                with res_col1:
                    st.metric(label="① 緯度 (Latitude)", value=f"{lat:.8f}°", delta=f"度分秒: {to_dms(lat)}")
                with res_col2:
                    st.metric(label="② 経度 (Longitude)", value=f"{lon:.8f}°", delta=f"度分秒: {to_dms(lon)}")
                
                st.divider()
                
                st.markdown("#### 📏 高さの計算結果")
                st.info(f"**ジオイド高**: `{geoid:.4f} m`")
                st.success(f"**楕円体高** (標高 + ジオイド高): `{ellipsoid_height:.3f} m`")
                
                # 最も重要な「入力高」を大きく赤字で強調表示
                st.markdown(f"""
                <div style="background-color: #ffebee; padding: 20px; border-radius: 10px; border-left: 6px solid #d32f2f; text-align: center; margin-top: 15px;">
                    <span style="font-size: 1.1rem; color: #b71c1c; font-weight: bold;">③ 入力高 (楕円体高 + アンテナ高)</span><br>
                    <span style="font-size: 2.2rem; color: #d32f2f; font-weight: 700;">{total_height:.3f} m</span>
                </div>
                """, unsafe_allow_html=True)
                
                st.caption("※ 本ツールのジオイド高は国土地理院API (GSIGEO2011/2024) よりリアルタイム取得しています。")
            else:
                st.error("⚠️ 国土地理院サーバーからのジオイド高の取得に失敗しました。")
        else:
            st.info("👈 左側の数値を入力し、「座標変換を実行する」ボタンを押してください。")

# ==========================================
# タブ2：CSV一括変換モード
# ==========================================
with tab2:
    st.markdown("### 📁 CSV一括変換")
    st.write("測量ソフト（EX-TREND武蔵など）から出力したCSVファイルを一括で変換します。")
    
    with st.expander("⚙️ 変換オプションの詳細設定（クリックで開く）", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            direction = st.radio("変換方向", ["緯度経度 → XYZ", "XYZ → 緯度経度"], index=1)
        with col2:
            datum = st.selectbox("測地系", ["JGD2011 (日本測地系2011)", "WGS84 (世界測地系)", "Tokyo (日本測地系:旧)"])
            if datum == "JGD2011 (日本測地系2011)":
                epsg_latlon = 6668
            elif datum == "WGS84 (世界測地系)":
                epsg_latlon = 4326
            else:
                epsg_latlon = 4301
            
            if datum in ["JGD2011 (日本測地系2011)", "WGS84 (世界測地系)"]:
                epsg_xy = 6668 + zone_global
            else:
                epsg_xy = 30160 + zone_global
                
        has_header = st.checkbox("1行目は列名（ヘッダー）として扱う", value=False)
        st.caption("※ EX-TREND武蔵などの出力で、1行目から座標データが始まる場合はチェックを外したままにしてください。")
        
    uploaded_file = st.file_uploader("📤 CSVファイルをここにドラッグ＆ドロップ", type="csv")

    def find_column(columns, candidates):
        cols_lower = [str(c).strip().lower() for c in columns]
        for candidate in candidates:
            if candidate.lower() in cols_lower:
                return columns[cols_lower.index(candidate.lower())]
        return None

    if uploaded_file is not None:
        try:
            if has_header:
                df = pd.read_csv(uploaded_file, encoding='utf-8-sig')
            else:
                df = pd.read_csv(uploaded_file, encoding='utf-8-sig', header=None)
        except UnicodeDecodeError:
            uploaded_file.seek(0)
            if has_header:
                df = pd.read_csv(uploaded_file, encoding='cp932')
            else:
                df = pd.read_csv(uploaded_file, encoding='cp932', header=None)
                
        if not has_header:
            if len(df.columns) >= 4:
                if direction == "緯度経度 → XYZ":
                    df.columns = ['測点名', '緯度', '経度', '標高'] + list(df.columns[4:])
                else:
                    df.columns = ['測点名', 'X座標', 'Y座標', '標高'] + list(df.columns[4:])
            elif len(df.columns) == 3:
                if direction == "緯度経度 → XYZ":
                    df.columns = ['測点名', '緯度', '経度']
                else:
                    df.columns = ['測点名', 'X座標', 'Y座標']

        st.write("■ 入力データプレビュー")
        st.dataframe(df.head(), use_container_width=True)

        if st.button("🚀 一括変換を実行する"):
            try:
                if direction == "緯度経度 → XYZ":
                    lat_col = find_column(df.columns, ['lat', 'latitude', '緯度', 'B'])
                    lon_col = find_column(df.columns, ['lon', 'longitude', '経度', 'L'])
                    z_col = find_column(df.columns, ['z', 'z座標', '標高', 'h', 'height', 'Z'])
                    
                    if not lat_col or not lon_col:
                        st.error("エラー: CSVに「緯度」「経度」にあたる列が見つかりません。")
                    else:
                        transformer = Transformer.from_crs(epsg_latlon, epsg_xy, always_xy=True)
                        y_easting, x_northing = transformer.transform(df[lon_col].values, df[lat_col].values)
                        
                        df['X座標_変換後(北)'] = x_northing
                        df['Y座標_変換後(東)'] = y_easting
                        if z_col:
                            df['Z座標_変換後(標高)'] = df[z_col]
                        
                        st.success("✅ 変換が完了しました！")
                        
                else:
                    x_col = find_column(df.columns, ['x', 'x座標', 'x(北)', 'X'])
                    y_col = find_column(df.columns, ['y', 'y座標', 'y(東)', 'Y'])
                    z_col = find_column(df.columns, ['z', 'z座標', '標高', 'h', 'height', 'Z'])
                    
                    if not x_col or not y_col:
                        st.error("エラー: CSVに「X座標」「Y座標」にあたる列が見つかりません。")
                    else:
                        transformer = Transformer.from_crs(epsg_xy, epsg_latlon, always_xy=True)
                        lon, lat = transformer.transform(df[y_col].values, df[x_col].values)
                        
                        df['緯度_変換後'] = lat
                        df['経度_変換後'] = lon
                        if z_col:
                            df['標高_変換後'] = df[z_col]
                            
                        st.success("✅ 変換が完了しました！")

                if 'X座標_変換後(北)' in df.columns or '緯度_変換後' in df.columns:
                    st.write("■ 変換結果")
                    st.dataframe(df.head(), use_container_width=True)
                    csv_data = df.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(label="📥 変換結果をダウンロード (CSV)", data=csv_data, file_name="converted_coordinates.csv", mime="text/csv")
            except Exception as e:
                st.error(f"処理中にエラーが発生しました: {e}")
