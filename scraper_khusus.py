import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import datetime
import pytz
import time

# Setup Browser
chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

wib = pytz.timezone('Asia/Jakarta')
waktu_sekarang = datetime.datetime.now(wib).strftime('%Y-%m-%d %H:%M:%S')

def scrape_aws():
    try:
        print("Mencoba scraping AWS...")
        driver.get("URL_WEB_AWS_LU") # Ganti pake URL AWS
        time.sleep(5)
        # MODE ONCLICK: Klik dulu baru ambil data
        button = driver.find_element(By.XPATH, "//button[contains(@onclick, 'aws')]") # Sesuaikan onclick-nya
        driver.execute_script("arguments[0].click();", button)
        time.sleep(3)
        nilai = driver.find_element(By.ID, "id_nilai_aws").text # Sesuaikan ID-nya
        return nilai
    except Exception as e:
        print(f"Gagal AWS: {e}")
        return None

def scrape_bpbd():
    try:
        print("Mencoba scraping Pasar Ikan (BPBD)...")
        driver.get("https://bpbd.jakarta.go.id/waterlevel") # Contoh URL BPBD
        time.sleep(5)
        # MODE ONCLICK: Klik tombol Pasar Ikan
        btn_pasar_ikan = driver.find_element(By.XPATH, "//*[contains(text(), 'Pasar Ikan')]")
        driver.execute_script("arguments[0].click();", btn_pasar_ikan)
        time.sleep(3)
        nilai = driver.find_element(By.CLASS_NAME, "nilai-waterlevel").text # Sesuaikan
        return nilai
    except Exception as e:
        print(f"Gagal BPBD: {e}")
        return None

# Eksekusi
data_aws = scrape_aws()
data_bpbd = scrape_bpbd()

# SIMPAN AWS
if data_aws:
    df_aws = pd.DataFrame([{'waktu': waktu_sekarang, 'nilai': data_aws}])
    df_aws.to_csv('history_aws_priok.csv', mode='a', header=False, index=False)
    print(f"SUCCESS -> AWS {data_aws} tersimpan.")

# SIMPAN PASAR IKAN (Gak bakal ketuker lagi)
if data_bpbd:
    df_bpbd = pd.DataFrame([{'waktu': waktu_sekarang, 'nilai': data_bpbd}])
    df_bpbd.to_csv('history_bpbd_pasarikan.csv', mode='a', header=False, index=False)
    print(f"SUCCESS -> Pasar Ikan {data_bpbd} tersimpan.")

driver.quit()
