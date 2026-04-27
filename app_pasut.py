import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta # TAMBAHKAN timedelta
from streamlit_autorefresh import st_autorefresh # TAMBAHKAN INI
import os

# --- 0. AUTO REFRESH (Update tiap 5 menit) ---
st_autorefresh(interval=5 * 60 * 1000, key="datarefresh")

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Navigasi Pasut Online", layout="wide")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; color: #1e1e1e; }
    [data-testid="stMetricValue"] { font-size: 28px; color: #007bff; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #dee2e6; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    </style>
    """, unsafe_allow_html=True)

# --- 2. PENGATURAN DATA ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
excel_files = [f for f in os.listdir(BASE_DIR) if f.endswith('.xlsx')]

if excel_files:
    FILE_PATH = os.path.join(BASE_DIR, excel_files[0])
else:
    FILE_PATH = None

BATAS_ROB = 1.2

@st.cache_data(ttl=600) # Kasih umur cache 10 menit biar gak nyangkut terus
def load_data(path):
    if not path: return None, None, None
    try:
        df = pd.read_excel(path)
        tgl_col, val_col = 'Waktu_WIB', 'Tinggi_Navigasi_m'
        df[tgl_col] = pd.to_datetime(df[tgl_col])
        df = df.sort_values(tgl_col)
        return df, tgl_col, val_col
    except: return None, None, None

df, tgl, val = load_data(FILE_PATH)

if df is not None:
    # --- 3. LOGIKA WAKTU WIB (PENTING!) ---
    # Pakai UTC + 7 Jam agar sinkron dengan waktu Jakarta
    sekarang_dt = datetime.utcnow() + timedelta(hours=7) 
    
    st.sidebar.title("⚓ Navigasi Panel")
    st.sidebar.write(f"Waktu Lokal: {sekarang_dt.strftime('%H:%M:%S')} WIB")
    
    tgl_awal = max(sekarang_dt.date(), df[tgl].min().date())
    tgl_akhir = min(tgl_awal + pd.Timedelta(days=7), df[tgl].max().date())
    rentang = st.sidebar.date_input("Rentang Waktu:", value=(tgl_awal, tgl_akhir),
                                    min_value=df[tgl].min().date(), max_value=df[tgl].max().date())

    if isinstance(rentang, tuple) and len(rentang) == 2:
        df_view = df[(df[tgl].dt.date >= rentang[0]) & (df[tgl].dt.date <= rentang[1])].copy()
    else:
        df_view = df[df[tgl].dt.date == rentang[0]].copy()

    # --- 4. LOGIKA STATUS ---
    msl = (df[val].max() + df[val].min()) / 2
    idx_now = (df[tgl] - sekarang_dt).abs().idxmin()
    h_now = df.loc[idx_now, val]
    
    status_elevasi = "PASANG" if h_now >= msl else "SURUT"
    
    if idx_now + 1 < len(df):
        gerak = "NAIK" if df.loc[idx_now + 1, val] > h_now else "TURUN"
        prediksi = f"AKAN {gerak}"
    else: prediksi = "STABIL"

    # --- 5. TAMPILAN ---
    st.title("🌊 Monitoring Pasang Surut")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Tinggi Sekarang", f"{h_now:.2f} m")
    m2.metric("Status", status_elevasi, f"MSL: {msl:.2f}m")
    m3.metric("Tren Mendatang", prediksi)
    m4.metric("Batas ROB", f"{BATAS_ROB} m")

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_view[tgl], y=df_view[val],
        mode='lines',
        line=dict(color='#0056b3', width=3, shape='spline'),
        name='Elevasi Pasut'
    ))

    # Titik Sekarang Berdasarkan Waktu WIB
    if rentang[0] <= sekarang_dt.date() <= rentang[1]:
        fig.add_trace(go.Scatter(
            x=[df.loc[idx_now, tgl]], y=[h_now],
            mode='markers+text',
            text=[f"SKRG: {status_elevasi}"],
            textposition="top center",
            marker=dict(color='#dc3545', size=12),
            name='Sekarang'
        ))

    fig.add_hline(y=BATAS_ROB, line_dash="dash", line_color="red", 
                  annotation_text="BATAS ROB", annotation_font_color="red")

    fig.update_layout(
        plot_bgcolor='white', paper_bgcolor='white', font_color='#333333',
        height=550,
        xaxis=dict(showgrid=False, showline=True, linewidth=2, linecolor='black', title="Waktu"),
        yaxis=dict(showgrid=False, showline=True, linewidth=2, linecolor='black', title="Ketinggian (Meter)"),
        hovermode="x unified"
    )
    st.plotly_chart(fig, use_container_width=True)

    st.sidebar.divider()
    if h_now >= BATAS_ROB: st.sidebar.error(f"🚨 WASPADA ROB!")
    else: st.sidebar.success(f"✅ KONDISI {status_elevasi} AMAN")
    
else:
    st.error("Data Excel tidak terbaca atau file tidak ditemukan.")
