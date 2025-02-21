import tkinter as tk
from tkinter import ttk, messagebox
import textwrap
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

locale.setlocale(locale.LC_TIME, 'id_ID.UTF-8')

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

def parse_date(tanggal_berita):
    try:
        return datetime.strptime(tanggal_berita, "%d %B %Y").date()
    except ValueError:
        return None

def scroll(driver):
    last_height = driver.execute_script("return document.body.scrollHeight")
    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(3)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

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
        try:
            waktu = datetime.strptime(tanggal_relatif, "%A, %d %B %Y")
        except ValueError:
            return None
    return waktu.strftime("%A, %Y-%m-%d")

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

def berita_sudah_ada(cursor, nama_tabel, judul, link):
    query_check = f"SELECT EXISTS (SELECT 1 FROM {nama_tabel} WHERE judul = %s OR link = %s);"
    cursor.execute(query_check, (judul, link))
    return cursor.fetchone()[0]

def simpan_ke_database(data, daerah):
    try:
        conn = psycopg2.connect(
            dbname=" ",        # ganti dengan nama database
            user=" ",          # ganti dengan nama user database
            password=" ",      # ganti dengan password database
            host=" ",          # ganti dengan nama host database
            port=" "           # ganti dengan port yang di gunakan pada database
        )
        cursor = conn.cursor()
        nama_tabel = f"berita_tribun_{daerah.replace(' ', '_').lower()}"
        buat_tabel_jika_belum_ada(cursor, nama_tabel)

        for item in data:
            if not berita_sudah_ada(cursor, nama_tabel, item["judul"], item["link"]):
                cursor.execute(f"""
                    INSERT INTO {nama_tabel} (tema, judul, tanggal, link, isi_berita)
                    VALUES (%s, %s, %s, %s, %s)
                """, (item["tema"], item["judul"], item["tanggal"], item["link"], item["isi_berita"]))
        conn.commit()
        cursor.close()
        conn.close()
        print(f"Berhasil menyimpan {len(data)} berita {daerah} ke database!")
    except Exception as e:
        print(f"Terjadi kesalahan saat menyimpan ke database: {e}")

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
        driver.close()
        driver.switch_to.window(main_window)
        return ' '.join(isi_berita.split())
    except Exception as e:
        print(f"Error mengambil isi berita: {e}")
        if len(driver.window_handles) > 1:
            driver.close()
        driver.switch_to.window(main_window)
        return "Gagal mengambil isi berita"

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
            tanggal_berita = konversi_waktu(tanggal_element.text.strip() if tanggal_element else "Tanggal tidak ditemukan")

            tema_element = berita.find_element(By.TAG_NAME, "h4")
            tema_berita = tema_element.text.strip() if tema_element else "Tema tidak ditemukan"

            link_berita = judul_element.find_element(By.TAG_NAME, "a").get_attribute("href")
            isi_berita = ambil_isi_berita(driver, link_berita)
            
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
    simpan_ke_database(daftar_berita, daerah_terpilih)

    nama_file_csv = f"result_scrap_{daerah_terpilih.replace(' ', '_').lower()}.csv"
    with open(nama_file_csv, mode='w', newline='', encoding='utf-8') as file_csv:
        penulis_csv = csv.DictWriter(file_csv, fieldnames=["tema", "judul", "tanggal", "link", "isi_berita"])
        penulis_csv.writeheader()
        penulis_csv.writerows(daftar_berita)

    nama_file_json = f"result_scrap_{daerah_terpilih.replace(' ', '_').lower()}.json"
    with open(nama_file_json, mode='w', encoding='utf-8') as file_json:
        json.dump(daftar_berita, file_json, ensure_ascii=False, indent=4)

def start_scraping():
    daerah = daerah_var.get()
    if not daerah:
        messagebox.showerror("Error", "Pilih daerah terlebih dahulu!")
        return
    url = tribun_daerah[daerah]
    threading.Thread(target=lakukan_scraping, args=(url, daerah), daemon=True).start()
    messagebox.showinfo("Info", f"Memulai scraping untuk {daerah}...")

