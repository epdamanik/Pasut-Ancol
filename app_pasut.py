"""
Dashboard Monitoring Tinggi Muka Air (TMA) Real-Time - Multi Stasiun.

Stasiun yang tersedia (pilih lewat sidebar):
    - Tanjung Priok  (prediksi harmonik + AWS BMKG + Pintu Air Pasar Ikan/DSDA)
    - Cirebon        (prediksi harmonik + telemetri PUSHIDROSAL)

Fitur (sama untuk semua stasiun):
    - Prediksi pasang surut (analisis harmonik) vs data real-time
    - Status siaga rob (AWAS / WASPADA) -> hanya aktif jika ambang batas stasiun diisi
    - Grafik timeseries interaktif dengan penanda max/min harian
    - Evaluasi akurasi prediksi bulanan (RMSE, MAE, %Akurasi)
    - Unduhan data historis

CARA MENAMBAH STASIUN BARU:
    Cukup tambahkan satu entri di dictionary STASIUN (bagian 1B). Tidak perlu
    mengubah fungsi lain.
"""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import pytz
import streamlit as st
from streamlit_autorefresh import st_autorefresh

# =========================================================================
# 1A. KONSTANTA GLOBAL (berlaku untuk semua stasiun)
# =========================================================================

PAGE_ICON = "🌊"
TIMEZONE = "Asia/Jakarta"
AUTO_REFRESH_INTERVAL_MIN = 15

FILE_LOGO = "logo-bmkg-transparan.png"
FILE_AUDIO_AWAS = "AWAS ROB.mp3"
FILE_AUDIO_WASPADA = "waspada ROB.mp3"

# Toleransi perubahan (meter) untuk menentukan status tren
TREN_NAIK_TURUN_TOLERANSI = 0.05
TREN_JAM_KEDEPAN = 3

COLOR_PALETTE = {
    "primary": "#1e3a8a",
    "accent": "#1e40af",
    "danger": "#ef4444",
    "warning": "#ea580c",
    "success": "#22c55e",
    "info_blue": "#3b82f6",
    "aws_hist": "rgba(124, 58, 237, 0.65)",
    "bpbd_hist": "rgba(245, 158, 11, 0.65)",
    "cirebon_hist": "rgba(16, 185, 129, 0.65)",
    "prediksi_line": "rgba(148, 163, 184, 0.7)",
}

NAMA_BULAN_ID = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]

# Nama kolom CSV observasi yang diterima (alias -> nama standar).
# Jadi CSV hasil skrip lama (timestamp, water_level_m) pun tetap terbaca.
KOLOM_ALIAS_OBS = {"timestamp": "waktu", "water_level_m": "nilai"}


# =========================================================================
# 1B. REGISTRY STASIUN  <-- TAMBAH / UBAH STASIUN DI SINI
# =========================================================================

@dataclass(frozen=True)
class Sumber:
    """Satu sumber data observasi real-time (satu file CSV)."""
    key: str               # id unik (tanpa spasi)
    file: str              # path CSV (kolom: waktu, nilai)
    nama_kpi: str          # label kartu KPI
    nama_hist: str         # label di legenda grafik
    nama_status: str       # label di banner AWAS/WASPADA
    nama_akurasi: str      # judul kartu akurasi bulanan
    nama_data: str         # nama singkat untuk pesan "data tidak tersedia"
    warna_garis: str       # warna garis grafik (rgba)
    warna_solid: str       # warna aksen kartu akurasi (hex)
    label_unduh: str       # tulisan tombol unduh
    nama_file_unduh: str   # nama file hasil unduhan


@dataclass(frozen=True)
class Stasiun:
    key: str
    nama_menu: str                 # tampil di pilihan stasiun
    nama_singkat: str              # untuk judul tab browser
    nama_lengkap: str              # judul di sidebar & footer
    file_prediksi: str             # file Excel prediksi
    sumber: tuple                  # tuple[Sumber, ...]
    thr_awas: Optional[float]      # None = stasiun ini tidak punya ambang rob
    thr_waspada: Optional[float]
    web_label: str                 # tulisan tombol link (kosongkan jika tidak ada)
    web_url: str
    info_prediksi: str
    info_realtime: tuple           # tuple[str, ...]


