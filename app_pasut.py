import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
import os
import time

# --- 0. SMART AUTO REFRESH (Sinkron per 15 Menit) ---
now_sync = datetime.now()
seconds_to_next = ((15 - (now_sync.minute % 15)) * 60) - now_sync.second
st_autorefresh(interval=seconds_to_next * 1000, key="datarefresh")

# --- 1. KONFIGURASI HALAMAN & CSS ---
st.set_page_config(page_title="Monitoring Pasut Tg. Priok", layout="wide", page_icon="🌊")

st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    
    /* Fix Opacity & Warna Label */
    [data-testid="stMetricLabel"] {
        opacity: 1 !important;
        color: #000000 !important;
        font-weight: 700 !important;
    }

    [data-testid="stMetricValue"] {
        font-size: 26px;
        font-weight: 800;
        color: #000000 !important;
    }

    /* Fix Simetris Kotak */
    [data-testid="stMetric"] {
        background-color: #ffffff;
        padding: 15px;
        border-radius: 12px;
        border: 2px solid #e0e0e0;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
        min-height: 140px;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }

    @media (max-width: 640px) {
        [data-testid="stMetricValue"] { font-size: 22px !important; }
        [data-testid="stMetric"] { min-height: 120px; }
    }

    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. SIDEBAR ---
with st.sidebar:
    st.subheader("🗓️ Filter Waktu")
    sekarang = datetime.now()
    if os.name != 'nt': sekarang = sekarang + timedelta(hours=7)

    tgl_range = st.date_input(
        "Rentang Grafik", 
        value=(sekarang.date() - timedelta(days=1), sekarang.date() + timedelta(days=2))
    )
    st.divider()
    st.info("💡 Data dicatat otomatis setiap 15 menit ke dalam file history.")

# --- 3. HEADER UTAMA ---
h1, h2, h3, h4, h5 = st.columns([2, 1, 0.7, 1, 2])
NAMA_FILE_LOGO = "logo-bmkg-transparan.png" 

with h3:
    if os.path.exists(NAMA_FILE_LOGO):
        st.image(NAMA_FILE_LOGO, use_container_width=True)

