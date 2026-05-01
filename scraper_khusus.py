import os
import time
import re
import pandas as pd
from datetime import datetime
import pytz
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# --- KONFIGURASI ---
# Sesuaikan nama file AWS agar sinkron dengan yang ada di laptop (Ancol)
FILE_HISTORY_AWS = 'history_aws_ancol.csv'
FILE_HISTORY_BPBD = 'history_bpbd_pasarikan.csv'
LIMIT_SENSOR_ERROR = 3.5

def save_to_csv(filename, waktu, nilai):
    """Menyimpan data ke CSV dengan proteksi duplikat dan spasi liar."""
    if nilai is None or nilai > LIMIT_SENSOR_ERROR:
        return
        
    # Pembulatan waktu per 15 menit
    menit_bulat = (waktu.minute // 15) * 15
    waktu_fixed = waktu.replace(minute=menit_bulat, second=0, microsecond=0)
    waktu_str = waktu_fixed.strftime('%Y-%m-%d %H:%M')
    
    new_data = pd.DataFrame({'waktu': [waktu_str], 'nilai': [nilai]})
    
    try:
        if not os.path.exists(filename):
            new_data.to_csv(filename, index=False)
        else:
            old_data = pd.read_csv(filename)
            # Bersihkan data agar tidak ada spasi gaib yang bikin gagal push
            old_data['waktu'] = old_data['waktu'].astype(str).str.strip()
            
            # Gabungkan dan hapus duplikat di jam yang sama
            combined = pd.concat([old_data, new_data])
            combined = combined.drop_duplicates(subset=['waktu'], keep='last').sort_values('waktu')
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
            el = WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.ID, "waterlevel")))
            match = re.search(r"(\d+[\.,]?\d*)", el.text)
            if match:
                val = float(match.group(1).replace(',', '.'))
                if val <= LIMIT_SENSOR_ERROR:
                    res["aws"] = val
                    print(f"Dapat data AWS: {val}m")
        except Exception as e: 
            print(f"Gagal narik AWS: {e}")
            
        # --- 2. SCRAPING BPBD DKI (PASAR IKAN) - VERSI ANTI ERROR REGEX ---
        try:
            print("Mencoba scraping BPBD...")
            driver.get("https://poskobanjir.dsdadki.web.id/")
            
            # Cari baris yang berisi teks 'Pasar Ikan'
            wait = WebDriverWait(driver, 30)
            row_el = wait.until(EC.presence_of_element_located(
                (By.XPATH, "//tr[td[contains(., 'Pasar Ikan')]]")
            ))
            
            # Ambil semua teks di baris tersebut (lebih stabil daripada onclick)
            row_text = row_el.text
            print(f"DEBUG: Baris ketemu -> {row_text}")
            
            # Cari angka pertama yang muncul di baris tersebut
            match = re.search(r"(\d+[\.,]?\d*)", row_text)
            if match:
                raw_val = float(match.group(1).replace(',', '.'))
                
                # Logika pembagi: jika > 500 berarti mm, jika kecil berarti cm
                if raw_val > 500:
                    val = raw_val / 1000
                else:
                    val = raw_val / 100
                    
                if 0.0 < val <= LIMIT_SENSOR_ERROR:
                    res["bpbd"] = val
                    print(f"SUCCESS -> BPBD dapet: {val}m")
            else:
                print("Gagal menemukan angka di teks BPBD")
                
        except Exception as e: 
            print(f"Gagal narik BPBD: {e}")
            
    except Exception as e:
        print(f"Driver Error Utama: {e}")
    finally:
        if driver:
            driver.quit()
        
    return res

if __name__ == "__main__":
    tz_jkt = pytz.timezone('Asia/Jakarta')
    sekarang = datetime.now(tz_jkt).replace(tzinfo=None)
    
    print(f"=== Memulai Eksekusi Scraping: {sekarang.strftime('%Y-%m-%d %H:%M:%S')} WIB ===")
    
    live_data = run_scraper()
    
    # Simpan AWS
    if live_data["aws"] is not None:
        save_to_csv(FILE_HISTORY_AWS, sekarang, live_data["aws"])
        print(f"LOG: File AWS ({FILE_HISTORY_AWS}) diperbarui: {live_data['aws']}m")
    
    # Simpan BPBD
    if live_data["bpbd"] is not None:
        save_to_csv(FILE_HISTORY_BPBD, sekarang, live_data["bpbd"])
        print(f"LOG: File BPBD ({FILE_HISTORY_BPBD}) diperbarui: {live_data['bpbd']}m")
    else:
        print("LOG: Data BPBD kosong, tidak ada yang disimpan.")

    print("=== Eksekusi Selesai ===")
