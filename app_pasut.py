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
    /* Container Utama - Dikasih ruang dikit biar gak kepotong headernya */
    .block-container { 
        padding-top: 2.2rem !important; 
        padding-bottom: 0rem !important; 
        max-width: 95% !important; 
    }
    .stApp { background-color: #ffffff; }
    
    /* Header Utama - Posisi Aman gak nyundul atap */
    .header-text { 
        text-align: center; 
        width: 100%; 
        margin-top: -25px; 
        margin-bottom: 15px; 
    }

    /* Kotak Metrik - SIMETRIS & ANIMASI HOVER */
    div[data-testid="stMetric"] {
        background-color: #ffffff !important; 
        border: 1px solid #e2e8f0 !important;
        border-left: 5px solid #1e40af !important; 
        padding: 15px !important; 
        border-radius: 12px !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
        
        /* Kunci Simetris sempurna */
        min-height: 125px !important; 
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
        transition: all 0.3s ease-in-out !important;
    }
    
    /* Efek Floating saat Hover */
    div[data-testid="stMetric"]:hover {
        transform: translateY(-5px) !important;
        box-shadow: 0 12px 20px -5px rgba(0, 0, 0, 0.1) !important;
        border-color: #1e40af !important;
        background-color: #fcfdfe !important;
    }

    /* Font Metrics */
    [data-testid="stMetricLabel"] { color: #1e3a8a !important; font-weight: 700 !important; font-size: 0.85rem !important; }
    [data-testid="stMetricValue"] { font-size: 24px !important; font-weight: 800 !important; color: #0f172a !important; }

    /* Summary Bar */
    .summary-box {
        background-color: #f1f5f9 !important; padding: 10px !important; 
        border-radius: 10px !important; margin-bottom: 15px !important; 
        border-left: 5px solid #1e3a8a !important; text-align: center !important;
    }
    .summary-text { font-weight: 850 !important; font-size: 0.95rem !important; color: #0f172a !important; }

    /* Footer Sidebar - Minimalis & Elegan */
    .footer-card {
        margin-top: 50px; padding: 12px; border-radius: 10px; 
        background-color: #f8fafc; border: 1px solid #e2e8f0; 
        text-align: center;
    }
    .dev-name { color: #475569; font-weight: 400; font-size: 0.72rem; margin-top: 2px; display: block; }
    
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIC WAKTU ---
tz_jkt = pytz.timezone('Asia/Jakarta')
sekarang = datetime.now(tz_jkt).replace(tzinfo=None)

# --- 3. SIDEBAR ---
NAMA_FILE_LOGO = "logo-bmkg-transparan.png" 

with st.sidebar:
    if os.path.exists(NAMA_FILE_LOGO):
        # Logo diperkecil (kolom tengah dipersempit biar proporsional)
        _, col_img, _ = st.columns([0.38, 0.24, 0.38])
        with col_img:
            st.image(NAMA_FILE_LOGO, use_container_width=True)
    
    st.markdown("<p style='text-align: center; color: #1e3a8a; margin-top: -10px; font-size: 0.85rem; font-weight: bold;'>STAMAR TANJUNG PRIOK</p>", unsafe_allow_html=True)
    st.divider()
    
    # Filter & Link Ke Web Kantor
    tgl_range = st.date_input("🗓️ Rentang Waktu Grafik", value=(sekarang.date() - timedelta(days=1), sekarang.date() + timedelta(days=2)))
    st.link_button("🌐 Web BMKG Tanjung Priok", "https://bmkgtanjungpriok.info/", use_container_width=True)
    
    st.divider()
    with st.expander("ℹ️ Info Sumber Data"):
        st.caption("""
        **Prediksi:** Analisis Harmonik data TMA Pasar Ikan I (DSDA) 2025.
        **Real-time:** AWS BMKG & Pintu Air Pasar Ikan I (DSDA).
        """)
    
    # Footer - Inisial Nama & Jabatan (Kecil & Rapih)
    st.markdown(f"""
        <div class="footer-card">
            <p style='font-size: 0.7rem; color: #1e3a8a; margin-bottom: 0;'>© 2026 Stamar Tanjung Priok</p>
            <p style='font-size: 0.6rem; color: #64748b; margin-top: 4px;'>
                Developed by <br>
                <span class="dev-name">E.P. Damanik</span>
                <span style='font-style: italic; font-size: 0.6rem;'>Forecaster</span>
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
live_data = {"aws": get_latest_from_csv(FILE_HISTORY_AWS), "bpbd": get_latest_from_csv(FILE_HISTORY_BPBD)}

# --- 7. DISPLAY ---
if df_pred is not None:
    h_now = df_pred.loc[(df_pred[col_tgl] - sekarang).abs().idxmin(), col_val]
    
    # Alert System
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

    # Metrics Layout (DIJAMIN SIMETRIS)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Prediksi Pasut", f"{h_now:.2f} m")
    m2.metric("AWS Tj. Priok", f"{live_data['aws']:.2f} m" if live_data["aws"] else "N/A", delta=f"{(live_data['aws']-h_now):+.2f}m" if live_data['aws'] else None, delta_color="inverse")
    m3.metric("TMA Psr. Ikan", f"{live_data['bpbd']:.2f} m" if live_data["bpbd"] else "N/A", delta=f"{(live_data['bpbd']-h_now):+.2f}m" if live_data["bpbd"] else None, delta_color="inverse")
    
    # Tren
    h_next = df_pred.loc[(df_pred[col_tgl] - (sekarang + timedelta(hours=3))).abs().idxmin(), col_val]
    selisih = h_next - h_now
    icon, status = ("📈", "NAIK") if selisih > 0.05 else ("📉", "TURUN") if selisih < -0.05 else ("↔️", "STAGNAN")
    m4.metric("Tren (3j Kedepan)", f"{icon} {status}")

    # --- PLOTLY CHART ---
    t_start, t_end = datetime.combine(tgl_range[0], datetime.min.time()), datetime.combine(tgl_range[1], datetime.max.time())
    fig = go.Figure()
    df_plot = df_pred[(df_pred[col_tgl] >= t_start) & (df_pred[col_tgl] <= t_end)].copy()
    
    fig.add_trace(go.Scatter(x=df_plot[col_tgl], y=df_plot[col_val], name='Prediksi', line=dict(color='#94a3b8', dash='dot')))
    
    for file, label, color in [(FILE_HISTORY_AWS, 'AWS (Hist)', '#7c3aed'), (FILE_HISTORY_BPBD, 'BPBD (Hist)', '#f59e0b')]:
        if os.path.exists(file):
            dh = pd.read_csv(file); dh['waktu'] = pd.to_datetime(dh['waktu'], format='mixed', errors='coerce')
            dh = dh[(dh['waktu'] >= t_start) & (dh['waktu'] <= t_end)].sort_values('waktu')
            fig.add_trace(go.Scatter(x=dh['waktu'], y=dh['nilai'], name=label, connectgaps=True, line=dict(color=color, width=3)))

    fig.add_vline(x=sekarang, line_width=2, line_dash="dash", line_color="#22c55e")
    fig.add_hline(y=2.5, line_dash="dash", line_color="#ef4444", annotation_text="AWAS")
    fig.add_hline(y=2.3, line_dash="dash", line_color="#ea580c", annotation_text="WASPADA")
    
    fig.update_layout(height=450, template="plotly_white", margin=dict(l=10, r=10, t=10, b=10), hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    st.plotly_chart(fig, use_container_width=True)

    # Footer Action Buttons
    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1: st.download_button("📥 AWS CSV", open(FILE_HISTORY_AWS, 'rb') if os.path.exists(FILE_HISTORY_AWS) else "", "aws.csv", use_container_width=True)
    with c2: st.download_button("📥 BPBD CSV", open(FILE_HISTORY_BPBD, 'rb') if os.path.exists(FILE_HISTORY_BPBD) else "", "bpbd.csv", use_container_width=True)
    with c3: 
        if st.button("🔄 Refresh Data", use_container_width=True): st.cache_data.clear(); st.rerun()
else:
    st.error("Gagal memuat data prediksi.")
