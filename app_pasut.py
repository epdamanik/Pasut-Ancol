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
    /* Container Utama - Ruang aman agar tidak kepotong */
    .block-container { 
        padding-top: 2.2rem !important; 
        padding-bottom: 0rem !important; 
        max-width: 95% !important; 
    }
    .stApp { background-color: #ffffff; }
    
    /* Header Utama */
    .header-text { 
        text-align: center; 
        width: 100%; 
        margin-top: -25px; 
        margin-bottom: 15px; 
    }

    /* Kotak Metrik - SIMETRIS & ANIMASI HOVER */
    div[data-testid="stMetric"] {
        background-color: #ffffff !important; 
        border: 1px solid #e2e8f0 !important;
        border-left: 5px solid #1e40af !important; 
        padding: 15px !important; 
        border-radius: 12px !important;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
        min-height: 125px !important; 
        display: flex !important;
        flex-direction: column !important;
        justify-content: center !important;
        transition: all 0.3s ease-in-out !important;
    }
    
    div[data-testid="stMetric"]:hover {
        transform: translateY(-5px) !important;
        box-shadow: 0 12px 20px -5px rgba(0, 0, 0, 0.1) !important;
        border-color: #1e40af !important;
    }

    /* Font Metrics */
    [data-testid="stMetricLabel"] { color: #1e3a8a !important; font-weight: 700 !important; font-size: 0.85rem !important; }
    [data-testid="stMetricValue"] { font-size: 24px !important; font-weight: 800 !important; color: #0f172a !important; }

    /* Summary Bar */
    .summary-box {
        background-color: #f1f5f9 !important; padding: 10px !important; 
        border-radius: 10px !important; margin-bottom: 15px !important; 
        border-left: 5px solid #1e3a8a !important; text-align: center !important;
    }
    .summary-text { font-weight: 850 !important; font-size: 0.95rem !important; color: #0f172a !important; }

    /* Footer Sidebar - Minimalis */
    .footer-card {
        margin-top: 50px; padding: 12px; border-radius: 10px; 
        background-color: #f8fafc; border: 1px solid #e2e8f0; 
        text-align: center;
    }
    .dev-name { color: #475569; font-weight: 400; font-size: 0.72rem; margin-top: 4px; display: block; }
    
    footer {visibility: hidden;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOGIC WAKTU ---
tz_jkt = pytz.timezone('Asia/Jakarta')
sekarang = datetime.now(tz_jkt).replace(tzinfo=None)

# --- 3. SIDEBAR ---
NAMA_FILE_LOGO = "logo-bmkg-transparan.png" 

with st.sidebar:
    if os.path.exists(NAMA_FILE_LOGO):
        _, col_img, _ = st.columns([0.38, 0.24, 0.38])
        with col_img:
            st.image(NAMA_FILE_LOGO, use_container_width=True)
    
    st.markdown("<p style='text-align: center; color: #1e3a8a; margin-top: -10px; font-size: 0.85rem; font-weight: bold;'>STAMAR TANJUNG PRIOK</p>", unsafe_allow_html=True)
    st.divider()
    
    tgl_range = st.date_input("🗓️ Rentang Waktu Grafik", value=(sekarang.date() - timedelta(days=1), sekarang.date() + timedelta(days=2)))
    st.link_button("🌐 Web BMKG Tanjung Priok", "https://bmkgtanjungpriok.info/", use_container_width=True)
    
    st.divider()
    with st.expander("ℹ️ Info Sumber Data"):
        st.caption("""
        **Prediksi:** Analisis Harmonik data TMA Pasar Ikan I (DSDA) 2025.
        **Real-time:** AWS BMKG & Pintu Air Pasar Ikan I (DSDA).
        """)
    
    # Footer - Developed by E.P. Damanik (Tanpa Forecaster)
    st.markdown(f"""
        <div class="footer-card">
            <p style='font-size: 0.7rem; color: #1e3a8a; margin-bottom: 0;'>© 2026 Stamar Tanjung Priok</p>
            <p style='font-size: 0.6rem; color: #64748b; margin-top: 4px;'>
                Developed by <br>
                <span class="dev-name">E.P. Damanik</span>
            </p>
        </div>
    """, unsafe_allow_html=True)

# --- 4. HEADER UTAMA ---
st.markdown(f"""
    <div class="header-text">
        <h2 style="margin: 0; color: #0f172a; font-weight: bold; font-size: 1.6rem;">
            MONITORING TINGGI MUKA AIR (TMA) REAL TIME
        </h2>
    </div>
    """, unsafe_allow_html=True)

# sisanya tetap (Data Functions, Execution, Display Plotly)...
# ... (Pastikan copy sisa kode dari file sebelumnya agar aplikasi tetap jalan)
