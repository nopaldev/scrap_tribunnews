from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import csv
import json
import psycopg2

# Daftar link Tribun dari berbagai daerah
tribun_daerah = {
    "Tribun Medan": "https://medan.tribunnews.com",
    "Tribun Pekanbaru": "https://pekanbaru.tribunnews.com",
    "Tribun Batam": "https://batam.tribunnews.com",
    "Tribun Jambi": "https://jambi.tribunnews.com",
    "Tribun Sumsel": "https://sumsel.tribunnews.com",
    "Bangka Pos": "https://bangka.tribunnews.com",
    "Tribun Lampung": "https://lampung.tribunnews.com",
    "Tribun Jakarta": "https://jakarta.tribunnews.com",
    "Tribun Jabar": "https://jabar.tribunnews.com",
    "Tribun Jateng": "https://jateng.tribunnews.com",
    "Tribun Jogja": "https://jogja.tribunnews.com",
    "Surya (Tribun Jatim)": "https://surabaya.tribunnews.com",
    "Tribun Pontianak": "https://pontianak.tribunnews.com",
    "Tribun Kaltim": "https://kaltim.tribunnews.com",
    "Banjarmasin Post": "https://banjarmasin.tribunnews.com",
    "Tribun Timur": "https://makassar.tribunnews.com",
    "Tribun Manado": "https://manado.tribunnews.com",
    "Tribun Bali": "https://bali.tribunnews.com",
    "Pos Kupang": "https://kupang.tribunnews.com",
}

# Fungsi untuk membuat tabel jika belum ada
def buat_tabel_jika_belum_ada(cursor, nama_tabel):
    query_buat_tabel = f"""
    CREATE TABLE IF NOT EXISTS {nama_tabel} (
        id SERIAL PRIMARY KEY,
        tema TEXT,
        judul TEXT,
        tanggal TEXT,
        link TEXT
    );
    """
    cursor.execute(query_buat_tabel)

# Fungsi menyimpan hasil scrap ke database
def simpan_ke_database(data, daerah):
    try:
        # Konfigurasi koneksi ke database
        conn = psycopg2.connect(
            dbname="data_scrap_tribun",  # Nama database
            user="postgres",             # Username PostgreSQL
            password="12345",            # Password PostgreSQL
            host="localhost",            # Alamat server database
            port="7777"                  # Port PostgreSQL 
        )
        cursor = conn.cursor()

        # Nama tabel berdasarkan daerah
        nama_tabel = f"berita_tribun_{daerah.replace(' ', '_').lower()}"

        # Membuat tabel
        buat_tabel_jika_belum_ada(cursor, nama_tabel)

        # Masukkan data ke dalam tabel
        for item in data:
            cursor.execute(f"""
                INSERT INTO {nama_tabel} (tema, judul, tanggal, link)
                VALUES (%s, %s, %s, %s)
            """, (item["tema"], item["judul"], item["tanggal"], item["link"]))

        # Commit perubahan dan tutup koneksi
        conn.commit()
        cursor.close()
        conn.close()

        print(f"Berhasil menyimpan {len(data)} berita {daerah} ke database!")
    except Exception as e:
        print(f"Terjadi kesalahan saat menyimpan ke database: {e}")

# Fungsi untuk memilih daerah
def pilih_daerah():
    print("\nPilih daerah yang ingin di-scrap:")
    for index, daerah in enumerate(tribun_daerah.keys(), start=1):
        print(f"{index}. {daerah}")
    print("0. Exit program")
    
    try:
        pilihan = int(input("Masukkan nomor daerah yang dipilih: "))
        
        if pilihan == 0:
            print("Program selesai. Terima kasih!")
            return None, None
        
        if pilihan < 1 or pilihan > len(tribun_daerah):
            print("Pilihan tidak valid! Silakan coba lagi.")
            return pilih_daerah()
        
        # Mengambil link berdasarkan pilihan
        daerah_terpilih = list(tribun_daerah.keys())[pilihan - 1]
        url = tribun_daerah[daerah_terpilih]
        
        print(f"Anda memilih: {daerah_terpilih} - {url}")
        return url, daerah_terpilih
    except ValueError:
        print("Input tidak valid! Masukkan angka.")
        return pilih_daerah()

