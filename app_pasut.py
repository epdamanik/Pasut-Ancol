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

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Monitoring TMA Priok", layout="wide", page_icon="🌊")

st.markdown("""
    <style>
    /* Reset & Container */
    .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; max-width: 95% !important; }
    .stApp { background-color: #ffffff; }
    
    /* Header compact */
    .header-text { text-align: center; width: 100%; margin-top: -40px; margin-bottom: 5px; }
    
    /* Card Melayang untuk Metrics */
    div[data-testid="stMetric"] {
        background-color: #ffffff !important; 
        border: 1px solid #e2e8f0 !important;
        border-left: 5px solid #1e40af !important; 
        padding: 15px !important; 
        border-radius: 12px !important;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06) !important;
        transition: transform 0.2s ease-in-out;
    }
    div[data-testid="stMetric"]:hover { transform: translateY(-3px); }
    
    /* Font Styling */
    [data-testid="stMetricLabel"] { color: #1e3a8a !important; font-weight: 700 !important; font-size: 1rem !important; }
    [data-testid="stMetricValue"] { font-size: 26px !important; font-weight: 850 !important; color: #0f172a !important; }

    /* Footer Card di Sidebar */
    .footer-card {
        margin-top: 50px; padding: 15px; border-radius: 12px; 
        background-color: #f8fafc; border: 1px solid #e2e8f0; 
        text-align: center; box-shadow: inset 0 2px 4px 0 rgba(0, 0, 0, 0.05);
    }
    
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIC WAKTU ---
tz_jkt = pytz.timezone('Asia/Jakarta')
sekarang = datetime.now(tz_jkt).replace(tzinfo=None)

# --- 3. SIDEBAR (LOGO, FILTER, & FOOTER) ---
NAMA_FILE_LOGO = "logo-bmkg-transparan.png" 

with st.sidebar:
    # Logo diperkecil (0.35 di tengah)
    if os.path.exists(NAMA_FILE_LOGO):
        _, col_img, _ = st.columns([0.3, 0.4, 0.3])
        with col_img:
            st.image(NAMA_FILE_LOGO, use_container_width=True)
    
    st.markdown("<h3 style='text-align: center; color: #1e3a8a; margin-top: -10px; font-size: 1rem;'>STAMAR TANJUNG PRIOK</h3>", unsafe_allow_html=True)
    st.divider()
    
    # Filter & Link
    st.subheader("🗓️ Filter Grafik")
    tgl_range = st.date_input("Rentang Waktu", value=(sekarang.date() - timedelta(days=1), sekarang.date() + timedelta(days=2)))
    
    st.link_button("🌐 Portal Resmi BMKG Priok", "https://bmkgtanjungpriok.info/", use_container_width=True)
    
    st.divider()
    
    # Detail Info dalam Expander (Ganteng & Rapi)
    with st.expander("ℹ️ Detail Sumber Data"):
        st.caption("""
        **Prediksi:** Analisis Harmonik data historis TMA Pompa Pasar Ikan I (DSDA DKI) Tahun 2025.
        
        **Real-time:** 1. AWS Stamar Tanjung Priok (BMKG).
        2. Sensor Pintu Air Pasar Ikan (DSDA).
        """)
    
    # Footer Developed by E.P. Damanik
    st.markdown(f"""
        <div class="footer-card">
            <p style='font-size: 0.8rem; color: #1e3a8a; margin-bottom: 0;'>
                © 2026 <b>Stamar Tanjung Priok</b>
            </p>
            <p style='font-size: 0.7rem; color: #475569; margin-top: 8px;'>
                Developed by <br>
                <span style='color: #1e40af; font-weight: 800; font-size: 0.9rem;'>E.P. Damanik</span><br>
                <span style='font-size: 0.65rem; font-style: italic; color: #64748b;'>Maritime Forecaster</span>
            </p>
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
LIMIT_SENSOR_ERROR = 3.5 

def play_audio(file_path):
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
            st.components.v1.html(f'<audio autoplay><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>', height=0)

def get_latest_from_csv(file_path):
    if not os.path.exists(file_path): return None
    try:
        df = pd.read_csv(file_path); df['waktu'] = pd.to_datetime(df['waktu'], format='mixed', errors='coerce')
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
live_data = {"aws": get_latest_from_csv(FILE_HISTORY_AWS), "bpbd": get_latest_from_csv(FILE_HISTORY_BPBD)}

# --- 7. DISPLAY ---
if df_pred is not None:
    h_now = df_pred.loc[(df_pred[col_tgl] - sekarang).abs().idxmin(), col_val]
    
    # Status Alert
    check = {"Prediksi": h_now, "AWS": live_data['aws'], "BPBD": live_data['bpbd']}
    awas = [n for n, v in check.items() if v and v >= 2.5]
    waspada = [n for n, v in check.items() if v and 2.3 <= v < 2.5]

    if awas:
        st.error(f"🚨 STATUS: AWAS ROB! ({', '.join(awas)})", icon="⚠️")
        play_audio("AWAS ROB.mp3") 
    elif waspada:
        st.warning(f"📢 STATUS: WASPADA ROB! ({', '.join(waspada)})", icon="📢")
        play_audio("waspada ROB.mp3")

    # Summary Bar
    df_h = df_pred[df_pred[col_tgl].dt.date == sekarang.date()]
    if not df_h.empty:
        v_max, v_min = df_h[col_val].max(), df_h[col_val].min()
        st.markdown(f'<div class="summary-box"><span class="summary-text">📅 {sekarang.strftime("%d %b %Y")} | <span style="color: #ef4444;">▲ MAX: {v_max:.2f}m</span> | <span style="color: #3b82f6;">▼ MIN: {v_min:.2f}m</span></span></div>', unsafe_allow_html=True)

    # Metrics Layout
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Prediksi Pasut", f"{h_now:.2f} m")
    m2.metric("AWS Tj. Priok", f"{live_data['aws']:.2f} m" if live_data["aws"] else "N/A", delta=f"{(live_data['aws']-h_now):+.2f}m" if live_data['aws'] else None, delta_color="inverse")
    m3.metric("TMA Psr. Ikan", f"{live_data['bpbd']:.2f} m" if live_data["bpbd"] else "N/A", delta=f"{(live_data['bpbd']-h_now):+.2f}m" if live_data["bpbd"] else None, delta_color="inverse")
    
    # Tren Logic
    h_next = df_pred.loc[(df_pred[col_tgl] - (sekarang + timedelta(hours=3))).abs().idxmin(), col_val]
    selisih = h_next - h_now
    icon, status = ("📈", "NAIK") if selisih > 0.05 else ("📉", "TURUN") if selisih < -0.05 else ("↔️", "STAGNAN")
    m4.metric("Tren (3j Kedepan)", f"{icon} {status}")

    # --- PLOTLY ---
    t_start, t_end = datetime.combine(tgl_range[0], datetime.min.time()), datetime.combine(tgl_range[1], datetime.max.time())
    fig = go.Figure()
    df_plot = df_pred[(df_pred[col_tgl] >= t_start) & (df_pred[col_tgl] <= t_end)].copy()
    
    # Prediksi Line
    fig.add_trace(go.Scatter(x=df_plot[col_tgl], y=df_plot[col_val], name='Prediksi', line=dict(color='#94a3b8', dash='dot')))
    
    # History Lines (with Gap Connection)
    for file, label, color in [(FILE_HISTORY_AWS, 'AWS (Hist)', '#7c3aed'), (FILE_HISTORY_BPBD, 'BPBD (Hist)', '#f59e0b')]:
        if os.path.exists(file):
            dh = pd.read_csv(file); dh['waktu'] = pd.to_datetime(dh['waktu'], format='mixed', errors='coerce')
            dh = dh[(dh['waktu'] >= t_start) & (dh['waktu'] <= t_end)].sort_values('waktu')
            fig.add_trace(go.Scatter(x=dh['waktu'], y=dh['nilai'], name=label, connectgaps=True, line=dict(color=color, width=3)))

    # Thresholds
    fig.add_vline(x=sekarang, line_width=2, line_dash="dash", line_color="#22c55e")
    fig.add_hline(y=2.5, line_dash="dash", line_color="#ef4444", annotation_text="AWAS")
    fig.add_hline(y=2.3, line_dash="dash", line_color="#ea580c", annotation_text="WASPADA")
    
    fig.update_layout(height=450, template="plotly_white", margin=dict(l=10, r=10, t=10, b=10), hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig, use_container_width=True)

    # Action Buttons
    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1: st.download_button("📥 AWS Data", open(FILE_HISTORY_AWS, 'rb') if os.path.exists(FILE_HISTORY_AWS) else "", "aws.csv", use_container_width=True)
    with c2: st.download_button("📥 BPBD Data", open(FILE_HISTORY_BPBD, 'rb') if os.path.exists(FILE_HISTORY_BPBD) else "", "bpbd.csv", use_container_width=True)
    with c3: 
        if st.button("🔄 Refresh System", use_container_width=True): st.cache_data.clear(); st.rerun()
