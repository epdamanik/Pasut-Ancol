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
    /* 1. Merapatkan container utama ke paling atas layar */
    .block-container { 
        padding-top: 0rem !important; 
        padding-bottom: 0rem !important; 
        max-width: 95% !important; 
    }
    
    /* 2. Menghilangkan spasi antar elemen default Streamlit */
    [data-testid="stVerticalBlock"] > div {
        gap: 0rem !important;
    }

    .stApp { background-color: #ffffff; }
    
    /* 3. Header Utama (Sangat Rapat) */
    .header-text { 
        text-align: center; 
        width: 100%; 
        margin-top: -10px; 
        margin-bottom: 0px; 
        padding-bottom: 0px;
    }

    /* 4. Summary Box (Ditarik ke atas pepet header) */
    .summary-box {
        background-color: #f1f5f9 !important; 
        padding: 6px !important; 
        border-radius: 8px !important; 
        margin-top: -5px !important; 
        margin-bottom: 8px !important; 
        border-left: 5px solid #1e3a8a !important; 
        text-align: center !important;
    }
    .summary-text { font-weight: 850 !important; font-size: 0.9rem !important; color: #0f172a !important; }

    /* 5. Metrik (Sangat Ramping) */
    div[data-testid="stMetric"] {
        background-color: #ffffff !important; 
        border: 1px solid #e2e8f0 !important;
        border-left: 4px solid #1e40af !important; 
        padding: 2px 8px !important; 
        border-radius: 8px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
        min-height: 50px !important; 
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
    }
    
    div[data-testid="stMetricLabel"] { 
        color: #1e3a8a !important; 
        font-weight: 700 !important; 
        font-size: 0.65rem !important; 
        margin-bottom: -12px !important; 
    }

    [data-testid="stMetricValue"] { 
        font-size: 14px !important; 
        font-weight: 800 !important; 
        color: #0f172a !important; 
    }

    div[data-testid="stMetricDelta"] { display: none !important; }
    div[data-testid="column"] { padding: 0 2px !important; }

    /* Sidebar Logo Center */
    [data-testid="stSidebar"] [data-testid="stImage"] {
        text-align: center !important;
        display: block !important;
        margin: 0 auto !important;
    }

    .footer-card {
        margin-top: 20px; padding: 10px; border-radius: 10px; 
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
                <img src="data:image/png;base64,{encoded}" style="width: 80px; height: auto;">
            </div>
            """,
            unsafe_allow_html=True
        )
    
    st.markdown("<p style='text-align: center; color: #1e3a8a; margin-top: -5px; font-size: 0.8rem; font-weight: bold;'>STASIUN METEOROLOGI MARITIM TANJUNG PRIOK</p>", unsafe_allow_html=True)
    st.divider()
    
    tgl_range = st.date_input("🗓️ Rentang Waktu Grafik", value=(sekarang.date() - timedelta(days=1), sekarang.date() + timedelta(days=2)))
    st.link_button("🌐 Web BMKG Tanjung Priok", "https://bmkgtanjungpriok.info/", use_container_width=True)
    
    with st.expander("ℹ️ Info Sumber Data"):
        st.markdown("<div style='font-size: 0.85rem; color: #475569;'><strong>📍 Prediksi:</strong> Harmonik 2025.<br><strong>⚡ Real-time:</strong> AWS BMKG & DSDA.</div>", unsafe_allow_html=True)
    
    st.markdown(f"""
        <div class="footer-card">
            <p style='font-size: 0.65rem; color: #1e3a8a; margin-bottom: 0; font-weight: 600;'>© 2026 BMKG Tanjung Priok</p>
        </div>
        <div style="text-align: center; margin-top: 10px;">
            <p style='font-size: 0.45rem; color: #94a3b8; margin: 0;'>Dev by E.P. Damanik</p>
        </div>
    """, unsafe_allow_html=True)

# --- 4. HEADER UTAMA ---
st.markdown(f"""
    <div class="header-text">
        <h2 style="margin: 0; color: #0f172a; font-weight: bold; font-size: 1.4rem;">
            MONITORING TINGGI MUKA AIR (TMA) REAL TIME
        </h2>
    </div>
    """, unsafe_allow_html=True)

# --- 5. DATA LOADING ---
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

# --- 7. DISPLAY ---
if df_pred is not None and not df_pred.empty:
    h_now = df_pred.loc[(df_pred[col_tgl] - sekarang_naive).abs().idxmin(), col_val]

    # --- SUMMARY BOX ---
    df_h = df_pred[df_pred[col_tgl].dt.date == sekarang.date()]
    if not df_h.empty:
        idx_max = df_h[col_val].idxmax()
        idx_min = df_h[col_val].idxmin()
        st.markdown(f"""
            <div class="summary-box">
                <span class="summary-text">
                    📅 {sekarang.strftime("%d %b %Y")} | 
                    <span style="color: #ef4444;">▲ MAX: {df_h.loc[idx_max, col_val]:.2f}m ({df_h.loc[idx_max, col_tgl].strftime("%H:%M")})</span> | 
                    <span style="color: #3b82f6;">▼ MIN: {df_h.loc[idx_min, col_val]:.2f}m ({df_h.loc[idx_min, col_tgl].strftime("%H:%M")})</span>
                </span>
            </div>
        """, unsafe_allow_html=True)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Prediksi Pasut", f"{h_now:.2f} m")
    
    if live_data['aws']:
        d_aws = live_data['aws'] - h_now
        m2.metric("AWS Tj. Priok", f"{live_data['aws']:.2f} m {'🔺' if d_aws > 0 else '🔹'}({d_aws:+.2f})")
    else: m2.metric("AWS Tj. Priok", "N/A")

    if live_data['bpbd']:
        d_bpbd = live_data['bpbd'] - h_now
        m3.metric("TMA Psr. Ikan", f"{live_data['bpbd']:.2f} m {'🔺' if d_bpbd > 0 else '🔹'}({d_bpbd:+.2f})")
    else: m3.metric("TMA Psr. Ikan", "N/A")
    
    h_next = df_pred.loc[(df_pred[col_tgl] - (sekarang_naive + timedelta(hours=3))).abs().idxmin(), col_val]
    selisih = h_next - h_now
    icon = "📈" if selisih > 0.05 else "📉" if selisih < -0.05 else "↔️"
    m4.metric("Tren (3j)", f"{icon} {'NAIK' if selisih > 0.05 else 'TURUN' if selisih < -0.05 else 'STAGNAN'}")

    # --- PLOTLY CHART ---
    t_start, t_end = datetime.combine(tgl_range[0], datetime.min.time()), datetime.combine(tgl_range[1], datetime.max.time())
    df_plot = df_pred[(df_pred[col_tgl] >= t_start) & (df_pred[col_tgl] <= t_end)].copy()
    
    if not df_plot.empty:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=df_plot[col_tgl], y=df_plot[col_val], name='Prediksi', mode='lines', line=dict(color='rgba(148, 163, 184, 0.7)', dash='dot', width=2)))
        
        # History
        for file, label, color in [(FILE_HISTORY_AWS, 'AWS', '#7c3aed'), (FILE_HISTORY_BPBD, 'Pasar Ikan', '#f59e0b')]:
            if os.path.exists(file):
                dh = pd.read_csv(file)
                dh['waktu'] = pd.to_datetime(dh['waktu'], format='mixed', errors='coerce')
                dh = dh[(dh['waktu'] >= t_start) & (dh['waktu'] <= t_end)].sort_values('waktu')
                if not dh.empty:
                    fig.add_trace(go.Scatter(x=dh['waktu'], y=dh['nilai'], name=label, line=dict(color=color, width=3)))

        fig.update_layout(height=450, template="plotly_white", margin=dict(l=5, r=5, t=10, b=5), hovermode="x unified", legend=dict(orientation="h", y=1.05))
        st.plotly_chart(fig, use_container_width=True)

    c1, c2, c3 = st.columns(3)
    with c3: 
        if st.button("🔄 Refresh", use_container_width=True): st.cache_data.clear(); st.rerun()
else:
    st.error("Gagal memuat data.")