STASIUN: dict[str, Stasiun] = {
    # ---------------------------------------------------------------------
    # TANJUNG PRIOK  (konfigurasi lama, tidak berubah)
    # ---------------------------------------------------------------------
    "priok": Stasiun(
        key="priok",
        nama_menu="Tanjung Priok",
        nama_singkat="Priok",
        nama_lengkap="STASIUN METEOROLOGI MARITIM TANJUNG PRIOK",
        file_prediksi="prediksi_pasut_ancol_2026_FINAL_WIB.xlsx",
        sumber=(
            Sumber(
                key="aws",
                file="history_aws_priok.csv",
                nama_kpi="AWS Tj. Priok",
                nama_hist="AWS (Hist)",
                nama_status="AWS",
                nama_akurasi="📡 Akurasi AWS Tj. Priok",
                nama_data="AWS",
                warna_garis=COLOR_PALETTE["aws_hist"],
                warna_solid="#7c3aed",
                label_unduh="📥 AWS CSV",
                nama_file_unduh="AWS.csv",
            ),
            Sumber(
                key="bpbd",
                file="history_bpbd_pasarikan.csv",
                nama_kpi="TMA Psr. Ikan",
                nama_hist="Psr. Ikan (Hist)",
                nama_status="PASAR IKAN",
                nama_akurasi="🌊 Akurasi TMA Psr. Ikan",
                nama_data="Pasar Ikan",
                warna_garis=COLOR_PALETTE["bpbd_hist"],
                warna_solid="#f59e0b",
                label_unduh="📥 Psr. Ikan CSV",
                nama_file_unduh="Pasarikan.csv",
            ),
        ),
        thr_awas=2.5,
        thr_waspada=2.3,
        web_label="🌐 Web BMKG Tanjung Priok",
        web_url="https://bmkgtanjungpriok.info/",
        info_prediksi="Analisis Harmonik data TMA Pasar Ikan I (DSDA) Tahun 2025.",
        info_realtime=(
            "AWS Maritim Tanjung Priok (BMKG).",
            "Pintu Air Pasar Ikan I (DSDA).",
        ),
    ),
    # ---------------------------------------------------------------------
    # CIREBON
    # Bagian bertanda  <-- ISI  perlu disesuaikan oleh pemilik dashboard.
    # ---------------------------------------------------------------------
    "cirebon": Stasiun(
        key="cirebon",
        nama_menu="Cirebon",
        nama_singkat="Cirebon",
        nama_lengkap="STASIUN CIREBON",                                    # <-- ISI nama resmi
        file_prediksi="data/cirebon/prediksi_pasut_cirebon_2026.xlsx",
        sumber=(
            Sumber(
                key="pushidrosal",
                file="data/cirebon/history_pushidrosal_cirebon.csv",
                nama_kpi="TMA Cirebon",
                nama_hist="TMA Cirebon (Hist)",
                nama_status="CIREBON",
                nama_akurasi="🌊 Akurasi TMA Cirebon",
                nama_data="Cirebon",
                warna_garis=COLOR_PALETTE["cirebon_hist"],
                warna_solid="#10b981",
                label_unduh="📥 Cirebon CSV",
                nama_file_unduh="Cirebon.csv",
            ),
        ),
        thr_awas=None,                                                     # <-- ISI ambang AWAS Cirebon (meter), None = nonaktif
        thr_waspada=None,                                                  # <-- ISI ambang WASPADA Cirebon (meter), None = nonaktif
        web_label="",                                                      # <-- ISI mis. "🌐 Web BMKG Cirebon" (kosong = tombol disembunyikan)
        web_url="",
        info_prediksi="Analisis Harmonik data TMA Cirebon.",              # <-- ISI sumber data prediksi
        info_realtime=("TMA Cirebon (Telemetri PUSHIDROSAL).",),
    ),
}

DEFAULT_STASIUN = "priok"


def resolve_station_key() -> str:
    """Tentukan stasiun aktif: pilihan terakhir user > parameter URL (?stasiun=...) > default."""
    key = st.session_state.get("stasiun_key") or st.query_params.get("stasiun", DEFAULT_STASIUN)
    return key if key in STASIUN else DEFAULT_STASIUN


# =========================================================================
# 2. AUTO REFRESH (sinkron ke kelipatan 15 menit terdekat)
# =========================================================================

def setup_smart_autorefresh(interval_minutes: int = AUTO_REFRESH_INTERVAL_MIN) -> None:
    """Jadwalkan auto-refresh agar selalu jatuh pas di kelipatan interval (mis. :00, :15, :30, :45)."""
    now_sync = datetime.now()
    seconds_to_next = ((interval_minutes - (now_sync.minute % interval_minutes)) * 60) - now_sync.second
    if seconds_to_next <= 0:
        seconds_to_next = interval_minutes * 60
    st_autorefresh(interval=seconds_to_next * 1000, key="datarefresh")