# Fungsi scroll sampai bawah
def scroll(driver):
    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)

        new_height = driver.execute_script("return document.body.scrollHeight")

        if new_height == last_height:
            break
        last_height = new_height

# Fungsi utama untuk melakukan scraping
def lakukan_scraping(url, daerah_terpilih):
    # Inisialisasi driver Selenium
    driver = webdriver.Chrome()

    # Membuka website
    driver.get(url)

    # Delay waktu untuk scroll
    time.sleep(3)

    # Memulai proses scroll
    scroll(driver)

    # Variabel untuk menyimpan data hasil scrap
    daftar_berita = []

    # Mengambil semua elemen berita
    elemen_berita = driver.find_elements(By.CLASS_NAME, "mr140")

    # Loop mengambil data dari setiap berita
    for berita in elemen_berita:
        try:
            judul_element = berita.find_element(By.TAG_NAME, "h3")
            judul_berita = judul_element.text.strip()

            tanggal_element = berita.find_element(By.TAG_NAME, "time")
            tanggal_berita = tanggal_element.text.strip() if tanggal_element else "Tanggal tidak ditemukan"

            tema_element = berita.find_element(By.TAG_NAME, "h4")
            tema_berita = tema_element.text.strip() if tema_element else "Tema tidak ditemukan"

            link_element = berita.find_element(By.TAG_NAME, "h3").find_element(By.TAG_NAME, "a")
            link_berita = link_element.get_attribute("href") if link_element else "Link tidak ditemukan"

            daftar_berita.append({
                "tema": tema_berita,
                "judul": judul_berita,
                "tanggal": tanggal_berita,
                "link": link_berita
            })

            print(f"Sukses mengambil data berita: {judul_berita}")
        except Exception as e:
            print(f"Terjadi kesalahan saat mengambil data berita: {e}")

    # Menutup browser
    driver.quit()

    # Menyimpan data hasil scrap ke database
    simpan_ke_database(daftar_berita, daerah_terpilih)

    # Menyimpan data hasil scrap ke file CSV
    nama_file_csv = f"result_scrap_{daerah_terpilih.replace(' ', '_').lower()}.csv"
    try:
        with open(nama_file_csv, mode='w', newline='', encoding='utf-8') as file_csv:
            penulis_csv = csv.DictWriter(file_csv, fieldnames=["tema", "judul", "tanggal", "link"])
            penulis_csv.writeheader()
            penulis_csv.writerows(daftar_berita)
        print(f"Berhasil menyimpan {len(daftar_berita)} data berita ke file {nama_file_csv}")
    except Exception as e:
        print(f"Terjadi kesalahan saat menyimpan: {e}")

    # Menyimpan data hasil scrap ke file JSON
    nama_file_json = f"result_scrap_{daerah_terpilih.replace(' ', '_').lower()}.json"
    try:
        with open(nama_file_json, mode='w', encoding='utf-8') as file_json:
            json.dump(daftar_berita, file_json, ensure_ascii=False, indent=4)
        print(f"Berhasil menyimpan {len(daftar_berita)} data berita di file {nama_file_json}")
    except Exception as e:
        print(f"Terjadi kesalahan saat menyimpan file JSON: {e}")

# Loop utama program
def main():
    while True:
        url, daerah_terpilih = pilih_daerah()
        
        if url is None:  # Jika user memilih exit
            break
        
        lakukan_scraping(url, daerah_terpilih)
        
        print("\n" + "="*50)
        print("Scraping selesai! Anda dapat memilih daerah lain atau exit.")
        print("="*50)

# Memulai program
if __name__ == "__main__":
    main()