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
    .block-container { padding-top: 1.5rem !important; padding-bottom: 0rem !important; max-width: 95% !important; }
    .stApp { background-color: #ffffff; }
    .header-text { text-align: center; width: 100%; margin-top: -20px; margin-bottom: 5px; }

    /* --- SIDEBAR LOGO & CALENDAR --- */
    [data-testid="stSidebar"] [data-testid="stImage"] { text-align: center !important; display: block !important; margin: 0 auto !important; width: 100% !important; }
    div[data-baseweb="popover"] { top: 90px !important; width: fit-content !important; }
    div[data-baseweb="calendar"] { transform: scale(1) !important; margin: 0 !important; }
    div[data-testid="stDateInput"] { max-width: 90% !important; margin: 0 auto !important; }

    /* --- METRIK RAMPING (2 BARIS + INLINE DELTA) --- */
    div[data-testid="stMetric"] {
        background-color: #ffffff !important; 
        border: 1px solid #e2e8f0 !important;
        border-left: 5px solid #1e40af !important; 
        padding: 10px 15px !important; 
        border-radius: 10px !important;
        min-height: 80px !important; 
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
    }
    [data-testid="stMetricLabel"] { color: #1e3a8a !important; font-weight: 700 !important; font-size: 0.8rem !important; margin-bottom: -10px !important; }
    [data-testid="stMetricValue"] { 
        font-size: 22px !important; font-weight: 800 !important; color: #0f172a !important; 
        display: flex !important; align-items: center !important;
    }
    /* Paksa Delta ke samping Nilai */
    [data-testid="stMetricDelta"] { margin-left: 10px !important; font-size: 14px !important; font-weight: 600 !important; }

    /* --- SUMMARY BOX PEPET HEADER --- */
    .summary-box {
        background-color: #f1f5f9 !important; padding: 8px !important; 
        border-radius: 8px !important; margin-bottom: 10px !important; 
        border-left: 5px solid #1e3a8a !important; text-align: center !important;
    }
    .summary-text { font-weight: 800 !important; font-size: 0.9rem !important; color: #0f172a !important; }

    .footer-card { margin-top: 30px; padding: 10px; border-radius: 10px; background-color: #f8fafc; border: 1px solid #e2e8f0; text-align: center; }
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
            encoded = base64.b64encode(f.read()).decode()
        st.markdown(f'<div style="text-align: center; margin-bottom: 10px;"><img src="data:image/png;base64,{encoded}" style="width: 85px;"></div>', unsafe_allow_html=True)
    
    st.markdown("<p style='text-align: center; color: #1e3a8a; font-size: 0.85rem; font-weight: bold;'>STASIUN METEOROLOGI MARITIM TANJUNG PRIOK</p>", unsafe_allow_html=True)
    st.divider()
    
    tgl_range = st.date_input("🗓️ Rentang Waktu Grafik", value=(sekarang.date() - timedelta(days=1), sekarang.date() + timedelta(days=2)))
    st.link_button("🌐 Web BMKG Tanjung Priok", "https://bmkgtanjungpriok.info/", use_container_width=True)
    
    with st.expander("ℹ️ Info Sumber Data"):
        st.markdown("""
        <div style="text-align: justify; font-size: 0.9rem; color: #475569;">
            <strong>📍 Prediksi:</strong> Analisis Harmonik data TMA Pasar Ikan I (DSDA) Tahun 2025.<br><br>
            <strong>⚡ Real-time:</strong>
            <ul style="margin-top: 5px; padding-left: 20px;">
                <li>AWS Maritim Tanjung Priok (BMKG).</li>
                <li>Pintu Air Pasar Ikan I (DSDA).</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown(f"""
        <div class="footer-card">
            <p style='font-size: 0.7rem; color: #1e3a8a; margin-bottom: 0; font-weight: 600;'>© 2026 Stasiun Meteorologi Maritim Tanjung Priok</p>
        </div>
        <div style="text-align: center; margin-top: 10px;">
            <p style='font-size: 0.5rem; color: #94a3b8; margin: 0;'>Developed by E.P. Damanik</p>
        </div>
    """, unsafe_allow_html=True)

# --- 4. HEADER UTAMA ---
st.markdown('<div class="header-text"><h2 style="margin: 0; color: #0f172a; font-weight: bold; font-size: 1.5rem;">MONITORING TINGGI MUKA AIR (TMA) REAL TIME</h2></div>', unsafe_allow_html=True)

# --- 5. DATA FUNCTIONS ---
FILE_PREDIKSI = 'prediksi_pasut_ancol_2026_FINAL_WIB.xlsx'
FILE_HISTORY_AWS = 'history_aws_priok.csv' 
FILE_HISTORY_BPBD = 'history_bpbd_pasarikan.csv'

def play_audio(file_path):
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
            st.components.v1.html(f'<audio autoplay><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>', height=0)

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

# --- 6. EXECUTION ---
df_pred, col_tgl, col_val = load_prediction()
live_aws = get_latest_from_csv(FILE_HISTORY_AWS)
live_bpbd = get_latest_from_csv(FILE_HISTORY_BPBD)

# --- 7. DISPLAY ---
if df_pred is not None and not df_pred.empty:
    h_now = df_pred.loc[(df_pred[col_tgl] - sekarang_naive).abs().idxmin(), col_val]
    
    # Alert Status
    check = {"Prediksi": h_now, "AWS": live_aws, "PASAR IKAN": live_bpbd}
    awas = [n for n, v in check.items() if v and v >= 2.5]
    waspada = [n for n, v in check.items() if v and 2.3 <= v < 2.5]

    if awas:
        st.error(f"🚨 STATUS: AWAS ROB! ({', '.join(awas)})", icon="⚠️")
        play_audio("AWAS ROB.mp3") 
    elif waspada:
        st.warning(f"📢 STATUS: WASPADA ROB! ({', '.join(waspada)})", icon="📢")
        play_audio("waspada ROB.mp3")

    # --- SUMMARY BOX (DENGAN JAM MAX/MIN) ---
    df_h = df_pred[df_pred[col_tgl].dt.date == sekarang.date()]
    if not df_h.empty:
        row_max = df_h.loc[df_h[col_val].idxmax()]
        row_min = df_h.loc[df_h[col_val].idxmin()]
        st.markdown(f"""
            <div class="summary-box">
                <span class="summary-text">
                    📅 {sekarang.strftime("%d %b %Y")} | 
                    <span style="color: #ef4444;">▲ MAX: {row_max[col_val]:.2f}m ({row_max[col_tgl].strftime('%H:%M')})</span> | 
                    <span style="color: #3b82f6;">▼ MIN: {row_min[col_val]:.2f}m ({row_min[col_tgl].strftime('%H:%M')})</span>
                </span>
            </div>
            """, unsafe_allow_html=True)

    # --- METRICS (INLINE DELTA) ---
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Prediksi Pasut", f"{h_now:.2f} m")
    
    diff_aws = f"{(live_aws - h_now):+.2f}m" if live_aws else None
    m2.metric("AWS Tj. Priok", f"{live_aws:.2f} m" if live_aws else "N/A", delta=diff_aws, delta_color="inverse")
    
    diff_bpbd = f"{(live_bpbd - h_now):+.2f}m" if live_bpbd else None
    m3.metric("TMA Psr. Ikan", f"{live_bpbd:.2f} m" if live_bpbd else "N/A", delta=diff_bpbd, delta_color="inverse")
    
    h_next = df_pred.loc[(df_pred[col_tgl] - (sekarang_naive + timedelta(hours=3))).abs().idxmin(), col_val]
    tren = h_next - h_now
    icon, status = ("📈 NAIK", "normal") if tren > 0.05 else ("📉 TURUN", "normal") if tren < -0.05 else ("↔️ STAGNAN", "off")
    m4.metric("Tren (3 Jam Ke Depan)", icon)

    # --- PLOTLY CHART ---
    t_start, t_end = datetime.combine(tgl_range[0], datetime.min.time()), datetime.combine(tgl_range[1], datetime.max.time())
    df_plot = df_pred[(df_pred[col_tgl] >= t_start) & (df_pred[col_tgl] <= t_end)].copy()
    
    fig = go.Figure()
    if not df_plot.empty:
        # Garis Prediksi
        fig.add_trace(go.Scatter(x=df_plot[col_tgl], y=df_plot[col_val], name='Prediksi', mode='lines', line=dict(color='rgba(148, 163, 184, 0.7)', dash='dot', width=2, shape='spline')))
        
        # Dot Max & Min Harian
        for day in df_plot[col_tgl].dt.date.unique():
            df_day = df_plot[df_plot[col_tgl].dt.date == day]
            idx_max, idx_min = df_day[col_val].idxmax(), df_day[col_val].idxmin()
            fig.add_trace(go.Scatter(x=[df_day.loc[idx_max, col_tgl]], y=[df_day.loc[idx_max, col_val]], mode='markers+text', marker=dict(color='#ef4444', size=8), text=[f"{df_day.loc[idx_max, col_val]:.2f}"], textposition="top center", showlegend=False))
            fig.add_trace(go.Scatter(x=[df_day.loc[idx_min, col_tgl]], y=[df_day.loc[idx_min, col_val]], mode='markers+text', marker=dict(color='#3b82f6', size=8), text=[f"{df_day.loc[idx_min, col_val]:.2f}"], textposition="bottom center", showlegend=False))

        # History Data
        for file, label, color in [(FILE_HISTORY_AWS, 'AWS (Hist)', '#7c3aed'), (FILE_HISTORY_BPBD, 'Psr. Ikan (Hist)', '#f59e0b')]:
            if os.path.exists(file):
                dh = pd.read_csv(file)
                dh['waktu'] = pd.to_datetime(dh['waktu'], format='mixed', errors='coerce')
                dh = dh[(dh['waktu'] >= t_start) & (dh['waktu'] <= t_end)].sort_values('waktu')
                if not dh.empty:
                    fig.add_trace(go.Scatter(x=dh['waktu'], y=dh['nilai'], name=label, mode='lines', line=dict(color=color, width=3, shape='spline')))

        # Garis Waktu Sekarang
        fig.add_vline(x=sekarang_naive, line_width=2, line_dash="dash", line_color="#22c55e")
        fig.add_hline(y=2.5, line_dash="dash", line_color="#ef4444")
        fig.add_hline(y=2.3, line_dash="dash", line_color="#ea580c")
        
        fig.update_layout(height=480, template="plotly_white", margin=dict(l=10, r=10, t=30, b=10), hovermode="x unified", legend=dict(orientation="h", y=1.05))
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1: st.download_button("📥 Scrape AWS Maritim Tj. Priok CSV", open(FILE_HISTORY_AWS, 'rb') if os.path.exists(FILE_HISTORY_AWS) else "", "AWS.csv", use_container_width=True)
    with c2: st.download_button("📥 Scrape Pintu air Pasar Ikan I CSV", open(FILE_HISTORY_BPBD, 'rb') if os.path.exists(FILE_HISTORY_BPBD) else "", "Pasarikan.csv", use_container_width=True)
    with c3: 
        if st.button("🔄 Refresh Data", use_container_width=True): st.cache_data.clear(); st.rerun()
else:
    st.error("Gagal memuat data prediksi.")
