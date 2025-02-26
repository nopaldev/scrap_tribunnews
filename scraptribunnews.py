import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
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
import webbrowser
import requests
from PIL import Image, ImageTk
import io
import os
import re
import textwrap
from wordpress_xmlrpc import Client, WordPressPost
from wordpress_xmlrpc.methods.posts import NewPost
import mysql.connector

locale.setlocale(locale.LC_TIME, 'id_ID.UTF-8')

# Daftar Tribun Daerah
tribun_daerah = {
    "Tribun Medan": "https://medan.tribunnews.com",
    "Tribun Pekanbaru": "https://pekanbaru.tribunnews.com",
    "Tribun Batam": "https://batam.tribunnews.com",
    "Tribun Jambi": "https://jambi.tribunnews.com",
    "Tribun Sumsel": "https://sumsel.tribunnews.com",
    "Tribun Bangka": "https://bangka.tribunnews.com",
    "Tribun Lampung": "https://lampung.tribunnews.com",
    "Tribun Aceh": "https://aceh.tribunnews.com",
    "Tribun Jakarta": "https://jakarta.tribunnews.com",
    "Tribun Jabar": "https://jabar.tribunnews.com",
    "Tribun Jateng": "https://jateng.tribunnews.com",
    "Tribun Jogja": "https://jogja.tribunnews.com",
    "Tribun Jatim": "https://surabaya.tribunnews.com",
    "Tribun Pontianak": "https://pontianak.tribunnews.com",
    "Tribun Kaltim": "https://kaltim.tribunnews.com",
    "Tribun Kalteng": "https://kalteng.tribunnews.com",
    "Tribun Kalbar": "https://pontianak.tribunnews.com",
    "Tribun Kalsel": "https://banjarmasin.tribunnews.com",
    "Tribun Banjarmasin": "https://banjarmasin.tribunnews.com",
    "Tribun Ambon": "https://ambon.tribunnews.com",
    "Tribun Timur": "https://makassar.tribunnews.com",
    "Tribun Manado": "https://manado.tribunnews.com",
    "Tribun Bali": "https://bali.tribunnews.com",
    "Tribun Papua": "https://papua.tribunnews.com",
    "Tribun Kupang": "https://kupang.tribunnews.com",
}

# Kredensial WordPress, dalam projek ini menggunakan xmlrpc
WP_URL = " " url dari direktori wordpress
WP_USERNAME = " " # username wordpress
WP_PASSWORD = " " # password wordpress

scraping_thread = None
stop_scraping_flag = False
all_data = []

def clean_filename(text):
    text = re.sub(r'[^\w\s-]', '_', text)
    text = re.sub(r'\s+', '_', text)
    return text.strip('_')[:50]

def konversi_waktu(tanggal_relatif):
    sekarang = datetime.now()
    if not tanggal_relatif or tanggal_relatif.strip() == "Tanggal tidak ditemukan":
        return None
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
        try:
            waktu = datetime.strptime(tanggal_relatif, "%A, %d %B %Y")
        except ValueError:
            return None
    return waktu.strftime("%Y-%m-%d")

def scroll(driver):
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height or stop_scraping_flag:
            break
        last_height = new_height

def buat_tabel_jika_belum_ada(cursor, nama_tabel, db_type="postgresql"):
    if db_type == "postgresql":
        query = f"""
        CREATE TABLE IF NOT EXISTS {nama_tabel} (
            id SERIAL PRIMARY KEY,
            tema TEXT,
            judul TEXT,
            tanggal DATE,
            link TEXT,
            isi_berita TEXT,
            image_url VARCHAR(255)
        );
        """
    elif db_type == "mysql":
        query = f"""
        CREATE TABLE IF NOT EXISTS {nama_tabel} (
            id BIGINT AUTO_INCREMENT PRIMARY KEY,
            tema VARCHAR(255),
            judul VARCHAR(255),
            tanggal DATE,
            link TEXT,
            isi_berita TEXT,
            image_url VARCHAR(255)
        );
        """
    cursor.execute(query)

