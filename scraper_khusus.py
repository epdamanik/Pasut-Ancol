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

FILE_HISTORY_AWS = 'history_aws_priok.csv'
FILE_HISTORY_BPBD = 'history_bpbd_pasarikan.csv'
LIMIT_SENSOR_ERROR = 3.5

def save_to_csv(filename, waktu, nilai):
    if nilai is None or nilai > LIMIT_SENSOR_ERROR: return
    menit_bulat = (waktu.minute // 15) * 15
    waktu_fixed = waktu.replace(minute=menit_bulat, second=0, microsecond=0)
    waktu_str = waktu_fixed.strftime('%Y-%m-%d %H:%M')
    new_data = pd.DataFrame({'waktu': [waktu_str], 'nilai': [nilai]})
    
    if not os.path.exists(filename):
        new_data.to_csv(filename, index=False)
    else:
        try:
            old_data = pd.read_csv(filename)
            old_data = old_data[old_data['waktu'] != waktu_str]
            combined = pd.concat([old_data, new_data]).sort_values('waktu')
            combined.to_csv(filename, index=False)
        except Exception as e:
            print(f"Error saat simpan CSV: {e}")

def run_scraper():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = None
    res = {"aws": None, "bpbd": None}
    
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        
        # --- AWS BMKG ---
        try:
            print("\n--- Memulai Scraping AWS ---")
            driver.get("http://202.90.199.132/aws-new/monitoring/3000000009")
            el = WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.ID, "waterlevel")))
            time.sleep(3)
            val = float(re.search(r"(\d+[\.,]?\d*)", el.text).group(1).replace(',', '.'))
            if val <= LIMIT_SENSOR_ERROR: 
                res["aws"] = val
                print(f"✅ Hasil AWS: {val} m")
        except Exception as e: print(f"❌ Gagal AWS: {e}")
            
        # --- BPBD (PASAR IKAN) ---
        try:
            print("\n--- Memulai Scraping BPBD ---")
            driver.get("https://poskobanjir.dsdadki.web.id/")
            
            # Cari baris Pasar Ikan
            xpath_pasar_ikan = "//td[contains(text(), 'Pasar Ikan')]/.."
            row_el = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, xpath_pasar_ikan)))
            
            # Langsung tembak kolom ke-4 (Index 4) di dalam baris tersebut
            # Kita ambil span di dalamnya jika ada
            cells = row_el.find_elements(By.TAG_NAME, "td")
            
            # Kita coba ambil teks dari kolom 4 dan kolom 5 (cadangan)
            target_cols = [4, 5, 3] # Urutan prioritas kolom
            for idx in target_cols:
                if len(cells) > idx:
                    raw_text = cells[idx].get_attribute("innerText")
                    print(f"Cek Kolom [{idx}]: '{raw_text}'")
                    
                    # Cari angka dalam teks tersebut
                    match = re.search(r"(-?\d+)", raw_text)
                    if match:
                        num = float(match.group(1))
                        # Jika angka ratusan (cm), kita konversi. Jika satuan (m), biarkan.
                        if abs(num) > 10:
                            final_val = num / 100.0
                        else:
                            final_val = num
                            
                        # Validasi: TMA Pasar Ikan normalnya 1.0m - 2.5m (100-250cm)
                        if 0.1 < abs(final_val) < LIMIT_SENSOR_ERROR:
                            res["bpbd"] = final_val
                            print(f"✅ Kolom [{idx}] valid sebagai TMA: {final_val} m")
                            break

        except Exception as e: print(f"❌ Gagal BPBD: {e}")
            
    except Exception as e: print(f"Driver Error: {e}")
    finally:
        if driver: driver.quit()
    return res

if __name__ == "__main__":
    tz_jkt = pytz.timezone('Asia/Jakarta')
    sekarang = datetime.now(tz_jkt).replace(tzinfo=None)
    print(f"\nEksekusi: {sekarang.strftime('%Y-%m-%d %H:%M:%S')} WIB")
    live_data = run_scraper()
    
    if live_data["aws"] is not None:
        save_to_csv(FILE_HISTORY_AWS, sekarang, live_data["aws"])
        print(f"STAMP -> AWS: {live_data['aws']} m")
    if live_data["bpbd"] is not None:
        waktu_bpbd = sekarang - timedelta(minutes=15)
        save_to_csv(FILE_HISTORY_BPBD, waktu_bpbd, live_data["bpbd"])
        print(f"STAMP -> BPBD: {live_data['bpbd']} m")
