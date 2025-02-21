from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import csv
import json
import psycopg2
from datetime import datetime, timedelta
import locale

# Daftar link Tribun dari berbagai daerah
tribun_daerah = {
    "Tribun Medan": "https://medan.tribunnews.com",
    "Tribun Pekanbaru": "https://pekanbaru.tribunnews.com",
    "Tribun Batam": "https://batam.tribunnews.com",
    "Tribun Jambi": "https://jambi.tribunnews.com",
    "Tribun Sumsel": "https://sumsel.tribunnews.com",
    "Tribun Bangka": "https://bangka.tribunnews.com",
    "Tribun Lampung": "https://lampung.tribunnews.com",
    "Tribun Aceh" : "https://aceh.tribunnews.com",
    "Tribun Jakarta": "https://jakarta.tribunnews.com",
    "Tribun Jabar": "https://jabar.tribunnews.com",
    "Tribun Jateng": "https://jateng.tribunnews.com",
    "Tribun Jogja": "https://jogja.tribunnews.com",
    "Tribun Jatim": "https://surabaya.tribunnews.com",
    "Tribun Pontianak": "https://pontianak.tribunnews.com",
    "Tribun Kaltim": "https://kaltim.tribunnews.com",
    "Tribun Kalteng" : "https://kalteng.tribunnews.com",
    "Tribun Kalbar" : "https://pontianak.tribunnews.com",
    "Tribun Kalsel" : "https://banjarmasin.tribunnews.com",
    "Tribun Banjarmasin ": "https://banjarmasin.tribunnews.com",
    "Tribun Ambon" : "https://ambon.tribunnews.com",
    "Tribun Timur": "https://makassar.tribunnews.com",
    "Tribun Manado": "https://manado.tribunnews.com",
    "Tribun Bali": "https://bali.tribunnews.com",
    "Tribun Papua" : "https://papua.tribunnews.com",
    "Tribun Kupang": "https://kupang.tribunnews.com",
}

# Atur locale ke Bahasa Indonesia
locale.setlocale(locale.LC_TIME, 'id_ID.UTF-8')

# Def pengganti query tanggal dari text ke date
def parse_date(tanggal_berita):
    try:
        return datetime.strptime(tanggal_berita, "%d %B %Y").date()  
    except ValueError:
        return None

# Loop utama program
def main():
    while True:
        url, daerah_terpilih = pilih_daerah()
        
        if url is None:  # Jika user memilih 0 exit
            break
        
        lakukan_scraping(url, daerah_terpilih)
        
        print("\n" + "="*50)
        print(f"Scraping data: {daerah_terpilih} berhasil!!!, Anda dapat memilih daerah lain atau exit.")
        print("="*50)


# Modify the table creation function to include the article content
def buat_tabel_jika_belum_ada(cursor, nama_tabel):
    query_buat_tabel = f"""
    CREATE TABLE IF NOT EXISTS {nama_tabel} (
        id SERIAL PRIMARY KEY,
        tema TEXT,
        judul TEXT,
        tanggal DATE,
        link TEXT,
        isi_berita TEXT
    );
    """
    cursor.execute(query_buat_tabel)

# Fungsi untuk mengecek apakah sudah ada data yang sama
def berita_sudah_ada(cursor, nama_tabel, judul, link):
    query_check = f"SELECT EXISTS (SELECT 1 FROM {nama_tabel} WHERE judul = %s OR link = %s);"
    cursor.execute(query_check, (judul, link))
    return cursor.fetchone()[0]

# Fungsi koneksi ke database
def simpan_ke_database(data, daerah):
    try:
        conn = psycopg2.connect(
            dbname=" ",
            user=" ",
            password=" ",
            host=" ",
            port=" "
        )
        cursor = conn.cursor()

        # Fungsi agar tidak menyimpan data yang sudah ada / terjadinya duplikasi
        nama_tabel = f"berita_tribun_{daerah.replace(' ', '_').lower()}"
        buat_tabel_jika_belum_ada(cursor, nama_tabel)

        for item in data:
            if not berita_sudah_ada(cursor, nama_tabel, item["judul"], item["link"]):
                cursor.execute(f"""
                    INSERT INTO {nama_tabel} (tema, judul, tanggal, link, isi_berita)
                    VALUES (%s, %s, %s, %s, %s)
                """, (item["tema"], item["judul"], item["tanggal"], item["link"], item["isi_berita"]))
            else:
                print(f"Data sudah ada di database, tidak menyimpan ulang: {item['judul']}")

        conn.commit()
        cursor.close()
        conn.close()

        print(f"Berhasil menyimpan {len(data)} berita {daerah} ke database!")
    except Exception as e:
        print(f"Terjadi kesalahan saat menyimpan ke database: {e}")

