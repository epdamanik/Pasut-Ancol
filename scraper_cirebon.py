"""
Scraper TMA Cirebon (telemetri PUSHIDROSAL) -> data/cirebon/history_pushidrosal_cirebon.csv

Dijalankan tiap jam oleh GitHub Actions. Setiap run menghasilkan SATU baris:
median dari titik data di sekitar jam bulat (jendela +-5 menit), setelah
titik yang tidak masuk akal (spike / sensor error) dibuang.

Format CSV (dibaca langsung oleh app_pasut.py):
    waktu,nilai,station_id
    2026-11-04 15:00:00,1.2345,3
"""

import csv
import statistics
from datetime import datetime, timedelta, timezone
from pathlib import Path

import requests

BASE_URL = "https://telemetri.pushidrosal.id/API/get-chart-singledata.php"
WIB = timezone(timedelta(hours=7))
STATION_ID = 3  # <-- pastikan ini memang stasiun Cirebon di Pushidrosal

# Path dibuat relatif terhadap lokasi skrip ini (= root repo), jadi aman
# dijalankan dari folder mana pun (termasuk dari GitHub Actions).
CSV_FILE = Path(__file__).resolve().parent / "data" / "cirebon" / "history_pushidrosal_cirebon.csv"
CSV_HEADER = ["waktu", "nilai", "station_id"]

# ---------------------------------------------------------------------------
# FILTER DATA (meter) - sesuaikan dengan kondisi lokal Cirebon.
# Ini filter KUALITAS DATA, bukan ambang rob.
# PENTING: MAX harus lebih tinggi dari ambang AWAS ROB Cirebon (+ margin),
# kalau tidak, kejadian rob asli ikut dianggap spike dan dibuang.
# ---------------------------------------------------------------------------
MAX_ALLOWED_WATER_LEVEL = 2.50
MIN_ALLOWED_WATER_LEVEL = -1.00  # buang nilai sensor error (mis. -999)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
    "Referer": "https://telemetri.pushidrosal.id/enavigation/chart.php",
}


def get_smoothed_hourly_data():
    now_wib = datetime.now(WIB)

    # Target jam bulat (misal jam 15:00:00)
    target_hour = now_wib.replace(minute=0, second=0, microsecond=0)

    # Window 10 menit: menit 55 s/d 05
    win_start = target_hour - timedelta(minutes=5)
    win_end = target_hour + timedelta(minutes=5)

    # Tanggal diambil dari batas window (bukan "hari ini"), supaya jam 00:00
    # tetap membawa titik 23:55-23:59 dari hari sebelumnya.
    tss = win_start.strftime("%Y-%m-%d")
    tse = win_end.strftime("%Y-%m-%d")

    try:
        r = requests.get(
            BASE_URL,
            params={
                "id_station": STATION_ID,
                "tss": tss,
                "tse": tse,
                "data": "Water_Level",
            },
            headers=HEADERS,
            timeout=20,
        )
        r.raise_for_status()
        res_json = r.json()
    except Exception as e:
        print(f"Gagal koneksi API: {e}")
        return

    points = (res_json.get("data") or {}).get("data") or []
    if not points:
        print("Data kosong dari server.")
        return

    # Filter titik dalam jendela waktu & seleksi batas wajar
    raw_count = 0
    valid_values = []
    rejected_count = 0

    for item in points:
        try:
            ts_raw, val = item[0], item[1]
            dt_point = datetime.fromtimestamp(ts_raw / 1000, WIB)
            val_float = float(val)
        except (TypeError, ValueError, IndexError):
            continue  # titik rusak, lewati

        if not (win_start <= dt_point <= win_end):
            continue

        raw_count += 1
        if MIN_ALLOWED_WATER_LEVEL <= val_float <= MAX_ALLOWED_WATER_LEVEL:
            valid_values.append(val_float)
        else:
            rejected_count += 1
            print(
                f"[REJECT] {val_float:.4f} m pada {dt_point.strftime('%H:%M:%S')} "
                f"di luar batas {MIN_ALLOWED_WATER_LEVEL} s/d {MAX_ALLOWED_WATER_LEVEL} m"
            )

    if not valid_values:
        print(
            f"Semua titik ditolak atau tidak ada data pada rentang "
            f"{win_start.strftime('%H:%M')} - {win_end.strftime('%H:%M')}."
        )
        return

    # Median dari data yang lolos filter
    final_value = round(statistics.median(valid_values), 4)
    target_timestamp_str = target_hour.strftime("%Y-%m-%d %H:%M:%S")

    print(
        f"Window {win_start.strftime('%H:%M')}-{win_end.strftime('%H:%M')}: "
        f"Total={raw_count}, Ditolak={rejected_count}, Valid={len(valid_values)} | "
        f"Hasil Akhir: {final_value} m"
    )

    # Simpan ke CSV jika belum ada
    CSV_FILE.parent.mkdir(parents=True, exist_ok=True)
    file_exists = CSV_FILE.exists()

    existing_timestamps = set()
    if file_exists:
        with open(CSV_FILE, "r", encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            next(reader, None)  # lewati header
            for row in reader:
                if row:
                    existing_timestamps.add(row[0])

    if target_timestamp_str in existing_timestamps:
        print(f"Data jam {target_timestamp_str} sudah ada. Skip.")
        return

    with open(CSV_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(CSV_HEADER)
        writer.writerow([target_timestamp_str, final_value, STATION_ID])

    print(f"Berhasil disimpan: {target_timestamp_str} -> {final_value} m")


if __name__ == "__main__":
    get_smoothed_hourly_data()
