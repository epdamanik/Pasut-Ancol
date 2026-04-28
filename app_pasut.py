import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
import os

# --- 0. AUTO REFRESH (Update tiap 5 menit) ---
st_autorefresh(interval=5 * 60 * 1000, key="datarefresh")

# --- 1. KONFIGURASI HALAMAN ---
st.set_page_config(page_title="Pasut ANCOL 2026", layout="wide", page_icon="🌊")

st.markdown("""
    <style>
    .stApp { background-color: #f8f9fa; color: #1e1e1e; }
    [data-testid="stMetricValue"] { font-size: 28px; color: #007bff; }
    .stMetric { 
        background-color: #ffffff; 
        padding: 15px; 
        border-radius: 10px; 
        border: 1px solid #dee2e6; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); 
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. PENGATURAN DATA & LOAD ---
FILE_NAME = 'PASUT_NAVIGASI_APRIL_2026.xlsx'
BATAS_ROB = 2.5

@st.cache_data(ttl=600)
def load_data(filename):
    if not os.path.exists(filename):
        return None, f"⚠️ File '{filename}' tidak ditemukan di repository.", None
    
    try:
        # Load dengan engine openpyxl
        df = pd.read_excel(filename, engine='openpyxl')
        cols = list(df.columns)
        
        # 1. Deteksi Kolom Waktu (Mencari kemungkinan nama)
        tgl_candidates = ['tanggal_prediksi', 'jam_group', 'Waktu_WIB', 'Waktu', 'Datetime']
        tgl_col = next((c for c in tgl_candidates if c in cols), None)
        
        # 2. Deteksi Kolom Ketinggian (Mencari kemungkinan nama)
        val_candidates = ['wl_prediksi', 'wl_final', 'Tinggi_Navigasi_m', 'Ketinggian', 'Water_Level']
        val_col = next((c for c in val_candidates if c in cols), None)
        
        if not tgl_col or not val_col:
            return None, f"❌ Kolom tidak dikenali! Kolom di Excel Anda: {cols}", None
            
        df[tgl_col] = pd.to_datetime(df[tgl_col])
        df = df.sort_values(tgl_col)
        return df, tgl_col, val_col
    except Exception as e:
        return None, f"❌ Gagal membaca Excel: {str(e)}", None

# Eksekusi Load Data
res_df, msg, col_val = load_data(FILE_NAME)

# --- 3. LOGIKA UTAMA ---
if res_df is not None:
    df, tgl, val = res_df, msg, col_val
    
    # Waktu Jakarta (WIB)
    sekarang_dt = datetime.utcnow() + timedelta(hours=7) 
    
    st.sidebar.title("⚓ Navigasi Panel")
    st.sidebar.write(f"**Waktu Sekarang:** {sekarang_dt.strftime('%d %b %Y | %H:%M')} WIB")
    
    min_date = df[tgl].min().date()
    max_date = df[tgl].max().date()
    
    # Proteksi jika hari ini di luar range data
    default_start = max(min(sekarang_dt.date(), max_date), min_date)
    default_end = min(default_start + timedelta(days=7), max_date)
    
    rentang = st.sidebar.date_input(
        "Rentang Waktu:", 
        value=(default_start, default_end),
        min_value=min_date, 
        max_value=max_date
    )

    if isinstance(rentang, tuple) and len(rentang) == 2:
        df_view = df[(df[tgl].dt.date >= rentang[0]) & (df[tgl].dt.date <= rentang[1])].copy()
    else:
        df_view = df[df[tgl].dt.date == rentang[0]].copy()

    # Logika Metrik
    msl = df[val].mean()
    idx_now = (df[tgl] - sekarang_dt).abs().idxmin()
    h_now = df.loc[idx_now, val]
    
    status_elevasi = "PASANG" if h_now >= msl else "SURUT"
    prediksi = "STABIL"
    if idx_now + 1 < len(df):
        prediksi = f"AKAN {'NAIK' if df.loc[idx_now + 1, val] > h_now else 'TURUN'}"

    # Dashboard
    st.title("🌊 Monitoring Pasut Ancol 2026")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Tinggi Air", f"{h_now:.2f} m")
    m2.metric("Status", status_elevasi, f"MSL: {msl:.2f}m")
    m3.metric("Tren", prediksi)
    m4.metric("Batas ROB", f"{BATAS_ROB} m")

    # Grafik
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df_view[tgl], y=df_view[val], mode='lines', line=dict(color='#007bff', width=3), name='Elevasi'))
    
    if rentang[0] <= sekarang_dt.date() <= rentang[1]:
        fig.add_trace(go.Scatter(x=[df.loc[idx_now, tgl]], y=[h_now], mode='markers', marker=dict(color='red', size=10), name='Sekarang'))

    fig.add_hline(y=BATAS_ROB, line_dash="dash", line_color="red", annotation_text="BATAS ROB")
    fig.update_layout(plot_bgcolor='white', height=500, xaxis_title="Waktu", yaxis_title="Meter", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

    st.sidebar.divider()
    if h_now >= BATAS_ROB:
        st.sidebar.error("🚨 **WASPADA ROB!**")
    else:
        st.sidebar.success("✅ **KONDISI AMAN**")
else:
    st.error(msg)
    # Debugging folder jika masih error
    st.write("Isi folder saat ini:", os.listdir("."))
