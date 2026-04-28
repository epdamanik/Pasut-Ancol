import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
import os
import time

# --- IMPORT SELENIUM ---
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager

# --- 0. AUTO REFRESH (Update tiap 15 Menit) ---
# 15 menit * 60 detik * 1000 milidetik
st_autorefresh(interval=15 * 60 * 1000, key="datarefresh")

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Pasut ANCOL 15-Min", layout="wide", page_icon="🌊")

# Nama file data
FILE_PREDIKSI = 'prediksi_pasut_ancol_2026_FINAL_WIB.xlsx'
FILE_HISTORY = 'history_aws.csv'
BATAS_ROB = 2.5

# --- 2. FUNGSI PERMANEN (CSV) ---
def save_to_csv(waktu, nilai):
    new_data = pd.DataFrame({'waktu': [waktu], 'nilai': [nilai]})
    if not os.path.exists(FILE_HISTORY):
        new_data.to_csv(FILE_HISTORY, index=False)
    else:
        old_data = pd.read_csv(FILE_HISTORY)
        # Gabung dan hapus duplikat berdasarkan waktu menit yang sama
        combined = pd.concat([old_data, new_data]).drop_duplicates(subset=['waktu'])
        combined.to_csv(FILE_HISTORY, index=False)

# --- 3. FUNGSI SCRAPING ---
@st.cache_data(ttl=800) # Sedikit di bawah 15 menit
def fetch_aws_realtime():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        driver.get("http://202.90.199.132/aws-new/monitoring/3000000018")
        time.sleep(5)
        val_text = driver.find_element(By.ID, "waterlevel").text.strip()
        driver.quit()
        val = float(val_text.replace('m', ''))
        return val, datetime.now()
    except:
        return None, None

# --- 4. LOAD DATA ---
@st.cache_data(ttl=3600)
def load_prediction(filename):
    if not os.path.exists(filename): return None, "File Prediksi Hilang", None
    df = pd.read_excel(filename, engine='openpyxl')
    cols = df.columns
    tgl_col = next((c for c in ['tanggal_prediksi', 'jam_group', 'Waktu_WIB', 'Waktu'] if c in cols), None)
    val_col = next((c for c in ['wl_prediksi', 'wl_final', 'Tinggi_Navigasi_m'] if c in cols), None)
    df[tgl_col] = pd.to_datetime(df[tgl_col])
    return df.sort_values(tgl_col), tgl_col, val_col

# --- EKSEKUSI DATA ---
df_pred, col_tgl, col_val = load_prediction(FILE_PREDIKSI)
aws_val, aws_time = fetch_aws_realtime()

# Simpan ke CSV jika berhasil scrap
if aws_val is not None:
    save_to_csv(aws_time.strftime('%Y-%m-%d %H:%M'), aws_val)

# --- 5. UI DASHBOARD ---
st.title("🌊 Dashboard Pasut Ancol (15-Min Monitoring)")

if df_pred is not None:
    sekarang = datetime.now()
    
    # Ambil Data History dari CSV
    df_hist = pd.read_csv(FILE_HISTORY) if os.path.exists(FILE_HISTORY) else pd.DataFrame()
    if not df_hist.empty:
        df_hist['waktu'] = pd.to_datetime(df_hist['waktu'])

    # Logika Metrik
    idx_now = (df_pred[col_tgl] - sekarang).abs().idxmin()
    h_pred = df_pred.loc[idx_now, col_val]
    
    m1, m2, m3 = st.columns(3)
    val_akhir = aws_val if aws_val else (df_hist['nilai'].iloc[-1] if not df_hist.empty else h_pred)
    
    m1.metric("AWS Real-time", f"{val_akhir:.2f} m")
    m2.metric("Prediksi Model", f"{h_pred:.2f} m")
    m3.metric("Selisih (Surge)", f"{val_akhir - h_pred:.2f} m")

    # --- 6. GRAFIK ---
    fig = go.Figure()

    # A. Garis Prediksi (Biru Tipis)
    t_start = sekarang - timedelta(hours=12)
    t_end = sekarang + timedelta(hours=12)
    df_view = df_pred[(df_pred[col_tgl] >= t_start) & (df_pred[col_tgl] <= t_end)]
    
    fig.add_trace(go.Scatter(x=df_view[col_tgl], y=df_view[col_val], mode='lines+markers',
                             line=dict(color='rgba(0, 123, 255, 0.3)', dash='dot'),
                             marker=dict(size=3, color='#007bff'), name='Prediksi Astronomis'))

    # B. Jejak AWS Permanen (Garis Merah Solid)
    if not df_hist.empty:
        # Hanya tampilkan history 24 jam terakhir biar gak berat grafiknya
        hist_view = df_hist[df_hist['waktu'] >= (sekarang - timedelta(hours=24))]
        fig.add_trace(go.Scatter(x=hist_view['waktu'], y=hist_view['nilai'],
                                 mode='lines+markers', line=dict(color='red', width=2),
                                 marker=dict(size=5), name='Data Aktual (AWS)'))

    # C. Titik Diamond Sekarang
    fig.add_trace(go.Scatter(x=[sekarang], y=[val_akhir], mode='markers+text',
                             marker=dict(color='red', size=12, symbol='diamond', line=dict(width=2, color='white')),
                             text=[f"<b>SEKARANG: {val_akhir}m</b>"], textposition="top center",
                             name='Posisi Saat Ini'))

    fig.add_hline(y=BATAS_ROB, line_dash="dash", line_color="orange", annotation_text="WASPADA ROB")
    fig.update_layout(height=550, template="plotly_white", hovermode="x unified", xaxis_title="Waktu (WIB)")
    st.plotly_chart(fig, use_container_width=True)

    st.success(f"✅ Data diperbarui otomatis tiap 15 menit. Terakhir update: {sekarang.strftime('%H:%M:%S')}")
    st.info(f"📂 Jejak AWS tersimpan permanen di: `{FILE_HISTORY}`")
