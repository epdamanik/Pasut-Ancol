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
            print(f"Error simpan CSV: {e}")

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
        
        # --- AWS ---
        try:
            print("\n--- Scraping AWS ---")
            driver.get("http://202.90.199.132/aws-new/monitoring/3000000009")
            el = WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.ID, "waterlevel")))
            time.sleep(3)
            val = float(re.search(r"(\d+[\.,]?\d*)", el.text).group(1).replace(',', '.'))
            res["aws"] = val
            print(f"✅ AWS: {val} m")
        except Exception as e: print(f"❌ AWS Gagal: {e}")
            
        # --- BPBD (PASAR IKAN) ---
        try:
            print("\n--- Scraping BPBD ---")
            driver.get("https://poskobanjir.dsdadki.web.id/")
            
            # Tunggu baris Pasar Ikan muncul
            xpath_row = "//td[contains(text(), 'Pasar Ikan')]/.."
            row_el = WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.XPATH, xpath_row)))
            
            # Ambil semua text di baris itu tanpa peduli kolom
            full_text = row_el.get_attribute("innerText")
            print(f"Full Row Text: {full_text}")
            
            # Cari angka 3 digit (100-299) yang biasanya merupakan TMA (cm)
            # Kita cari angka yang diikuti spasi atau karakter non-huruf
            all_numbers = re.findall(r"(\d{3})", full_text)
            
            if all_numbers:
                # Ambil angka pertama yang ditemukan (biasanya itu TMA-nya)
                tma_cm = float(all_numbers[0])
                res["bpbd"] = tma_cm / 100.0
                print(f"✅ BPBD Berhasil: {res['bpbd']} m (dari {tma_cm} cm)")
            else:
                # Jika tidak ada 3 digit, cari angka apapun yang masuk akal
                match = re.search(r"(\d+)", full_text.replace("Pasar Ikan", "").replace("11", ""))
                if match:
                    tma_cm = float(match.group(1))
                    res["bpbd"] = tma_cm / 100.0
                    print(f"✅ BPBD Berhasil (Alt): {res['bpbd']} m")

        except Exception as e: print(f"❌ BPBD Gagal: {e}")
            
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
        print(f"SUCCESS AWS: {live_data['aws']}m")
    if live_data["bpbd"] is not None:
        save_to_csv(FILE_HISTORY_BPBD, sekarang - timedelta(minutes=15), live_data["bpbd"])
        print(f"SUCCESS BPBD: {live_data['bpbd']}m")
