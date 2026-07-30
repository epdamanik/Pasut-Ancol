"""
Dashboard Monitoring Tinggi Muka Air (TMA) Real-Time - Tanjung Priok.

Aplikasi Streamlit untuk Stasiun Meteorologi Maritim Tanjung Priok (BMKG)
yang menampilkan:
    - Prediksi pasang surut (analisis harmonik) vs data real-time
    - Status siaga rob (AWAS / WASPADA)
    - Grafik timeseries interaktif dengan penanda max/min harian
    - Evaluasi akurasi prediksi bulanan (RMSE, MAE, %Akurasi)
    - Unduhan data historis

Sumber data:
    - prediksi_pasut_ancol_2026_FINAL_WIB.xlsx  (prediksi harmonik)
    - history_aws_priok.csv                     (observasi AWS BMKG)
    - history_bpbd_pasarikan.csv                (observasi Pintu Air Pasar Ikan/DSDA)
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
# 1. KONSTANTA & KONFIGURASI GLOBAL
# =========================================================================

PAGE_TITLE = "Monitoring TMA Priok"
PAGE_ICON = "🌊"
TIMEZONE = "Asia/Jakarta"
AUTO_REFRESH_INTERVAL_MIN = 15

FILE_LOGO = "logo-bmkg-transparan.png"
FILE_PREDIKSI = "prediksi_pasut_ancol_2026_FINAL_WIB.xlsx"
FILE_HISTORY_AWS = "history_aws_priok.csv"
FILE_HISTORY_BPBD = "history_bpbd_pasarikan.csv"
FILE_AUDIO_AWAS = "AWAS ROB.mp3"
FILE_AUDIO_WASPADA = "waspada ROB.mp3"

# Ambang batas siaga rob (dalam meter)
THRESHOLD_AWAS_ROB = 2.5
THRESHOLD_WASPADA_ROB = 2.3

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
    "prediksi_line": "rgba(148, 163, 184, 0.7)",
}

NAMA_BULAN_ID = [
    "Januari", "Februari", "Maret", "April", "Mei", "Juni",
    "Juli", "Agustus", "September", "Oktober", "November", "Desember",
]


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

def get_latest_from_csv(file_path: str) -> Optional[float]:
    """Ambil nilai observasi terakhir (paling baru) dari berkas CSV histori."""
    if not os.path.exists(file_path):
        return None
    try:
        df = pd.read_csv(file_path)
        df["waktu"] = pd.to_datetime(df["waktu"], format="mixed", errors="coerce")
        return df.dropna(subset=["waktu", "nilai"]).sort_values("waktu").iloc[-1]["nilai"]
    except Exception:
        return None


def load_csv_for_eval(file_path: str) -> pd.DataFrame:
    """Muat CSV histori untuk keperluan evaluasi akurasi bulanan."""
    if not os.path.exists(file_path):
        return pd.DataFrame()
    d = pd.read_csv(file_path)
    d["waktu"] = pd.to_datetime(d["waktu"], format="mixed", errors="coerce")
    return d.dropna(subset=["waktu", "nilai"])


@st.cache_data(ttl=3600)
def load_prediction() -> tuple[Optional[pd.DataFrame], Optional[str], Optional[str]]:
    """Muat data prediksi pasut dari Excel dan deteksi otomatis nama kolom waktu/nilai."""
    if not os.path.exists(FILE_PREDIKSI):
        return None, None, None

    df = pd.read_excel(FILE_PREDIKSI, engine="openpyxl")
    t_col = next((c for c in ["tanggal_prediksi", "Waktu_WIB", "Waktu"] if c in df.columns), None)
    v_col = next((c for c in ["wl_prediksi", "Tinggi_Navigasi_m"] if c in df.columns), None)

    if t_col:
        df[t_col] = pd.to_datetime(df[t_col], format="mixed", errors="coerce")

    return df.dropna(subset=[t_col, v_col]).sort_values(t_col), t_col, v_col


# =========================================================================
# 7. SIDEBAR
# =========================================================================

def render_sidebar(sekarang: datetime) -> tuple:
    """Render sidebar (logo, judul stasiun, filter tanggal, info sumber data, footer)."""
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

        st.markdown(
            "<p style='text-align: center; color: #1e3a8a; margin-top: 15px; "
            "font-size: 0.85rem; font-weight: bold;'>"
            "STASIUN METEOROLOGI MARITIM TANJUNG PRIOK</p>",
            unsafe_allow_html=True,
        )
        st.divider()

        tgl_range = st.date_input(
            "🗓️ Rentang Waktu Grafik",
            value=(sekarang.date() - timedelta(days=1), sekarang.date() + timedelta(days=2)),
        )
        st.link_button("🌐 Web BMKG Tanjung Priok", "https://bmkgtanjungpriok.info/", use_container_width=True)

        with st.expander("ℹ️ Info Sumber Data"):
            st.markdown(
                """
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
                """,
                unsafe_allow_html=True,
            )

        st.markdown(
            """
            <div class="footer-card">
                <p style='font-size: 0.72rem; color: #1e3a8a; margin-bottom: 0; font-weight: 600;'>
                    © 2026 Stasiun Meteorologi Maritim Tanjung Priok
                </p>
            </div>
            <div style="text-align: center; margin-top: 15px; line-height: 1;">
                <p style='font-size: 0.5rem; color: #94a3b8; margin-bottom: 2px;'>Developed by</p>
                <p style="color: #64748b; font-weight: 500; font-size: 0.5rem; margin: 0;">E.P. Damanik</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    return tgl_range