# Fungsi untuk ambil isi dari tiap berita
def ambil_isi_berita(driver, link):
    try:
        # Menyimpan handle (ID unik) dari jendela utama browser
        main_window = driver.current_window_handle
        
        # Fungsi membuka tab link dari tiap url berita
        driver.execute_script(f'window.open("{link}", "_blank");')
        
        # Funtuk berpindah ke tab baru setelah Selenium membuka link dalam tab terpisah.
        driver.switch_to.window(driver.window_handles[-1])
        
        # Penambahan delay agar laman termuat seutuhnya
        time.sleep(3)
        
        # Fungsi untuk menunggu hingga elemen <script> yang mengandung teks "keywordBrandSafety" muncul di halaman web sebelum melanjutkan eksekusi.
        wait = WebDriverWait(driver, 10)
        script_element = wait.until(EC.presence_of_element_located((
            By.XPATH, "//script[contains(text(), 'keywordBrandSafety')]"
        )))
        
        # Fungsi untuk mengambil teks yang ada di dalam elemen <script> yang sebelumnya ditemukan.
        script_content = script_element.get_attribute('innerHTML')
        
        # Fungsi untuk mengekstrak teks yang ada di dalam variabel keywordBrandSafety di dalam elemen <script>.
        if 'keywordBrandSafety' in script_content:
            # Fungsi untuk mencari content diantara quotes setelah keywordBrandSafety
            start_index = script_content.find('keywordBrandSafety = "') + len('keywordBrandSafety = "')
            end_index = script_content.find('";', start_index)
            
            if start_index > -1 and end_index > -1:
                isi_berita = script_content[start_index:end_index]
                
                # Membersihkan content
                isi_berita = isi_berita.strip()
                # Menghapus tambahan spasi
                isi_berita = ' '.join(isi_berita.split())
        else:
            isi_berita = "Isi berita tidak ditemukan dalam script"
        
        # Menutup tab dan kembali ke halaman utama
        driver.close()
        driver.switch_to.window(main_window)
        
        return isi_berita
        
    except Exception as e:
        print(f"Error mengambil isi berita: {e}")
        if len(driver.window_handles) > 1:
            driver.close()
        driver.switch_to.window(main_window)
        return "Gagal mengambil isi berita"
    
# Fungsi untuk scraping
def lakukan_scraping(url, daerah_terpilih):
    driver = webdriver.Chrome()
    driver.get(url)
    time.sleep(3)
    scroll(driver)

    daftar_berita = []
    elemen_berita = driver.find_elements(By.CLASS_NAME, "mr140")

    for berita in elemen_berita:
        try:
            judul_element = berita.find_element(By.TAG_NAME, "h3")
            judul_berita = judul_element.text.strip()

            tanggal_element = berita.find_element(By.TAG_NAME, "time")
            tanggal_berita = tanggal_element.text.strip() if tanggal_element else "Tanggal tidak ditemukan"
            tanggal_berita = konversi_waktu(tanggal_berita)

            tema_element = berita.find_element(By.TAG_NAME, "h4")
            tema_berita = tema_element.text.strip() if tema_element else "Tema tidak ditemukan"

            link_element = berita.find_element(By.TAG_NAME, "h3").find_element(By.TAG_NAME, "a")
            link_berita = link_element.get_attribute("href") if link_element else "Link tidak ditemukan"
            
            # Mengambil isi berita, diambil dari fungsi diatas
            print(f"Mengambil isi berita: {judul_berita}")
            isi_berita = ambil_isi_berita(driver, link_berita)
            # Memasukan hasil scrap
            daftar_berita.append({
                "tema": tema_berita,
                "judul": judul_berita,
                "tanggal": tanggal_berita,
                "link": link_berita,
                "isi_berita": isi_berita
            })

            print(f"Sukses mengambil data berita: {judul_berita}")
        except Exception as e:
            print(f"Terjadi kesalahan saat mengambil data berita: {e}")

    driver.quit()

    # Simpan ke database
    simpan_ke_database(daftar_berita, daerah_terpilih)

    # Simpan sebagai csv
    nama_file_csv = f"result_scrap_{daerah_terpilih.replace(' ', '_').lower()}.csv"
    try:
        with open(nama_file_csv, mode='w', newline='', encoding='utf-8') as file_csv:
            penulis_csv = csv.DictWriter(file_csv, fieldnames=["tema", "judul", "tanggal", "link", "isi_berita"])
            penulis_csv.writeheader()
            penulis_csv.writerows(daftar_berita)
        print(f"Berhasil menyimpan {len(daftar_berita)} data berita ke file {nama_file_csv}")
    except Exception as e:
        print(f"Terjadi kesalahan saat menyimpan: {e}")

    # Simpan ke Json
    nama_file_json = f"result_scrap_{daerah_terpilih.replace(' ', '_').lower()}.json"
    try:
        with open(nama_file_json, mode='w', encoding='utf-8') as file_json:
            json.dump(daftar_berita, file_json, ensure_ascii=False, indent=4)
        print(f"Berhasil menyimpan {len(daftar_berita)} data berita di file {nama_file_json}")
    except Exception as e:
        print(f"Terjadi kesalahan saat menyimpan file JSON: {e}")

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

# Fungsi konversi waktu
def konversi_waktu(tanggal_relatif):
    sekarang = datetime.now()

    if "menit" in tanggal_relatif:
        jumlah_menit = int(tanggal_relatif.split(" ")[0])
        waktu = sekarang - timedelta(minutes=jumlah_menit)
    elif "jam" in tanggal_relatif:
        jumlah_jam = int(tanggal_relatif.split(" ")[0])
        waktu = sekarang - timedelta(hours=jumlah_jam)
    elif "hari" in tanggal_relatif:
        jumlah_hari = int(tanggal_relatif.split(" ")[0])
        waktu = sekarang - timedelta(days=jumlah_hari)
    else:
        # Jika format tidak dikenali, anggap itu adalah tanggal lengkap
        try:
            waktu = datetime.strptime(tanggal_relatif, "%A, %d %B %Y")  # Ubah dari string tanggal
        except ValueError:
            return None  # Jika gagal, kembalikan None untuk di-handle nanti

    # Kembalikan dalam format YYYY-MM-DD yang sesuai untuk PostgreSQL
    return waktu.strftime("%Y-%m-%d")

# Memulai program
if __name__ == "__main__":
    main()
