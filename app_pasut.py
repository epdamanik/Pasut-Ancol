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
    .block-container { padding-top: 2.2rem !important; padding-bottom: 0rem !important; max-width: 95% !important; }
    .stApp { background-color: #ffffff; }
    .header-text { text-align: center; width: 100%; margin-top: -25px; margin-bottom: 15px; }

    /* --- FIX LOGO CENTER TOTAL --- */
    /* Targetkan semua container gambar di sidebar agar rata tengah */
    [data-testid="stSidebar"] [data-testid="stImage"] {
        text-align: center !important;
        display: block !important;
        margin-left: auto !important;
        margin-right: auto !important;
        width: 100% !important;
    }

    /* Targetkan tag img-nya langsung */
    [data-testid="stSidebar"] [data-testid="stImage"] img {
        max-width: 90px !important; /* Ukuran pas buat logo */
        margin-left: auto !important;
        margin-right: auto !important;
        display: inline-block !important;
    }

    /* --- FIX POSISI & UKURAN KALENDER (PRESISI) --- */
    
    /* 1. Atur wadah putih (popover) agar fit dengan kalender */
    div[data-baseweb="popover"] {
        top: 90px !important; 
        bottom: auto !important;
        transform: none !important;
        /* Biar wadahnya gak kebesaran */
        width: fit-content !important;
        min-width: auto !important;
    }

    /* 2. Hajar kontainer kalender agar mengecil dan rapat */
    div[data-baseweb="calendar"] {
        transform: scale(1) !important;
        transform-origin: top left !important;
        background-color: #ffffff !important;
        border-radius: 8px !important;
        /* Menghilangkan margin bawaan yang bikin wadah kelihatan besar */
        margin: 0 !important; 
    }

    /* 3. Menghilangkan padding sisa di pembungkus agar kotak putihnya pas */
    div[data-baseweb="popover"] > div {
        width: fit-content !important;
        height: fit-content !important;
        padding: 0 !important; /* Hapus ruang kosong di pinggiran */
    }

    /* 4. Rampingkan kotak input di sidebar */
    div[data-testid="stDateInput"] {
        max-width: 90% !important;
        margin: 0 auto !important;
    }

    /* --- GAYA METRIK & FOOTER --- */
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

    [data-testid="stMetricLabel"] { color: #1e3a8a !important; font-weight: 700 !important; font-size: 0.85rem !important; }
    [data-testid="stMetricValue"] { font-size: 24px !important; font-weight: 800 !important; color: #0f172a !important; }

    .summary-box {
        background-color: #f1f5f9 !important; padding: 10px !important; 
        border-radius: 10px !important; margin-bottom: 15px !important; 
        border-left: 5px solid #1e3a8a !important; text-align: center !important;
    }
    .summary-text { font-weight: 850 !important; font-size: 0.95rem !important; color: #0f172a !important; }

    .footer-card {
        margin-top: 50px; padding: 12px; border-radius: 10px; 
        background-color: #f8fafc; border: 1px solid #e2e8f0; 
        text-align: center;
    }
    .dev-name { color: #475569; font-weight: 400; font-size: 0.55rem; margin-top: 2px; display: block; }
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
        # Trik Base64: Mengubah gambar jadi kode teks supaya bisa dipanggil via HTML murni
        with open(NAMA_FILE_LOGO, "rb") as f:
            data = f.read()
            encoded = base64.b64encode(data).decode()
        
        # Paksa rata tengah pakai HTML murni (Pasti Berhasil!)
        st.markdown(
            f"""
            <div style="display: flex; justify-content: center; align-items: center; width: 100%; margin-top: -15px; margin-bottom: 10px;">
                <img src="data:image/png;base64,{encoded}" style="width: 85px; height: auto;">
            </div>
            """,
            unsafe_allow_html=True
        )
    
    st.markdown("<p style='text-align: center; color: #1e3a8a; margin-top: -5px; font-size: 0.85rem; font-weight: bold;'>STASIUN METEOROLOGI MARITIM TANJUNG PRIOK</p>", unsafe_allow_html=True)
    st.divider()
    
    tgl_range = st.date_input("🗓️ Rentang Waktu Grafik", value=(sekarang.date() - timedelta(days=1), sekarang.date() + timedelta(days=2)))
    st.link_button("🌐 Web BMKG Tanjung Priok", "https://bmkgtanjungpriok.info/", use_container_width=True)
    
    with st.expander("ℹ️ Info Sumber Data"):
        st.markdown("""
        <div style="text-align: justify; font-size: 0.95rem; color: #475569;">
            <strong>📍 Prediksi:</strong><br>
            Analisis Harmonik data TMA Pasar Ikan I (DSDA) Tahun 2025.
        </div>
        <br>
        <div style="text-align: justify; font-size: 0.95rem; color: #475569;">
            <strong>⚡ Real-time:</strong>
            <ul style="margin-top: 5px; padding-left: 20px;">
                <li>AWS Maritim Tanjung Priok (BMKG).</li>
                <li>Pintu Air Pasar Ikan I (DSDA).</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
    
   # Footer - Dipisah biar lebih estetik
    st.markdown(f"""
        <div class="footer-card">
            <p style='font-size: 0.72rem; color: #1e3a8a; margin-bottom: 0; font-weight: 600;'>
                © 2026 Stasiun Meteorologi Maritim Tanjung Priok
            </p>
        </div>
        <div style="text-align: center; margin-top: 15px;">
            <p style='font-size: 0.5rem; color: #94a3b8; margin-bottom: 0;'>Developed by</p>
            <span style="color: #64748b; font-weight: 500; font-size: 0.5rem;">E.P. Damanik</span>
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

# --- 5. DATA FUNCTIONS ---
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
    if t_col: 
        df[t_col] = pd.to_datetime(df[t_col], format='mixed', errors='coerce')
    return df.dropna(subset=[t_col, v_col]).sort_values(t_col), t_col, v_col

# --- 6. EXECUTION ---
df_pred, col_tgl, col_val = load_prediction()
live_data = {"aws": get_latest_from_csv(FILE_HISTORY_AWS), "bpbd": get_latest_from_csv(FILE_HISTORY_BPBD)}

# --- 7. DISPLAY ---
if df_pred is not None and not df_pred.empty:
    h_now = df_pred.loc[(df_pred[col_tgl] - sekarang_naive).abs().idxmin(), col_val]
    
    check = {"Prediksi": h_now, "AWS": live_data['aws'], "BPBD": live_data['bpbd']}
    awas = [n for n, v in check.items() if v and v >= 2.5]
    waspada = [n for n, v in check.items() if v and 2.3 <= v < 2.5]

    if awas:
        st.error(f"🚨 STATUS: AWAS ROB! ({', '.join(awas)})", icon="⚠️")
        play_audio("AWAS ROB.mp3") 
    elif waspada:
        st.warning(f"📢 STATUS: WASPADA ROB! ({', '.join(waspada)})", icon="📢")
        play_audio("waspada ROB.mp3")

    df_h = df_pred[df_pred[col_tgl].dt.date == sekarang.date()]
    if not df_h.empty:
        v_max_today, v_min_today = df_h[col_val].max(), df_h[col_val].min()
        st.markdown(f'<div class="summary-box"><span class="summary-text">📅 {sekarang.strftime("%d %b %Y")} | <span style="color: #ef4444;">▲ MAX: {v_max_today:.2f}m</span> | <span style="color: #3b82f6;">▼ MIN: {v_min_today:.2f}m</span></span></div>', unsafe_allow_html=True)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Prediksi Pasut", f"{h_now:.2f} m")
    m2.metric("AWS Tj. Priok", f"{live_data['aws']:.2f} m" if live_data["aws"] else "N/A", delta=f"{(live_data['aws']-h_now):+.2f}m" if live_data['aws'] else None, delta_color="inverse")
    m3.metric("TMA Psr. Ikan", f"{live_data['bpbd']:.2f} m" if live_data["bpbd"] else "N/A", delta=f"{(live_data['bpbd']-h_now):+.2f}m" if live_data["bpbd"] else None, delta_color="inverse")
    
    h_next = df_pred.loc[(df_pred[col_tgl] - (sekarang_naive + timedelta(hours=3))).abs().idxmin(), col_val]
    selisih = h_next - h_now
    icon, status = ("📈", "NAIK") if selisih > 0.05 else ("📉", "TURUN") if selisih < -0.05 else ("↔️", "STAGNAN")
    m4.metric("Tren (3 jam Kedepan)", f"{icon} {status}")

    # --- PLOTLY CHART ---
    t_start, t_end = datetime.combine(tgl_range[0], datetime.min.time()), datetime.combine(tgl_range[1], datetime.max.time())
    fig = go.Figure()
    df_plot = df_pred[(df_pred[col_tgl] >= t_start) & (df_pred[col_tgl] <= t_end)].copy()
    
    if not df_plot.empty:
        # 1. Garis Prediksi
        fig.add_trace(go.Scatter(
            x=df_plot[col_tgl], y=df_plot[col_val], 
            name='Prediksi', mode='lines',
            line=dict(color='rgba(148, 163, 184, 0.7)', dash='dot', width=2, shape='spline'),
        ))
        
        # --- LOGIKA BARU: DOT MAX & MIN SETIAP HARI ---
        unique_days = df_plot[col_tgl].dt.date.unique()
        
        for day in unique_days:
            df_day = df_plot[df_plot[col_tgl].dt.date == day]
            idx_max = df_day[col_val].idxmax()
            idx_min = df_day[col_val].idxmin()
            
            # Marker Max Harian
            fig.add_trace(go.Scatter(
                x=[df_day.loc[idx_max, col_tgl]], y=[df_day.loc[idx_max, col_val]],
                mode='markers+text', name=f'Max {day}',
                marker=dict(color='#ef4444', size=8, symbol='circle'),
                text=[f"{df_day.loc[idx_max, col_val]:.2f}"],
                textposition="top center", showlegend=False
            ))
            
            # Marker Min Harian
            fig.add_trace(go.Scatter(
                x=[df_day.loc[idx_min, col_tgl]], y=[df_day.loc[idx_min, col_val]],
                mode='markers+text', name=f'Min {day}',
                marker=dict(color='#3b82f6', size=8, symbol='circle'),
                text=[f"{df_day.loc[idx_min, col_val]:.2f}"],
                textposition="bottom center", showlegend=False
            ))

        # 2. History Data
        for file, label, color in [(FILE_HISTORY_AWS, 'AWS (Hist)', '#7c3aed'), (FILE_HISTORY_BPBD, 'Psr. Ikan (Hist)', '#f59e0b')]:
            if os.path.exists(file):
                dh = pd.read_csv(file)
                dh['waktu'] = pd.to_datetime(dh['waktu'], format='mixed', errors='coerce')
                dh = dh[(dh['waktu'] >= t_start) & (dh['waktu'] <= t_end)].sort_values('waktu')
                if not dh.empty:
                    fig.add_trace(go.Scatter(
                        x=dh['waktu'], y=dh['nilai'], 
                        name=label, connectgaps=True, mode='lines',
                        line=dict(color=color, width=3.5, shape='spline'),
                    ))

        # 3. Garis Sekarang
        y_max_axis = df_plot[col_val].max() + 0.3
        y_min_axis = df_plot[col_val].min() - 0.2

        fig.add_trace(go.Scatter(
            x=[sekarang_naive, sekarang_naive],
            y=[y_min_axis, y_max_axis],
            mode="lines+text",
            name="Waktu Sekarang",
            line=dict(color="#22c55e", width=2, dash="dash"),
            text=["", f"Sekarang: {sekarang.strftime('%d %b, %H:%M')}"],
            textposition="top center",
            textfont=dict(color="#166534", size=12),
            showlegend=False
        ))
        
        # Threshold
        fig.add_hline(y=2.5, line_dash="dash", line_color="#ef4444")
        fig.add_hline(y=2.3, line_dash="dash", line_color="#ea580c")
        
        fig.update_layout(
            height=500, template="plotly_white", margin=dict(l=10, r=10, t=30, b=10), 
            hovermode="x unified", legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            yaxis=dict(showgrid=True, gridwidth=0.5, gridcolor='rgba(235, 235, 235, 0.8)', title="Tinggi Air (m)", autorange=True),
            xaxis=dict(showgrid=True, gridwidth=0.5, gridcolor='rgba(235, 235, 235, 0.8)')
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.warning("Pilih rentang waktu pada filter di sidebar untuk menampilkan grafik.")

    st.divider()
    c1, c2, c3 = st.columns(3)
    with c1: st.download_button("📥 Scrape AWS Maritim Tj. Priok CSV", open(FILE_HISTORY_AWS, 'rb') if os.path.exists(FILE_HISTORY_AWS) else "", "AWS.csv", use_container_width=True)
    with c2: st.download_button("📥 Scrape Pintu air Pasar Ikan I CSV", open(FILE_HISTORY_BPBD, 'rb') if os.path.exists(FILE_HISTORY_BPBD) else "", "Pasarikan.csv", use_container_width=True)
    with c3: 
        if st.button("🔄 Refresh Data", use_container_width=True): st.cache_data.clear(); st.rerun()
else:
    st.error("Gagal memuat data prediksi.")
