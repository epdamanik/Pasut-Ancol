import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pytz
from streamlit_autorefresh import st_autorefresh
import os
import base64

# --- 0. SMART AUTO REFRESH ---
now_sync = datetime.now()
seconds_to_next = ((15 - (now_sync.minute % 15)) * 60) - now_sync.second
if seconds_to_next <= 0: seconds_to_next = 900
st_autorefresh(interval=seconds_to_next * 1000, key="datarefresh")

# --- 1. KONFIGURASI HALAMAN & CSS (ULTRA COMPACT) ---
st.set_page_config(page_title="Monitoring TMA Priok", layout="wide", page_icon="🌊")

st.markdown("""
    <style>
    .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; max-width: 98% !important; }
    .stApp { background-color: #ffffff; }
    .header-text { text-align: center; width: 100%; margin-top: -45px; margin-bottom: 5px; }

    /* METRIK 2 BARIS & MEPET */
    div[data-testid="stMetric"] {
        background-color: #ffffff !important; border: 1px solid #e2e8f0 !important;
        border-left: 4px solid #1e40af !important; padding: 2px 10px !important; 
        border-radius: 8px !important; min-height: 45px !important; 
        display: flex !important; flex-direction: column !important; justify-content: center !important;
    }
    div[data-testid="stMetricLabel"] { color: #1e3a8a !important; font-weight: 700 !important; font-size: 0.75rem !important; margin-bottom: -15px !important; }
    div[data-testid="stMetricValue"] { font-size: 16px !important; font-weight: 800 !important; color: #0f172a !important; }
    div[data-testid="stMetricDelta"] { display: none !important; }

    .summary-box {
        background-color: #f1f5f9 !important; padding: 4px !important; border-radius: 6px !important; 
        margin-bottom: 8px !important; border-left: 5px solid #1e3a8a !important; text-align: center !important;
    }
    .summary-text { font-weight: 800 !important; font-size: 0.85rem !important; color: #0f172a !important; }
    
    /* SIDEBAR STYLING */
    .footer-card { margin-top: 20px; padding: 10px; border-radius: 8px; background-color: #f8fafc; text-align: center; border: 1px solid #e2e8f0; }
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIC WAKTU ---
tz_jkt = pytz.timezone('Asia/Jakarta')
sekarang = datetime.now(tz_jkt)
sekarang_naive = sekarang.replace(tzinfo=None)

# --- 3. DATA FUNCTIONS ---
FILE_PREDIKSI, FILE_AWS, FILE_BPBD = 'prediksi_pasut_ancol_2026_FINAL_WIB.xlsx', 'history_aws_priok.csv', 'history_bpbd_pasarikan.csv'

def play_audio(file_path):
    if os.path.exists(file_path):
        with open(file_path, "rb") as f:
            b64 = base64.b64encode(f.read()).decode()
            st.components.v1.html(f'<audio autoplay><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>', height=0)

def get_latest(file_path):
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

# --- 4. SIDEBAR (LOGOS & INFO) ---
with st.sidebar:
    st.markdown("<p style='text-align: center; color: #1e3a8a; font-weight: bold;'>STASIUN METEOROLOGI MARITIM TANJUNG PRIOK</p>", unsafe_allow_html=True)
    tgl_range = st.date_input("🗓️ Rentang Grafik", value=(sekarang.date() - timedelta(days=1), sekarang.date() + timedelta(days=2)))
    st.link_button("🌐 Web BMKG", "https://bmkgtanjungpriok.info/", use_container_width=True)
    with st.expander("ℹ️ Info"):
        st.write("Prediksi: Harmonik 2025. Real-time: BMKG & DSDA.")
    st.markdown('<div class="footer-card"><p style="font-size: 0.7rem; color: #1e3a8a; font-weight: 600; margin:0;">© 2026 BMKG Priok<br><span style="font-size: 0.5rem; font-weight:400;">Dev: E.P. Damanik</span></p></div>', unsafe_allow_html=True)

# --- 5. DISPLAY ---
st.markdown('<div class="header-text"><h2 style="margin: 0; font-size: 1.3rem; font-weight: bold;">MONITORING TMA REAL TIME</h2></div>', unsafe_allow_html=True)

df_pred, col_tgl, col_val = load_prediction()
val_aws, val_bpbd = get_latest(FILE_AWS), get_latest(FILE_BPBD)

if df_pred is not None and not df_pred.empty:
    h_now = df_pred.loc[(df_pred[col_tgl] - sekarang_naive).abs().idxmin(), col_val]
    
    # AUDIO ALERT
    check = {"Prediksi": h_now, "AWS": val_aws, "PASAR IKAN": val_bpbd}
    if any(v and v >= 2.5 for v in check.values()):
        st.error("🚨 STATUS: AWAS ROB!", icon="⚠️"); play_audio("AWAS ROB.mp3")
    elif any(v and 2.3 <= v < 2.5 for v in check.values()):
        st.warning("📢 STATUS: WASPADA ROB!", icon="📢"); play_audio("waspada ROB.mp3")

    # SUMMARY BOX + JAM
    df_h = df_pred[df_pred[col_tgl].dt.date == sekarang.date()]
    if not df_h.empty:
        idx_max, idx_min = df_h[col_val].idxmax(), df_h[col_val].idxmin()
        st.markdown(f'<div class="summary-box"><span class="summary-text">📅 {sekarang.strftime("%d %b %Y")} | <span style="color: #ef4444;">▲ MAX: {df_h.loc[idx_max, col_val]:.2f}m ({df_h.loc[idx_max, col_tgl].strftime("%H:%M")})</span> | <span style="color: #3b82f6;">▼ MIN: {df_h.loc[idx_min, col_val]:.2f}m ({df_h.loc[idx_min, col_tgl].strftime("%H:%M")})</span></span></div>', unsafe_allow_html=True)

    # METRIKS (Sesuai Permintaan: 2 Baris, Selisih di samping nilai)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Prediksi", f"{h_now:.2f} m")
    m2.metric("AWS Tj. Priok", f"{val_aws:.2f} m ({(val_aws-h_now):+.2f})" if val_aws else "N/A")
    m3.metric("TMA Psr. Ikan", f"{val_bpbd:.2f} m ({(val_bpbd-h_now):+.2f})" if val_bpbd else "N/A")
    h_next = df_pred.loc[(df_pred[col_tgl] - (sekarang_naive + timedelta(hours=3))).abs().idxmin(), col_val]
    icon = "📈" if (h_next - h_now) > 0.05 else "📉" if (h_next - h_now) < -0.05 else "↔️"
    m4.metric("Tren (3j)", f"{icon} {'NAIK' if icon=='📈' else 'TURUN' if icon=='📉' else 'STAGNAN'}")

    # CHART
    t_start, t_end = datetime.combine(tgl_range[0], datetime.min.time()), datetime.combine(tgl_range[1], datetime.max.time())
    df_plot = df_pred[(df_pred[col_tgl] >= t_start) & (df_pred[col_tgl] <= t_end)].copy()
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_plot[col_tgl], y=df_plot[col_val], name='Prediksi', mode='lines+markers', marker=dict(size=3), line=dict(color='#94a3b8', dash='dot', width=1.5)))
    for f, l, c in [(FILE_AWS, 'AWS', '#7c3aed'), (FILE_BPBD, 'Psr. Ikan', '#f59e0b')]:
        if os.path.exists(f):
            dh = pd.read_csv(f); dh['waktu'] = pd.to_datetime(dh['waktu'], format='mixed', errors='coerce')
            dh = dh[(dh['waktu'] >= t_start) & (dh['waktu'] <= t_end)].sort_values('waktu')
            fig.add_trace(go.Scatter(x=dh['waktu'], y=dh['nilai'], name=l, line=dict(color=c, width=2.5)))
    fig.add_vline(x=sekarang_naive, line_width=2, line_dash="dash", line_color="#22c55e")
    fig.add_hline(y=2.3, line_dash="dash", line_color="#ea580c", annotation_text="2.3 Waspada")
    fig.add_hline(y=2.5, line_dash="dash", line_color="#ef4444", annotation_text="2.5 Awas")
    fig.update_layout(height=380, margin=dict(l=5, r=5, t=10, b=5), template="plotly_white", legend=dict(orientation="h", y=1.05))
    st.plotly_chart(fig, use_container_width=True)

    # TOMBOL DOWNLOAD & REFRESH (YANG TADI ILANG)
    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1: st.download_button("📥 AWS CSV", open(FILE_AWS, 'rb') if os.path.exists(FILE_AWS) else b"", "AWS.csv", use_container_width=True)
    with c2: st.download_button("📥 Psr Ikan CSV", open(FILE_BPBD, 'rb') if os.path.exists(FILE_BPBD) else b"", "Pasarikan.csv", use_container_width=True)
    with c3: 
        if st.button("🔄 Refresh Data", use_container_width=True): st.cache_data.clear(); st.rerun()
else:
    st.error("Data prediksi tidak ditemukan.")