def render_header() -> None:
    st.markdown(
        """
        <div class="header-text">
            <h2 style="margin: 0; color: #0f172a; font-weight: bold; font-size: 1.6rem;">
                MONITORING TINGGI MUKA AIR (TMA) REAL TIME
            </h2>
        </div>
        """,
        unsafe_allow_html=True,
    )


# =========================================================================
# 8. STATUS SIAGA ROB
# =========================================================================

def render_rob_status(h_now: float, live_data: dict) -> None:
    """Cek ambang batas AWAS/WASPADA rob pada prediksi & data real-time, tampilkan banner + audio."""
    check = {"Prediksi": h_now, "AWS": live_data["aws"], "PASAR IKAN": live_data["bpbd"]}
    awas = [n for n, v in check.items() if v and v >= THRESHOLD_AWAS_ROB]
    waspada = [n for n, v in check.items() if v and THRESHOLD_WASPADA_ROB <= v < THRESHOLD_AWAS_ROB]

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


def render_kpi_row(df_pred: pd.DataFrame, col_tgl: str, col_val: str, h_now: float,
                    live_data: dict, sekarang_naive: datetime) -> None:
    """Tampilkan 4 kartu KPI: Prediksi, AWS, Pasar Ikan, dan Tren 3 jam ke depan."""
    m1, m2, m3, m4 = st.columns(4)

    m1.metric("Prediksi Pasut", f"{h_now:.2f} m")

    if live_data["aws"] is not None:
        _render_delta_metric(m2, "AWS Tj. Priok", live_data["aws"], h_now)
    else:
        m2.metric("AWS Tj. Priok", "N/A")

    if live_data["bpbd"] is not None:
        _render_delta_metric(m3, "TMA Psr. Ikan", live_data["bpbd"], h_now)
    else:
        m3.metric("TMA Psr. Ikan", "N/A")

    waktu_target = sekarang_naive + timedelta(hours=TREN_JAM_KEDEPAN)
    h_next = df_pred.loc[(df_pred[col_tgl] - waktu_target).abs().idxmin(), col_val]
    selisih = h_next - h_now
    if selisih > TREN_NAIK_TURUN_TOLERANSI:
        icon, status = "📈", "NAIK"
    elif selisih < -TREN_NAIK_TURUN_TOLERANSI:
        icon, status = "📉", "TURUN"
    else:
        icon, status = "↔️", "STAGNAN"
    m4.metric(f"Tren ({TREN_JAM_KEDEPAN}j Kedepan)", f"{icon} {status}")


# =========================================================================
# 10. GRAFIK TIMESERIES UTAMA
# =========================================================================