def berita_sudah_ada(cursor, nama_tabel, judul, link):
    query_check = f"SELECT EXISTS (SELECT 1 FROM {nama_tabel} WHERE judul = %s OR link = %s);"
    cursor.execute(query_check, (judul, link))
    return cursor.fetchone()[0]

def ambil_isi_berita(driver, link):
    try:
        main_window = driver.current_window_handle
        driver.execute_script(f'window.open("{link}", "_blank");')
        driver.switch_to.window(driver.window_handles[-1])
        time.sleep(3)
        
        wait = WebDriverWait(driver, 10)
        script_element = wait.until(EC.presence_of_element_located((
            By.XPATH, "//script[contains(text(), 'keywordBrandSafety')]"
        )))
        
        script_content = script_element.get_attribute('innerHTML')
        start_index = script_content.find('keywordBrandSafety = "') + len('keywordBrandSafety = "')
        end_index = script_content.find('";', start_index)
        isi_berita = script_content[start_index:end_index].strip() if start_index > -1 and end_index > -1 else "Isi berita tidak ditemukan"

        try:
            image_element = wait.until(EC.presence_of_element_located((By.XPATH, "//div[@class='bsh mb20']//img[@class='imgfull']")))
            image_url = image_element.get_attribute("src")
        except Exception:
            image_url = None

        driver.close()
        driver.switch_to.window(main_window)
        return ' '.join(isi_berita.split()), image_url
    except Exception as e:
        print(f"Error mengambil isi berita: {e}")
        if len(driver.window_handles) > 1:
            driver.close()
        driver.switch_to.window(main_window)
        return "Gagal mengambil isi berita", None

def simpan_berita_individu(data, daerah):
    try:
        # Simpan ke PostgreSQL
        conn_pg = psycopg2.connect(dbname=" ", user=" ", password=" ", host=" ", port=" ") # ganti menggunakan database postgre sendiri
        cursor_pg = conn_pg.cursor()
        nama_tabel_pg = f"berita_tribun_{daerah.replace(' ', '_').lower()}"
        buat_tabel_jika_belum_ada(cursor_pg, nama_tabel_pg, "postgresql")
        if not berita_sudah_ada(cursor_pg, nama_tabel_pg, data["judul"], data["link"]):
            cursor_pg.execute(f"""
                INSERT INTO {nama_tabel_pg} (tema, judul, tanggal, link, isi_berita, image_url)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (data["tema"], data["judul"], data["tanggal"], data["link"], data["isi_berita"], data["image_url"]))
            conn_pg.commit()
        cursor_pg.close()
        conn_pg.close()

        # Simpan ke MySQL
        conn_mysql = mysql.connector.connect(database=" ", user=" ", password=" ", host=" ", port=" ") # ganti menggunakan database wordpress sendiri
        cursor_mysql = conn_mysql.cursor()
        nama_tabel_mysql = f"berita_{daerah.replace(' ', '_').lower()}"
        buat_tabel_jika_belum_ada(cursor_mysql, nama_tabel_mysql, "mysql")
        if not berita_sudah_ada(cursor_mysql, nama_tabel_mysql, data["judul"], data["link"]):
            cursor_mysql.execute(f"""
                INSERT INTO {nama_tabel_mysql} (tema, judul, tanggal, link, isi_berita, image_url)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (data["tema"], data["judul"], data["tanggal"], data["link"], data["isi_berita"], data["image_url"]))
            conn_mysql.commit()
        cursor_mysql.close()
        conn_mysql.close()

        # Publikasikan ke WordPress
        publish_to_wordpress(data, daerah)

    except Exception as e:
        print(f"Terjadi kesalahan saat menyimpan: {e}")

def publish_to_wordpress(data, daerah):
    try:
        wp = Client(WP_URL, WP_USERNAME, WP_PASSWORD)
        post = WordPressPost()
        post.title = data["judul"]
        post.content = f"<p><strong>Tema:</strong> {data['tema']}</p><p>{data['isi_berita']}</p>"
        if data["image_url"]:
            post.content += f'<p><img src="{data["image_url"]}" alt="{data["judul"]}"></p>'
        post.terms_names = {'category': [daerah], 'post_tag': [data["tema"]]}
        post.post_status = 'publish'
        post.date = datetime.strptime(data["tanggal"], "%Y-%m-%d") if data["tanggal"] else datetime.now()
        wp.call(NewPost(post))
        print(f"Berita '{data['judul']}' berhasil dipublikasikan ke WordPress!")
    except Exception as e:
        print(f"Gagal mempublikasikan ke WordPress: {e}")

