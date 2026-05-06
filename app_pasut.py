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

# --- 1. KONFIGURASI HALAMAN & CSS CUSTOM ---
st.set_page_config(page_title="Monitoring TMA Priok", layout="wide", page_icon="🌊")

st.markdown("""
    <style>
    /* --- LAYOUT DASAR & HEADER --- */
    .block-container { padding-top: 1.2rem !important; padding-bottom: 0rem !important; max-width: 95% !important; }
    .stApp { background-color: #ffffff; }
    .header-text { text-align: center; width: 100%; margin-top: -35px; margin-bottom: 5px; }

    /* --- SIDEBAR LOGO & KALENDER --- */
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
    div[data-baseweb="popover"] { top: 90px !important; transform: none !important; }

    /* --- UI METRIK: TIPIS & SEJAJAR (GRID SYSTEM) --- */
    div[data-testid="stMetric"] {
        display: grid !important;
        grid-template-columns: auto auto !important; /* Nilai dan Delta sampingan */
        grid-template-rows: auto auto !important;
        padding: 6px 12px !important;
        background-color: #ffffff !important;
        border: 1px solid #e2e8f0 !important;
        border-left: 5px solid #1e40af !important;
        border-radius: 8px !important;
        min-height: 60px !important;
    }
    
    [data-testid="stMetricLabel"] {
        grid-column: 1 / 3 !important; /* Label di baris atas sendiri */
        margin-bottom: 2px !important;
        color: #1e3a8a !important;
        font-weight: 700 !important;
        font-size: 0.75rem !important;
    }
    
    [data-testid="stMetricValue"] {
        grid-column: 1 !important; /* Nilai di kiri bawah */
        font-size: 1.2rem !important;
        font-weight: 800 !important;
        color: #0f172a !important;
        line-height: 1.2 !important;
    }
    
    [data-testid="stMetricDelta"] {
        grid-column: 2 !important; /* Delta di kanan bawah (sejajar nilai) */
        align-self: center !important;
        font-size: 0.85rem !important;
        font-weight: 700 !important;
        margin-left: 5px !important;
    }

    /* --- SUMMARY & FOOTER --- */
    .summary-box {
        background-color: #f1f5f9 !important; padding: 8px !important; 
        border-radius: 8px !important; margin-bottom: 12px !important; 
        border-left: 5px solid #1e3a8a !important; text-align: center !important;
    }
    .summary-text { font-weight: 850 !important; font-size: 0.9rem !important; color: #0f172a !important; }
    .footer-card {
        margin-top: 50px; padding: 12px; border-radius: 10px; 
        background-color: #f8fafc; border: 1px solid #e2e8f0; text-align: center;
    }
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIC WAKTU ---
tz_jkt = pytz.timezone('Asia/Jakarta')
sekarang = datetime.now(tz_jkt)
sekarang_naive = sekarang.replace(tzinfo=None)

# --- 3. SIDEBAR (SESUAI ASLINYA) ---
NAMA_FILE_LOGO = "logo-bmkg-transparan.png" 

with st.sidebar:
    if os.path.exists(NAMA_FILE_LOGO):
        with open(NAMA_FILE_LOGO, "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        st.markdown(f'<div style="text-align: center;"><img src="data:image/png;base64,{encoded}" style="width: 85px;"></div>', unsafe_allow_html=True)
    
    st.markdown("<p style='text-align: center; color: #1e3a8a; font-weight: bold;'>STASIUN METEOROLOGI MARITIM TANJUNG PRIOK</p>", unsafe_allow_html=True)
    st.divider()
    
    tgl_range = st.date_input("🗓️ Rentang Waktu Grafik", value=(sekarang.date() - timedelta(days=1), sekarang.date() + timedelta(days=2)))
    st.link_button("🌐 Web BMKG Tanjung Priok", "https://bmkgtanjungpriok.info/", use_container_width=True)
    
    with st.expander("ℹ️ Info Sumber Data"):
        st.markdown("<strong>📍 Prediksi:</strong> Analisis Harmonik 2025.<br><strong>⚡ Real-time:</strong> AWS BMKG & Pasar Ikan (DSDA).", unsafe_allow_html=True)
    
    st.markdown('<div class="footer-card"><p style="font-size: 0.72rem; color: #1e3a8a; font-weight: 600;">© 2026 Stasiun Meteorologi Maritim Tanjung Priok</p></div>', unsafe_allow_html=True)
    st.markdown('<p style="text-align: center; font-size: 0.5rem; color: #64748b; margin-top: 10px;">Developed by E.P. Damanik</p>', unsafe_allow_html=True)

# --- 4. HEADER ---
st.markdown('<div class="header-text"><h2 style="color: #0f172a; font-weight: bold;">MONITORING TINGGI MUKA AIR (TMA) REAL TIME</h2></div>', unsafe_allow_html=True)

# --- 5. DATA LOADING ---
FILE_PREDIKSI = 'prediksi_pasut_ancol_2026_FINAL_WIB.xlsx'
FILE_HISTORY_AWS = 'history_aws_priok.csv' 
FILE_HISTORY_BPBD = 'history_bpbd_pasarikan.csv'

def play_audio(file_path):
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
            st.components.v1.html(f'<audio autoplay><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>', height=0)

def get_latest_val(path):
    try:
        df = pd.read_csv(path)
        df['waktu'] = pd.to_datetime(df['waktu'])
        return df.sort_values('waktu').iloc[-1]['nilai']
    except: return None

@st.cache_data(ttl=3600)
def load_data():
    if not os.path.exists(FILE_PREDIKSI): return None
    df = pd.read_excel(FILE_PREDIKSI)
    t_col = next(c for c in ['tanggal_prediksi', 'Waktu_WIB'] if c in df.columns)
    v_col = next(c for c in ['wl_prediksi', 'Tinggi_Navigasi_m'] if c in df.columns)
    df[t_col] = pd.to_datetime(df[t_col])
    return df.sort_values(t_col), t_col, v_col

# --- 6. DISPLAY ---
res = load_data()
if res:
    df_pred, col_t, col_v = res
    h_now = df_pred.loc[(df_pred[col_t] - sekarang_naive).abs().idxmin(), col_v]
    val_aws = get_latest_val(FILE_HISTORY_AWS)
    val_bpbd = get_latest_val(FILE_HISTORY_BPBD)

    # Status & Audio
    if any(v and v >= 2.5 for v in [h_now, val_aws, val_bpbd]):
        st.error("🚨 STATUS: AWAS ROB!", icon="⚠️")
        play_audio("AWAS ROB.mp3")
    elif any(v and 2.3 <= v < 2.5 for v in [h_now, val_aws, val_bpbd]):
        st.warning("📢 STATUS: WASPADA ROB!", icon="📢")
        play_audio("waspada ROB.mp3")

    # Summary Box
    df_h = df_pred[df_pred[col_t].dt.date == sekarang.date()]
    if not df_h.empty:
        v_max, t_max = df_h[col_v].max(), df_h.loc[df_h[col_v].idxmax(), col_t].strftime("%H:%M")
        v_min, t_min = df_h[col_v].min(), df_h.loc[df_h[col_v].idxmin(), col_t].strftime("%H:%M")
        st.markdown(f'<div class="summary-box"><span class="summary-text">📅 {sekarang.strftime("%d %b %Y")} | <span style="color: #ef4444;">▲ MAX: {v_max:.2f}m ({t_max})</span> | <span style="color: #3b82f6;">▼ MIN: {v_min:.2f}m ({t_min})</span></span></div>', unsafe_allow_html=True)

    # Metrics Row
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Prediksi Pasut", f"{h_now:.2f} m")
    
    d_aws = val_aws - h_now if val_aws else None
    m2.metric("AWS Tj. Priok", f"{val_aws:.2f} m" if val_aws else "N/A", delta=f"({d_aws:+.2f}m)" if d_aws else None)
    
    d_bpbd = val_bpbd - h_now if val_bpbd else None
    m3.metric("TMA Psr. Ikan", f"{val_bpbd:.2f} m" if val_bpbd else "N/A", delta=f"({d_bpbd:+.2f}m)" if d_bpbd else None)
    
    h_next = df_pred.loc[(df_pred[col_t] - (sekarang_naive + timedelta(hours=3))).abs().idxmin(), col_v]
    tren = "NAIK" if h_next > h_now + 0.05 else "TURUN" if h_next < h_now - 0.05 else "STAGNAN"
    m4.metric("Tren (3j Ke Depan)", tren)

    # --- PLOTLY ---
    t_s, t_e = [datetime.combine(t, datetime.min.time()) for t in tgl_range]
    df_p = df_pred[(df_pred[col_t] >= t_s) & (df_pred[col_t] <= t_e)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_p[col_t], y=df_p[col_v], name="Prediksi", line=dict(color='gray', dash='dash')))
    
    # Tambah Data History (AWS & BPBD)
    for f, n, c in [(FILE_HISTORY_AWS, "AWS", "purple"), (FILE_HISTORY_BPBD, "Psr. Ikan", "orange")]:
        if os.path.exists(f):
            dh = pd.read_csv(f)
            dh['waktu'] = pd.to_datetime(dh['waktu'])
            dh = dh[(dh['waktu'] >= t_s) & (dh['waktu'] <= t_e)]
            fig.add_trace(go.Scatter(x=dh['waktu'], y=dh['nilai'], name=n, line=dict(color=c, width=3)))

    fig.update_layout(height=450, margin=dict(l=10, r=10, t=30, b=10), hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

    # Buttons Row
    c1, c2, c3 = st.columns(3)
    c1.download_button("📥 AWS CSV", open(FILE_HISTORY_AWS, 'rb') if os.path.exists(FILE_HISTORY_AWS) else b"", "aws.csv", use_container_width=True)
    c2.download_button("📥 Psr Ikan CSV", open(FILE_HISTORY_BPBD, 'rb') if os.path.exists(FILE_HISTORY_BPBD) else b"", "bpbd.csv", use_container_width=True)
    if c3.button("🔄 Refresh", use_container_width=True): st.rerun()
