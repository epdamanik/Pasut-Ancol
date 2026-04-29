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

# --- 0. SMART AUTO REFRESH ---
now_sync = datetime.now()
seconds_to_next = ((15 - (now_sync.minute % 15)) * 60) - now_sync.second
st_autorefresh(interval=seconds_to_next * 1000, key="datarefresh")

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Monitoring Pasut Tg. Priok", layout="wide", page_icon="🌊")

st.markdown("""
    <style>
    .stApp { background-color: #ffffff; }
    .header-text { text-align: center; width: 100%; }
    
    [data-testid="stMetricLabel"] { opacity: 1 !important; color: #1e3a8a !important; font-weight: 700 !important; }
    [data-testid="stMetricValue"] { font-size: 24px !important; font-weight: 850 !important; color: #0f172a !important; }
    
    div[data-testid="stMetric"] {
        background-color: #f8fafc !important; border: 1px solid #e2e8f0 !important;
        border-left: 5px solid #1e40af !important; padding: 15px !important; border-radius: 10px !important;
    }

    .summary-box {
        background-color: #f1f5f9 !important; padding: 12px !important; 
        border-radius: 10px !important; margin-bottom: 15px !important; 
        border-left: 5px solid #1e3a8a !important; text-align: center !important;
    }
    .summary-text { font-weight: 850 !important; font-size: 0.95rem !important; color: #0f172a !important; }

    @media (max-width: 768px) {
        div[data-testid="stMetric"] { min-height: 110px !important; margin-bottom: 10px !important; }
    }
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIC WAKTU ---
tz_jkt = pytz.timezone('Asia/Jakarta')
sekarang = datetime.now(tz_jkt).replace(tzinfo=None)

# --- 3. SIDEBAR ---
with st.sidebar:
    st.subheader("🗓️ Filter Grafik")
    tgl_range = st.date_input("Rentang Waktu", value=(sekarang.date() - timedelta(days=1), sekarang.date() + timedelta(days=2)))

# --- 4. HEADER ---
NAMA_FILE_LOGO = "logo-bmkg-transparan.png" 
c1, c2, c3 = st.columns([1, 0.4, 1])
with c2:
    if os.path.exists(NAMA_FILE_LOGO):
        st.image(NAMA_FILE_LOGO, use_container_width=True)

st.markdown(f"""
    <div class="header-text">
        <h2 style="margin: 0; color: #0f172a; font-weight: bold; font-size: 1.5rem;">STASIUN METEOROLOGI MARITIM TANJUNG PRIOK</h2>
        <p style="color: #1e40af; font-weight: 700; margin-top: 5px;">Monitoring Water Level Real-Time</p>
    </div>
    """, unsafe_allow_html=True)
st.divider()

# --- 5. DATA FUNCTIONS ---
FILE_PREDIKSI = 'prediksi_pasut_ancol_2026_FINAL_WIB.xlsx'
FILE_HISTORY_AWS = 'history_aws_priok.csv' 
FILE_HISTORY_BPBD = 'history_bpbd_pasarikan.csv'
LIMIT_SENSOR_ERROR = 3.5  # <--- Balik lagi filternya

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
    driver = None
    res = {"aws": None, "bpbd": None}
    try:
        if os.name == 'nt':
            from webdriver_manager.chrome import ChromeDriverManager
            driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        else:
            options.binary_location = "/usr/bin/chromium"
            driver = webdriver.Chrome(service=Service("/usr/bin/chromedriver"), options=options)
        
        # AWS Priok
        try:
            driver.get("http://202.90.199.132/aws-new/monitoring/3000000009")
            el = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "waterlevel")))
            val = float(re.search(r"(\d+[\.,]?\d*)", el.text).group(1).replace(',', '.'))
            if val <= LIMIT_SENSOR_ERROR: res["aws"] = val
        except: pass
        
        # BPBD Pasar Ikan
        try:
            driver.get("https://bpbd.jakarta.go.id/waterlevel")
            time.sleep(3)
            rows = driver.find_elements(By.TAG_NAME, "tr")
            for r in rows:
                if "Pasar Ikan" in r.text:
                    match = re.search(r"(\d+[\.,]?\d*)\s*(?:cm|m)", r.text.lower())
                    if match:
                        val = float(match.group(1).replace(',', '.'))
                        if "cm" in r.text.lower(): val /= 100
                        if val <= LIMIT_SENSOR_ERROR: res["bpbd"] = val
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
    t_col = next((c for c in ['tanggal_prediksi', 'Waktu_WIB', 'Waktu'] if c in df.columns), None)
    v_col = next((c for c in ['wl_prediksi', 'Tinggi_Navigasi_m'] if c in df.columns), None)
    if t_col: df[t_col] = pd.to_datetime(df[t_col])
    return df.sort_values(t_col), t_col, v_col

# --- 6. EXECUTION ---
df_pred, col_tgl, col_val = load_prediction()
live_data = fetch_all_realtime()
save_to_csv(FILE_HISTORY_AWS, sekarang, live_data["aws"])
save_to_csv(FILE_HISTORY_BPBD, sekarang, live_data["bpbd"])

# --- 7. DISPLAY ---
if df_pred is not None:
    # Summary Box
    df_h = df_pred[df_pred[col_tgl].dt.date == sekarang.date()]
    if not df_h.empty:
        i_max, i_min = df_h[col_val].idxmax(), df_h[col_val].idxmin()
        st.markdown(f'<div class="summary-box"><span class="summary-text">📅 {sekarang.strftime("%d %b %Y")} | <span style="color: #ef4444;">▲ MAX: {df_h.loc[i_max, col_val]:.2f}m</span> | <span style="color: #3b82f6;">▼ MIN: {df_h.loc[i_min, col_val]:.2f}m</span></span></div>', unsafe_allow_html=True)

    # Metrics
    m_col = st.columns(4)
    h_now = df_pred.loc[(df_pred[col_tgl] - sekarang).abs().idxmin(), col_val]
    m_col[0].metric("Prediksi", f"{h_now:.2f} m")
    m_col[1].metric("AWS Priok", f"{live_data['aws']:.2f} m" if live_data["aws"] else "N/A")
    m_col[2].metric("BPBD Psr Ikan", f"{live_data['bpbd']:.2f} m" if live_data["bpbd"] else "N/A")
    m_col[3].metric("Tren", "📈 PASANG" if (df_pred.loc[(df_pred[col_tgl] - (sekarang + timedelta(hours=3))).abs().idxmin(), col_val] - h_now) > 0.05 else "📉 SURUT")

    # Chart
    t_start, t_end = datetime.combine(tgl_range[0], datetime.min.time()), datetime.combine(tgl_range[1], datetime.max.time())
    fig = go.Figure()
    
    df_plot = df_pred[(df_pred[col_tgl] >= t_start) & (df_pred[col_tgl] <= t_end)]
    fig.add_trace(go.Scatter(x=df_plot[col_tgl], y=df_plot[col_val], name='Prediksi', line=dict(color='#64748b', width=2, dash='dot')))
    
    if os.path.exists(FILE_HISTORY_AWS):
        dh_a = pd.read_csv(FILE_HISTORY_AWS); dh_a['waktu'] = pd.to_datetime(dh_a['waktu'])
        dh_a = dh_a[(dh_a['waktu'] >= t_start) & (dh_a['waktu'] <= t_end) & (dh_a['nilai'] <= LIMIT_SENSOR_ERROR)]
        fig.add_trace(go.Scatter(x=dh_a['waktu'], y=dh_a['nilai'], name='AWS Priok', mode='lines+markers', marker=dict(size=6), line=dict(color='#0033cc', width=4)))

    if os.path.exists(FILE_HISTORY_BPBD):
        dh_b = pd.read_csv(FILE_HISTORY_BPBD); dh_b['waktu'] = pd.to_datetime(dh_b['waktu'])
        dh_b = dh_b[(dh_b['waktu'] >= t_start) & (dh_b['waktu'] <= t_end) & (dh_b['nilai'] <= LIMIT_SENSOR_ERROR)]
        fig.add_trace(go.Scatter(x=dh_b['waktu'], y=dh_b['nilai'], name='Psr Ikan', mode='lines+markers', line=dict(color='#f59e0b', width=4)))

    # Garis Sekarang & Rob
    fig.add_shape(type="line", x0=sekarang, x1=sekarang, y0=0, y1=1, yref="paper", line=dict(color="#22c55e", width=3, dash="dash"))
    fig.add_annotation(
        x=sekarang, y=1.05, yref="paper",
        text=f"<b>WAKTU SEKARANG ({sekarang.strftime('%H:%M')})</b>",
        showarrow=False, font=dict(size=12, color="#22c55e"),
        bgcolor="white", bordercolor="#22c55e", borderwidth=1, borderpad=4, yanchor="bottom"
    )
    
    fig.add_hline(y=2.5, line_dash="dash", line_color="#ef4444", annotation_text="<b>AWAS ROB</b>", annotation_position="top left")
    fig.add_hline(y=2.3, line_dash="dash", line_color="#ea580c", annotation_text="<b>WASPADA</b>", annotation_position="bottom left")

    fig.update_layout(
        height=500, template="plotly_white", hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=-0.25, xanchor="left", x=0),
        margin=dict(l=10, r=10, t=60, b=100)
    )
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    # Footer
    st.divider()
    f_col = st.columns(3)
    with f_col[2]: 
        if st.button("🔄 Refresh Data", use_container_width=True): st.cache_data.clear(); st.rerun()