def lakukan_scraping(url, daerah_terpilih):
    global stop_scraping_flag
    stop_scraping_flag = False
    
    driver = webdriver.Chrome()
    driver.get(url)
    time.sleep(3)
    scroll(driver)

    elemen_berita = driver.find_elements(By.CLASS_NAME, "mr140")
    for berita in elemen_berita:
        if stop_scraping_flag:
            print("Proses scraping dihentikan.")
            break
        try:
            judul_element = berita.find_element(By.TAG_NAME, "h3")
            judul_berita = judul_element.text.strip()
            tanggal_element = berita.find_element(By.TAG_NAME, "time")
            tanggal_berita = konversi_waktu(tanggal_element.text.strip() if tanggal_element else "Tanggal tidak ditemukan")
            tema_element = berita.find_element(By.TAG_NAME, "h4")
            tema_berita = tema_element.text.strip() if tema_element else "Tema tidak ditemukan"
            link_berita = judul_element.find_element(By.TAG_NAME, "a").get_attribute("href")
            isi_berita, image_url = ambil_isi_berita(driver, link_berita)
            
            data_berita = {
                "tema": tema_berita,
                "judul": judul_berita,
                "tanggal": tanggal_berita,
                "link": link_berita,
                "isi_berita": isi_berita,
                "image_url": image_url
            }
            simpan_berita_individu(data_berita, daerah_terpilih)
            print(f"Sukses menyimpan berita: {judul_berita}")
        except Exception as e:
            print(f"Terjadi kesalahan saat mengambil berita: {e}")

    driver.quit()
    if not stop_scraping_flag:
        messagebox.showinfo("Info", f"Scraping untuk {daerah_terpilih} selesai!")

def start_scraping():
    global scraping_thread
    daerah = daerah_var.get()
    if not daerah:
        messagebox.showerror("Error", "Pilih daerah terlebih dahulu!")
        return
    url = tribun_daerah[daerah]
    scraping_thread = threading.Thread(target=lakukan_scraping, args=(url, daerah), daemon=True)
    scraping_thread.start()
    messagebox.showinfo("Info", f"Memulai scraping untuk {daerah}...")

def stop_scraping():
    global stop_scraping_flag
    stop_scraping_flag = True
    messagebox.showinfo("Info", "Proses scraping akan dihentikan.")

def load_data_from_db():
    daerah = daerah_var.get()
    if not daerah:
        messagebox.showerror("Error", "Pilih daerah terlebih dahulu!")
        return
    try:
        conn = psycopg2.connect(dbname="data_scrap_tribun", user="postgres", password="12345", host="localhost", port="7777")
        cursor = conn.cursor()
        nama_tabel = f"berita_tribun_{daerah.replace(' ', '_').lower()}"
        cursor.execute(f"SELECT id, tema, judul, tanggal, link, isi_berita, image_url FROM {nama_tabel}")
        data = cursor.fetchall()
        
        for item in tree_top.get_children():
            tree_top.delete(item)
        for item in tree_bottom.get_children():
            tree_bottom.delete(item)
        
        global all_data
        all_data = data
        
        for row in data:
            id_berita, tema, judul, tanggal, link, isi_berita, image_url = row
            tanggal_str = datetime.strptime(str(tanggal), "%Y-%m-%d").strftime("%A, %Y-%m-%d") if tanggal else "Tanggal tidak ditemukan"
            tree_top.insert("", "end", values=(id_berita, tema, judul, tanggal_str, link, image_url if image_url else "Tidak ada gambar"))
        
        cursor.close()
        conn.close()
    except Exception as e:
        messagebox.showerror("Error", f"Data kosong atau belum di-scrape: {e}")

