import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import pytz
import os

# --- KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Dashboard TMA", layout="wide")

# --- VARIABEL GLOBAL ---
LIMIT_SENSOR_ERROR = 3.2
FILE_HISTORY_AWS = 'history_aws_priok.csv'
FILE_HISTORY_BPBD = 'history_bpbd_pasarikan.csv'
FILE_PREDIKSI = 'Data_Pasut_Jam-jaman.csv'
TZ_WIB = pytz.timezone('Asia/Jakarta')

# --- CUSTOM CSS ---
st.markdown("""
<style>
    .metric-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        border-left: 5px solid #0033cc;
    }
    .metric-card-bpbd { border-left: 5px solid #f59e0b; }
    .metric-title { font-size: 14px; color: #555; }
    .metric-value { font-size: 24px; font-weight: bold; color: #111; }
    .metric-delta { font-size: 12px; color: #28a745; }
    .metric-delta.negative { color: #dc3545; }
    @keyframes blinker { 50% { opacity: 0; } }
</style>
""", unsafe_allow_html=True)

# --- FUNGSI BACA DATA TERAKHIR DARI CSV ---
def get_latest_from_csv(file_path):
    if not os.path.exists(file_path):
        return None, None
    try:
        # Baju Zirah anti Excel
        df = pd.read_csv(file_path)
        if df.empty: return None, None
        df['waktu'] = pd.to_datetime(df['waktu'], format='mixed', errors='coerce')
        df = df.dropna(subset=['waktu', 'nilai'])
        if df.empty: return None, None
        
        last_row = df.iloc[-1]
        return last_row['waktu'], last_row['nilai']
    except Exception:
        return None, None

# --- LOGIKA WAKTU SAAT INI ---
sekarang = datetime.now(TZ_WIB)
t_start = sekarang - timedelta(days=3)
t_end = sekarang + timedelta(days=4)

# Buat timezone-naive untuk Plotly & Pandas
now_naive = sekarang.replace(tzinfo=None)
start_naive = t_start.replace(tzinfo=None)
end_naive = t_end.replace(tzinfo=None)

# --- BACA DATA PREDIKSI ---
@st.cache_data(ttl=3600)
def load_prediksi():
    try:
        df = pd.read_csv(FILE_PREDIKSI)
        df['waktu'] = pd.to_datetime(df['waktu'], errors='coerce')
        df = df.dropna(subset=['waktu', 'nilai'])
        return df
    except Exception:
        return pd.DataFrame(columns=['waktu', 'nilai'])

df_pred = load_prediksi()

# --- AMBIL NILAI SAAT INI (HISTORY TERBARU) ---
_, nilai_aws = get_latest_from_csv(FILE_HISTORY_AWS)
_, nilai_bpbd = get_latest_from_csv(FILE_HISTORY_BPBD)

# Hitung nilai prediksi terdekat
nilai_pred_now = None
if not df_pred.empty:
    terdekat = df_pred.iloc[(df_pred['waktu'] - now_naive).abs().argsort()[:1]]
    if not terdekat.empty:
        nilai_pred_now = terdekat['nilai'].values[0]

# --- UI HEADER ---
st.markdown("## 🌊 Dashboard Pemantauan TMA Jakarta Utara")
st.markdown(f"**Update Terakhir:** {sekarang.strftime('%d %b %Y, %H:%M WIB')}")

# --- SISTEM PERINGATAN DINI (ALARM VISUAL & AUDIO) ---
# Cek nilai tertinggi saat ini dari kedua sensor
max_now = max([v for v in [nilai_aws, nilai_bpbd] if v is not None] or [0])

if max_now >= 2.50:
    st.markdown("""
    <div style="background-color: #dc3545; color: white; padding: 15px; text-align: center; font-size: 22px; font-weight: bold; border-radius: 10px; animation: blinker 1s linear infinite; margin-bottom: 20px;">
        🚨 BAHAYA: TINGGI MUKA AIR MENCAPAI LEVEL AWAS ROB! 🚨
    </div>
    <audio autoplay loop>
        <source src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3" type="audio/mpeg">
    </audio>
    """, unsafe_allow_html=True)
elif max_now >= 2.30:
    st.markdown("""
    <div style="background-color: #f59e0b; color: white; padding: 15px; text-align: center; font-size: 20px; font-weight: bold; border-radius: 10px; margin-bottom: 20px;">
        ⚠️ PERINGATAN: TINGGI MUKA AIR MENCAPAI LEVEL WASPADA! ⚠️
    </div>
    <audio autoplay>
        <source src="https://assets.mixkit.co/active_storage/sfx/2868/2868-preview.mp3" type="audio/mpeg">
    </audio>
    """, unsafe_allow_html=True)

