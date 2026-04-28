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

# Styling CSS agar tampilan lebih profesional
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
# Nama file harus sesuai dengan yang lu upload ke GitHub
FILE_NAME = 'PASUT_NAVIGASI_APRIL_2026.xlsx'
BATAS_ROB = 1.2

@st.cache_data(ttl=600)
def load_data(filename):
    if not os.path.exists(filename):
        return None, f"⚠️ File '{filename}' tidak ditemukan di repository GitHub lu.", None
    
    try:
        df = pd.read_excel(filename)
        
        # SINKRONISASI KOLOM HASIL PREDIKSI FFT
        tgl_col = 'tanggal_prediksi'
        val_col = 'wl_prediksi'
        
        # Validasi kolom jika ternyata lu upload file hasil audit (bukan prediksi)
        if tgl_col not in df.columns:
            tgl_col = 'jam_group'
            val_col = 'wl_final'
            
        if tgl_col not in df.columns:
            return None, f"❌ Kolom tidak sesuai! Ditemukan: {list(df.columns)}", None
            
        df[tgl_col] = pd.to_datetime(df[tgl_col])
        df = df.sort_values(tgl_col)
        return df, tgl_col, val_col
    except Exception as e:
        return None, f"❌ Error saat membaca file: {str(e)}", None

# Menjalankan fungsi load data
df, tgl, val = load_data(FILE_NAME)

# --- 3. LOGIKA UTAMA (Jika Data Berhasil Dimuat) ---
if isinstance(df, pd.DataFrame):
    # Logika Waktu WIB (UTC+7)
    sekarang_dt = datetime.utcnow() + timedelta(hours=7) 
    
    st.sidebar.title("⚓ Navigasi Panel")
    st.sidebar.write(f"**Waktu Sekarang:** {sekarang_dt.strftime('%d %b %Y | %H:%M')} WIB")
    
    # Range Tanggal (Default seminggu ke depan dari hari ini)
    min_date = df[tgl].min().date()
    max_date = df[tgl].max().date()
    
    # Pastikan tgl_awal tidak out of range dari data yang ada
    default_start = max(sekarang_dt.date(), min_date)
    default_end = min(default_start + timedelta(days=7), max_date)
    
    rentang = st.sidebar.date_input(
        "Pilih Rentang Waktu:", 
        value=(default_start, default_end),
        min_value=min_date, 
        max_value=max_date
    )

    # Filter Data untuk Grafik
    if isinstance(rentang, tuple) and len(rentang) == 2:
        df_view = df[(df[tgl].dt.date >= rentang[0]) & (df[tgl].dt.date <= rentang[1])].copy()
    else:
        df_view = df[df[tgl].dt.date == rentang[0]].copy()

    # --- 4. LOGIKA STATUS PASANG SURUT ---
    msl = df[val].mean()
    # Cari index yang paling dekat dengan jam sekarang
    idx_now = (df[tgl] - sekarang_dt).abs().idxmin()
    h_now = df.loc[idx_now, val]
    
    status_elevasi = "PASANG" if h_now >= msl else "SURUT"
    
    if idx_now + 1 < len(df):
        gerak = "NAIK" if df.loc[idx_now + 1, val] > h_now else "TURUN"
        prediksi = f"AKAN {gerak}"
    else: 
        prediksi = "STABIL"

    # --- 5. TAMPILAN DASHBOARD ---
    st.title("🌊 Monitoring Pasut Ancol (Prediksi FFT)")
    
    # Baris Metrik
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Tinggi Air Sekarang", f"{h_now:.2f} m")
    m2.metric("Status", status_elevasi, f"MSL: {msl:.2f}m")
    m3.metric("Tren Mendatang", prediksi)
    m4.metric("Batas Aman ROB", f"{BATAS_ROB} m")

    # Grafik Plotly
    fig = go.Figure()
    
    # Garis Elevasi
    fig.add_trace(go.Scatter(
        x=df_view[tgl], y=df_view[val],
        mode='lines',
        line=dict(color='#007bff', width=3, shape='spline'),
        name='Prediksi Elevasi'
    ))

    # Titik "Sekarang" di Grafik
    if rentang[0] <= sekarang_dt.date() <= rentang[1]:
        fig.add_trace(go.Scatter(
            x=[df.loc[idx_now, tgl]], y=[h_now],
            mode='markers+text',
            text=[f"Waktu Sekarang"],
            textposition="top center",
            marker=dict(color='#dc3545', size=12, symbol='diamond'),
            name='Posisi Saat Ini'
        ))

    # Garis Batas ROB
    fig.add_hline(y=BATAS_ROB, line_dash="dash", line_color="#ff4b4b", 
                  annotation_text="BATAS BAHAYA ROB", annotation_font_color="#ff4b4b")

    fig.update_layout(
        plot_bgcolor='white', paper_bgcolor='white',
        margin=dict(l=20, r=20, t=50, b=20),
        height=500,
        xaxis=dict(showgrid=True, gridcolor='#f0f0f0', title="Waktu (WIB)"),
        yaxis=dict(showgrid=True, gridcolor='#f0f0f0', title="Ketinggian (Meter)"),
        hovermode="x unified"
    )
    
    st.plotly_chart(fig, use_container_width=True)

    # Sidebar Alert
    st.sidebar.divider()
    if h_now >= BATAS_ROB:
        st.sidebar.error(f"🚨 **WASPADA ROB!**\nKetinggian air ({h_now:.2f}m) melewati batas aman.")
    else:
        st.sidebar.success(f"✅ **KONDISI AMAN**\nKetinggian air masih di bawah batas ROB.")
    
    st.sidebar.info("Data ini adalah hasil prediksi menggunakan metode FFT (Harmonic Analysis) berdasarkan data historis AWS Ancol.")

else:
    # Jika data gagal dimuat (df berisi pesan error String)
    st.error(df if df else "Terjadi kesalahan fatal saat memuat aplikasi.")
    st.info("💡 **Tips:** Pastikan file Excel 'prediksi_pasut_ancol_2026.xlsx' sudah di-upload ke repository GitHub lu.")