def show_article_content(event):
    item = tree_top.selection()
    if not item:
        return
    values = tree_top.item(item[0], "values")
    judul = values[2]
    for row in all_data:
        if row[2] == judul:
            _, _, _, _, _, isi_berita, image_url = row
            for item in tree_bottom.get_children():
                tree_bottom.delete(item)
            for line in textwrap.wrap(isi_berita, width=230):
                tree_bottom.insert("", "end", values=(line,))
            if image_url:
                img = Image.open(io.BytesIO(requests.get(image_url).content))
                img.thumbnail((100, 100))
                photo = ImageTk.PhotoImage(img)
                image_label.config(image=photo)
                image_label.image = photo
            else:
                image_label.config(image='')
            break

def open_link(event):
    item = tree_top.identify_row(event.y)
    if item:
        values = tree_top.item(item, "values")
        link = values[4]
        if link and link != "Link tidak ditemukan":
            webbrowser.open(link)

def export_to_csv():
    daerah = daerah_var.get()
    if not daerah or not all_data:
        messagebox.showerror("Error", "Pilih daerah dan muat data terlebih dahulu!")
        return
    nama_file_csv = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")], initialfile=f"result_scrap_{daerah.replace(' ', '_').lower()}.csv")
    if not nama_file_csv:
        return
    export_folder = os.path.join(os.path.dirname(nama_file_csv), "images", daerah.replace(" ", "_").lower())
    os.makedirs(export_folder, exist_ok=True)
    try:
        with open(nama_file_csv, mode='w', newline='', encoding='utf-8') as file_csv:
            writer = csv.writer(file_csv)
            writer.writerow(["ID", "Tema", "Judul", "Tanggal", "Link", "Isi Berita", "Image Path"])
            for row in all_data:
                id_berita, tema, judul, tanggal, link, isi_berita, image_url = row
                tanggal_str = datetime.strptime(str(tanggal), "%Y-%m-%d").strftime("%A, %Y-%m-%d") if tanggal else "Tanggal tidak ditemukan"
                image_path = ""
                if image_url:
                    image_filename = f"{clean_filename(judul)}.jpg"
                    image_path = os.path.join(export_folder, image_filename)
                    with open(image_path, "wb") as f:
                        f.write(requests.get(image_url).content)
                writer.writerow([id_berita, tema, judul, tanggal_str, link, isi_berita, image_path])
        messagebox.showinfo("Info", f"Data diekspor ke {nama_file_csv}")
    except Exception as e:
        messagebox.showerror("Error", f"Gagal mengekspor ke CSV: {e}")

def export_to_json():
    daerah = daerah_var.get()
    if not daerah or not all_data:
        messagebox.showerror("Error", "Pilih daerah dan muat data terlebih dahulu!")
        return
    nama_file_json = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")], initialfile=f"result_scrap_{daerah.replace(' ', '_').lower()}.json")
    if not nama_file_json:
        return
    export_folder = os.path.join(os.path.dirname(nama_file_json), "images", daerah.replace(" ", "_").lower())
    os.makedirs(export_folder, exist_ok=True)
    try:
        with open(nama_file_json, mode='w', encoding='utf-8') as file_json:
            formatted_data = []
            for row in all_data:
                id_berita, tema, judul, tanggal, link, isi_berita, image_url = row
                tanggal_str = datetime.strptime(str(tanggal), "%Y-%m-%d").strftime("%A, %Y-%m-%d") if tanggal else "Tanggal tidak ditemukan"
                image_path = ""
                if image_url:
                    image_filename = f"{clean_filename(judul)}.jpg"
                    image_path = os.path.join(export_folder, image_filename)
                    with open(image_path, "wb") as f:
                        f.write(requests.get(image_url).content)
                formatted_data.append({"id": id_berita, "tema": tema, "judul": judul, "tanggal": tanggal_str, "link": link, "isi_berita": isi_berita, "image_path": image_path})
            json.dump(formatted_data, file_json, ensure_ascii=False, indent=4)
        messagebox.showinfo("Info", f"Data diekspor ke {nama_file_json}")
    except Exception as e:
        messagebox.showerror("Error", f"Gagal mengekspor ke JSON: {e}")

# GUI Setup
root = tk.Tk()
root.title("Tribun News Scraper")
root.geometry("1200x800")
root.configure(bg="#FFFFFF")

