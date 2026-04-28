import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
import os
import time

# --- IMPORT SELENIUM & TOOLS ---
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- 0. AUTO REFRESH (Update tiap 15 Menit) ---
st_autorefresh(interval=15 * 60 * 1000, key="datarefresh")

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Pasut Tg. Priok Real-time", layout="wide", page_icon="🌊")

# CSS Custom
st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    [data-testid="stMetricValue"] { font-size: 32px; font-weight: bold; }
    .stMetric { 
        background-color: #ffffff; 
        padding: 20px; 
        border-radius: 15px; 
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. PENGATURAN FILE ---
FILE_PREDIKSI = 'prediksi_pasut_ancol_2026_FINAL_WIB.xlsx'
# Ganti nama file history agar data Tg. Priok tidak campur dengan data Kep. Seribu
FILE_HISTORY = 'history_aws_priok.csv' 
BATAS_ROB = 2.5

def save_to_csv(waktu, nilai):
    new_data = pd.DataFrame({'waktu': [waktu], 'nilai': [nilai]})
    if not os.path.exists(FILE_HISTORY):
        new_data.to_csv(FILE_HISTORY, index=False)
    else:
        try:
            old_data = pd.read_csv(FILE_HISTORY)
            combined = pd.concat([old_data, new_data]).drop_duplicates(subset=['waktu'])
            combined.to_csv(FILE_HISTORY, index=False)
        except:
            new_data.to_csv(FILE_HISTORY, index=False)

# --- 3. FUNGSI SCRAPING (Target: Tg. Priok) ---
@st.cache_data(ttl=850)
def fetch_aws_realtime():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    
    driver = None
    try:
        if os.name == 'nt':  # Windows
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
        else:  # Linux (Streamlit Cloud)
            options.binary_location = "/usr/bin/chromium"
            service = Service("/usr/bin/chromedriver")
            driver = webdriver.Chrome(service=service, options=options)
        
        # URL UPDATE KE TANJUNG PRIOK
        driver.get("http://202.90.199.132/aws-new/monitoring/3000000009")
        
        wait = WebDriverWait(driver, 25)
        # Tetap gunakan ID 'waterlevel' karena ini standar di dashboard AWS BMKG
        element = wait.until(EC.visibility_of_element_located((By.ID, "waterlevel")))
        
        time.sleep(3) 
        val_text = element.text.strip()
        
        val_clean = val_text.replace('m', '').replace(',', '.').strip()
        val = float(val_clean)
        
        driver.quit()
        return val, datetime.now()
    except Exception as e:
        if driver: driver.quit()
        return None, None

# --- 4. LOAD DATA PREDIKSI ---
@st.cache_data(ttl=3600)
def load_prediction():
    if not os.path.exists(FILE_PREDIKSI):
        return None, None, None
    df = pd.read_excel(FILE_PREDIKSI, engine='openpyxl')
    cols = df.columns
    tgl_col = next((c for c in ['tanggal_prediksi', 'jam_group', 'Waktu_WIB', 'Waktu'] if c in cols), None)
    val_col = next((c for c in ['wl_prediksi', 'wl_final', 'Tinggi_Navigasi_m'] if c in cols), None)
    if tgl_col:
        df[tgl_col] = pd.to_datetime(df[tgl_col])
    return df.sort_values(tgl_col) if tgl_col else None, tgl_col, val_col

# --- EKSEKUSI ---
df_pred, col_tgl, col_val = load_prediction()
aws_val, aws_time = fetch_aws_realtime()

if aws_val is not None:
    save_to_csv(aws_time.strftime('%Y-%m-%d %H:%M'), aws_val)

# --- 5. TAMPILAN DASHBOARD ---
st.title("⚓ Monitoring Pasut AWS Tg. Priok (Real-time)")

if df_pred is not None:
    sekarang = datetime.now()
    if os.name != 'nt':
        sekarang = sekarang + timedelta(hours=7)

    df_hist = pd.read_csv(FILE_HISTORY) if os.path.exists(FILE_HISTORY) else pd.DataFrame()
    if not df_hist.empty:
        df_hist['waktu'] = pd.to_datetime(df_hist['waktu'])

    idx_now = (df_pred[col_tgl] - sekarang).abs().idxmin()
    h_pred = df_pred.loc[idx_now, col_val]
    
    val_tampil = aws_val if aws_val else (df_hist['nilai'].iloc[-1] if not df_hist.empty else h_pred)
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Tinggi Air (AWS)", f"{val_tampil:.2f} m", 
              delta=f"{val_tampil - h_pred:.2f} m" if aws_val else None, delta_color="inverse")
    m2.metric("Status", "PASANG" if val_tampil >= df_pred[col_val].mean() else "SURUT")
    m3.metric("Prediksi Pasut", f"{h_pred:.2f} m")
    m4.metric("Batas ROB", f"{BATAS_ROB} m")

    # --- 6. GRAFIK GABUNGAN ---
    fig = go.Figure()

    t_start = sekarang - timedelta(hours=12)
    t_end = sekarang + timedelta(hours=12)
    df_plot = df_pred[(df_pred[col_tgl] >= t_start) & (df_pred[col_tgl] <= t_end)]
    
    fig.add_trace(go.Scatter(x=df_plot[col_tgl], y=df_plot[col_val], mode='lines+markers',
                             line=dict(color='rgba(0, 123, 255, 0.2)', dash='dot'),
                             marker=dict(size=3, color='#007bff'), name='Prediksi Astronomis'))

    if not df_hist.empty:
        hist_view = df_hist[df_hist['waktu'] >= (sekarang - timedelta(hours=24))]
        fig.add_trace(go.Scatter(x=hist_view['waktu'], y=hist_view['nilai'],
                                 mode='lines+markers', line=dict(color='red', width=2),
                                 marker=dict(size=5, color='red'), name='Data Aktual (AWS Priok)'))

    fig.add_trace(go.Scatter(x=[sekarang], y=[val_tampil], mode='markers+text',
                             marker=dict(color='red', size=15, symbol='diamond', line=dict(width=2, color='white')),
                             text=[f"<b>SAAT INI: {val_tampil}m</b>"], textposition="top center",
                             name='Posisi Sekarang'))

    fig.add_hline(y=BATAS_ROB, line_dash="dash", line_color="orange", annotation_text="WASPADA ROB")
    
    fig.update_layout(height=600, template="plotly_white", hovermode="x unified",
                      legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                      xaxis_title="Waktu (WIB)", yaxis_title="Ketinggian Air (Meter)")
    
    st.plotly_chart(fig, use_container_width=True)

    st.success(f"✅ Lokasi: Tg. Priok. Update tiap 15 Menit. Terakhir: {sekarang.strftime('%H:%M:%S')} WIB")
else:
    st.error("❌ File Prediksi Excel tidak ditemukan!")
