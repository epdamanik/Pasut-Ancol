import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pytz  
from streamlit_autorefresh import st_autorefresh
import os
import time
import re
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# --- 0. SMART AUTO REFRESH (Setiap 15 Menit) ---
now_sync = datetime.now()
seconds_to_next = ((15 - (now_sync.minute % 15)) * 60) - now_sync.second
st_autorefresh(interval=seconds_to_next * 1000, key="datarefresh")

# --- 1. KONFIGURASI HALAMAN & CSS ---
st.set_page_config(page_title="Monitoring Pasut Tg. Priok", layout="wide", page_icon="🌊")

st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    
    /* Perbaikan visual Metric */
    [data-testid="stMetricLabel"] { opacity: 1 !important; color: #1e3a8a !important; font-weight: 700 !important; height: 2.5rem !important; overflow: hidden !important; }
    [data-testid="stMetricValue"] { font-size: 24px !important; font-weight: 850 !important; color: #0f172a !important; }
    
    div[data-testid="stMetric"] {
        background-color: #f8fafc !important; border: 1px solid #e2e8f0 !important;
        border-left: 5px solid #1e40af !important; padding: 15px !important; border-radius: 10px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important;
        min-height: 140px !important; max-height: 140px !important;
        display: flex !important; flex-direction: column !important; justify-content: center !important;
    }

    /* Logo Center Fix */
    .logo-container {
        display: flex;
        justify-content: center;
        align-items: center;
        width: 100%;
        margin-bottom: 10px;
    }

    /* Summary Box tebal di Desktop & HP */
    .summary-box {
        background-color: #f1f5f9 !important; 
        padding: 12px !important; 
        border-radius: 10px !important; 
        margin-bottom: 15px !important; 
        border-left: 5px solid #1e3a8a !important;
        color: #0f172a !important;
        opacity: 1 !important;
    }
    .summary-text {
        font-weight: 800 !important;
        font-size: 0.9rem !important;
        line-height: 1.4 !important;
        color: #0f172a !important;
        display: block !important;
    }

    @media (max-width: 768px) {
        div[data-testid="stMetric"] { min-height: 110px !important; max-height: 110px !important; margin-bottom: 10px !important; }
        [data-testid="stMetricValue"] { font-size: 20px !important; }
        [data-testid="stMetricLabel"] { height: 2rem !important; font-size: 0.85rem !important; }
        .summary-text { font-size: 0.8rem !important; }
    }
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIC WAKTU (FORCE ASIA/JAKARTA) ---
tz_jkt = pytz.timezone('Asia/Jakarta')
sekarang = datetime.now(tz_jkt).replace(tzinfo=None)

# --- 3. SIDEBAR ---
with st.sidebar:
    st.subheader("🗓️ Filter Grafik")
    tgl_range = st.date_input("Rentang Waktu", value=(sekarang.date() - timedelta(days=1), sekarang.date() + timedelta(days=2)))

# --- 4. HEADER (Logo & Judul) ---
# FIX LOGO CENTER: Kita tidak pakai st.columns lagi untuk logo
NAMA_FILE_LOGO = "logo-bmkg-transparan.png" 
if os.path.exists(NAMA_FILE_LOGO):
    st.markdown(f"""
        <div class="logo-container">
            <img src="data:image/png;base64,{st.image(NAMA_FILE_LOGO, width=80)}" style="display:none;">
        </div>
        """, unsafe_allow_html=True)
    # Cara Streamlit yang paling stabil buat centering image:
    col_l, col_m, col_r = st.columns([2, 1, 2])
    with col_m:
        st.image(NAMA_FILE_LOGO, width=80)

st.markdown(f"""
    <div style="text-align: center; margin-top: -10px;">
        <h2 style="margin-bottom: 0px; color: #0f172a; font-weight: bold; font-size: 1.5rem;">STASIUN METEOROLOGI MARITIM TANJUNG PRIOK</h2>
        <p style="color: #1e40af; font-weight: 700; margin-top: 0px;">Monitoring Water Level Real-Time</p>
    </div>
    """, unsafe_allow_html=True)
st.divider()

# --- 5. DATA FUNCTIONS ---
FILE_PREDIKSI = 'prediksi_pasut_ancol_2026_FINAL_WIB.xlsx'
FILE_HISTORY_AWS = 'history_aws_priok.csv' 
FILE_HISTORY_BPBD = 'history_bpbd_pasarikan.csv'
BATAS_ROB_AWAS = 2.5
BATAS_ROB_WASPADA = 2.3
LIMIT_SENSOR_ERROR = 3.5 

def save_to_csv(filename, waktu, nilai):
    if nilai is None or nilai > LIMIT_SENSOR_ERROR: return
    waktu_str = waktu.strftime('%Y-%m-%d %H:%M')
    new_data = pd.DataFrame({'waktu': [waktu_str], 'nilai': [nilai]})
    if not os.path.exists(filename):
        new_data.to_csv(filename, index=False)
    else:
        try:
            old_data = pd.read_csv(filename)
            combined = pd.concat([old_data, new_data]).drop_duplicates(subset=['waktu'], keep='last')
            combined.to_csv(filename, index=False)
        except: pass

@st.cache_data(ttl=800)
def fetch_all_realtime():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36")
    driver = None
    res = {"aws": None, "bpbd": None}
    try:
        if os.name == 'nt':
            from webdriver_manager.chrome import ChromeDriverManager
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        else:
            options.binary_location = "/usr/bin/chromium"
            driver = webdriver.Chrome(service=Service("/usr/bin/chromedriver"), options=options)
        
        try:
            driver.get("http://202.90.199.132/aws-new/monitoring/3000000009")
            el = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "waterlevel")))
            val = float(re.search(r"(\d+[\.,]?\d*)", el.text).group(1).replace(',', '.'))
            if val < LIMIT_SENSOR_ERROR: res["aws"] = val
        except: pass

        try:
            driver.get("https://bpbd.jakarta.go.id/waterlevel")
            time.sleep(10)
            rows = driver.find_elements(By.TAG_NAME, "tr")
            for r in rows:
                if "Pasar Ikan" in r.text:
                    txt = r.text.lower()
                    match = re.search(r"(\d+[\.,]?\d*)\s*(?:cm|m)", txt)
                    if match:
                        val = float(match.group(1).replace(',', '.'))
                        if "cm" in txt: val /= 100
                        if val < LIMIT_SENSOR_ERROR: res["bpbd"] = val
                    break
        except: pass
        driver.quit()
    except:
        if driver: driver.quit()
    return res