# =========================================================================
# 3. STYLING (CSS)
# =========================================================================

def inject_custom_css() -> None:
    st.markdown(
        f"""
        <style>
        [data-baseweb="popover"] {{
            transform: scale(0.95) !important;
            transform-origin: top left !important;
        }}
        [data-baseweb="popover"] > div {{ max-width: 260px !important; }}

        .block-container {{
            padding-top: 0.5rem !important;
            padding-bottom: 0rem !important;
            max-width: 95% !important;
        }}
        [data-testid="stVerticalBlock"] > div {{ gap: 0px !important; }}
        .stApp {{ background-color: #ffffff; }}

        .header-text {{
            text-align: center;
            width: 100%;
            margin-top: -15px;
            margin-bottom: 0px !important;
            padding-bottom: 0px !important;
        }}

        [data-testid="stSidebar"] [data-testid="stImage"] {{
            text-align: center !important;
            display: block !important;
            margin-left: auto !important;
            margin-right: auto !important;
            width: 100% !important;
        }}
        [data-testid="stSidebar"] [data-testid="stImage"] img {{
            max-width: 90px !important;
            margin-left: auto !important;
            margin-right: auto !important;
            display: inline-block !important;
        }}

        div[data-testid="stMetric"] {{
            background-color: #ffffff !important;
            border: 1px solid #e2e8f0 !important;
            border-left: 4px solid {COLOR_PALETTE['accent']} !important;
            padding: 4px 10px !important;
            border-radius: 8px !important;
            box-shadow: 0 1px 2px rgba(0,0,0,0.05) !important;
            min-height: 55px !important;
            display: flex !important;
            flex-direction: column !important;
            justify-content: center !important;
        }}
        div[data-testid="stMetricLabel"] {{
            color: {COLOR_PALETTE['primary']} !important;
            font-weight: 700 !important;
            font-size: 0.7rem !important;
            margin-bottom: -10px !important;
            white-space: nowrap !important;
        }}
        [data-testid="stMetricValue"] {{
            font-size: 15px !important;
            font-weight: 800 !important;
            color: #0f172a !important;
            white-space: nowrap !important;
        }}
        div[data-testid="stMetricDelta"] {{ display: none !important; }}
        div[data-testid="column"] {{ padding: 0 5px !important; }}

        .summary-box {{
            background-color: #f1f5f9 !important;
            padding: 8px !important;
            border-radius: 10px !important;
            margin-top: -15px !important;
            margin-bottom: 10px !important;
            border-left: 5px solid {COLOR_PALETTE['primary']} !important;
            text-align: center !important;
        }}
        .summary-text {{ font-weight: 850 !important; font-size: 0.9rem !important; color: #0f172a !important; }}

        .footer-card {{
            margin-top: 30px; padding: 12px; border-radius: 10px;
            background-color: #f8fafc; border: 1px solid #e2e8f0;
            text-align: center;
        }}
        footer {{visibility: hidden;}}
        </style>
        """,
        unsafe_allow_html=True,
    )


# =========================================================================
# 4. UTILITAS WAKTU
# =========================================================================

def get_current_time_jakarta() -> tuple[datetime, datetime]:
    """Kembalikan (waktu_aware, waktu_naive) untuk zona waktu Asia/Jakarta."""
    tz_jkt = pytz.timezone(TIMEZONE)
    sekarang = datetime.now(tz_jkt)
    return sekarang, sekarang.replace(tzinfo=None)


# =========================================================================
# 5. AUDIO / NOTIFIKASI
# =========================================================================

