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

# --- 1. KONFIGURASI HALAMAN & CSS ---
st.set_page_config(page_title="Monitoring TMA Priok", layout="wide", page_icon="🌊")

st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem !important; padding-bottom: 0rem !important; max-width: 95% !important; }
    .stApp { background-color: #ffffff; }
    .header-text { text-align: center; width: 100%; margin-top: -20px; margin-bottom: 5px; }

    /* --- SIDEBAR LOGO --- */
    [data-testid="stSidebar"] [data-testid="stImage"] { text-align: center !important; display: block !important; margin: 0 auto !important; width: 100% !important; }

    /* --- METRIK RAMPING (PASTI 2 BARIS) --- */
    div[data-testid="stMetric"] {
        background-color: #ffffff !important; 
        border: 1px solid #e2e8f0 !important;
        border-left: 5px solid #1e40af !important; 
        padding: 5px 12px !important; 
        border-radius: 10px !important;
        min-height: 70px !important; 
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
    }

    /* BARIS 1: Label */
    [data-testid="stMetricLabel"] { 
        color: #1e3a8a !important; 
        font-weight: 700 !important; 
        font-size: 0.75rem !important; 
        margin-bottom: -15px !important;
    }

    /* BARIS 2: Paksa Nilai & Delta Sejajar */
    [data-testid="stMetricValue"] { 
        font-size: 20px !important; 
        font-weight: 800 !important; 
        color: #0f172a !important; 
        display: flex !important; 
        flex-direction: row !important; /* Paksa horizontal */
        align-items: baseline !important;
        gap: 8px !important; /* Jarak antara angka dan delta */
    }

    /* Styling Delta agar lebih kecil di samping */
    [data-testid="stMetricDelta"] { 
        font-size: 14px !important; 
        font-weight: 600 !important; 
        display: inline-block !important;
    }

    /* --- SUMMARY BOX --- */
    .summary-box {
        background-color: #f1f5f9 !important; padding: 6px !important; 
        border-radius: 8px !important; margin-bottom: 8px !important; 
        border-left: 5px solid #1e3a8a !important; text-align: center !important;
    }
    .summary-text { font-weight: 800 !important; font-size: 0.85rem !important; color: #0f172a !important; }

    .footer-card { margin-top: 20px; padding: 10px; border-radius: 10px; background-color: #f8fafc; border: 1px solid #e2e8f0; text-align: center; }
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
        st.markdown(f'<div style="text-align: center;"><img src="data:image/png;base64,{encoded}" style="width: 80px;"></div>', unsafe_allow_html=True)
    
    st.markdown("<p style='text-align: center; color: #1e3a8a; font-size: 0.8rem; font-weight: bold;'>STASIUN METEOROLOGI MARITIM<br>TANJUNG PRIOK</p>", unsafe_allow_html=True)
    st.divider()
    tgl_range = st.date_input("🗓️ Rentang Grafik", value=(sekarang.date() - timedelta(days=1), sekarang.date() + timedelta(days=2)))
    st.link_button("🌐 Web BMKG Tanjung Priok", "https://bmkgtanjungpriok.info/", use_container_width=True)
    
    with st.expander("ℹ️ Info Sumber Data"):
        st.markdown("<div style='font-size: 0.85rem; color: #475569;'><strong>📍 Prediksi:</strong> Harmonik TMA Pasar Ikan 2025.<br><strong>⚡ Real-time:</strong> AWS BMKG & DSDA Jakarta.</div>", unsafe_allow_html=True)

    st.markdown(f'<div class="footer-card"><p style="font-size: 0.65rem; color: #1e3a8a; margin: 0;">© 2026 BMKG Tanjung Priok</p></div>', unsafe_allow_html=True)

# --- 4. HEADER ---
st.markdown('<div class="header-text"><h2 style="margin: 0; color: #0f172a; font-weight: bold; font-size: 1.4rem;">MONITORING TMA REAL TIME</h2></div>', unsafe_allow_html=True)

# --- 5. DATA FUNCTIONS ---
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

# --- 6. EXECUTION ---
df_pred, col_tgl, col_val = load_prediction()
live_aws = get_latest_from_csv(FILE_HISTORY_AWS)
live_bpbd = get_latest_from_csv(FILE_HISTORY_BPBD)

# --- 7. DISPLAY ---
if df_pred is not None and not df_pred.empty:
    h_now = df_pred.loc[(df_pred[col_tgl] - sekarang_naive).abs().idxmin(), col_val]
    
    # Summary Box (DENGAN JAM)
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

    # METRICS 2 BARIS (INLINE DELTA)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Prediksi", f"{h_now:.2f} m")
    
    diff_aws = f"{(live_aws - h_now):+.2f}m" if live_aws else None
    m2.metric("AWS Priok", f"{live_aws:.2f} m" if live_aws else "N/A", delta=diff_aws, delta_color="inverse")
    
    diff_bpbd = f"{(live_bpbd - h_now):+.2f}m" if live_bpbd else None
    m3.metric("TMA Psr. Ikan", f"{live_bpbd:.2f} m" if live_bpbd else "N/A", delta=diff_bpbd, delta_color="inverse")
    
    h_next = df_pred.loc[(df_pred[col_tgl] - (sekarang_naive + timedelta(hours=3))).abs().idxmin(), col_val]
    tren = h_next - h_now
    icon = "📈 NAIK" if tren > 0.05 else "📉 TURUN" if tren < -0.05 else "↔️ STAGNAN"
    m4.metric("Tren (3J)", icon)

    # --- PLOTLY CHART ---
    t_start, t_end = datetime.combine(tgl_range[0], datetime.min.time()), datetime.combine(tgl_range[1], datetime.max.time())
    df_plot = df_pred[(df_pred[col_tgl] >= t_start) & (df_pred[col_tgl] <= t_end)].copy()
    
    fig = go.Figure()
    if not df_plot.empty:
        fig.add_trace(go.Scatter(x=df_plot[col_tgl], y=df_plot[col_val], name='Prediksi', mode='lines', line=dict(color='gray', dash='dot', width=1.5)))
        
        # Dot Max/Min Harian
        for day in df_plot[col_tgl].dt.date.unique():
            df_day = df_plot[df_plot[col_tgl].dt.date == day]
            idx_max, idx_min = df_day[col_val].idxmax(), df_day[col_val].idxmin()
            fig.add_trace(go.Scatter(x=[df_day.loc[idx_max, col_tgl]], y=[df_day.loc[idx_max, col_val]], mode='markers+text', marker=dict(color='#ef4444', size=6), text=[f"{df_day.loc[idx_max, col_val]:.2f}"], textposition="top center", showlegend=False))
            fig.add_trace(go.Scatter(x=[df_day.loc[idx_min, col_tgl]], y=[df_day.loc[idx_min, col_val]], mode='markers+text', marker=dict(color='#3b82f6', size=6), text=[f"{df_day.loc[idx_min, col_val]:.2f}"], textposition="bottom center", showlegend=False))

        # History
        for f, label, color in [(FILE_HISTORY_AWS, 'AWS', '#7c3aed'), (FILE_HISTORY_BPBD, 'Pasar Ikan', '#f59e0b')]:
            if os.path.exists(f):
                dh = pd.read_csv(f)
                dh['waktu'] = pd.to_datetime(dh['waktu'], format='mixed', errors='coerce')
                dh = dh[(dh['waktu'] >= t_start) & (dh['waktu'] <= t_end)].sort_values('waktu')
                if not dh.empty:
                    fig.add_trace(go.Scatter(x=dh['waktu'], y=dh['nilai'], name=label, line=dict(color=color, width=2.5)))

        fig.update_layout(height=450, template="plotly_white", margin=dict(l=5, r=5, t=25, b=5), hovermode="x unified", legend=dict(orientation="h", y=1.08))
        st.plotly_chart(fig, use_container_width=True)

    # --- DOWNLOAD BUTTONS ---
    c1, c2, c3 = st.columns(3)
    with c1: st.download_button("📥 AWS CSV", open(FILE_HISTORY_AWS, 'rb') if os.path.exists(FILE_HISTORY_AWS) else "", "AWS.csv", use_container_width=True)
    with c2: st.download_button("📥 Pasar Ikan CSV", open(FILE_HISTORY_BPBD, 'rb') if os.path.exists(FILE_HISTORY_BPBD) else "", "PasarIkan.csv", use_container_width=True)
    with c3: 
        if st.button("🔄 Refresh Data", use_container_width=True): st.cache_data.clear(); st.rerun()
else:
    st.error("Data tidak tersedia.")
