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
st.set_page_config(page_title="Monitoring Pasut Tg. Priok", layout="wide", page_icon="🌊")

st.markdown("""
    <style>
    /* Reset & Base */
    .stApp { background-color: #ffffff; }
    
    /* --- CSS UNTUK ALERT AGAR TIDAK NABRAK DI HP --- */
    /* Target khusus st.warning di area utama */
    [data-testid="stMain"] [data-testid="stNotificationContentWarning"] {
        background-color: #FF8C00 !important;
        color: #000000 !important;
        border-radius: 8px !important;
        padding: 10px !important;
    }
    
    /* Target khusus st.error di area utama */
    [data-testid="stMain"] [data-testid="stNotificationContentError"] {
        background-color: #FF4B4B !important;
        color: #000000 !important;
        border-radius: 8px !important;
        padding: 10px !important;
    }

    /* Pastikan teks di dalam alert (p tag) selalu hitam dan pas ukurannya */
    [data-testid="stMain"] [data-testid="stNotificationContentWarning"] p,
    [data-testid="stMain"] [data-testid="stNotificationContentError"] p {
        color: #000000 !important;
        font-weight: 800 !important;
        margin: 0 !important;
        font-size: 1rem !important;
    }

    /* --- SIDEBAR TETAP BIRU (ST.INFO) --- */
    [data-testid="stSidebar"] [data-testid="stNotificationContentInfo"] {
        background-color: rgba(0, 104, 201, 0.1) !important;
    }

    /* Metric Styling agar rapi di Mobile */
    [data-testid="stMetricLabel"] { color: #1e3a8a !important; font-weight: 700 !important; }
    div[data-testid="stMetric"] {
        background-color: #f8fafc !important; 
        border-left: 5px solid #1e40af !important; 
        border-radius: 10px !important;
        padding: 10px !important;
    }
    
    .summary-box {
        background-color: #f1f5f9; padding: 10px; 
        border-radius: 10px; border-left: 5px solid #1e3a8a; 
        text-align: center; margin-bottom: 10px;
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
    st.divider()
    
    st.write("🔔 **Notifikasi**")
    if st.button("🔊 Tes Suara"):
        st.success("Audio Siap!")
    
    # Ini akan tetap Biru karena CSS target stMain
    st.info("Data Prediksi ditarik dari Excel. Update tiap 15 menit.")

# --- 4. HEADER ---
st.markdown("<h2 style='text-align: center; color: #0f172a;'>STASIUN METEOROLOGI MARITIM TANJUNG PRIOK</h2>", unsafe_allow_html=True)
st.divider()

# --- 5. DATA FUNCTIONS ---
FILE_PREDIKSI = 'prediksi_pasut_ancol_2026_FINAL_WIB.xlsx'
FILE_HISTORY_AWS = 'history_aws_priok.csv' 
FILE_HISTORY_BPBD = 'history_bpbd_pasarikan.csv'

def play_audio(file_path):
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            data = f.read()
            b64 = base64.b64encode(data).decode()
            audio_html = f'<audio autoplay="true"><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>'
            st.components.v1.html(audio_html, height=0)

def get_latest_from_csv(file_path):
    if not os.path.exists(file_path): return None
    try:
        df = pd.read_csv(file_path)
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
    
    # ALERT LOGIC
    check_values = {"Prediksi": h_now, "AWS": live_data['aws'], "BPBD": live_data['bpbd']}
    awas = [n for n, v in check_values.items() if v is not None and v >= 2.5]
    waspada = [n for n, v in check_values.items() if v is not None and 2.3 <= v < 2.5]

    if awas:
        st.error(f"🚨 STATUS: AWAS ROB! ({', '.join(awas)})")
        play_audio("AWAS ROB.mp3") 
    elif waspada:
        st.warning(f"⚠️ STATUS: WASPADA ROB! ({', '.join(waspada)})")
        play_audio("waspada ROB.mp3")

    # Summary Box
    df_h = df_pred[df_pred[col_tgl].dt.date == sekarang.date()]
    if not df_h.empty:
        val_max = df_h[col_val].max()
        jam_max = df_h.loc[df_h[col_val].idxmax(), col_tgl].strftime("%H:%M")
        st.markdown(f'<div class="summary-box"><b>📅 {sekarang.strftime("%d %b %Y")} | <span style="color:red">▲ MAX: {val_max:.2f}m ({jam_max})</span></b></div>', unsafe_allow_html=True)

    # Metrics
    m1, m2, m3, m4 = st.columns([1,1,1,1])
    m1.metric("Prediksi", f"{h_now:.2f} m")
    m2.metric("AWS Priok", f"{live_data['aws']:.2f} m" if live_data['aws'] else "N/A")
    m3.metric("TMA P.Ikan", f"{live_data['bpbd']:.2f} m" if live_data['bpbd'] else "N/A")
    
    # Tren 3 Jam
    h_next = df_pred.loc[(df_pred[col_tgl] - (sekarang + timedelta(hours=3))).abs().idxmin(), col_val]
    tren = "📈 NAIK" if h_next - h_now > 0.05 else ("📉 TURUN" if h_next - h_now < -0.05 else "↔️ STAGNAN")
    m4.metric("Tren", tren)

    # --- PLOTLY CHART ---
    t_start = datetime.combine(tgl_range[0], datetime.min.time())
    t_end = datetime.combine(tgl_range[1], datetime.max.time())
    df_plot = df_pred[(df_pred[col_tgl] >= t_start) & (df_pred[col_tgl] <= t_end)]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_plot[col_tgl], y=df_plot[col_val], name='Prediksi', line=dict(color='gray', dash='dot')))
    
    if live_data['aws']:
        # Dummy history plot logic for AWS if file exists
        pass 

    fig.add_vline(x=sekarang, line_width=2, line_dash="dash", line_color="green")
    fig.update_layout(height=450, template="plotly_white", margin=dict(l=0, r=0, t=30, b=0))
    st.plotly_chart(fig, use_container_width=True)

    # Footer
    if st.button("🔄 Force Refresh"):
        st.cache_data.clear()
        st.rerun()
else:
    st.error("Data tidak ditemukan.")