def build_main_chart(df_pred: pd.DataFrame, col_tgl: str, col_val: str,
                      tgl_range: tuple, sekarang_naive: datetime, sekarang: datetime) -> Optional[go.Figure]:
    """Susun grafik prediksi vs observasi historis, lengkap dengan marker max/min harian dan garis "sekarang"."""
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

    # Overlay data historis (AWS & Pasar Ikan), warna transparan agar tidak saling menutupi
    for file_path, label, color_rgba in [
        (FILE_HISTORY_AWS, "AWS (Hist)", COLOR_PALETTE["aws_hist"]),
        (FILE_HISTORY_BPBD, "Psr. Ikan (Hist)", COLOR_PALETTE["bpbd_hist"]),
    ]:
        if not os.path.exists(file_path):
            continue
        dh = pd.read_csv(file_path)
        dh["waktu"] = pd.to_datetime(dh["waktu"], format="mixed", errors="coerce")
        dh = dh[(dh["waktu"] >= t_start) & (dh["waktu"] <= t_end)].sort_values("waktu")
        if not dh.empty:
            fig.add_trace(go.Scatter(
                x=dh["waktu"], y=dh["nilai"], name=label, connectgaps=True, mode="lines",
                line=dict(color=color_rgba, width=3.5, shape="spline"),
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

    fig.add_hline(y=THRESHOLD_AWAS_ROB, line_dash="dash", line_color=COLOR_PALETTE["danger"],
                  annotation_text="🚨 AWAS ROB", annotation_position="top right",
                  annotation_font_color=COLOR_PALETTE["danger"], annotation_font_size=12)
    fig.add_hline(y=THRESHOLD_WASPADA_ROB, line_dash="dash", line_color=COLOR_PALETTE["warning"],
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

    df_filtered = df[(df[time_col].dt.month == bulan) & (df[time_col].dt.year == tahun)].copy()
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


def render_monthly_accuracy_section(df_pred: pd.DataFrame, col_tgl: str, col_val: str,
                                     sekarang: datetime) -> None:
    """Render seluruh bagian evaluasi akurasi prediksi bulanan (pemilih bulan + 2 kartu hasil)."""
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
    df_aws_hourly = prepare_hourly_data(
        load_csv_for_eval(FILE_HISTORY_AWS), "waktu", "nilai", selected_month, selected_year
    )
    df_bpbd_hourly = prepare_hourly_data(
        load_csv_for_eval(FILE_HISTORY_BPBD), "waktu", "nilai", selected_month, selected_year
    )

    metrics_aws = calc_monthly_metrics(df_pred_hourly, df_aws_hourly)
    metrics_bpbd = calc_monthly_metrics(df_pred_hourly, df_bpbd_hourly)

    c_res_aws, c_res_bpbd = st.columns(2)
    with c_res_aws:
        render_accuracy_card("📡 Akurasi AWS Tj. Priok", metrics_aws, "#7c3aed", "AWS")
    with c_res_bpbd:
        render_accuracy_card("🌊 Akurasi TMA Psr. Ikan", metrics_bpbd, "#f59e0b", "Pasar Ikan")


# =========================================================================
# 12. FOOTER & UNDUHAN
# =========================================================================

def render_footer_downloads() -> None:
    st.divider()
    c1, c2, c3 = st.columns(3)

    with c1:
        data_aws = open(FILE_HISTORY_AWS, "rb") if os.path.exists(FILE_HISTORY_AWS) else ""
        st.download_button("📥 AWS CSV", data_aws, "AWS.csv", use_container_width=True)

    with c2:
        data_bpbd = open(FILE_HISTORY_BPBD, "rb") if os.path.exists(FILE_HISTORY_BPBD) else ""
        st.download_button("📥 Psr. Ikan CSV", data_bpbd, "Pasarikan.csv", use_container_width=True)

    with c3:
        if st.button("🔄 Refresh Data", use_container_width=True):
            st.cache_data.clear()
            st.rerun()


# =========================================================================
# 13. MAIN
# =========================================================================

def main() -> None:
    setup_smart_autorefresh()

    st.set_page_config(page_title=PAGE_TITLE, layout="wide", page_icon=PAGE_ICON)
    inject_custom_css()

    sekarang, sekarang_naive = get_current_time_jakarta()
    tgl_range = render_sidebar(sekarang)
    render_header()

    df_pred, col_tgl, col_val = load_prediction()
    live_data = {
        "aws": get_latest_from_csv(FILE_HISTORY_AWS),
        "bpbd": get_latest_from_csv(FILE_HISTORY_BPBD),
    }

    if df_pred is None or df_pred.empty:
        st.error("Gagal memuat data prediksi.")
        return

    h_now = df_pred.loc[(df_pred[col_tgl] - sekarang_naive).abs().idxmin(), col_val]

    render_rob_status(h_now, live_data)
    render_daily_summary_box(df_pred, col_tgl, col_val, sekarang)
    render_kpi_row(df_pred, col_tgl, col_val, h_now, live_data, sekarang_naive)

    fig = build_main_chart(df_pred, col_tgl, col_val, tgl_range, sekarang_naive, sekarang)
    if fig is not None:
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})

    render_monthly_accuracy_section(df_pred, col_tgl, col_val, sekarang)
    render_footer_downloads()


if __name__ == "__main__":
    main()
