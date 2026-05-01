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
    driver = None
    res = {"aws": None, "bpbd": None}
    
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        
        # --- SCRAPING AWS ---
        try:
            print("Mencoba scraping AWS...")
            driver.get("http://202.90.199.132/aws-new/monitoring/3000000009")
            el = WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.ID, "waterlevel")))
            val = float(re.search(r"(\d+[\.,]?\d*)", el.text).group(1).replace(',', '.'))
            if val <= LIMIT_SENSOR_ERROR: res["aws"] = val
        except Exception as e: 
            print(f"Gagal narik AWS: {e}")
            
        # --- SCRAPING BPBD ---
        try:
            print("Mencoba scraping BPBD...")
            driver.get("https://poskobanjir.dsdadki.web.id/")
            row_el = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.XPATH, "//tr[contains(@onclick, 'Pasar Ikan')]")))
            script_text = row_el.get_attribute("onclick")
            match = re.search(r"ShowPopup\('[^']*',\s*'(\d+)'", script_text)
            if match:
                val = float(match.group(1)) / 1000 
                if val <= LIMIT_SENSOR_ERROR: res["bpbd"] = val
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
    
    # Karena ini dijalankan oleh GitHub Actions tiap 15 menit, kita langsung simpan
    if live_data["aws"] is not None:
        save_to_csv(FILE_HISTORY_AWS, sekarang, live_data["aws"])
        print(f"SUCCESS -> AWS tersimpan: {live_data['aws']}m")
        
    if live_data["bpbd"] is not None:
        # Sesuai logic lu, mundur 15 menit buat BPBD
        waktu_bpbd_mundur = sekarang - timedelta(minutes=15)
        save_to_csv(FILE_HISTORY_BPBD, waktu_bpbd_mundur, live_data["bpbd"])
        print(f"SUCCESS -> BPBD tersimpan: {live_data['bpbd']}m")
