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
    .block-container { padding-top: 2.2rem !important; padding-bottom: 0rem !important; max-width: 95% !important; }
    .stApp { background-color: #ffffff; }
    .header-text { text-align: center; width: 100%; margin-top: -25px; margin-bottom: 15px; }

    /* --- KOTAK METRIK (ULTRA SLIM) --- */
    div[data-testid="stMetric"] {
        background-color: #ffffff !important; 
        border: 1px solid #e2e8f0 !important;
        border-left: 4px solid #1e40af !important; 
        padding: 4px 10px !important; 
        border-radius: 8px !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
        min-height: 55px !important; 
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
    }
    
    div[data-testid="stMetricLabel"] { 
        color: #1e3a8a !important; 
        font-weight: 700 !important; 
        font-size: 0.7rem !important; 
        margin-bottom: -10px !important; 
        white-space: nowrap !important;
    }

    [data-testid="stMetricValue"] { 
        font-size: 15px !important; 
        font-weight: 800 !important; 
        color: #0f172a !important; 
        white-space: nowrap !important;
    }

    /* Sembunyikan delta asli Streamlit */
    div[data-testid="stMetricDelta"] { display: none !important; }

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
sekarang = datetime.now(tz_jkt)
sekarang_naive = sekarang.replace(tzinfo=None)

# --- 3. SIDEBAR ---
NAMA_FILE_LOGO = "logo-bmkg-transparan.png" 
with st.sidebar:
    if os.path.exists(NAMA_FILE_LOGO):
        with open(NAMA_FILE_LOGO, "rb") as f:
            data = f.read()
            encoded = base64.b64encode(data).decode()
        st.markdown(f'<div style="text-align: center;"><img src="data:image/png;base64,{encoded}" style="width: 85px;"></div>', unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #1e3a8a; font-weight: bold;'>STASIUN METEOROLOGI MARITIM TANJUNG PRIOK</p>", unsafe_allow_html=True)
    st.divider()
    tgl_range = st.date_input("🗓️ Rentang Grafik", value=(sekarang.date() - timedelta(days=1), sekarang.date() + timedelta(days=2)))
    st.link_button("🌐 Web BMKG", "https://bmkgtanjungpriok.info/", use_container_width=True)

# --- 4. DATA FUNCTIONS ---
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

# --- 5. EXECUTION ---
df_pred, col_tgl, col_val = load_prediction()
live_data = {"aws": get_latest_from_csv(FILE_HISTORY_AWS), "bpbd": get_latest_from_csv(FILE_HISTORY_BPBD)}

# --- 6. DISPLAY ---
st.markdown('<div class="header-text"><h2 style="margin: 0; font-weight: bold; font-size: 1.5rem;">MONITORING TMA REAL TIME</h2></div>', unsafe_allow_html=True)

if df_pred is not None and not df_pred.empty:
    h_now = df_pred.loc[(df_pred[col_tgl] - sekarang_naive).abs().idxmin(), col_val]
    
    # Summary Box
    df_h = df_pred[df_pred[col_tgl].dt.date == sekarang.date()]
    if not df_h.empty:
        v_max = df_h[col_val].max()
        v_min = df_h[col_val].min()
        st.markdown(f'<div class="summary-box"><span class="summary-text">📅 {sekarang.strftime("%d %b %Y")} | <span style="color: #ef4444;">▲ MAX: {v_max:.2f}m</span> | <span style="color: #3b82f6;">▼ MIN: {v_min:.2f}m</span></span></div>', unsafe_allow_html=True)

    m1, m2, m3, m4 = st.columns(4)
    
    # 1. Prediksi (Kotak Tetap)
    m1.metric("Prediksi Pasut", f"{h_now:.2f} m")
    
    # Fungsi format teks di dalam st.metric asli
    def get_metric_text(val_real, val_pred):
        if val_real is None: return "N/A"
        diff = val_real - val_pred
        # Pakai karakter warna & simbol manual
        color = "🟢" if diff >= 0 else "🔴"
        sign = "+" if diff >= 0 else ""
        # Karena kita mau font warna, tapi Streamlit metric value cuma terima string, 
        # kita biarkan CSS yang handle atau pakai simbol warna.
        return f"{val_real:.2f} m ({sign}{diff:.2f})"

    # 2. AWS (Kembali ke st.metric)
    val_aws = get_latest_from_csv(FILE_HISTORY_AWS)
    diff_aws = (val_aws - h_now) if val_aws else 0
    sign_aws = "+" if diff_aws >= 0 else ""
    color_aws = "#22c55e" if diff_aws >= 0 else "#ef4444"
    
    m2.metric("AWS Tj. Priok", f"{val_aws:.2f} m")
    # Trik: Gunakan markdown tepat di bawah label untuk menyuntikkan delta warna-warni di samping value
    st.markdown(f"""
        <style>
        [data-testid="column"]:nth-child(2) [data-testid="stMetricValue"]::after {{
            content: " ({sign_aws}{diff_aws:.2f})";
            color: {color_aws};
            font-size: 14px;
        }}
        </style>
    """, unsafe_allow_html=True)

    # 3. Psr Ikan (Kembali ke st.metric)
    val_bpbd = get_latest_from_csv(FILE_HISTORY_BPBD)
    diff_bpbd = (val_bpbd - h_now) if val_bpbd else 0
    sign_bpbd = "+" if diff_bpbd >= 0 else ""
    color_bpbd = "#22c55e" if diff_bpbd >= 0 else "#ef4444"
    
    m3.metric("TMA Psr. Ikan", f"{val_bpbd:.2f} m")
    st.markdown(f"""
        <style>
        [data-testid="column"]:nth-child(3) [data-testid="stMetricValue"]::after {{
            content: " ({sign_bpbd}{diff_bpbd:.2f})";
            color: {color_bpbd};
            font-size: 14px;
        }}
        </style>
    """, unsafe_allow_html=True)
    
    # 4. Tren
    h_next = df_pred.loc[(df_pred[col_tgl] - (sekarang_naive + timedelta(hours=3))).abs().idxmin(), col_val]
    icon = "📈 NAIK" if (h_next - h_now) > 0.05 else "📉 TURUN" if (h_next - h_now) < -0.05 else "↔️ STAGNAN"
    m4.metric("Tren (3j)", icon)

    # --- PLOTLY CHART ---
    t_start, t_end = datetime.combine(tgl_range[0], datetime.min.time()), datetime.combine(tgl_range[1], datetime.max.time())
    df_plot = df_pred[(df_pred[col_tgl] >= t_start) & (df_pred[col_tgl] <= t_end)]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_plot[col_tgl], y=df_plot[col_val], name='Prediksi', line=dict(color='#94a3b8', dash='dot')))
    
    for file, label, color in [(FILE_HISTORY_AWS, 'AWS', '#7c3aed'), (FILE_HISTORY_BPBD, 'Psr. Ikan', '#f59e0b')]:
        if os.path.exists(file):
            dh = pd.read_csv(file)
            dh['waktu'] = pd.to_datetime(dh['waktu'], format='mixed', errors='coerce')
            dh = dh[(dh['waktu'] >= t_start) & (dh['waktu'] <= t_end)]
            fig.add_trace(go.Scatter(x=dh['waktu'], y=dh['nilai'], name=label, line=dict(color=color, width=3)))

    fig.update_layout(height=400, margin=dict(l=0,r=0,t=20,b=0), legend=dict(orientation="h", y=1.1, x=0.5, xanchor="center"))
    st.plotly_chart(fig, use_container_width=True)

    # Tombol Aksi
    c1, c2, c3 = st.columns(3)
    c1.download_button("📥 AWS", open(FILE_HISTORY_AWS, 'rb').read() if os.path.exists(FILE_HISTORY_AWS) else b"", "AWS.csv", use_container_width=True)
    c2.download_button("📥 Psr Ikan", open(FILE_HISTORY_BPBD, 'rb').read() if os.path.exists(FILE_HISTORY_BPBD) else b"", "Pasarikan.csv", use_container_width=True)
    if c3.button("🔄 Refresh", use_container_width=True): st.cache_data.clear(); st.rerun()