def load_data_from_db():
    daerah = daerah_var.get()
    if not daerah:
        messagebox.showerror("Error", "Pilih daerah terlebih dahulu!")
        return
    try:
        conn = psycopg2.connect(
            dbname=" ",        # ganti dengan nama database
            user=" ",          # ganti dengan nama user database
            password=" ",      # ganti dengan password database
            host=" ",          # ganti dengan nama host database
            port=" "           # ganti dengan port yang di gunakan pada database
        )
        cursor = conn.cursor()
        nama_tabel = f"berita_tribun_{daerah.replace(' ', '_').lower()}"
        cursor.execute(f"SELECT id, tema, judul, tanggal, link, isi_berita FROM {nama_tabel}")
        data = cursor.fetchall()
        
        for item in tree_top.get_children():
            tree_top.delete(item)
        for item in tree_bottom.get_children():
            tree_bottom.delete(item)
        
        global all_data
        all_data = data
        
        for row in data:
            id_berita, tema, judul, tanggal, link, _ = row
            tanggal_str = tanggal.strftime("%A, %Y-%m-%d")
            tree_top.insert("", "end", values=(id_berita, tema, judul, tanggal_str, link))
        
        cursor.close()
        conn.close()
    except Exception as e:
        messagebox.showerror("Error", f"Terjadi kesalahan: {e}")

def show_article_content(event):
    item = tree_top.selection()
    if not item:
        return
    values = tree_top.item(item[0], "values")
    judul = values[2]
    for row in all_data:
        if row[2] == judul:
            _, _, _, _, _, isi_berita = row
            for item in tree_bottom.get_children():
                tree_bottom.delete(item)
            wrapped_isi = textwrap.wrap(isi_berita, width=230)
            for line in wrapped_isi:
                tree_bottom.insert("", "end", values=(line,))
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
    if not daerah:
        messagebox.showerror("Error", "Pilih daerah terlebih dahulu!")
        return
    nama_file_csv = f"result_scrap_{daerah.replace(' ', '_').lower()}.csv"
    try:
        with open(nama_file_csv, mode='w', newline='', encoding='utf-8') as file_csv:
            writer = csv.writer(file_csv)
            writer.writerow(["ID", "Tema", "Judul", "Tanggal", "Link", "Isi Berita"])
            for row in all_data:
                id_berita, tema, judul, tanggal, link, isi_berita = row
                tanggal_str = tanggal.strftime("%A, %Y-%m-%d")
                writer.writerow([id_berita, tema, judul, tanggal_str, link, isi_berita])
        messagebox.showinfo("Info", f"Data diekspor ke {nama_file_csv}")
    except Exception as e:
        messagebox.showerror("Error", f"Gagal mengekspor ke CSV: {e}")

def export_to_json():
    daerah = daerah_var.get()
    if not daerah:
        messagebox.showerror("Error", "Pilih daerah terlebih dahulu!")
        return
    nama_file_json = f"result_scrap_{daerah.replace(' ', '_').lower()}.json"
    try:
        with open(nama_file_json, mode='w', encoding='utf-8') as file_json:
            formatted_data = [
                {
                    "id": row[0],
                    "tema": row[1],
                    "judul": row[2],
                    "tanggal": row[3].strftime("%A, %Y-%m-%d"),
                    "link": row[4],
                    "isi_berita": row[5]
                } for row in all_data
            ]
            json.dump(formatted_data, file_json, ensure_ascii=False, indent=4)
        messagebox.showinfo("Info", f"Data diekspor ke {nama_file_json}")
    except Exception as e:
        messagebox.showerror("Error", f"Gagal mengekspor ke JSON: {e}")

def copy_selected(event=None):
    widget = root.focus_get()
    if widget == tree_top:
        selected = tree_top.selection()
        if selected:
            values = tree_top.item(selected[0], "values")
            root.clipboard_clear()
            root.clipboard_append(" | ".join(values))
            root.update()
    elif widget == tree_bottom:
        selected = tree_bottom.selection()
        if selected:
            value = tree_bottom.item(selected[0], "values")[0]
            root.clipboard_clear()
            root.clipboard_append(value)
            root.update()

def show_context_menu(event, tree):
    selected = tree.selection()
    if not selected:
        return
    context_menu = tk.Menu(root, tearoff=0)
    context_menu.add_command(label="Copy", command=copy_selected)
    context_menu.post(event.x_root, event.y_root)

