import streamlit as st
import pandas as pd
from pyproj import Transformer

st.set_page_config(page_title="座標一括変換ツール", layout="centered")

st.title("🌐 座標一括変換ツール")
st.write("CSVファイルを読み込み、緯度経度 ⇔ XYZ（平面直角座標）を一括変換します。")

# --- 1. 変換設定 ---
st.header("1. 変換設定")
col1, col2 = st.columns(2)

with col1:
    # EX-TREND武蔵からの出力が多いと想定し、デフォルトを「XYZ → 緯度経度」に変更
    direction = st.radio("変換方向", ["緯度経度 → XYZ", "XYZ → 緯度経度"], index=1)

with col2:
    datum = st.selectbox("測地系", ["JGD2011 (日本測地系2011)", "WGS84 (世界測地系)", "Tokyo (日本測地系:旧)"])
    
    if datum == "JGD2011 (日本測地系2011)":
        epsg_latlon = 6668
    elif datum == "WGS84 (世界測地系)":
        epsg_latlon = 4326
    else:
        epsg_latlon = 4301 # Tokyo
        
    # 北海道（空知・石狩など）エリアの12系をデフォルトに設定
    zone = st.selectbox("平面直角座標系の系番号 (1〜19)", list(range(1, 20)), index=11)
    
    if datum in ["JGD2011 (日本測地系2011)", "WGS84 (世界測地系)"]:
        epsg_xy = 6668 + zone
    else:
        epsg_xy = 30160 + zone

st.info(f"内部パラメータ: 緯度経度(EPSG:{epsg_latlon}) ⇔ 平面直角座標(EPSG:{epsg_xy})")

# --- 2. ファイルアップロード ---
st.header("2. CSVファイルのアップロード")

# ヘッダー有無のチェックボックスを追加（デフォルトはチェックなし＝列名なし）
has_header = st.checkbox("1行目は列名（ヘッダー）として扱う", value=False)
st.write("※ EX-TREND武蔵などの出力で、1行目から座標データが始まる場合はチェックを**外したまま**にしてください。")

uploaded_file = st.file_uploader("CSVファイルを選択", type="csv")

def find_column(columns, candidates):
    cols_lower = [str(c).strip().lower() for c in columns]
    for candidate in candidates:
        if candidate.lower() in cols_lower:
            idx = cols_lower.index(candidate.lower())
            return columns[idx]
    return None

if uploaded_file is not None:
    # ファイル読み込み（ヘッダー有無の処理分岐）
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
            
    # ヘッダーがない場合、一般的な測量CSVの列名を自動付与
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

    # --- 3. 変換実行 ---
    st.header("3. 変換実行")
    if st.button("変換を実行する", type="primary"):
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
                    
            else: # XYZ → 緯度経度
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

            # 結果の表示とダウンロード
            if 'X座標_変換後(北)' in df.columns or '緯度_変換後' in df.columns:
                st.write("■ 変換結果プレビュー:")
                st.dataframe(df.head())
                
                csv_data = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button(
                    label="📥 変換結果をダウンロード (CSV)",
                    data=csv_data,
                    file_name="converted_coordinates.csv",
                    mime="text/csv"
                )

        except Exception as e:
            st.error(f"処理中にエラーが発生しました: {e}")