st.markdown(f"""
    <div style="text-align: center; margin-top: -15px;">
        <h2 style="margin-bottom: 0px; font-size: 1.8rem; color: #000000; font-weight: bold;">STASIUN METEOROLOGI MARITIM TANJUNG PRIOK</h2>
        <p style="color: #004085; font-weight: 700; font-size: 1rem; margin-top: 0px;">
            Monitoring Water Level AWS Maritim Tanjung Priok
        </p>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# --- 4. DATA LOGIC ---
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

FILE_PREDIKSI = 'prediksi_pasut_ancol_2026_FINAL_WIB.xlsx'
FILE_HISTORY = 'history_aws_priok.csv' 
BATAS_ROB_AWAS = 2.5
BATAS_ROB_WASPADA = 2.3

def save_to_csv(waktu, nilai):
    waktu_str = waktu.strftime('%Y-%m-%d %H:%M')
    new_data = pd.DataFrame({'waktu': [waktu_str], 'nilai': [nilai]})
    if not os.path.exists(FILE_HISTORY):
        new_data.to_csv(FILE_HISTORY, index=False)
    else:
        try:
            old_data = pd.read_csv(FILE_HISTORY)
            combined = pd.concat([old_data, new_data]).drop_duplicates(subset=['waktu'], keep='last')
            combined.to_csv(FILE_HISTORY, index=False)
        except: pass

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
        wait = WebDriverWait(driver, 20)
        element = wait.until(EC.visibility_of_element_located((By.ID, "waterlevel")))
        time.sleep(2) 
        val = float(element.text.replace('m', '').replace(',', '.').strip())
        driver.quit()
        return val, datetime.now()
    except:
        if driver: driver.quit()
        return None, None

@st.cache_data(ttl=3600)
def load_prediction():
    if not os.path.exists(FILE_PREDIKSI): return None, None, None
    try:
        df = pd.read_excel(FILE_PREDIKSI, engine='openpyxl')
        tgl_col = next((c for c in ['tanggal_prediksi', 'jam_group', 'Waktu_WIB', 'Waktu'] if c in df.columns), None)
        val_col = next((c for c in ['wl_prediksi', 'wl_final', 'Tinggi_Navigasi_m'] if c in df.columns), None)
        if tgl_col: df[tgl_col] = pd.to_datetime(df[tgl_col])
        return df.sort_values(tgl_col), tgl_col, val_col
    except: return None, None, None

df_pred, col_tgl, col_val = load_prediction()
aws_val, aws_time = fetch_aws_realtime()

if aws_val is not None:
    waktu_catat = aws_time
    if os.name != 'nt': waktu_catat += timedelta(hours=7)
    save_to_csv(waktu_catat, aws_val)

# --- 5. METRICS & GRAFIK ---
if df_pred is not None:
    # Ringkasan Harian HTML Box
    df_hari_ini = df_pred[df_pred[col_tgl].dt.date == sekarang.date()]
    if not df_hari_ini.empty:
        idx_max = df_hari_ini[col_val].idxmax()
        v_max = f"{df_hari_ini.loc[idx_max, col_val]:.2f}"
        w_max = df_hari_ini.loc[idx_max, col_tgl].strftime('%H:%M')
        idx_min = df_hari_ini[col_val].idxmin()
        v_min = f"{df_hari_ini.loc[idx_min, col_val]:.2f}"
        w_min = df_hari_ini.loc[idx_min, col_tgl].strftime('%H:%M')
        
        st.markdown(f"""
        <div style="background-color: #f8f9fa; padding: 15px; border-radius: 12px; margin-bottom: 20px; border: 1px solid #e9ecef; color: #000;">
            <div style="font-weight: 700; color: #004085; border-bottom: 1px solid #dee2e6; padding-bottom: 8px; margin-bottom: 10px;">📝 Ringkasan Kondisi ({sekarang.strftime('%d %b %Y')})</div>
            🚀 <b>Pasang Tertinggi:</b> <span style="color: #c00000;">{w_max} WIB ({v_max} m)</span> | 📉 <b>Surut Terendah:</b> <span style="color: #007000;">{w_min} WIB ({v_min} m)</span>
        </div>
        """, unsafe_allow_html=True)

    # Metrics Logic
    idx_now = (df_pred[col_tgl] - sekarang).abs().idxmin()
    h_pred = df_pred.loc[idx_now, col_val]
    idx_nanti = (df_pred[col_tgl] - (sekarang + timedelta(hours=3))).abs().idxmin()
    h_nanti = df_pred.loc[idx_nanti, col_val]
    selisih_tren = h_nanti - h_pred

    df_hist = pd.read_csv(FILE_HISTORY) if os.path.exists(FILE_HISTORY) else pd.DataFrame()
    if not df_hist.empty: df_hist['waktu'] = pd.to_datetime(df_hist['waktu'])

    val_tampil = aws_val if aws_val else (df_hist['nilai'].iloc[-1] if not df_hist.empty else h_pred)
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Aktual (AWS)", f"{val_tampil:.2f} m", delta=f"{val_tampil - h_pred:.2f} m" if aws_val else None, delta_color="inverse")
    m2.metric("Tren 3 Jam", "📈 PASANG" if selisih_tren > 0.05 else "📉 SURUT" if selisih_tren < -0.05 else "➡️ STAGNAN")
    m3.metric("Prediksi", f"{h_pred:.2f} m")
    m4.metric("Batas AWAS ROB", f"{BATAS_ROB_AWAS} m")

    # Grafik Plotly
    t_start_view = datetime.combine(tgl_range[0], datetime.min.time())
    t_end_view = datetime.combine(tgl_range[1], datetime.max.time())
    fig = go.Figure()
    df_plot = df_pred[(df_pred[col_tgl] >= t_start_view) & (df_pred[col_tgl] <= t_end_view)]
    fig.add_trace(go.Scatter(x=df_plot[col_tgl], y=df_plot[col_val], mode='lines', line=dict(color='rgba(0, 102, 204, 0.4)', width=2), name='Prediksi'))
    if not df_hist.empty:
        hist_view = df_hist[(df_hist['waktu'] >= t_start_view) & (df_hist['waktu'] <= t_end_view)]
        fig.add_trace(go.Scatter(x=hist_view['waktu'], y=hist_view['nilai'], mode='lines', line=dict(color='#cc0000', width=3), name='Aktual'))

    fig.add_hline(y=BATAS_ROB_AWAS, line_dash="dash", line_color="#ff0000", annotation_text="🔴 AWAS ROB")
    fig.add_hline(y=BATAS_ROB_WASPADA, line_dash="dash", line_color="#ffa500", annotation_text="🟠 WASPADA ROB")
    fig.add_vline(x=sekarang, line_dash="dot", line_width=2, line_color="#008000")
    fig.add_annotation(x=sekarang, y=1.05, yref="paper", text=f"Waktu Sekarang: {sekarang.strftime('%H:%M')}", showarrow=False, font=dict(color="#008000"), xanchor="left")
    
    fig.update_layout(height=500, template="plotly_white", margin=dict(l=10, r=10, t=50, b=10), hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

    # --- 6. FOOTER & DOWNLOAD AREA ---
    st.divider()
    col_f1, col_f2, col_f3 = st.columns([2, 1, 1])
    
    with col_f1:
        st.success(f"✅ SISTEM AKTIF | Update: {sekarang.strftime('%H:%M:%S')} WIB")
    
    with col_f2:
        # FITUR DOWNLOAD DATA HISTORY
        if os.path.exists(FILE_HISTORY):
            with open(FILE_HISTORY, "rb") as file:
                st.download_button(
                    label="📥 Download Data History",
                    data=file,
                    file_name=f"history_aws_priok_{sekarang.strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    help="Klik untuk mendownload semua data rekaman AWS yang tersimpan"
                )
    
    with col_f3:
        if st.button("🔄 Force Refresh", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    st.markdown(f'<div style="text-align: center; color: #333; font-size: 11px; font-weight: bold; margin-top: 20px;">© 2026 BMKG Maritim Tanjung Priok</div>', unsafe_allow_html=True)
else:
    st.error("❌ File Prediksi Excel tidak ditemukan!")
