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
    .stApp { background-color: #ffffff; }
    .header-text { text-align: center; width: 100%; }
    
    /* --- FIX CSS: HANYA TARGET ALERT DI BAGIAN UTAMA (MAIN) --- */
    
    /* Waspada (Warning) jadi Orange - Hanya di Main Area */
    [data-testid="stMain"] div[data-testid="stNotificationContentWarning"] {
        background-color: #FF8C00 !important; 
        border-radius: 10px !important;
        border: none !important;
    }
    [data-testid="stMain"] div[data-testid="stNotificationContentWarning"] p {
        color: #000000 !important;
        font-weight: 850 !important;
    }

    /* Awas (Error) jadi Merah - Hanya di Main Area */
    [data-testid="stMain"] div[data-testid="stNotificationContentError"] {
        background-color: #FF4B4B !important; 
        border-radius: 10px !important;
        border: none !important;
    }
    [data-testid="stMain"] div[data-testid="stNotificationContentError"] p {
        color: #000000 !important;
        font-weight: 850 !important;
    }

    /* Icon Alert jadi Hitam */
    [data-testid="stMain"] [data-testid="stNotificationContentWarning"] svg,
    [data-testid="stMain"] [data-testid="stNotificationContentError"] svg {
        fill: #000000 !important;
    }

    /* --- SIDEBAR INFO TETAP BIRU ASLI --- */
    [data-testid="stSidebar"] div[data-testid="stNotification"] {
        background-color: transparent !important;
    }

    /* Metric & Box Style */
    [data-testid="stMetricLabel"] { opacity: 1 !important; color: #1e3a8a !important; font-weight: 700 !important; }
    [data-testid="stMetricValue"] { font-size: 24px !important; font-weight: 850 !important; color: #0f172a !important; }
    div[data-testid="stMetric"] {
        background-color: #f8fafc !important; 
        border: 1px solid #e2e8f0 !important;
        border-left: 5px solid #1e40af !important; 
        padding: 15px !important; 
        border-radius: 10px !important;
        min-height: 130px !important; 
        display: flex; flex-direction: column; justify-content: center;
    }
    .summary-box {
        background-color: #f1f5f9 !important; padding: 12px !important; 
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

# --- 3. SIDEBAR ---
with st.sidebar:
    st.subheader("🗓️ Filter Grafik")
    tgl_range = st.date_input("Rentang Waktu", value=(sekarang.date() - timedelta(days=1), sekarang.date() + timedelta(days=2)))
    st.divider()
    
    st.write("🔔 **Pengaturan Suara**")
    if st.button("🔊 Aktifkan Notifikasi Suara"):
        st.success("Audio Siap!")
    
    st.info("Data Prediksi ditarik dari Excel. Data History disuplai otomatis tiap 15 menit.")

# --- 4. HEADER ---
NAMA_FILE_LOGO = "logo-bmkg-transparan.png" 
c1, c2, c3 = st.columns([1, 0.4, 1])
with c2:
    if os.path.exists(NAMA_FILE_LOGO):
        st.image(NAMA_FILE_LOGO, use_container_width=True)

st.markdown(f"""
    <div class="header-text">
        <h2 style="margin: 0; color: #0f172a; font-weight: bold; font-size: 1.5rem;">STASIUN METEOROLOGI MARITIM TANJUNG PRIOK</h2>
        <p style="color: #1e40af; font-weight: 700; margin-top: 5px;">Monitoring Tinggi Muka Air (TMA) Real-Time</p>
    </div>
    """, unsafe_allow_html=True)
st.divider()

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
            audio_html = f'''
                <audio autoplay="true">
                    <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
                </audio>
            '''
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
    
    check_values = {"Prediksi": h_now, "AWS": live_data['aws'], "BPBD": live_data['bpbd']}
    awas = [n for n, v in check_values.items() if v is not None and v >= 2.5]
    waspada = [n for n, v in check_values.items() if v is not None and 2.3 <= v < 2.5]

    if awas:
        st.error(f"🚨 STATUS: AWAS ROB! ({', '.join(awas)})", icon="⚠️")
        play_audio("AWAS ROB.mp3") 
    elif waspada:
        st.warning(f"⚠️ STATUS: WASPADA ROB! ({', '.join(waspada)})", icon="📢")
        play_audio("waspada ROB.mp3")

    # Summary Today
    df_h = df_pred[df_pred[col_tgl].dt.date == sekarang.date()]
    if not df_h.empty:
        val_max, jam_max = df_h[col_val].max(), df_h.loc[df_h[col_val].idxmax(), col_tgl].strftime("%H:%M")
        val_min, jam_min = df_h[col_val].min(), df_h.loc[df_h[col_val].idxmin(), col_tgl].strftime("%H:%M")
        st.markdown(f'<div class="summary-box"><span class="summary-text">📅 {sekarang.strftime("%d %b %Y")} | <span style="color: #ef4444;">▲ MAX: {val_max:.2f}m ({jam_max})</span> | <span style="color: #3b82f6;">▼ MIN: {val_min:.2f}m ({jam_min})</span></span></div>', unsafe_allow_html=True)

    # Metrics
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Prediksi Pasut (TMA psr. ikan 2025)", f"{h_now:.2f} m")
    m2.metric("TMA AWS Tj. Priok", f"{live_data['aws']:.2f} m" if live_data["aws"] else "N/A", delta=f"{(live_data['aws'] - h_now):+.2f} m dr prediksi" if live_data['aws'] else None, delta_color="inverse")
    m3.metric("TMA Psr. Ikan", f"{live_data['bpbd']:.2f} m" if live_data["bpbd"] else "N/A", delta=f"{(live_data['bpbd'] - h_now):+.2f} m dr prediksi" if live_data['bpbd'] else None, delta_color="inverse")
    
    # Tren Logika
    waktu_target = sekarang + timedelta(hours=3)
    h_next = df_pred.loc[(df_pred[col_tgl] - waktu_target).abs().idxmin(), col_val]
    selisih = h_next - h_now
    threshold = 0.05 

    if abs(selisih) < threshold:
        tren_status = "↔️ STAGNAN"
    elif selisih > 0:
        tren_status = "📈 LEVEL AIR NAIK"
    else:
        tren_status = "📉 LEVEL AIR TURUN"
    
    m4.metric("Tren", tren_status)

    # --- PLOTLY CHART ---
    t_start, t_end = datetime.combine(tgl_range[0], datetime.min.time()), datetime.combine(tgl_range[1], datetime.max.time())
    fig = go.Figure()
    df_plot = df_pred[(df_pred[col_tgl] >= t_start) & (df_pred[col_tgl] <= t_end)].copy()
    
    fig.add_trace(go.Scatter(x=df_plot[col_tgl], y=df_plot[col_val], name='Prediksi', line=dict(color='#64748b', dash='dot')))
    
    df_plot['tgl_saja'] = df_plot[col_tgl].dt.date
    for tgl in df_plot['tgl_saja'].unique():
        df_tgl = df_plot[df_plot['tgl_saja'] == tgl]
        p_max = df_tgl.loc[df_tgl[col_val].idxmax()]
        fig.add_trace(go.Scatter(x=[p_max[col_tgl]], y=[p_max[col_val]], mode='markers+text', text=[f"<b>{p_max[col_val]:.2f}</b>"], textposition="top center", marker=dict(color='red', size=8, symbol='diamond'), showlegend=False))
        p_min = df_tgl.loc[df_tgl[col_val].idxmin()]
        fig.add_trace(go.Scatter(x=[p_min[col_tgl]], y=[p_min[col_val]], mode='markers+text', text=[f"<b>{p_min[col_val]:.2f}</b>"], textposition="bottom center", marker=dict(color='blue', size=8, symbol='diamond'), showlegend=False))

    if os.path.exists(FILE_HISTORY_AWS):
        dh_a = pd.read_csv(FILE_HISTORY_AWS); dh_a['waktu'] = pd.to_datetime(dh_a['waktu'], format='mixed', errors='coerce')
        dh_a = dh_a[(dh_a['waktu'] >= t_start) & (dh_a['waktu'] <= t_end) & (dh_a['nilai'] <= LIMIT_SENSOR_ERROR)].sort_values('waktu')
        fig.add_trace(go.Scatter(x=dh_a['waktu'], y=dh_a['nilai'], name='AWS (History)', mode='lines+markers', line=dict(color='#7c3aed', width=3)))

    if os.path.exists(FILE_HISTORY_BPBD):
        dh_b = pd.read_csv(FILE_HISTORY_BPBD); dh_b['waktu'] = pd.to_datetime(dh_b['waktu'], format='mixed', errors='coerce')
        dh_b = dh_b[(dh_b['waktu'] >= t_start) & (dh_b['waktu'] <= t_end) & (dh_b['nilai'] <= LIMIT_SENSOR_ERROR)].sort_values('waktu')
        fig.add_trace(go.Scatter(x=dh_b['waktu'], y=dh_b['nilai'], name='BPBD (History)', mode='lines+markers', line=dict(color='#f59e0b', width=3)))

    fig.add_vline(x=sekarang, line_width=2, line_dash="dash", line_color="green")
    
    teks_waktu = f"<b>Saat Ini ({sekarang.strftime('%d %b, %H:%M')} WIB)</b>"
    fig.add_annotation(x=sekarang, y=1, yref="paper", text=teks_waktu, showarrow=False, font=dict(color="green", size=12), xanchor="left", xshift=5)
    
    fig.add_hline(y=2.5, line_dash="dash", line_color="#ef4444", annotation_text="<b>AWAS ROB</b>")
    fig.add_hline(y=2.3, line_dash="dash", line_color="#ea580c", annotation_text="<b>WASPADA</b>")
    fig.update_layout(height=550, template="plotly_white", margin=dict(l=10, r=10, t=40, b=10), hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

    # Footer
    st.divider()
    f1, f2, f3 = st.columns(3)
    with f1:
        if os.path.exists(FILE_HISTORY_AWS): st.download_button("📥 Download AWS", open(FILE_HISTORY_AWS, 'rb'), "history_aws.csv", "text/csv", use_container_width=True)
    with f2:
        if os.path.exists(FILE_HISTORY_BPBD): st.download_button("📥 Download TMA PSR. IKAN", open(FILE_HISTORY_BPBD, 'rb'), "history_bpbd.csv", "text/csv", use_container_width=True)
    with f3: 
        if st.button("🔄 Force Refresh", use_container_width=True): st.cache_data.clear(); st.rerun()
else:
    st.error("Data prediksi tidak ditemukan atau format kolom Excel salah.")
