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
    .block-container { padding-top: 0.5rem !important; padding-bottom: 0rem !important; max-width: 95% !important; }
    [data-testid="stVerticalBlock"] > div { gap: 0px !important; }
    .stApp { background-color: #ffffff; }
    .header-text { text-align: center; width: 100%; margin-top: -15px; margin-bottom: 0px !important; }
    [data-testid="stSidebar"] [data-testid="stImage"] { text-align: center !important; display: block !important; margin-left: auto !important; margin-right: auto !important; width: 100% !important; }
    div[data-testid="stMetric"] { background-color: #ffffff !important; border: 1px solid #e2e8f0 !important; border-left: 4px solid #1e40af !important; padding: 4px 10px !important; border-radius: 8px !important; min-height: 55px !important; display: flex !important; flex-direction: column !important; justify-content: center !important; }
    div[data-testid="stMetricLabel"] { color: #1e3a8a !important; font-weight: 700 !important; font-size: 0.7rem !important; margin-bottom: -10px !important; }
    [data-testid="stMetricValue"] { font-size: 15px !important; font-weight: 800 !important; color: #0f172a !important; }
    div[data-testid="stMetricDelta"] { display: none !important; }
    .summary-box { background-color: #f1f5f9 !important; padding: 8px !important; border-radius: 10px !important; margin-top: -15px !important; margin-bottom: 10px !important; border-left: 5px solid #1e3a8a !important; text-align: center !important; }
    .summary-text { font-weight: 850 !important; font-size: 0.9rem !important; color: #0f172a !important; }
    .footer-card { margin-top: 30px; padding: 12px; border-radius: 10px; background-color: #f8fafc; border: 1px solid #e2e8f0; text-align: center; }
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
        st.markdown(f'<div style="text-align: center; margin-top: -15px; margin-bottom: 10px;"><img src="data:image/png;base64,{encoded}" style="width: 85px;"></div>', unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #1e3a8a; font-size: 0.85rem; font-weight: bold;'>STASIUN METEOROLOGI MARITIM TANJUNG PRIOK</p>", unsafe_allow_html=True)
    st.divider()
    tgl_range = st.date_input("🗓️ Rentang Waktu", value=(sekarang.date() - timedelta(days=1), sekarang.date() + timedelta(days=2)))
    st.link_button("🌐 Web BMKG", "https://bmkgtanjungpriok.info/", use_container_width=True)

# --- 4. DATA FUNCTIONS ---
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
    if t_col: df[t_col] = pd.to_datetime(df[t_col], format='mixed', errors='coerce')
    return df.dropna(subset=[t_col, v_col]).sort_values(t_col), t_col, v_col

df_pred, col_tgl, col_val = load_prediction()
live_data = {"aws": get_latest_from_csv(FILE_HISTORY_AWS), "bpbd": get_latest_from_csv(FILE_HISTORY_BPBD)}

# --- 5. DISPLAY ---
if df_pred is not None and not df_pred.empty:
    h_now = df_pred.loc[(df_pred[col_tgl] - sekarang_naive).abs().idxmin(), col_val]
    
    st.markdown('<div class="header-text"><h2 style="color: #0f172a; font-weight: bold; font-size: 1.6rem;">MONITORING TINGGI MUKA AIR (TMA) REAL TIME</h2></div>', unsafe_allow_html=True)

    # Summary Box
    df_h = df_pred[df_pred[col_tgl].dt.date == sekarang.date()]
    if not df_h.empty:
        idx_max, idx_min = df_h[col_val].idxmax(), df_h[col_val].idxmin()
        st.markdown(f'<div class="summary-box"><span class="summary-text">📅 {sekarang.strftime("%d %b %Y")} | <span style="color: #ef4444;">▲ MAX: {df_h.loc[idx_max, col_val]:.2f}m</span> | <span style="color: #3b82f6;">▼ MIN: {df_h.loc[idx_min, col_val]:.2f}m</span></span></div>', unsafe_allow_html=True)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Prediksi Pasut", f"{h_now:.2f} m")
    
    # AWS & Psr Ikan Metrics (Dynamic Colors)
    for data_key, label, col in [("aws", "AWS Tj. Priok", m2), ("bpbd", "TMA Psr. Ikan", m3)]:
        val = live_data[data_key]
        if val:
            diff = val - h_now
            color = "#ef4444" if diff > 0 else "#22c55e"
            icon = "▲" if diff > 0 else "▼"
            col.markdown(f'<div data-testid="stMetric"><label data-testid="stMetricLabel">{label}</label><div data-testid="stMetricValue">{val:.2f} m <span style="color: {color}; font-size: 0.8rem;">{icon}({diff:+.2f})</span></div></div>', unsafe_allow_html=True)
        else: col.metric(label, "N/A")

    m4.metric("Tren (3j)", "📈 NAIK" if (df_pred.loc[(df_pred[col_tgl] - (sekarang_naive + timedelta(hours=3))).abs().idxmin(), col_val] - h_now) > 0.05 else "📉 TURUN")

    # --- PLOTLY CHART ---
    t_start, t_end = datetime.combine(tgl_range[0], datetime.min.time()), datetime.combine(tgl_range[1], datetime.max.time())
    fig = go.Figure()
    df_plot = df_pred[(df_pred[col_tgl] >= t_start) & (df_pred[col_tgl] <= t_end)].copy()
    
    if not df_plot.empty:
        fig.add_trace(go.Scatter(x=df_plot[col_tgl], y=df_plot[col_val], name='Prediksi', mode='lines', line=dict(color='rgba(148, 163, 184, 0.7)', dash='dot', width=2)))
        
        for file, label, color in [(FILE_HISTORY_AWS, 'AWS (Hist)', '#7c3aed'), (FILE_HISTORY_BPBD, 'Psr. Ikan (Hist)', '#f59e0b')]:
            if os.path.exists(file):
                dh = pd.read_csv(file)
                dh['waktu'] = pd.to_datetime(dh['waktu'], format='mixed', errors='coerce')
                dh = dh[(dh['waktu'] >= t_start) & (dh['waktu'] <= t_end)].sort_values('waktu')
                if not dh.empty: fig.add_trace(go.Scatter(x=dh['waktu'], y=dh['nilai'], name=label, mode='lines', line=dict(color=color, width=3)))

        fig.add_hline(y=2.5, line_dash="dash", line_color="#ef4444", annotation_text="🚨 AWAS", annotation_position="top right")
        fig.add_hline(y=2.3, line_dash="dash", line_color="#ea580c", annotation_text="📢 WASPADA", annotation_position="top right")
        
        # --- PERUBAHAN POSISI LEGENDA KE KANAN & MATIKAN MODEBAR ---
        fig.update_layout(
            height=400, 
            template="plotly_white", 
            margin=dict(l=10, r=10, t=30, b=10),
            hovermode="x unified",
            showlegend=True,
            legend=dict(
                orientation="v",      # Vertical
                yanchor="top",
                y=1,
                xanchor="left",
                x=1.02                # Di sebelah kanan luar grafik
            )
        )
        
        # config={'displayModeBar': False} untuk menghilangkan zoom, pan, dll yang nutupin legenda
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1: st.download_button("📥 AWS", open(FILE_HISTORY_AWS, 'rb') if os.path.exists(FILE_HISTORY_AWS) else "", "AWS.csv", use_container_width=True)
    with c2: st.download_button("📥 Psr. Ikan", open(FILE_HISTORY_BPBD, 'rb') if os.path.exists(FILE_HISTORY_BPBD) else "", "Ikan.csv", use_container_width=True)
    with c3: 
        if st.button("🔄 Refresh Data", use_container_width=True): st.cache_data.clear(); st.rerun()
else:
    st.error("Gagal memuat data prediksi.")
