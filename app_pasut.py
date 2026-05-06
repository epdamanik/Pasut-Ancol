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
    .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; max-width: 95% !important; }
    .stApp { background-color: #ffffff; }
    
    /* Header Rapat */
    .header-text { text-align: center; width: 100%; margin-top: -10px; margin-bottom: 5px; }
    
    /* Kotak Metrik Tipis (2 Baris) */
    div[data-testid="stMetric"] {
        background-color: #ffffff !important; 
        border: 1px solid #e2e8f0 !important;
        border-left: 4px solid #1e40af !important; 
        padding: 8px 12px !important; 
        border-radius: 8px !important;
        min-height: 65px !important; 
        display: flex !important;
        justify-content: center !important;
    }
    
    /* Styling Nilai & Delta Inline */
    [data-testid="stMetricValue"] { 
        font-size: 20px !important; 
        font-weight: 800 !important; 
        display: inline-flex !important; 
        align-items: center !important;
    }
    [data-testid="stMetricDelta"] {
        font-size: 14px !important;
        margin-left: 8px !important;
    }
    [data-testid="stMetricLabel"] { 
        font-size: 0.75rem !important; 
        margin-bottom: -5px !important;
    }

    /* Summary Box Pepet Header */
    .summary-box {
        background-color: #f1f5f9 !important; 
        padding: 5px !important; 
        border-radius: 8px !important; 
        margin-bottom: 10px !important; 
        border: 1px solid #cbd5e1 !important;
        text-align: center !important;
    }
    .summary-text { font-weight: 700 !important; font-size: 0.85rem !important; color: #0f172a !important; }

    /* Sidebar Logo Center */
    [data-testid="stSidebar"] [data-testid="stImage"] { text-align: center !important; display: block !important; }
    
    .footer-card { margin-top: 20px; padding: 10px; background-color: #f8fafc; border: 1px solid #e2e8f0; text-align: center; border-radius: 8px;}
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
    st.link_button("🌐 Web Maritim Priok", "https://bmkgtanjungpriok.info/", use_container_width=True)
    
    st.markdown(f"""<div class="footer-card"><p style='font-size: 0.7rem; color: #1e3a8a; margin: 0;'>© 2026 BMKG Tanjung Priok</p></div>
                <p style='text-align: center; font-size: 0.5rem; color: #94a3b8; margin-top: 10px;'>Dev by E.P. Damanik</p>""", unsafe_allow_html=True)

# --- 4. HEADER ---
st.markdown('<div class="header-text"><h2 style="margin: 0; color: #0f172a; font-size: 1.4rem;">MONITORING TMA REAL TIME</h2></div>', unsafe_allow_html=True)

# --- 5. FUNCTIONS ---
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

# --- 6. DATA LOADING ---
df_pred, col_tgl, col_val = load_prediction()
live_aws = get_latest_from_csv(FILE_HISTORY_AWS)
live_bpbd = get_latest_from_csv(FILE_HISTORY_BPBD)

# --- 7. DISPLAY ---
if df_pred is not None:
    # Cari nilai prediksi saat ini
    h_now = df_pred.loc[(df_pred[col_tgl] - sekarang_naive).abs().idxmin(), col_val]
    
    # Alert Status
    check = {"Prediksi": h_now, "AWS": live_aws, "PASAR IKAN": live_bpbd}
    awas = [n for n, v in check.items() if v and v >= 2.5]
    waspada = [n for n, v in check.items() if v and 2.3 <= v < 2.5]
    if awas: 
        st.error(f"🚨 STATUS: AWAS ROB! ({', '.join(awas)})")
        play_audio("AWAS ROB.mp3")
    elif waspada: 
        st.warning(f"📢 STATUS: WASPADA ROB! ({', '.join(waspada)})")
        play_audio("waspada ROB.mp3")

    # Summary Box dengan Jam (Max/Min)
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

    # Metrik Baris Tunggal/Tipis
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Prediksi", f"{h_now:.2f} m")
    
    # AWS dengan Delta di samping
    diff_aws = f"{(live_aws - h_now):+.2f}m" if live_aws else None
    m2.metric("AWS Priok", f"{live_aws:.2f} m" if live_aws else "N/A", delta=diff_aws, delta_color="inverse")
    
    # Pasar Ikan dengan Delta di samping
    diff_bpbd = f"{(live_bpbd - h_now):+.2f}m" if live_bpbd else None
    m3.metric("TMA Psr. Ikan", f"{live_bpbd:.2f} m" if live_bpbd else "N/A", delta=diff_bpbd, delta_color="inverse")
    
    # Tren
    h_next = df_pred.loc[(df_pred[col_tgl] - (sekarang_naive + timedelta(hours=3))).abs().idxmin(), col_val]
    tren_val = h_next - h_now
    icon, status = ("📈 NAIK", "normal") if tren_val > 0.05 else ("📉 TURUN", "normal") if tren_val < -0.05 else ("↔️ STAGNAN", "off")
    m4.metric("Tren (3j)", icon)

    # --- PLOTLY CHART ---
    t_start, t_end = datetime.combine(tgl_range[0], datetime.min.time()), datetime.combine(tgl_range[1], datetime.max.time())
    df_plot = df_pred[(df_pred[col_tgl] >= t_start) & (df_pred[col_tgl] <= t_end)].copy()
    
    fig = go.Figure()
    if not df_plot.empty:
        fig.add_trace(go.Scatter(x=df_plot[col_tgl], y=df_plot[col_val], name='Prediksi', line=dict(color='gray', dash='dot', width=1.5)))
        
        # Plot Histori AWS & BPBD
        for f, label, color in [(FILE_HISTORY_AWS, 'AWS', '#7c3aed'), (FILE_HISTORY_BPBD, 'Pasar Ikan', '#f59e0b')]:
            if os.path.exists(f):
                dh = pd.read_csv(f)
                dh['waktu'] = pd.to_datetime(dh['waktu'], format='mixed', errors='coerce')
                dh = dh[(dh['waktu'] >= t_start) & (dh['waktu'] <= t_end)].sort_values('waktu')
                if not dh.empty:
                    fig.add_trace(go.Scatter(x=dh['waktu'], y=dh['nilai'], name=label, line=dict(color=color, width=3)))

        # Garis Waktu Sekarang
        fig.add_vline(x=sekarang_naive, line_width=2, line_dash="dash", line_color="green")
        
        fig.update_layout(height=400, margin=dict(l=10, r=10, t=10, b=10), hovermode="x unified", template="plotly_white",
                          legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"))
        st.plotly_chart(fig, use_container_width=True)

    # Footer Buttons
    c1, c2, c3 = st.columns(3)
    with c1: st.download_button("📥 AWS CSV", open(FILE_HISTORY_AWS, 'rb') if os.path.exists(FILE_HISTORY_AWS) else "", "AWS.csv", use_container_width=True)
    with c2: st.download_button("📥 Pasar Ikan CSV", open(FILE_HISTORY_BPBD, 'rb') if os.path.exists(FILE_HISTORY_BPBD) else "", "PasarIkan.csv", use_container_width=True)
    with c3: 
        if st.button("🔄 Refresh", use_container_width=True): st.cache_data.clear(); st.rerun()