# --- METRIK KARTU ---
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Prediksi (Model)</div>
        <div class="metric-value">{f'{nilai_pred_now:.2f} m' if nilai_pred_now is not None else '-'}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    delta_aws = (nilai_aws - nilai_pred_now) if nilai_aws and nilai_pred_now else 0
    delta_class = "negative" if delta_aws < 0 else ""
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">AWS Tj. Priok</div>
        <div class="metric-value">{f'{nilai_aws:.2f} m' if nilai_aws is not None else '-'}</div>
        <div class="metric-delta {delta_class}">{f'{delta_aws:+.2f} m dr prediksi' if nilai_aws else '-'}</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    delta_bpbd = (nilai_bpbd - nilai_pred_now) if nilai_bpbd and nilai_pred_now else 0
    delta_class2 = "negative" if delta_bpbd < 0 else ""
    st.markdown(f"""
    <div class="metric-card metric-card-bpbd">
        <div class="metric-title">BPBD Psr. Ikan</div>
        <div class="metric-value">{f'{nilai_bpbd:.2f} m' if nilai_bpbd is not None else '-'}</div>
        <div class="metric-delta {delta_class2}">{f'{delta_bpbd:+.2f} m dr prediksi' if nilai_bpbd else '-'}</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    tren = "PASANG 📈" if (nilai_aws and nilai_pred_now and nilai_aws > nilai_pred_now) else "SURUT 📉"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Tren Saat Ini</div>
        <div class="metric-value">{tren}</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# --- GRAFIK PLOTLY ---
fig = go.Figure()

# 1. Plot Prediksi
if not df_pred.empty:
    df_pred_filter = df_pred[(df_pred['waktu'] >= start_naive) & (df_pred['waktu'] <= end_naive)]
    fig.add_trace(go.Scatter(
        x=df_pred_filter['waktu'], y=df_pred_filter['nilai'],
        name='Prediksi', mode='lines',
        line=dict(color='#6c757d', width=2, dash='dot')
    ))

# 2. Plot History AWS
if os.path.exists(FILE_HISTORY_AWS):
    dh_a = pd.read_csv(FILE_HISTORY_AWS)
    dh_a['waktu'] = pd.to_datetime(dh_a['waktu'], format='mixed', errors='coerce')
    dh_a = dh_a.dropna(subset=['waktu', 'nilai'])
    dh_a = dh_a[(dh_a['waktu'] >= start_naive) & (dh_a['waktu'] <= end_naive) & (dh_a['nilai'] <= LIMIT_SENSOR_ERROR)]
    fig.add_trace(go.Scatter(
        x=dh_a['waktu'], y=dh_a['nilai'],
        name='AWS (History)', mode='lines+markers',
        line=dict(color='#0033cc', width=3)
    ))

# 3. Plot History BPBD
if os.path.exists(FILE_HISTORY_BPBD):
    dh_b = pd.read_csv(FILE_HISTORY_BPBD)
    dh_b['waktu'] = pd.to_datetime(dh_b['waktu'], format='mixed', errors='coerce')
    dh_b = dh_b.dropna(subset=['waktu', 'nilai'])
    dh_b = dh_b[(dh_b['waktu'] >= start_naive) & (dh_b['waktu'] <= end_naive) & (dh_b['nilai'] <= LIMIT_SENSOR_ERROR)]
    fig.add_trace(go.Scatter(
        x=dh_b['waktu'], y=dh_b['nilai'],
        name='BPBD (History)', mode='lines+markers',
        line=dict(color='#f59e0b', width=3)
    ))

# 4. Garis Batas & Garis Waktu Saat Ini
fig.add_hline(y=2.50, line_dash="dash", line_color="red", annotation_text="AWAS ROB", annotation_position="top right")
fig.add_hline(y=2.30, line_dash="dash", line_color="orange", annotation_text="WASPADA", annotation_position="top right")

# Fix Bug Plotly Timestamp
fig.add_vline(
    x=now_naive.timestamp() * 1000, 
    line_dash="dash", 
    line_color="green", 
    annotation_text=f"Saat Ini ({sekarang.strftime('%H:%M')})", 
    annotation_position="top left"
)

# Layout Grafik
fig.update_layout(
    xaxis_title="Waktu (WIB)",
    yaxis_title="Tinggi Muka Air (m)",
    height=550,
    hovermode="x unified",
    margin=dict(l=20, r=20, t=30, b=20),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
)

st.plotly_chart(fig, use_container_width=True)

# --- TOMBOL REFRESH ---
st.markdown("<br>", unsafe_allow_html=True)
if st.button("🔄 Force Refresh Data Terbaru"):
    st.cache_data.clear()
    st.rerun()
