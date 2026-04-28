import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
import os
import time

# --- 0. SMART AUTO REFRESH (Silent Sync) ---
now_sync = datetime.now()
seconds_to_next = ((15 - (now_sync.minute % 15)) * 60) - now_sync.second
st_autorefresh(interval=seconds_to_next * 1000, key="datarefresh")

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Monitoring Pasut Tg. Priok", layout="wide", page_icon="🌊")

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; }
    [data-testid="stMetricValue"] { font-size: 24px; font-weight: bold; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 12px; border: 1px solid #eee; }
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. PENGATURAN FILE ---
FILE_PREDIKSI = 'prediksi_pasut_ancol_2026_FINAL_WIB.xlsx'
FILE_HISTORY = 'history_aws_priok.csv' 
BATAS_ROB = 2.5

def save_to_csv(waktu, nilai):
    discard = timedelta(minutes=waktu.minute % 15, seconds=waktu.second, microseconds=waktu.microsecond)
    waktu_bulat = waktu - discard
    if discard >= timedelta(minutes=7, seconds=30):
        waktu_bulat += timedelta(minutes=15)
    
    waktu_str = waktu_bulat.strftime('%Y-%m-%d %H:%M')
    new_data = pd.DataFrame({'waktu': [waktu_str], 'nilai': [nilai]})
    
    if not os.path.exists(FILE_HISTORY):
        new_data.to_csv(FILE_HISTORY, index=False)
    else:
        try:
            old_data = pd.read_csv(FILE_HISTORY)
            combined = pd.concat([old_data, new_data]).drop_duplicates(subset=['waktu'], keep='last')
            combined.to_csv(FILE_HISTORY, index=False)
        except: pass

# --- 3. FUNGSI SCRAPING ---
@st.cache_data(ttl=800)
def fetch_aws_realtime():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = None
    try:
        if os.name == 'nt':
            from webdriver_manager.chrome import ChromeDriverManager
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
        else:
            options.binary_location = "/usr/bin/chromium"
            service = Service("/usr/bin/chromedriver")
            driver = webdriver.Chrome(service=service, options=options)
        
        driver.get("http://202.90.199.132/aws-new/monitoring/3000000009")
        wait = WebDriverWait(driver, 30)
        element = wait.until(EC.visibility_of_element_located((By.ID, "waterlevel")))
        time.sleep(5)
        val = float(element.text.replace('m', '').replace(',', '.').strip())
        driver.quit()
        return val, datetime.now()
    except:
        if driver: driver.quit()
        return None, None

# --- 4. LOAD DATA ---
@st.cache_data(ttl=3600)
def load_prediction():
    if not os.path.exists(FILE_PREDIKSI): return None, None, None
    df = pd.read_excel(FILE_PREDIKSI, engine='openpyxl')
    cols = df.columns
    tgl_col = next((c for c in ['tanggal_prediksi', 'jam_group', 'Waktu_WIB', 'Waktu'] if c in cols), None)
    val_col = next((c for c in ['wl_prediksi', 'wl_final', 'Tinggi_Navigasi_m'] if c in cols), None)
    if tgl_col: df[tgl_col] = pd.to_datetime(df[tgl_col])
    return df.sort_values(tgl_col), tgl_col, val_col

df_pred, col_tgl, col_val = load_prediction()
aws_val, aws_time = fetch_aws_realtime()

if aws_val is not None:
    waktu_catat = aws_time
    if os.name != 'nt': waktu_catat += timedelta(hours=7)
    save_to_csv(waktu_catat, aws_val)

# --- 5. SIDEBAR ---
st.sidebar.header("⚙️ Kontrol Panel")
sekarang = datetime.now()
if os.name != 'nt': sekarang = sekarang + timedelta(hours=7)

tgl_range = st.sidebar.date_input("Rentang Pantauan", value=(sekarang.date() - timedelta(days=1), sekarang.date() + timedelta(days=2)))

# --- 6. DISPLAY DASHBOARD ---
st.title("⚓ Monitoring Pasut AWS Tg. Priok")

if df_pred is not None:
    # Ambil Prediksi Sekarang
    idx_now = (df_pred[col_tgl] - sekarang).abs().idxmin()
    h_pred = df_pred.loc[idx_now, col_val]
    
    # Tren 3 Jam
    idx_nanti = (df_pred[col_tgl] - (sekarang + timedelta(hours=3))).abs().idxmin()
    h_nanti = df_pred.loc[idx_nanti, col_val]
    selisih_tren = h_nanti - h_pred

    df_hist = pd.read_csv(FILE_HISTORY) if os.path.exists(FILE_HISTORY) else pd.DataFrame()
    if not df_hist.empty: df_hist['waktu'] = pd.to_datetime(df_hist['waktu'])

    val_tampil = aws_val if aws_val else (df_hist['nilai'].iloc[-1] if not df_hist.empty else h_pred)
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Tinggi Air Aktual", f"{val_tampil:.2f} m", delta=f"{val_tampil - h_pred:.2f} m" if aws_val else None, delta_color="inverse")
    m2.metric("Tren 3 Jam", "📈 PASANG" if selisih_tren > 0.05 else "📉 SURUT" if selisih_tren < -0.05 else "➡️ STAGNAN")
    m3.metric("Prediksi", f"{h_pred:.2f} m")
    m4.metric("Batas ROB", f"{BATAS_ROB} m")

    # --- 7. GRAFIK (DENGAN DOUBLE MARKER) ---
    t_start_view = datetime.combine(tgl_range[0], datetime.min.time()) if len(tgl_range)==2 else sekarang - timedelta(hours=24)
    t_end_view = datetime.combine(tgl_range[1], datetime.max.time()) if len(tgl_range)==2 else sekarang + timedelta(hours=24)

    fig = go.Figure()
    
    # Garis Prediksi
    df_plot = df_pred[(df_pred[col_tgl] >= t_start_view) & (df_pred[col_tgl] <= t_end_view)]
    fig.add_trace(go.Scatter(
        x=df_plot[col_tgl], y=df_plot[col_val], 
        mode='lines', line=dict(color='rgba(0, 123, 255, 0.4)', width=2),
        name='Garis Prediksi',
        hoverinfo='skip'
    ))

    # Garis Aktual
    if not df_hist.empty:
        hist_view = df_hist[(df_hist['waktu'] >= t_start_view) & (df_hist['waktu'] <= t_end_view)]
        fig.add_trace(go.Scatter(
            x=hist_view['waktu'], y=hist_view['nilai'], 
            mode='lines', line=dict(color='red', width=2.5),
            name='Garis Aktual (AWS)',
            hoverinfo='skip'
        ))

    # --- TITIK LIVE 1: PREDIKSI (Lingkaran Biru) ---
    if t_start_view <= sekarang <= t_end_view:
        fig.add_trace(go.Scatter(
            x=[sekarang], y=[h_pred], 
            mode='markers+text',
            marker=dict(color='rgba(0, 123, 255, 0.8)', size=14, symbol='circle', line=dict(width=2, color='white')),
            text=[f"<b>PREDIKSI: {h_pred:.2f}m</b>"], textposition="bottom center", 
            name='Titik Prediksi'
        ))

    # --- TITIK LIVE 2: AKTUAL (Diamond Merah) ---
    if t_start_view <= sekarang <= t_end_view:
        fig.add_trace(go.Scatter(
            x=[sekarang], y=[val_tampil], 
            mode='markers+text',
            marker=dict(color='red', size=16, symbol='diamond', line=dict(width=2, color='white')),
            text=[f"<b>AKTUAL: {val_tampil:.2f}m</b>"], textposition="top center", 
            name='Titik Aktual'
        ))

    fig.add_hline(y=BATAS_ROB, line_dash="dash", line_color="orange", annotation_text="WASPADA ROB")
    
    fig.update_layout(
        height=650, 
        template="plotly_white", 
        margin=dict(l=20, r=20, t=50, b=20),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(showspikes=True, spikemode="across", spikesnap="cursor", showline=True, spikedash="dot"),
        yaxis=dict(showspikes=True, spikemode="across", spikesnap="cursor", spikedash="dot")
    )
    
    st.plotly_chart(fig, use_container_width=True)

    # --- 8. FOOTER ---
    st.divider()
    c1, c2, c3 = st.columns([2, 1, 1])
    with c1: 
        st.success(f"✅ Sistem Berjalan Normal | Update Terakhir: {sekarang.strftime('%H:%M:%S')} WIB")
    with c2:
        if os.path.exists(FILE_HISTORY):
            with open(FILE_HISTORY, "rb") as f: st.download_button("📥 Export CSV", f, "history_priok.csv", "text/csv")
    with c3:
        if st.button("🔄 Refresh Data"): st.cache_data.clear(); st.rerun()
else:
    st.error("❌ File Prediksi tidak ditemukan!")
