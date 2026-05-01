import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pytz
from streamlit_autorefresh import st_autorefresh
import os
import time
import base64

# --- 0. SMART AUTO REFRESH (Sync tiap 15 Menit) ---
now_sync = datetime.now()
seconds_to_next = ((15 - (now_sync.minute % 15)) * 60) - now_sync.second
if seconds_to_next <= 0: seconds_to_next = 900
st_autorefresh(interval=seconds_to_next * 1000, key="datarefresh")

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Monitoring Pasut Tg. Priok", layout="wide", page_icon="🌊")

st.markdown("""
    <style>
    /* Menghilangkan margin bawaan Streamlit agar konten naik ke atas */
    .block-container {
        padding-top: 1.5rem !important;
        padding-bottom: 0rem !important;
        max-width: 95% !important;
    }
    
    .stApp { background-color: #ffffff; }
    
    /* Header styling agar mepet ke atas */
    .header-text { 
        text-align: center; 
        width: 100%; 
        margin-top: -25px; 
        margin-bottom: 10px;
    }
    
    /* Perbaikan agar tulisan alert jelas */
    [data-testid="stAlert"] {
        border-radius: 10px !important;
        margin-bottom: 10px !important;
    }
    
    /* Background Waspada ke Orange */
    div[data-testid="stNotificationContentWarning"] {
        background-color: #ff9800 !important;
        color: #000000 !important;
    }

    [data-testid="stAlert"] * {
        color: #0f172a !important; 
        font-size: 1.1rem !important;
        font-weight: 700 !important;
    }
    
    /* Metrics Styling */
    [data-testid="stMetricLabel"] { opacity: 1 !important; color: #1e3a8a !important; font-weight: 700 !important; }
    [data-testid="stMetricValue"] { font-size: 22px !important; font-weight: 850 !important; color: #0f172a !important; }
    div[data-testid="stMetric"] {
        background-color: #f8fafc !important; 
        border: 1px solid #e2e8f0 !important;
        border-left: 5px solid #1e40af !important; 
        padding: 10px 15px !important; 
        border-radius: 10px !important;
        min-height: 100px !important; 
        display: flex; flex-direction: column; justify-content: center;
    }
    
    /* Summary Box Styling */
    .summary-box {
        background-color: #f1f5f9 !important; padding: 10px !important; 
        border-radius: 10px !important; margin-bottom: 15px !important; 
        border-left: 5px solid #1e3a8a !important; text-align: center !important;
    }
    .summary-text { font-weight: 850 !important; font-size: 0.95rem !important; color: #0f172a !important; }
    
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIC WAKTU ---
tz_jkt = pytz.timezone('Asia/Jakarta')
sekarang = datetime.now(tz_jkt).replace(tzinfo=None)

# --- 3. SIDEBAR (Logo & Filter) ---
NAMA_FILE_LOGO = "logo-bmkg-transparan.png" 

with st.sidebar:
    if os.path.exists(NAMA_FILE_LOGO):
        # Kolom untuk mengecilkan logo agar proporsional
        _, col_img, _ = st.columns([0.25, 0.5, 0.25])
        with col_img:
            st.image(NAMA_FILE_LOGO, use_container_width=True)
    
    st.markdown("<h3 style='text-align: center; color: #1e3a8a; margin-top: -10px; font-size: 1.1rem;'>STASIUN METEOROLOGI MARITIM TANJUNG PRIOK</h3>", unsafe_allow_html=True)
    st.divider()
    
    st.subheader("🗓️ Filter Grafik")
    tgl_range = st.date_input("Rentang Waktu", value=(sekarang.date() - timedelta(days=1), sekarang.date() + timedelta(days=2)))
    
    st.divider()
    st.info("Prediksi pasut dihitung menggunakan metode Analisis Harmonik dengan referensi data historis TMA Pasar Ikan tahun 2025.")
    st.caption("© 2026 Stasiun Meteorologi Maritim Tanjung Priok")

# --- 4. HEADER UTAMA (Posisi Diperbaiki) ---
st.markdown(f"""
    <div class="header-text">
        <h2 style="margin: 0; color: #0f172a; font-weight: bold; font-size: 1.55rem; line-height: 1.2;">
            MONITORING TINGGI MUKA AIR (TMA) REAL TIME
       
    </div>
    """, unsafe_allow_html=True)

# --- 5. DATA FUNCTIONS ---
FILE_PREDIKSI = 'prediksi_pasut_ancol_2026_FINAL_WIB.xlsx'
FILE_HISTORY_AWS = 'history_aws_priok.csv' 
FILE_HISTORY_BPBD = 'history_bpbd_pasarikan.csv'
LIMIT_SENSOR_ERROR = 3.5 

def play_audio(file_path):
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            data = f.read()
            b64 = base64.b64encode(data).decode()
            audio_html = f'<audio autoplay><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
            st.components.v1.html(audio_html, height=0)

def get_latest_from_csv(file_path):
    if not os.path.exists(file_path): return None
    try:
        df = pd.read_csv(file_path)
        if df.empty: return None
        df['waktu'] = pd.to_datetime(df['waktu'], format='mixed', errors='coerce')
        df = df.dropna(subset=['waktu', 'nilai']).sort_values('waktu')
        return df.iloc[-1]['nilai']
    except: return None

@st.cache_data(ttl=3600)
def load_prediction():
    if not os.path.exists(FILE_PREDIKSI): return None, None, None
    df = pd.read_excel(FILE_PREDIKSI, engine='openpyxl')
    t_col = next((c for c in ['tanggal_prediksi', 'Waktu_WIB', 'Waktu'] if c in df.columns), None)
    v_col = next((c for c in ['wl_prediksi', 'Tinggi_Navigasi_m'] if c in df.columns), None)
    if t_col: 
        df[t_col] = pd.to_datetime(df[t_col], format='mixed', errors='coerce')
        df = df.dropna(subset=[t_col, v_col])
    return df.sort_values(t_col), t_col, v_col

# --- 6. EXECUTION ---
df_pred, col_tgl, col_val = load_prediction()
live_data = {"aws": get_latest_from_csv(FILE_HISTORY_AWS), "bpbd": get_latest_from_csv(FILE_HISTORY_BPBD)}

# --- 7. DISPLAY ---
if df_pred is not None and not df_pred.empty:
    h_now = df_pred.loc[(df_pred[col_tgl] - sekarang).abs().idxmin(), col_val]
    
    # Alert System
    check_values = {"Prediksi": h_now, "AWS": live_data['aws'], "BPBD": live_data['bpbd']}
    awas = [n for n, v in check_values.items() if v is not None and v >= 2.5]
    waspada = [n for n, v in check_values.items() if v is not None and 2.3 <= v < 2.5]

    if awas:
        st.error(f"**🚨 STATUS: AWAS ROB! ({', '.join(awas)})**", icon="⚠️")
        play_audio("AWAS ROB.mp3") 
    elif waspada:
        st.warning(f"**⚠️ STATUS: WASPADA ROB! ({', '.join(waspada)})**", icon="📢")
        play_audio("waspada ROB.mp3")

    # Summary Box
    df_h = df_pred[df_pred[col_tgl].dt.date == sekarang.date()]
    if not df_h.empty:
        val_max, jam_max = df_h[col_val].max(), df_h.loc[df_h[col_val].idxmax(), col_tgl].strftime("%H:%M")
        val_min, jam_min = df_h[col_val].min(), df_h.loc[df_h[col_val].idxmin(), col_tgl].strftime("%H:%M")
        st.markdown(f'<div class="summary-box"><span class="summary-text">📅 {sekarang.strftime("%d %b %Y")} | <span style="color: #ef4444;">▲ MAX: {val_max:.2f}m ({jam_max})</span> | <span style="color: #3b82f6;">▼ MIN: {val_min:.2f}m ({jam_min})</span></span></div>', unsafe_allow_html=True)

    # Metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Prediksi Pasut", f"{h_now:.2f} m")
    m2.metric("AWS Tj. Priok", f"{live_data['aws']:.2f} m" if live_data["aws"] else "N/A", 
              delta=f"{(live_data['aws'] - h_now):+.2f}m" if live_data['aws'] else None, delta_color="inverse")
    m3.metric("TMA Psr. Ikan", f"{live_data['bpbd']:.2f} m" if live_data["bpbd"] else "N/A", 
              delta=f"{(live_data['bpbd'] - h_now):+.2f}m" if live_data['bpbd'] else None, delta_color="inverse")
    
    # Tren
    h_next = df_pred.loc[(df_pred[col_tgl] - (sekarang + timedelta(hours=3))).abs().idxmin(), col_val]
    selisih = h_next - h_now
    if abs(selisih) < 0.05: tren_status = "↔️ STAGNAN"
    elif selisih > 0: tren_status = "📈 NAIK"
    else: tren_status = "📉 TURUN"
    m4.metric("Tren (2j Kedepan)", tren_status)

    # --- PLOTLY CHART ---
    t_start, t_end = datetime.combine(tgl_range[0], datetime.min.time()), datetime.combine(tgl_range[1], datetime.max.time())
    fig = go.Figure()
    df_plot = df_pred[(df_pred[col_tgl] >= t_start) & (df_pred[col_tgl] <= t_end)].copy()
    
    # Garis Prediksi
    fig.add_trace(go.Scatter(x=df_plot[col_tgl], y=df_plot[col_val], name='Prediksi', line=dict(color='#94a3b8', dash='dot')))
    
    # Titik Max/Min Harian
    df_plot['tgl_saja'] = df_plot[col_tgl].dt.date
    for tgl in df_plot['tgl_saja'].unique():
        df_tgl = df_plot[df_plot['tgl_saja'] == tgl]
        p_max = df_tgl.loc[df_tgl[col_val].idxmax()]
        fig.add_trace(go.Scatter(x=[p_max[col_tgl]], y=[p_max[col_val]], mode='markers+text', text=[f"<b>{p_max[col_val]:.2f}</b>"], textposition="top center", marker=dict(color='#ef4444', size=7), showlegend=False))
        p_min = df_tgl.loc[df_tgl[col_val].idxmin()]
        fig.add_trace(go.Scatter(x=[p_min[col_tgl]], y=[p_min[col_val]], mode='markers+text', text=[f"<b>{p_min[col_val]:.2f}</b>"], textposition="bottom center", marker=dict(color='#3b82f6', size=7), showlegend=False))

    # History Data
    for file, label, color in [(FILE_HISTORY_AWS, 'AWS (Hist)', '#7c3aed'), (FILE_HISTORY_BPBD, 'BPBD (Hist)', '#f59e0b')]:
        if os.path.exists(file):
            dh = pd.read_csv(file); dh['waktu'] = pd.to_datetime(dh['waktu'], format='mixed', errors='coerce')
            dh = dh[(dh['waktu'] >= t_start) & (dh['waktu'] <= t_end) & (dh['nilai'] <= LIMIT_SENSOR_ERROR)].sort_values('waktu')
            fig.add_trace(go.Scatter(x=dh['waktu'], y=dh['nilai'], name=label, mode='lines', line=dict(color=color, width=2.5)))

    # Annotations
    fig.add_vline(x=sekarang, line_width=2, line_dash="dash", line_color="#22c55e")
    fig.add_hline(y=2.5, line_dash="dash", line_color="#ef4444", annotation_text="AWAS")
    fig.add_hline(y=2.3, line_dash="dash", line_color="#ea580c", annotation_text="WASPADA")
    
    fig.update_layout(height=500, template="plotly_white", margin=dict(l=10, r=10, t=30, b=10), hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig, use_container_width=True)

    # Footer Buttons
    st.divider()
    f1, f2, f3 = st.columns(3)
    with f1:
        if os.path.exists(FILE_HISTORY_AWS): st.download_button("📥 Unduh Data AWS", open(FILE_HISTORY_AWS, 'rb'), "aws_priok.csv", "text/csv", use_container_width=True)
    with f2:
        if os.path.exists(FILE_HISTORY_BPBD): st.download_button("📥 Unduh Data BPBD", open(FILE_HISTORY_BPBD, 'rb'), "bpbd_pasarikan.csv", "text/csv", use_container_width=True)
    with f3: 
        if st.button("🔄 Segarkan Data", use_container_width=True): st.cache_data.clear(); st.rerun()
else:
    st.error("Data prediksi tidak ditemukan. Pastikan file Excel tersedia.")
