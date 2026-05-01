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
        
        # --- AWS (STABIL) ---
        try:
            print("\n--- Scraping AWS ---")
            driver.get("http://202.90.199.132/aws-new/monitoring/3000000009")
            el = WebDriverWait(driver, 20).until(EC.visibility_of_element_located((By.ID, "waterlevel")))
            time.sleep(2)
            val = float(re.search(r"(\d+[\.,]?\d*)", el.text).group(1).replace(',', '.'))
            res["aws"] = val
            print(f"✅ AWS: {val} m")
        except Exception as e: print(f"❌ AWS Gagal: {e}")
            
        # --- BPBD (METODE SEARCH & SCAN) ---
        try:
            print("\n--- Scraping BPBD (Metode Search & Scan) ---")
            driver.get("https://poskobanjir.dsdadki.web.id/")
            
            # TUNGGU LAMA: Pastikan tabel beneran kelar loading
            WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_CtrlDataTinggiAir_GridListPintuAir_DXMainTable")))
            time.sleep(10) 
            
            # Cari SEMUA cell di tabel
            print("Mencari data Pasar Ikan di tabel...")
            rows = driver.find_elements(By.XPATH, "//tr[contains(@class, 'dxgvDataRow')]")
            
            for row in rows:
                if "Pasar Ikan" in row.text:
                    print(f"Ketemu Baris: {row.text}")
                    # Ambil semua <td> di baris ini
                    cells = row.find_elements(By.TAG_NAME, "td")
                    
                    # Kita cari angka di tiap kolom, tapi kita lewati kolom nama
                    for idx, cell in enumerate(cells):
                        txt = cell.text.strip()
                        # Regex untuk mencari angka 3 digit (TMA CM)
                        match = re.search(r"^(\d{3})$", txt)
                        if match:
                            tma_cm = float(match.group(1))
                            # Validasi: TMA Pasar Ikan biasanya 100-300cm
                            if 100 <= tma_cm <= 350:
                                res["bpbd"] = tma_cm / 100.0
                                print(f"✅ BPBD Berhasil: {res['bpbd']} m (Kolom {idx})")
                                break
                    if res["bpbd"]: break

            # FALLBACK: Jika masih gagal, scan seluruh span yang punya angka TMA
            if not res["bpbd"]:
                print("Metode baris gagal, mencoba Scan Seluruh Halaman...")
                spans = driver.find_elements(By.TAG_NAME, "span")
                for s in spans:
                    t = s.text.strip()
                    if t.isdigit() and 100 <= int(t) <= 300:
                        # Pastikan ini angka TMA dengan cek sekitarnya atau ID-nya
                        parent_text = s.find_element(By.XPATH, "./..").get_attribute("innerText")
                        if len(t) == 3: # TMA CM biasanya 3 digit
                            res["bpbd"] = int(t) / 100.0
                            print(f"✅ BPBD Berhasil (Scan): {res['bpbd']} m")
                            break

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
        print(f"STAMP -> AWS: {live_data['aws']} m")
    if live_data["bpbd"] is not None:
        save_to_csv(FILE_HISTORY_BPBD, sekarang - timedelta(minutes=15), live_data["bpbd"])
        print(f"STAMP -> BPBD: {live_data['bpbd']} m")