style = ttk.Style()
style.theme_use('clam')
style.configure("TLabel", font=("Segoe UI", 12, "bold"), background="#FFFFFF")
style.configure("TButton", font=("Segoe UI", 10), padding=6)
style.map("TButton", background=[('active', '#1976D2'), ('!active', '#2196F3')], foreground=[('active', 'white'), ('!active', 'white')])
style.configure("Treeview", font=("Segoe UI", 10), rowheight=25)
style.configure("Treeview.Heading", font=("Segoe UI", 11, "bold"), background="#BBDEFB")
style.configure("TCombobox", font=("Segoe UI", 10))

main_frame = tk.Frame(root, bg="#FFFFFF", padx=20, pady=20)
main_frame.pack(fill="both", expand=True)

ttk.Label(main_frame, text="Tribun News Scraper", font=("Segoe UI", 15, "bold")).pack(anchor="w", pady=(0, 10), padx=10)

control_frame = tk.Frame(main_frame, bg="#FFFFFF")
control_frame.pack(fill="x", pady=10, padx=10)

daerah_var = tk.StringVar()
ttk.Label(control_frame, text="Pilih Daerah Tribun:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
daerah_combo = ttk.Combobox(control_frame, textvariable=daerah_var, values=list(tribun_daerah.keys()))
daerah_combo.grid(row=0, column=1, padx=5, pady=5, sticky="we")
ttk.Button(control_frame, text="Mulai Scraping", command=start_scraping).grid(row=0, column=2, padx=5, pady=5)
ttk.Button(control_frame, text="Stop Scraping", command=stop_scraping).grid(row=0, column=3, padx=5, pady=5)
ttk.Button(control_frame, text="Muat Data", command=load_data_from_db).grid(row=0, column=4, padx=5, pady=5)
ttk.Button(control_frame, text="Ekspor ke CSV", command=export_to_csv).grid(row=0, column=5, padx=5, pady=5)
ttk.Button(control_frame, text="Ekspor ke JSON", command=export_to_json).grid(row=0, column=6, padx=5, pady=5)

tables_frame = tk.Frame(main_frame, bg="#FFFFFF")
tables_frame.pack(fill="both", expand=True)

ttk.Label(tables_frame, text="Daftar Berita").pack(anchor="w", pady=(0, 5), padx=10)
tree_top = ttk.Treeview(tables_frame, columns=("id", "tema", "judul", "tanggal", "link", "image_path"), show="headings", height=6)
tree_top.pack(fill="both", expand=True, pady=5)
tree_top.heading("id", text="ID")
tree_top.heading("tema", text="Tema")
tree_top.heading("judul", text="Judul")
tree_top.heading("tanggal", text="Tanggal")
tree_top.heading("link", text="Link")
tree_top.heading("image_path", text="Link Gambar")
tree_top.column("id", width=40)
tree_top.column("tema", width=150)
tree_top.column("judul", width=300)
tree_top.column("tanggal", width=100)
tree_top.column("link", width=350)
tree_top.column("image_path", width=100)
tree_top.bind("<Double-1>", open_link)
tree_top.bind("<<TreeviewSelect>>", show_article_content)

scroll_top = ttk.Scrollbar(tables_frame, orient="vertical", command=tree_top.yview)
scroll_top.pack(side="right", fill="y")
tree_top.configure(yscrollcommand=scroll_top.set)

ttk.Label(tables_frame, text="Isi Berita").pack(anchor="w", pady=(10, 10), padx=10)
tree_bottom = ttk.Treeview(tables_frame, columns=("isi_berita",), show="", height=35)
tree_bottom.pack(fill="both", expand=True, pady=5)
tree_bottom.column("isi_berita", width=1200)

scroll_bottom = ttk.Scrollbar(tables_frame, orient="vertical", command=tree_bottom.yview)
scroll_bottom.pack(side="right", fill="y")
tree_bottom.configure(yscrollcommand=scroll_bottom.set)

image_label = tk.Label(tables_frame, bg="#FFFFFF")
image_label.pack(anchor="w", pady=5, padx=10)

control_frame.columnconfigure(1, weight=1)

root.mainloop()
