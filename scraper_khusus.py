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
    # Bulatkan ke interval 15 menit terdekat
    menit_bulat = (waktu.minute // 15) * 15
    waktu_fixed = waktu.replace(minute=menit_bulat, second=0, microsecond=0)
    waktu_str = waktu_fixed.strftime('%Y-%m-%d %H:%M')
    new_data = pd.DataFrame({'waktu': [waktu_str], 'nilai': [nilai]})
    
    if not os.path.exists(filename):
        new_data.to_csv(filename, index=False)
    else:
        try:
            old_data = pd.read_csv(filename)
            # Hapus data lama di jam yang sama agar tidak duplikat
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
        
        # --- SCRAPING AWS BMKG ---
        try:
            print("\n--- Memulai Scraping AWS ---")
            driver.set_page_load_timeout(30) 
            driver.get("http://202.90.199.132/aws-new/monitoring/3000000009")
            
            el = WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.ID, "waterlevel")))
            time.sleep(3) 
            
            val_text = el.text.strip()
            match = re.search(r"(\d+[\.,]?\d*)", val_text)
            if match:
                val = float(match.group(1).replace(',', '.'))
                if val <= LIMIT_SENSOR_ERROR: 
                    res["aws"] = val
                    print(f"✅ Hasil AWS: {val} m")
        except Exception as e: 
            print(f"❌ Gagal AWS: {e}")
            
        # --- SCRAPING BPBD (POSKO BANJIR) ---
        try:
            print("\n--- Memulai Scraping BPBD ---")
            driver.get("https://poskobanjir.dsdadki.web.id/")
            
            xpath_pasar_ikan = "//td[contains(text(), 'Pasar Ikan')]/.."
            row_el = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, xpath_pasar_ikan)))
            
            cells = row_el.find_elements(By.TAG_NAME, "td")
            val_tma = None
            
            print("Mengecek data (Arah Terbalik: Kanan ke Kiri)...")
            # Kita cek dari kolom paling belakang untuk menghindari Status Siaga (1, 2, 3, 4)
            for idx in reversed(range(len(cells))):
                txt = cells[idx].text.strip()
                if not txt: continue
                
                # Ekstrak angka (desimal/negatif)
                match_num = re.search(r"(-?\d+[\.,]?\d*)", txt)
                
                if match_num:
                    raw_val = match_num.group(1).replace(',', '.')
                    temp_val = float(raw_val)
                    print(f"Kolom [{idx}] terdeteksi: {temp_val}")
                    
                    # LOGIKA FILTER ANTI-SIAGA:
                    # Abaikan angka bulat 1.0 s/d 4.0 di kolom index besar (biasanya status siaga)
                    if temp_val in [1.0, 2.0, 3.0, 4.0] and idx > 3:
                        print(f"--> Kolom [{idx}] dilewati (dicurigai Status Siaga)")
                        continue
                    
                    # Abaikan nomor urut (index 0, 1)
                    if idx > 1:
                        # Jika angka ratusan/ribuan (CM)
                        if abs(temp_val) > 50:
                            val_tma = temp_val / 100.0
                        # Jika angka satuan murni (Meter) tapi bukan status siaga bulat
                        elif -5.0 < temp_val < 5.0 and temp_val != 0:
                            val_tma = temp_val
                        
                        if val_tma is not None:
                            print(f"✅ Kolom [{idx}] dikonfirmasi sebagai TMA: {val_tma} m")
                            res["bpbd"] = val_tma
                            break
                            
            if res["bpbd"] is None:
                print("❌ Gagal menemukan TMA valid di BPBD")

        except Exception as e: 
            print(f"❌ Gagal BPBD: {e}")
            
    except Exception as e:
        print(f"Critical Driver Error: {e}")
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
        # Gunakan waktu mundur 15 menit agar sinkron dengan grid data
        waktu_bpbd = sekarang - timedelta(minutes=15)
        save_to_csv(FILE_HISTORY_BPBD, waktu_bpbd, live_data["bpbd"])
        print(f"STAMP -> BPBD: {live_data['bpbd']} m")