@st.cache_data(ttl=3600)
def load_prediction():
    if not os.path.exists(FILE_PREDIKSI): return None, None, None
    df = pd.read_excel(FILE_PREDIKSI, engine='openpyxl')
    t_col = next((c for c in ['tanggal_prediksi', 'jam_group', 'Waktu_WIB', 'Waktu'] if c in df.columns), None)
    v_col = next((c for c in ['wl_prediksi', 'wl_final', 'Tinggi_Navigasi_m'] if c in df.columns), None)
    if t_col: df[t_col] = pd.to_datetime(df[t_col])
    return df.sort_values(t_col), t_col, v_col

# --- 6. EXECUTION ---
df_pred, col_tgl, col_val = load_prediction()
live_data = fetch_all_realtime()

save_to_csv(FILE_HISTORY_AWS, sekarang, live_data["aws"])
save_to_csv(FILE_HISTORY_BPBD, sekarang, live_data["bpbd"])

# --- 7. DISPLAY ---
if df_pred is not None:
    # Summary Box (Mobile Optimized & Centered Text)
    df_hari_ini = df_pred[df_pred[col_tgl].dt.date == sekarang.date()]
    if not df_hari_ini.empty:
        idx_max, idx_min = df_hari_ini[col_val].idxmax(), df_hari_ini[col_val].idxmin()
        st.markdown(f"""
        <div class="summary-box">
            <span class="summary-text" style="text-align: center;">
                📅 {sekarang.strftime('%d %b %Y')} | 
                <span style="color: #ef4444;">▲ MAX: {df_hari_ini.loc[idx_max, col_val]:.2f}m ({df_hari_ini.loc[idx_max, col_tgl].strftime('%H:%M')})</span> | 
                <span style="color: #3b82f6;">▼ MIN: {df_hari_ini.loc[idx_min, col_val]:.2f}m ({df_hari_ini.loc[idx_min, col_tgl].strftime('%H:%M')})</span>
            </span>
        </div>
        """, unsafe_allow_html=True)

    idx_now = (df_pred[col_tgl] - sekarang).abs().idxmin()
    h_pred = df_pred.loc[idx_now, col_val]
    idx_nanti = (df_pred[col_tgl] - (sekarang + timedelta(hours=3))).abs().idxmin()
    selisih_tren = df_pred.loc[idx_nanti, col_val] - h_pred

    # Metrics Grid
    m_col = st.columns(4)
    m_col[0].metric("Prediksi Pasut", f"{h_pred:.2f} m")
    m_col[1].metric("AWS Tg. Priok", f"{live_data['aws']:.2f} m" if live_data["aws"] else "N/A", 
                    delta=f"{live_data['aws'] - h_pred:+.2f} m" if live_data["aws"] else None, delta_color="inverse")
    m_col[2].metric("BPBD Psr. Ikan", f"{live_data['bpbd']:.2f} m" if live_data["bpbd"] else "N/A", 
                    delta=f"{live_data['bpbd'] - h_pred:+.2f} m" if live_data["bpbd"] else None, delta_color="inverse")
    m_col[3].metric("Tren 3 Jam", "📈 PASANG" if selisih_tren > 0.05 else "📉 SURUT" if selisih_tren < -0.05 else "➡️ STAGNAN")

    # Chart Section
    t_start, t_end = datetime.combine(tgl_range[0], datetime.min.time()), datetime.combine(tgl_range[1], datetime.max.time())
    fig = go.Figure()
    
    # Trace 1: Prediksi
    df_p = df_pred[(df_pred[col_tgl] >= t_start) & (df_pred[col_tgl] <= t_end)]
    fig.add_trace(go.Scatter(x=df_p[col_tgl], y=df_p[col_val], name='Prediksi', line=dict(color='rgba(15, 23, 42, 0.2)', width=2)))
    
    # Trace 2: History AWS
    if os.path.exists(FILE_HISTORY_AWS):
        df_h = pd.read_csv(FILE_HISTORY_AWS)
        df_h['waktu'] = pd.to_datetime(df_h['waktu'])
        df_h = df_h[(df_h['waktu'] >= t_start) & (df_h['waktu'] <= t_end) & (df_h['nilai'] <= LIMIT_SENSOR_ERROR)]
        fig.add_trace(go.Scatter(x=df_h['waktu'], y=df_h['nilai'], name='AWS Priok', line=dict(color='#1e40af', width=3)))

    # Trace 3: History Pasar Ikan (BPBD)
    if os.path.exists(FILE_HISTORY_BPBD):
        df_hb = pd.read_csv(FILE_HISTORY_BPBD)
        df_hb['waktu'] = pd.to_datetime(df_hb['waktu'])
        df_hb = df_hb[(df_hb['waktu'] >= t_start) & (df_hb['waktu'] <= t_end) & (df_hb['nilai'] <= LIMIT_SENSOR_ERROR)]
        fig.add_trace(go.Scatter(x=df_hb['waktu'], y=df_hb['nilai'], name='Psr Ikan', line=dict(color='#15803d', width=3)))

    # --- SINKRONISASI GARIS WAKTU SEKARANG ---
    fig.add_shape(
        type="line", x0=sekarang, x1=sekarang, y0=0, y1=1,
        yref="paper", line=dict(color="#10b981", width=2, dash="dot")
    )
    fig.add_annotation(
        x=sekarang, y=1, yref="paper",
        text=f"WAKTU SEKARANG ({sekarang.strftime('%H:%M')})",
        showarrow=False, font=dict(size=10, color="#10b981"),
        bgcolor="white", yanchor="bottom"
    )

    # --- ROB LINES ---
    fig.add_hline(y=BATAS_ROB_AWAS, line_dash="dash", line_color="#ef4444", annotation_text="🔴 AWAS ROB")
    fig.add_hline(y=BATAS_ROB_WASPADA, line_dash="dash", line_color="#f59e0b", annotation_text="🟠 WASPADA ROB")
    
    # --- SPIKELINES & HOVER ---
    fig.update_xaxes(showspikes=True, spikemode="across", spikethickness=1, spikedash="dash", spikecolor="#64748b")
    fig.update_yaxes(showspikes=True, spikemode="across", spikethickness=1, spikedash="dash", spikecolor="#64748b")

    fig.update_layout(
        height=450, 
        template="plotly_white", 
        yaxis_range=[1.3, 3.0], 
        margin=dict(l=10, r=10, t=30, b=10),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # --- 8. FOOTER & DOWNLOAD ---
    st.divider()
    st.caption(f"Update Terakhir: {sekarang.strftime('%H:%M:%S')} WIB")
    f_col = st.columns(3)
    with f_col[0]: 
        if os.path.exists(FILE_HISTORY_AWS): st.download_button("📥 Data AWS", open(FILE_HISTORY_AWS, "rb"), "aws_priok.csv", use_container_width=True)
    with f_col[1]: 
        if os.path.exists(FILE_HISTORY_BPBD): st.download_button("📥 Data BPBD", open(FILE_HISTORY_BPBD, "rb"), "bpbd_pasarikan.csv", use_container_width=True)
    with f_col[2]: 
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    st.markdown('<div style="text-align: center; color: #64748b; font-size: 10px; font-weight: bold; margin-top: 10px;">© 2026 BMKG Maritim Tanjung Priok</div>', unsafe_allow_html=True)
