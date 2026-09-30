import streamlit as st
import pandas as pd
from pyproj import Transformer
import urllib.request
import json

# 画面を横広に使いやすく設定
st.set_page_config(page_title="座標・ジオイド変換ツール", layout="wide")

st.title("🌐 座標・ジオイド変換ツール")

# タブで「手入力」と「CSV一括」を分ける
tab1, tab2 = st.tabs(["📝 手入力（単一座標・ジオイド計算）", "📁 CSV一括変換"])

# ==========================================
# タブ1：手入力モード
# ==========================================
with tab1:
    col_in, col_out = st.columns([1, 1.2])
    
    with col_in:
        st.subheader("平面直角座標系")
        zone_manual = st.selectbox("系番号 (1〜19)", list(range(1, 20)), index=11, key="zone_manual")
        
        st.write("---")
        x_input = st.number_input("X座標 (m)", value=-97319.006, format="%.3f")
        y_input = st.number_input("Y座標 (m)", value=-47020.992, format="%.3f")
        z_input = st.number_input("標高 (m)", value=8.467, format="%.3f")
        ant_input = st.number_input("アンテナ高 (m)", value=1.500, format="%.3f")
        
        st.caption("DJI D-RTK2 : 1.8019m\n\nDJI D-RTK3 : 任意のポール高+0.1m")
        
        calc_btn = st.button("座標変換を実行", type="primary")

    with col_out:
        if calc_btn:
            epsg_latlon = 6668 # JGD2011
            epsg_xy = 6668 + zone_manual
            transformer = Transformer.from_crs(epsg_xy, epsg_latlon, always_xy=True)
            
            # y_input(東向き), x_input(北向き)の順で渡す
            lon, lat = transformer.transform(y_input, x_input)
            
            # ジオイド高の取得 (国土地理院APIを使用)
            geoid = None
            geoid_err = False
            try:
                # 修正: パラメータ名を latitude と longitude に変更し、User-Agentを追加
                url = f"https://vldb.gsi.go.jp/sokuchi/surveycalc/geoid/calcgh/cgi/geoidcalc.pl?outputType=json&latitude={lat}&longitude={lon}"
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
                with urllib.request.urlopen(req) as response:
                    data = json.loads(response.read().decode('utf-8'))
                    if 'OutputData' in data and 'geoidHeight' in data['OutputData']:
                        geoid = float(data['OutputData']['geoidHeight'])
                    else:
                        geoid_err = True
            except Exception as e:
                geoid_err = True
            
            if not geoid_err and geoid is not None:
                # 高さの計算
                ellipsoid_height = z_input + geoid
                total_height = ellipsoid_height + ant_input
                
                # 度分秒(60進法)への変換関数
                def to_dms(deg):
                    d = int(deg)
                    m = int((deg - d) * 60)
                    s = (deg - d - m/60) * 3600
                    return f"{d}度{m:02d}分{s:.5f}秒"
                    
                # 結果を画面右側に綺麗に表示する
                st.markdown(f"""
                <div style="border: 1px solid #ddd; padding: 25px; border-radius: 8px; background-color: #fcfcfc;">
                    <h4 style="margin-top:0;">入力値</h4>
                    <p style="margin:0;">平面直角座標系 : {zone_manual} 系</p>
                    <p style="margin:0;">X : {x_input:.3f} m</p>
                    <p style="margin:0;">Y : {y_input:.3f} m</p>
                    <p style="margin:0;">標高 : {z_input:.3f} m</p>
                    <p style="margin:0;">アンテナ高 : {ant_input:.3f} m</p>
                    <hr style="margin: 15px 0;">
                    <h4 style="color:#1e88e5;">変換結果</h4>
                    <p style="margin:0;"><b>① 経度 : </b> {lon:.8f} 度 <br><span style="color:#666; font-size:0.9em; margin-left:15px;">(60進法: {to_dms(lon)})</span></p>
                    <p style="margin:5px 0 0 0;"><b>② 緯度 : </b> {lat:.8f} 度 <br><span style="color:#666; font-size:0.9em; margin-left:15px;">(60進法: {to_dms(lat)})</span></p>
                    <p style="margin:10px 0 0 0;"><b>ジオイド高 : </b> {geoid:.4f} m</p>
                    <p style="margin:0;"><b>楕円体高 : </b> {ellipsoid_height:.3f} m</p>
                    <p style="margin:0; font-size:1.1em; color:#d32f2f;"><b>③ 入力高 : </b> {total_height:.3f} m</p>
                    <p style="font-size: 0.85em; color: #555; margin-top:15px;">※ 入力高 ＝ 標高 ＋ ジオイド高 ＋ アンテナ高</p>
                    <p style="font-size: 0.75em; color: #888;">※ 本ツールのジオイド高は国土地理院API (GSIGEO2011/2024) より取得しています。<br>サーバーの混雑状況等により取得エラーになる場合があります。</p>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.error("⚠️ 国土地理院サーバーからのジオイド高の取得に失敗しました。時間をおいて再度お試しください。")
        else:
            st.info("👈 左側の数値を入力して「座標変換を実行」ボタンを押してください。")

# ==========================================
# タブ2：CSV一括変換モード (既存の機能)
# ==========================================
with tab2:
    st.write("CSVファイルを読み込み、緯度経度 ⇔ XYZ（平面直角座標）を一括変換します。")
    st.header("1. 変換設定")
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
            
        zone = st.selectbox("平面直角座標系の系番号 (1〜19)", list(range(1, 20)), index=11)
        if datum in ["JGD2011 (日本測地系2011)", "WGS84 (世界測地系)"]:
            epsg_xy = 6668 + zone
        else:
            epsg_xy = 30160 + zone

    st.header("2. CSVファイルのアップロード")
    has_header = st.checkbox("1行目は列名（ヘッダー）として扱う", value=False)
    st.write("※ EX-TREND武蔵などの出力で、1行目から座標データが始まる場合はチェックを外したままにしてください。")
    uploaded_file = st.file_uploader("CSVファイルを選択", type="csv")

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

        st.write("■ 入力データプレビュー:")
        st.dataframe(df.head())

        st.header("3. 変換実行")
        if st.button("一括変換を実行する", type="primary"):
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
                    st.write("■ 変換結果プレビュー:")
                    st.dataframe(df.head())
                    csv_data = df.to_csv(index=False).encode('utf-8-sig')
                    st.download_button(label="📥 変換結果をダウンロード (CSV)", data=csv_data, file_name="converted_coordinates.csv", mime="text/csv")
            except Exception as e:
                st.error(f"処理中にエラーが発生しました: {e}")