# GUI Setup
root = tk.Tk()
root.title("Tribun News Scraper")
root.geometry("1200x800")
root.configure(bg="#FFFFFF")

style = ttk.Style()
style.theme_use('clam')
style.configure("TLabel", font=("Segoe UI", 12, "bold"), background="#FFFFFF")
style.configure("TButton", font=("Segoe UI", 10), padding=6)
style.map("TButton", 
          background=[('active', '#1976D2'), ('!active', '#2196F3')],
          foreground=[('active', 'white'), ('!active', 'white')])
style.configure("Treeview", font=("Segoe UI", 10), rowheight=25)
style.configure("Treeview.Heading", font=("Segoe UI", 11, "bold"), background="#BBDEFB")
style.configure("TCombobox", font=("Segoe UI", 10))

main_frame = tk.Frame(root, bg="#FFFFFF", padx=20, pady=20)
main_frame.pack(fill="both", expand=True)

ttk.Label(main_frame, text="Tribun News Scraper", font=("Segoe UI", 15, "bold")).pack(anchor="w", pady=(0, 10), padx=10)

control_frame = tk.Frame(main_frame, bg="#FFFFFF")
control_frame.pack(fill="x", pady=10, padx=10)

daerah_var = tk.StringVar()
ttk.Label(control_frame, text="Pilih Daerah:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
daerah_combo = ttk.Combobox(control_frame, textvariable=daerah_var, values=list(tribun_daerah.keys()))
daerah_combo.grid(row=0, column=1, padx=5, pady=5, sticky="we")

ttk.Button(control_frame, text="Mulai Scraping", command=start_scraping).grid(row=0, column=2, padx=5, pady=5)
ttk.Button(control_frame, text="Muat Data", command=load_data_from_db).grid(row=0, column=3, padx=5, pady=5)
ttk.Button(control_frame, text="Ekspor ke CSV", command=export_to_csv).grid(row=0, column=4, padx=5, pady=5)
ttk.Button(control_frame, text="Ekspor ke JSON", command=export_to_json).grid(row=0, column=5, padx=5, pady=5)

tables_frame = tk.Frame(main_frame, bg="#FFFFFF")
tables_frame.pack(fill="both", expand=True)

ttk.Label(tables_frame, text="Daftar Berita", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(0, 5), padx=10)
tree_top = ttk.Treeview(tables_frame, columns=("id", "tema", "judul", "tanggal", "link"), show="headings", height=6)
tree_top.pack(fill="both", expand=True, pady=5)
tree_top.heading("id", text="ID")
tree_top.heading("tema", text="Tema")
tree_top.heading("judul", text="Judul")
tree_top.heading("tanggal", text="Tanggal")
tree_top.heading("link", text="Link")
tree_top.column("id", width=40)
tree_top.column("tema", width=150)
tree_top.column("judul", width=300)
tree_top.column("tanggal", width=100)
tree_top.column("link", width=350)

tree_top.bind("<Double-1>", open_link)
tree_top.bind("<Control-c>", copy_selected)
tree_top.bind("<Button-3>", lambda event: show_context_menu(event, tree_top))

scroll_top = ttk.Scrollbar(tables_frame, orient="vertical", command=tree_top.yview)
scroll_top.pack(side="right", fill="y")
tree_top.configure(yscrollcommand=scroll_top.set)

ttk.Label(tables_frame, text="Isi Berita", font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(10, 10), padx=10)
tree_bottom = ttk.Treeview(tables_frame, columns=("isi_berita",), show="", height=35)
tree_bottom.pack(fill="both", expand=True, pady=5)
tree_bottom.column("isi_berita", width=1200)

tree_bottom.bind("<Control-c>", copy_selected)
tree_bottom.bind("<Button-3>", lambda event: show_context_menu(event, tree_bottom))

scroll_bottom = ttk.Scrollbar(tables_frame, orient="vertical", command=tree_bottom.yview)
scroll_bottom.pack(side="right", fill="y")
tree_bottom.configure(yscrollcommand=scroll_bottom.set)

tree_top.bind("<<TreeviewSelect>>", show_article_content)

control_frame.columnconfigure(1, weight=1)
all_data = []

root.mainloop()