def play_audio(file_path: str) -> None:
    """Putar berkas audio (mis. sirine peringatan) secara otomatis jika ada."""
    if not os.path.exists(file_path):
        return
    with open(file_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    st.components.v1.html(
        f'<audio autoplay><source src="data:audio/mp3;base64,{b64}" type="audio/mp3"></audio>',
        height=0,
    )


# =========================================================================
# 6. DATA LOADING
# =========================================================================

@st.cache_data(ttl=60)
def load_obs(file_path: str) -> pd.DataFrame:
    """
    Muat CSV observasi. Hasil selalu berkolom [waktu, nilai] (urut waktu).
    Kolom ekstra (mis. station_id) dibuang. Jika file hilang/rusak -> DataFrame kosong.
    """
    kosong = pd.DataFrame(columns=["waktu", "nilai"])
    if not os.path.exists(file_path):
        return kosong
    try:
        d = pd.read_csv(file_path).rename(columns=KOLOM_ALIAS_OBS)
    except Exception:
        return kosong
    if not {"waktu", "nilai"}.issubset(d.columns):
        return kosong

    d["waktu"] = pd.to_datetime(d["waktu"], format="mixed", errors="coerce")
    d["nilai"] = pd.to_numeric(d["nilai"], errors="coerce")
    d = d.dropna(subset=["waktu", "nilai"])[["waktu", "nilai"]]
    return d.sort_values("waktu").reset_index(drop=True)


def get_latest_from_csv(file_path: str) -> Optional[float]:
    """Ambil nilai observasi terakhir (paling baru) dari berkas CSV histori."""
    d = load_obs(file_path)
    if d.empty:
        return None
    return float(d.iloc[-1]["nilai"])


@st.cache_data(ttl=3600)
def load_prediction(file_path: str) -> tuple[Optional[pd.DataFrame], Optional[str], Optional[str]]:
    """Muat data prediksi pasut dari Excel dan deteksi otomatis nama kolom waktu/nilai."""
    if not os.path.exists(file_path):
        return None, None, None

    df = pd.read_excel(file_path, engine="openpyxl")
    t_col = next((c for c in ["tanggal_prediksi", "Waktu_WIB", "Waktu"] if c in df.columns), None)
    v_col = next((c for c in ["wl_prediksi", "Tinggi_Navigasi_m"] if c in df.columns), None)
    if t_col is None or v_col is None:
        return None, None, None

    df[t_col] = pd.to_datetime(df[t_col], format="mixed", errors="coerce")
    df[v_col] = pd.to_numeric(df[v_col], errors="coerce")
    return df.dropna(subset=[t_col, v_col]).sort_values(t_col).reset_index(drop=True), t_col, v_col


# =========================================================================
# 7. SIDEBAR
# =========================================================================

def render_sidebar(sekarang: datetime) -> tuple[Stasiun, tuple]:
    """Render sidebar (logo, pilihan stasiun, filter tanggal, info sumber data, footer)."""
    with st.sidebar:
        if os.path.exists(FILE_LOGO):
            with open(FILE_LOGO, "rb") as f:
                encoded = base64.b64encode(f.read()).decode()
            st.markdown(
                f"""
                <div style="display: flex; justify-content: center; align-items: center;
                            width: 100%; margin-top: 25px; margin-bottom: 10px;">
                    <img src="data:image/png;base64,{encoded}" style="width: 85px; height: auto;">
                </div>
                """,
                unsafe_allow_html=True,
            )

        # ---- Pilihan stasiun ----
        if "stasiun_key" not in st.session_state:
            st.session_state["stasiun_key"] = resolve_station_key()
        pilih = st.selectbox(
            "📍 Pilih Stasiun",
            list(STASIUN.keys()),
            format_func=lambda k: STASIUN[k].nama_menu,
            key="stasiun_key",
        )
        cfg = STASIUN[pilih]
        # Simpan ke URL supaya link bisa dibagikan (?stasiun=cirebon)
        if st.query_params.get("stasiun") != pilih:
            st.query_params["stasiun"] = pilih

        st.markdown(
            f"<p style='text-align: center; color: #1e3a8a; margin-top: 15px; "
            f"font-size: 0.85rem; font-weight: bold;'>{cfg.nama_lengkap}</p>",
            unsafe_allow_html=True,
        )
        st.divider()

        tgl_range = st.date_input(
            "🗓️ Rentang Waktu Grafik",
            value=(sekarang.date() - timedelta(days=1), sekarang.date() + timedelta(days=2)),
        )
        if cfg.web_url and cfg.web_label:
            st.link_button(cfg.web_label, cfg.web_url, use_container_width=True)

        with st.expander("ℹ️ Info Sumber Data"):
            daftar_realtime = "".join(f"<li>{item}</li>" for item in cfg.info_realtime)
            st.markdown(
                f"""
                <div style="text-align: justify; font-size: 0.95rem; color: #475569;">
                    <strong>📍 Prediksi:</strong><br>
                    {cfg.info_prediksi}
                </div>
                <br>
                <div style="text-align: justify; font-size: 0.95rem; color: #475569;">
                    <strong>⚡ Real-time:</strong>
                    <ul style="margin-top: 5px; padding-left: 20px;">
                        {daftar_realtime}
                    </ul>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown(
            f"""
            <div class="footer-card">
                <p style='font-size: 0.72rem; color: #1e3a8a; margin-bottom: 0; font-weight: 600;'>
                    © 2026 {cfg.nama_lengkap.title()}
                </p>
            </div>
            <div style="text-align: center; margin-top: 15px; line-height: 1;">
                <p style='font-size: 0.5rem; color: #94a3b8; margin-bottom: 2px;'>Developed by</p>
                <p style="color: #64748b; font-weight: 500; font-size: 0.5rem; margin: 0;">E.P. Damanik</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    return cfg, tgl_range


def render_header(cfg: Stasiun) -> None:
    st.markdown(
        f"""
        <div class="header-text">
            <h2 style="margin: 0; color: #0f172a; font-weight: bold; font-size: 1.6rem;">
                MONITORING TINGGI MUKA AIR (TMA) REAL TIME
            </h2>
            <p style="margin: 2px 0 8px 0; color: #475569; font-size: 0.85rem; font-weight: 600;">
                📍 {cfg.nama_menu}
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================================
# 8. STATUS SIAGA ROB
# =========================================================================

def render_rob_status(cfg: Stasiun, h_now: float, live_data: dict) -> None:
    """Cek ambang batas AWAS/WASPADA rob pada prediksi & data real-time, tampilkan banner + audio."""
    if cfg.thr_awas is None or cfg.thr_waspada is None:
        return  # stasiun ini belum punya ambang rob

    check = {"Prediksi": h_now}
    for s in cfg.sumber:
        check[s.nama_status] = live_data.get(s.key)

    awas = [n for n, v in check.items() if v is not None and v >= cfg.thr_awas]
    waspada = [n for n, v in check.items() if v is not None and cfg.thr_waspada <= v < cfg.thr_awas]

    if awas:
        st.error(f"🚨 STATUS: AWAS ROB! ({', '.join(awas)})", icon="⚠️")
        play_audio(FILE_AUDIO_AWAS)
    elif waspada:
        st.warning(f"📢 STATUS: WASPADA ROB! ({', '.join(waspada)})", icon="📢")
        play_audio(FILE_AUDIO_WASPADA)


# =========================================================================
# 9. SUMMARY BOX & KARTU KPI
# =========================================================================

def render_daily_summary_box(df_pred: pd.DataFrame, col_tgl: str, col_val: str, sekarang: datetime) -> None:
    """Tampilkan ringkasan nilai max/min prediksi untuk hari ini."""
    df_h = df_pred[df_pred[col_tgl].dt.date == sekarang.date()]
    if df_h.empty:
        return

    idx_max, idx_min = df_h[col_val].idxmax(), df_h[col_val].idxmin()
    v_max, t_max = df_h.loc[idx_max, col_val], df_h.loc[idx_max, col_tgl].strftime("%H:%M")
    v_min, t_min = df_h.loc[idx_min, col_val], df_h.loc[idx_min, col_tgl].strftime("%H:%M")

    st.markdown(
        f"""
        <div class="summary-box">
            <span class="summary-text">
                📅 {sekarang.strftime("%d %b %Y")} |
                <span style="color: {COLOR_PALETTE['danger']};">▲ MAX: {v_max:.2f}m ({t_max})</span> |
                <span style="color: {COLOR_PALETTE['info_blue']};">▼ MIN: {v_min:.2f}m ({t_min})</span>
            </span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_delta_metric(column, label: str, value: float, h_now: float) -> None:
    """Kartu metrik dengan panah naik/turun relatif terhadap nilai prediksi saat ini."""
    delta = value - h_now
    icon, color = ("▲", COLOR_PALETTE["danger"]) if delta > 0 else ("▼", COLOR_PALETTE["success"])
    column.markdown(
        f"""
        <div data-testid="stMetric">
            <label data-testid="stMetricLabel">{label}</label>
            <div data-testid="stMetricValue">
                {value:.2f} m
                <span style="color: {color}; font-size: 0.8rem; font-weight: bold;">{icon} ({delta:+.2f})</span>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_kpi_row(cfg: Stasiun, df_pred: pd.DataFrame, col_tgl: str, col_val: str, h_now: float,
                   live_data: dict, sekarang_naive: datetime) -> None:
    """Kartu KPI: Prediksi, satu kartu per sumber observasi, dan Tren beberapa jam ke depan."""
    cols = st.columns(len(cfg.sumber) + 2)

    cols[0].metric("Prediksi Pasut", f"{h_now:.2f} m")

    for col, s in zip(cols[1:-1], cfg.sumber):
        nilai = live_data.get(s.key)
        if nilai is not None:
            _render_delta_metric(col, s.nama_kpi, nilai, h_now)
        else:
            col.metric(s.nama_kpi, "N/A")

    waktu_target = sekarang_naive + timedelta(hours=TREN_JAM_KEDEPAN)
    h_next = df_pred.loc[(df_pred[col_tgl] - waktu_target).abs().idxmin(), col_val]
    selisih = h_next - h_now
    if selisih > TREN_NAIK_TURUN_TOLERANSI:
        icon, status = "📈", "NAIK"
    elif selisih < -TREN_NAIK_TURUN_TOLERANSI:
        icon, status = "📉", "TURUN"
    else:
        icon, status = "↔️", "STAGNAN"
    cols[-1].metric(f"Tren ({TREN_JAM_KEDEPAN}j Kedepan)", f"{icon} {status}")


# =========================================================================
# 10. GRAFIK TIMESERIES UTAMA
# =========================================================================

def build_main_chart(cfg: Stasiun, df_pred: pd.DataFrame, col_tgl: str, col_val: str,
                     tgl_range: tuple, sekarang_naive: datetime, sekarang: datetime) -> Optional[go.Figure]:
    """Susun grafik prediksi vs observasi historis, lengkap dengan marker max/min harian dan garis "sekarang"."""
    if len(tgl_range) != 2:
        return None  # user baru memilih tanggal awal; tunggu tanggal akhir

    t_start = datetime.combine(tgl_range[0], datetime.min.time())
    t_end = datetime.combine(tgl_range[1], datetime.max.time())

    df_plot = df_pred[(df_pred[col_tgl] >= t_start) & (df_pred[col_tgl] <= t_end)].copy()
    if df_plot.empty:
        return None

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=df_plot[col_tgl], y=df_plot[col_val], name="Prediksi", mode="lines",
        line=dict(color=COLOR_PALETTE["prediksi_line"], dash="dot", width=2, shape="spline"),
    ))

    # Marker nilai maksimum & minimum untuk setiap hari dalam rentang
    for day in df_plot[col_tgl].dt.date.unique():
        df_day = df_plot[df_plot[col_tgl].dt.date == day]
        idx_max_p, idx_min_p = df_day[col_val].idxmax(), df_day[col_val].idxmin()
        fig.add_trace(go.Scatter(
            x=[df_day.loc[idx_max_p, col_tgl]], y=[df_day.loc[idx_max_p, col_val]],
            mode="markers+text", marker=dict(color=COLOR_PALETTE["danger"], size=8),
            text=[f"{df_day.loc[idx_max_p, col_val]:.2f}"], textposition="top center", showlegend=False,
        ))
        fig.add_trace(go.Scatter(
            x=[df_day.loc[idx_min_p, col_tgl]], y=[df_day.loc[idx_min_p, col_val]],
            mode="markers+text", marker=dict(color=COLOR_PALETTE["info_blue"], size=8),
            text=[f"{df_day.loc[idx_min_p, col_val]:.2f}"], textposition="bottom center", showlegend=False,
        ))

    # Overlay data historis tiap sumber observasi, warna transparan agar tidak saling menutupi
    for s in cfg.sumber:
        dh = load_obs(s.file)
        if dh.empty:
            continue
        dh = dh[(dh["waktu"] >= t_start) & (dh["waktu"] <= t_end)]
        if not dh.empty:
            fig.add_trace(go.Scatter(
                x=dh["waktu"], y=dh["nilai"], name=s.nama_hist, connectgaps=True, mode="lines",
                line=dict(color=s.warna_garis, width=3.5, shape="spline"),
            ))

    # Garis vertikal penanda waktu "sekarang"
    y_max_axis = df_plot[col_val].max() + 0.3
    y_min_axis = df_plot[col_val].min() - 0.2
    fig.add_trace(go.Scatter(
        x=[sekarang_naive, sekarang_naive], y=[y_min_axis, y_max_axis],
        mode="lines+text", line=dict(color=COLOR_PALETTE["success"], width=2, dash="dash"),
        text=["", f"Sekarang: {sekarang.strftime('%d %b, %H:%M')}"],
        textposition="top center", showlegend=False,
    ))

    # Garis ambang rob (hanya jika stasiun punya ambang)
    if cfg.thr_awas is not None:
        fig.add_hline(y=cfg.thr_awas, line_dash="dash", line_color=COLOR_PALETTE["danger"],
                      annotation_text="🚨 AWAS ROB", annotation_position="top right",
                      annotation_font_color=COLOR_PALETTE["danger"], annotation_font_size=12)
    if cfg.thr_waspada is not None:
        fig.add_hline(y=cfg.thr_waspada, line_dash="dash", line_color=COLOR_PALETTE["warning"],
                      annotation_text="📢 WASPADA ROB", annotation_position="top right",
                      annotation_font_color=COLOR_PALETTE["warning"], annotation_font_size=12)

    fig.update_layout(
        height=450,
        template="plotly_white",
        margin=dict(l=10, r=10, t=30, b=10),
        hovermode="x unified",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
    )
    return fig


# =========================================================================
# 11. AKURASI PREDIKSI BULANAN
# =========================================================================

@dataclass
class AkurasiMetrik:
    rmse: float
    mae: float
    akurasi: float
    jumlah_data: int


def prepare_hourly_data(df: pd.DataFrame, time_col: str, val_col: str,
                        bulan: int, tahun: int) -> pd.DataFrame:
    """Filter data ke bulan/tahun terpilih lalu resample menjadi rata-rata per-jam."""
    if df is None or df.empty:
        return pd.DataFrame()

    df_filtered = df[(df[time_col].dt.month == bulan) & (df[time_col].dt.year == tahun)]
    df_filtered = df_filtered[[time_col, val_col]].copy()
    if df_filtered.empty:
        return pd.DataFrame()

    df_filtered.set_index(time_col, inplace=True)
    df_hourly = df_filtered.resample("1h").mean(numeric_only=True).reset_index()
    df_hourly.rename(columns={time_col: "waktu", val_col: "nilai"}, inplace=True)
    return df_hourly.dropna()


def calc_monthly_metrics(pred_df: pd.DataFrame, obs_df: pd.DataFrame) -> Optional[AkurasiMetrik]:
    """Hitung RMSE, MAE, dan persentase akurasi antara prediksi dan observasi per-jam."""
    if pred_df.empty or obs_df.empty:
        return None

    merged = pd.merge(obs_df, pred_df, on="waktu", suffixes=("_obs", "_pred")).dropna()
    if merged.empty:
        return None

    y_true, y_pred = merged["nilai_obs"], merged["nilai_pred"]
    mae = float(np.mean(np.abs(y_true - y_pred)))
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))

    mean_true = np.mean(y_true)
    akurasi = max(0.0, 100 - (mae / abs(mean_true) * 100)) if mean_true != 0 else 0.0

    return AkurasiMetrik(rmse=rmse, mae=mae, akurasi=akurasi, jumlah_data=len(merged))


def render_accuracy_card(title: str, metrik: Optional[AkurasiMetrik], border_color: str,
                         nama_sumber: str) -> None:
    st.markdown(
        f"""<div style='background-color:#f8fafc; padding:15px; border-radius:10px;
                border-left:5px solid {border_color}; border: 1px solid #e2e8f0;
                margin-bottom: 10px; box-shadow: 0 1px 3px rgba(0,0,0,0.05);'>
            <h5 style='color: #475569; margin-top:0;'>{title}</h5>
        </div>""",
        unsafe_allow_html=True,
    )

    if metrik is None:
        st.warning(f"Data observasi {nama_sumber} tidak tersedia untuk bulan ini.")
        return

    st.metric("Total Akurasi", f"{metrik.akurasi:.1f}%")
    col_rmse, col_mae = st.columns(2)
    col_rmse.metric("RMSE", f"{metrik.rmse:.2f} m")
    col_mae.metric("MAE", f"{metrik.mae:.2f} m")
    st.caption(f"📌 Dihitung dari {metrik.jumlah_data} titik data observasi per-jam.")


def render_monthly_accuracy_section(cfg: Stasiun, df_pred: pd.DataFrame, col_tgl: str, col_val: str,
                                    sekarang: datetime) -> None:
    """Render seluruh bagian evaluasi akurasi prediksi bulanan (pemilih bulan + kartu hasil per sumber)."""
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.divider()
    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown(
        """
        <div style="background-color: #1e3a8a; padding: 10px; border-radius: 8px;
                    margin-bottom: 20px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
            <h4 style="color: white; margin: 0; text-align: center; font-size: 1.15rem; letter-spacing: 0.5px;">
                📊 AKURASI PREDIKSI BULANAN
            </h4>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # Default: bulan sebelumnya dari bulan berjalan
    awal_bulan_ini = sekarang.replace(day=1)
    bulan_lalu = awal_bulan_ini - timedelta(days=1)
    default_month_idx = bulan_lalu.month - 1
    default_year = bulan_lalu.year

    _, c_pilih1, c_pilih2, _ = st.columns([1, 1.5, 1.5, 1])

    with c_pilih1:
        selected_month_name = st.selectbox("Pilih Bulan", NAMA_BULAN_ID, index=default_month_idx)
        selected_month = NAMA_BULAN_ID.index(selected_month_name) + 1

    with c_pilih2:
        years = list(range(2024, sekarang.year + 2))
        default_year_idx = years.index(default_year) if default_year in years else 0
        selected_year = st.selectbox("Pilih Tahun", years, index=default_year_idx)

    df_pred_hourly = prepare_hourly_data(df_pred.copy(), col_tgl, col_val, selected_month, selected_year)

    # Satu kartu per sumber observasi. Jika hanya satu sumber, taruh di tengah.
    if len(cfg.sumber) == 1:
        kolom_kartu = [st.columns([1, 2, 1])[1]]
    else:
        kolom_kartu = st.columns(len(cfg.sumber))

    for kolom, s in zip(kolom_kartu, cfg.sumber):
        df_obs_hourly = prepare_hourly_data(load_obs(s.file), "waktu", "nilai", selected_month, selected_year)
        metrik = calc_monthly_metrics(df_pred_hourly, df_obs_hourly)
        with kolom:
            render_accuracy_card(s.nama_akurasi, metrik, s.warna_solid, s.nama_data)


# =========================================================================
# 12. FOOTER & UNDUHAN
# =========================================================================

def render_footer_downloads(cfg: Stasiun) -> None:
    st.divider()
    cols = st.columns(len(cfg.sumber) + 1)

    for col, s in zip(cols[:-1], cfg.sumber):
        with col:
            ada = os.path.exists(s.file)
            data = open(s.file, "rb").read() if ada else b""
            st.download_button(
                s.label_unduh, data, s.nama_file_unduh,
                use_container_width=True, disabled=not ada, key=f"dl_{cfg.key}_{s.key}",
            )

    with cols[-1]:
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()


# =========================================================================
# 13. MAIN
# =========================================================================

def main() -> None:
    # set_page_config harus jadi perintah Streamlit pertama
    cfg_awal = STASIUN[resolve_station_key()]
    st.set_page_config(page_title=f"Monitoring TMA {cfg_awal.nama_singkat}", layout="wide", page_icon=PAGE_ICON)

    setup_smart_autorefresh()
    inject_custom_css()

    sekarang, sekarang_naive = get_current_time_jakarta()
    cfg, tgl_range = render_sidebar(sekarang)
    render_header(cfg)

    df_pred, col_tgl, col_val = load_prediction(cfg.file_prediksi)
    live_data = {s.key: get_latest_from_csv(s.file) for s in cfg.sumber}

    if df_pred is None or df_pred.empty:
        st.error(
            f"Gagal memuat data prediksi stasiun {cfg.nama_menu}. "
            f"Pastikan file `{cfg.file_prediksi}` ada di repo, berformat .xlsx, dan punya kolom waktu "
            f"(`tanggal_prediksi` / `Waktu_WIB` / `Waktu`) serta nilai (`wl_prediksi` / `Tinggi_Navigasi_m`)."
        )
        return

    h_now = df_pred.loc[(df_pred[col_tgl] - sekarang_naive).abs().idxmin(), col_val]

    render_rob_status(cfg, h_now, live_data)
    render_daily_summary_box(df_pred, col_tgl, col_val, sekarang)
    render_kpi_row(cfg, df_pred, col_tgl, col_val, h_now, live_data, sekarang_naive)

    fig = build_main_chart(cfg, df_pred, col_tgl, col_val, tgl_range, sekarang_naive, sekarang)
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    render_monthly_accuracy_section(cfg, df_pred, col_tgl, col_val, sekarang)
    render_footer_downloads(cfg)


if __name__ == "__main__":
    main()
