import os
import time
import re
import pandas as pd
from datetime import datetime, timedelta
import pytz
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- KONFIGURASI ---
FILE_HISTORY_AWS = 'history_aws_priok.csv'
FILE_HISTORY_BPBD = 'history_bpbd_pasarikan.csv'
LIMIT_SENSOR_ERROR = 3.5

def save_to_csv(filename, waktu, nilai):
    """Menyimpan data ke CSV dengan pembulatan waktu per 15 menit."""
    if nilai is None or nilai > LIMIT_SENSOR_ERROR:
        return
        
    # Pembulatan waktu ke bawah (00, 15, 30, 45)
    menit_bulat = (waktu.minute // 15) * 15
    waktu_fixed = waktu.replace(minute=menit_bulat, second=0, microsecond=0)
    waktu_str = waktu_fixed.strftime('%Y-%m-%d %H:%M')
    
    new_data = pd.DataFrame({'waktu': [waktu_str], 'nilai': [nilai]})
    
    if not os.path.exists(filename):
        new_data.to_csv(filename, index=False)
    else:
        try:
            old_data = pd.read_csv(filename)
            # Pastikan kolom waktu dibaca sebagai string untuk perbandingan
            old_data['waktu'] = old_data['waktu'].astype(str)
            
            # Hapus baris jika waktu yang sama sudah ada (biar nggak double)
            old_data = old_data[old_data['waktu'] != waktu_str]
            
            # Gabungkan dan urutkan
            combined = pd.concat([old_data, new_data]).sort_values('waktu')
            combined.to_csv(filename, index=False)
        except Exception as e:
            print(f"Error saat simpan CSV {filename}: {e}")

def run_scraper():
    """Proses pengambilan data dari website menggunakan Selenium."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = None
    res = {"aws": None, "bpbd": None}
    
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        
        # --- 1. SCRAPING AWS BMKG ---
        try:
            print("Mencoba scraping AWS...")
            driver.get("http://202.90.199.132/aws-new/monitoring/3000000009")
            el = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.ID, "waterlevel")))
            # Ambil angka saja, ganti koma jadi titik
            match = re.search(r"(\d+[\.,]?\d*)", el.text)
            if match:
                val = float(match.group(1).replace(',', '.'))
                if val <= LIMIT_SENSOR_ERROR:
                    res["aws"] = val
                    print(f"Dapat data AWS: {val}m")
        except Exception as e: 
            print(f"Gagal narik AWS: {e}")
            
        # --- 2. SCRAPING BPBD DKI (PASAR IKAN) ---
        try:
            print("Mencoba scraping BPBD...")
            driver.get("https://poskobanjir.dsdadki.web.id/")
            # Cari baris yang mengandung teks 'Pasar Ikan'
            row_el = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located((By.XPATH, "//tr[contains(., 'Pasar Ikan')]"))
            )
            script_text = row_el.get_attribute("onclick")
            # Ambil nilai milimeter dari fungsi ShowPopup('Nama', 'Nilai')
            match = re.search(r"ShowPopup\('[^']*',\s*'(\d+)'", script_text)
            if match:
                val = float(match.group(1)) / 1000 # Konversi mm ke meter
                if val <= LIMIT_SENSOR_ERROR:
                    res["bpbd"] = val
                    print(f"Dapat data BPBD: {val}m")
        except Exception as e: 
            print(f"Gagal narik BPBD: {e}")
            
    except Exception as e:
        print(f"Driver Error Utama: {e}")
    finally:
        if driver:
            driver.quit()
        
    return res

if __name__ == "__main__":
    # Setup zona waktu Jakarta
    tz_jkt = pytz.timezone('Asia/Jakarta')
    sekarang = datetime.now(tz_jkt).replace(tzinfo=None)
    
    print(f"=== Memulai Eksekusi Scraping: {sekarang.strftime('%Y-%m-%d %H:%M:%S')} WIB ===")
    
    live_data = run_scraper()
    
    # Simpan AWS jika berhasil ditarik
    if live_data["aws"] is not None:
        save_to_csv(FILE_HISTORY_AWS, sekarang, live_data["aws"])
        print(f"LOG: File AWS diperbarui: {live_data['aws']}m")
    else:
        print("LOG: Data AWS kosong, tidak ada yang disimpan.")
        
    # Simpan BPBD jika berhasil ditarik (SINKRON DENGAN WAKTU AWS)
    if live_data["bpbd"] is not None:
        save_to_csv(FILE_HISTORY_BPBD, sekarang, live_data["bpbd"])
        print(f"LOG: File BPBD diperbarui: {live_data['bpbd']}m")
    else:
        print("LOG: Data BPBD kosong, tidak ada yang disimpan.")

    print("=== Eksekusi Selesai ===")
