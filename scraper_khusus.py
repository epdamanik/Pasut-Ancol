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
    # Biar gak diblokir, kita nyamar jadi browser beneran
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    driver = None
    res = {"aws": None, "bpbd": None}
    
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        
        # --- SCRAPING AWS ---
        try:
            print("Mencoba scraping AWS...")
            # Pake timeout biar gak nunggu kelamaan kalau web down
            driver.set_page_load_timeout(30) 
            driver.get("http://202.90.199.132/aws-new/monitoring/3000000009")
            
            # Tunggu sampe ID waterlevel beneran muncul angkanya
            el = WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.ID, "waterlevel")))
            time.sleep(3) # Jeda dikit biar JS-nya kelar narik angka
            
            val_text = el.text.strip()
            print(f"Text AWS terdeteksi: {val_text}")
            
            match = re.search(r"(\d+[\.,]?\d*)", val_text)
            if match:
                val = float(match.group(1).replace(',', '.'))
                if val <= LIMIT_SENSOR_ERROR: res["aws"] = val
        except Exception as e: 
            print(f"Gagal narik AWS: {e}")
            
        # --- SCRAPING BPBD ---
        try:
            print("Mencoba scraping BPBD...")
            driver.get("https://poskobanjir.dsdadki.web.id/")
            
            # Tunggu sampe tabel Pasar Ikan muncul. Pake XPATH yang lebih spesifik.
            xpath_pasar_ikan = "//td[contains(text(), 'Pasar Ikan')]/.."
            row_el = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, xpath_pasar_ikan)))
            
            # Ambil semua text di baris itu
            row_text = row_el.text
            print(f"Baris BPBD ditemukan: {row_text}")
            
            # Cari angka (satuan cm) di baris tersebut
            # Biasanya formatnya: "Pasar Ikan ... 1800 ... dst"
            numbers = re.findall(r"(\d+)", row_text)
            if numbers:
                # Ambil angka pertama yang masuk akal sebagai TMA (biasanya ribuan/ratusan)
                # Kita cari angka yang > 100 karena satuannya cm
                for n in numbers:
                    val_cm = float(n)
                    if val_cm > 10: # Filter angka kecil yang mungkin bukan TMA
                        val = val_cm / 100.0 # Convert ke meter
                        if val <= LIMIT_SENSOR_ERROR: 
                            res["bpbd"] = val
                            break
        except Exception as e: 
            print(f"Gagal narik BPBD: {e}")
            
    except Exception as e:
        print(f"Driver Error: {e}")
    finally:
        if driver: driver.quit()
        
    return res

if __name__ == "__main__":
    tz_jkt = pytz.timezone('Asia/Jakarta')
    sekarang = datetime.now(tz_jkt).replace(tzinfo=None)
    
    print(f"Memulai eksekusi background scraping pada {sekarang} WIB...")
    live_data = run_scraper()
    
    if live_data["aws"] is not None:
        save_to_csv(FILE_HISTORY_AWS, sekarang, live_data["aws"])
        print(f"SUCCESS -> AWS tersimpan: {live_data['aws']}m")
    else:
        print("AWS Data Is None - Tidak Simpan ke CSV")
        
    if live_data["bpbd"] is not None:
        # Mundur 15 menit buat BPBD sesuai request lu
        waktu_bpbd_mundur = sekarang - timedelta(minutes=15)
        save_to_csv(FILE_HISTORY_BPBD, waktu_bpbd_mundur, live_data["bpbd"])
        print(f"SUCCESS -> BPBD tersimpan: {live_data['bpbd']}m")
    else:
        print("BPBD Data Is None - Tidak Simpan ke CSV")
