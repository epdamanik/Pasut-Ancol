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
    # User-agent agar tidak diblokir server
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
            time.sleep(3) # Jeda render JavaScript
            
            val_text = el.text.strip()
            print(f"Raw Text AWS: {val_text}")
            
            match = re.search(r"(\d+[\.,]?\d*)", val_text)
            if match:
                val = float(match.group(1).replace(',', '.'))
                if val <= LIMIT_SENSOR_ERROR: 
                    res["aws"] = val
                    print(f"Hasil AWS: {val} m")
        except Exception as e: 
            print(f"Gagal narik AWS: {e}")
            
        # --- SCRAPING BPBD (POSKO BANJIR) ---
        try:
            print("\n--- Memulai Scraping BPBD ---")
            driver.get("https://poskobanjir.dsdadki.web.id/")
            
            # Cari baris yang mengandung teks "Pasar Ikan"
            xpath_pasar_ikan = "//td[contains(text(), 'Pasar Ikan')]/.."
            row_el = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, xpath_pasar_ikan)))
            
            # Ambil semua kolom (td) dalam baris tersebut
            cells = row_el.find_elements(By.TAG_NAME, "td")
            
            val_tma = None
            print("Mengecek data di setiap kolom...")
            
            for idx, cell in enumerate(cells):
                txt = cell.text.strip()
                if not txt: continue
                
                # Ekstrak angka (mendukung desimal dan negatif)
                match_num = re.search(r"(-?\d+[\.,]?\d*)", txt)
                
                if match_num:
                    raw_val = match_num.group(1).replace(',', '.')
                    temp_val = float(raw_val)
                    print(f"Kolom [{idx}] terdeteksi angka: {temp_val}")
                    
                    # Logika Filter:
                    # Abaikan kolom 0 & 1 (biasanya No urut '11')
                    if idx > 1:
                        # Jika angka ribuan/ratusan (satuan CM)
                        if abs(temp_val) > 50:
                            val_tma = temp_val / 100.0
                        # Jika angka satuan (sudah dalam Meter)
                        elif -5.0 < temp_val < 5.0:
                            val_tma = temp_val
                        
                        if val_tma is not None:
                            print(f"✅ Kolom [{idx}] dikonfirmasi sebagai TMA: {val_tma} m")
                            res["bpbd"] = val_tma
                            break
                            
            if res["bpbd"] is None:
                print("Gagal menemukan angka TMA yang valid di baris Pasar Ikan")

        except Exception as e: 
            print(f"Gagal narik BPBD: {e}")
            
    except Exception as e:
        print(f"Driver Error Utama: {e}")
    finally:
        if driver: driver.quit()
        
    return res

if __name__ == "__main__":
    # Setup Waktu Jakarta
    tz_jkt = pytz.timezone('Asia/Jakarta')
    sekarang = datetime.now(tz_jkt).replace(tzinfo=None)
    
    print(f"\nEksekusi pada: {sekarang.strftime('%Y-%m-%d %H:%M:%S')} WIB")
    live_data = run_scraper()
    
    # Simpan Hasil AWS
    if live_data["aws"] is not None:
        save_to_csv(FILE_HISTORY_AWS, sekarang, live_data["aws"])
        print(f"SUCCESS -> AWS tersimpan: {live_data['aws']} m")
    else:
        print("AWS Data Is None - Lewati penyimpanan CSV")
        
    # Simpan Hasil BPBD (dengan logic mundur 15 menit jika diperlukan)
    if live_data["bpbd"] is not None:
        # Jika lu mau data BPBD dicatat pada slot 15 menit sebelumnya:
        waktu_bpbd = sekarang - timedelta(minutes=15)
        save_to_csv(FILE_HISTORY_BPBD, waktu_bpbd, live_data["bpbd"])
        print(f"SUCCESS -> BPBD tersimpan: {live_data['bpbd']} m")
    else:
        print("BPBD Data Is None - Lewati penyimpanan CSV")
