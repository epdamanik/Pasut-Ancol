import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pytz
from streamlit_autorefresh import st_autorefresh
import os
import base64

# --- 0. SMART AUTO REFRESH (Sync tiap 15 Menit) ---
now_sync = datetime.now()
seconds_to_next = ((15 - (now_sync.minute % 15)) * 60) - now_sync.second
if seconds_to_next <= 0: seconds_to_next = 900
st_autorefresh(interval=seconds_to_next * 1000, key="datarefresh")

# --- 1. KONFIGURASI HALAMAN & CSS ---
st.set_page_config(page_title="Monitoring TMA Priok", layout="wide", page_icon="🌊")

st.markdown("""
    <style>
    /* FIX KALENDER: Mengecilkan ukuran visual kalender agar tidak kepotong */
    div[data-baseweb="datepicker"] {
        transform: scale(0.85);
        transform-origin: top left;
    }

    /* Merapatkan container utama ke atas */
    .block-container { 
        padding-top: 0.5rem !important; 
        padding-bottom: 0rem !important; 
        max-width: 95% !important; 
    }
    
    /* Menghilangkan gap vertikal bawaan streamlit antar elemen */
    [data-testid="stVerticalBlock"] > div {
        gap: 0px !important;
    }

    .stApp { background-color: #ffffff; }
    
    /* Merapatkan Header Utama ke paling atas */
    .header-text { 
        text-align: center; 
        width: 100%; 
        margin-top: -15px; 
        margin-bottom: 0px !important;
        padding-bottom: 0px !important;
    }

    /* FIX LOGO CENTER SIDEBAR */
    [data-testid="stSidebar"] [data-testid="stImage"] {
        text-align: center !important;
        display: block !important;
        margin-left: auto !important;
        margin-right: auto !important;
        width: 100% !important;
    }

    [data-testid="stSidebar"] [data-testid="stImage"] img {
        max-width: 90px !important;
        margin-left: auto !important;
        margin-right: auto !important;
        display: inline-block !important;
    }

    /* GAYA METRIK (ULTRA SLIM) */
    div[data-testid="stMetric"] {
        background-color: #ffffff !important; 
        border: 1px solid #e2e8f0 !important;
        border-left: 4px solid #1e40af !important; 
        padding: 4px 10px !important; 
        border-radius: 8px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
        min-height: 55px !important; 
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
    }
    
    div[data-testid="stMetricLabel"] { 
        color: #1e3a8a !important; 
        font-weight: 700 !important; 
        font-size: 0.7rem !important; 
        margin-bottom: -10px !important; 
        white-space: nowrap !important;
    }

    [data-testid="stMetricValue"] { 
        font-size: 15px !important; 
        font-weight: 800 !important; 
        color: #0f172a !important; 
        white-space: nowrap !important;
    }

    div[data-testid="stMetricDelta"] { display: none !important; }

    div[data-testid="column"] { padding: 0 5px !important; }

    /* Summary Box dirapatkan ke header dengan margin negatif */
    .summary-box {
        background-color: #f1f5f9 !important; 
        padding: 8px !important; 
        border-radius: 10px !important; 
        margin-top: -15px !important; 
        margin-bottom: 10px !important; 
        border-left: 5px solid #1e3a8a !important; 
        text-align: center !important;
    }
    .summary-text { font-weight: 850 !important; font-size: 0.9rem !important; color: #0f172a !important; }

    .footer-card {
        margin-top: 30px; padding: 12px; border-radius: 10px; 
        background-color: #f8fafc; border: 1px solid #e2e8f0; 
        text-align: center;
    }
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIC WAKTU ---
tz_jkt = pytz.timezone('Asia/Jakarta')
sekarang = datetime.now(tz_jkt)
sekarang_naive = sekarang.replace(tzinfo=None)

# --- 3. SIDEBAR ---
NAMA_FILE_LOGO = "logo-bmkg-transparan.png" 

with st.sidebar:
    if os.path.exists(NAMA_FILE_LOGO):
        with open(NAMA_FILE_LOGO, "rb") as f:
            data = f.read()
            encoded = base64.b64encode(data).decode()
        st.markdown(
            f"""
            <div style="display: flex; justify-content: center; align-items: center; width: 100%; margin-top: -15px; margin-bottom: 10px;">
                <img src="data:image/png;base64,{encoded}" style="width: 85px; height: auto;">
            </div>
            """,
            unsafe_allow_html=True
        )
    
    st.markdown("<p style='text-align: center; color: #1e3a8a; margin-top: -5px; font-size: 0.85rem; font-weight: bold;'>STASIUN METEOROLOGI MARITIM TANJUNG PRIOK</p>", unsafe_allow_html=True)
    st.divider()
    
    tgl_range = st.date_input("🗓️ Rentang Waktu Grafik", value=(sekarang.date() - timedelta(days=1), sekarang.date() + timedelta(days=2)))
    st.link_button("🌐 Web BMKG Tanjung Priok", "https://bmkgtanjungpriok.info/", use_container_width=True)
    
    with st.expander("ℹ️ Info Sumber Data"):
        st.markdown("""
        <div style="text-align: justify; font-size: 0.95rem; color: #475569;">
            <strong>📍 Prediksi:</strong><br>
            Analisis Harmonik data TMA Pasar Ikan I (DSDA) Tahun 2025.
        </div>
        <br>
        <div style="text-align: justify; font-size: 0.95rem; color: #475569;">
            <strong>⚡ Real-time:</strong>
            <ul style="margin-top: 5px; padding-left: 20px;">
                <li>AWS Maritim Tanjung Priok (BMKG).</li>
                <li>Pintu Air Pasar Ikan I (DSDA).</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown(f"""
        <div class="footer-card">
            <p style='font-size: 0.72rem; color: #1e3a8a; margin-bottom: 0; font-weight: 600;'>
                © 2026 Stasiun Meteorologi Maritim Tanjung Priok
            </p>
        </div>
        <div style="text-align: center; margin-top: 15px; line-height: 1;">
            <p style='font-size: 0.5rem; color: #94a3b8; margin-bottom: 2px;'>Developed by</p>
            <p style="color: #64748b; font-weight: 500; font-size: 0.5rem; margin: 0;">E.P. Damanik</p>
        </div>
    """, unsafe_allow_html=True)

# --- 4. HEADER UTAMA ---
st.markdown(f"""
    <div class="header-text">
        <h2 style="margin: 0; color: #0f172a; font-weight: bold; font-size: 1.6rem;">
            MONITORING TINGGI MUKA AIR (TMA) REAL TIME
        </h2>
    </div>
    """, unsafe_allow_html=True)

# --- 5. DATA FUNCTIONS ---
FILE_PREDIKSI = 'prediksi_pasut_ancol_2026_FINAL_WIB.xlsx'
FILE_HISTORY_AWS = 'history_aws_priok.csv' 
FILE_HISTORY_BPBD = 'history_bpbd_pasarikan.csv'

def get_latest_from_csv(file_path):
    if not os.path.exists(file_path): return None
    try:
        df = pd.read_csv(file_path)
        df['waktu'] = pd.to_datetime(df['waktu'], format='mixed', errors='coerce')
        return df.dropna(subset=['waktu', 'nilai']).sort_values('waktu').iloc[-1]['nilai']
    except: return None

@st.cache_data(ttl=3600)
def load_prediction():
    if not os.path.exists(FILE_PREDIKSI): return None, None, None
    df = pd.read_excel(FILE_PREDIKSI, engine='openpyxl')
    t_col = next((c for c in ['tanggal_prediksi', 'Waktu_WIB', 'Waktu'] if c in df.columns), None)
    v_col = next((c for c in ['wl_prediksi', 'Tinggi_Navigasi_m'] if c in df.columns), None)
    if t_col: 
        df[t_col] = pd.to_datetime(df[t_col], format='mixed', errors='coerce')
    return df.dropna(subset=[t_col, v_col]).sort_values(t_col), t_col, v_col

# --- 6. EXECUTION ---
df_pred, col_tgl, col_val = load_prediction()
live_data = {"aws": get_latest_from_csv(FILE_HISTORY_AWS), "bpbd": get_latest_from_csv(FILE_HISTORY_BPBD)}

# --- 7. DISPLAY ---
if df_pred is not None and not df_pred.empty:
    h_now = df_pred.loc[(df_pred[col_tgl] - sekarang_naive).abs().idxmin(), col_val]
    
    # --- SUMMARY BOX ---
    df_h = df_pred[df_pred[col_tgl].dt.date == sekarang.date()]
    if not df_h.empty:
        idx_max = df_h[col_val].idxmax()
        idx_min = df_h[col_val].idxmin()
        v_max, t_max = df_h.loc[idx_max, col_val], df_h.loc[idx_max, col_tgl].strftime("%H:%M")
        v_min, t_min = df_h.loc[idx_min, col_val], df_h.loc[idx_min, col_tgl].strftime("%H:%M")

        st.markdown(f"""
            <div class="summary-box">
                <span class="summary-text">
                    📅 {sekarang.strftime("%d %b %Y")} | 
                    <span style="color: #ef4444;">▲ MAX: {v_max:.2f}m ({t_max})</span> | 
                    <span style="color: #3b82f6;">▼ MIN: {v_min:.2f}m ({t_min})</span>
                </span>
            </div>
        """, unsafe_allow_html=True)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Prediksi Pasut", f"{h_now:.2f} m")
    
    # Kolom 2: AWS
    if live_data['aws']:
        d_aws = live_data['aws'] - h_now
        icon_aws, color_aws = ("▲", "#ef44
