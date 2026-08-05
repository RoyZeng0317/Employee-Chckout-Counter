# 商品管理版 - 商品報表 / 商品編輯 / 訂貨系統等後台功能
# 由 check_counter_sql.py 的結帳視窗按「商品管理」開啟，也可單獨執行
# 進入前須以店長編號與密碼登入，驗證方式與 check_counter_sql.py 的員工登入相同，但讀取獨立的 manager 資料表（data/manager.sql）
import hashlib, os, secrets, sqlite3, time, tkinter as tk
from tkinter import ttk, messagebox

import Products_Edit

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.normpath(os.path.join(BASE_DIR, "..", "..", "..", "backend", "data", "products.db"))

PBKDF2_ITERATIONS = 100_000


def 取得連線():
    if not os.path.exists(DB_PATH):
        messagebox.showerror("錯誤", "找不到商品資料庫，請先執行 main.py 建立資料庫")
        return None
    c = sqlite3.connect(DB_PATH)
    c.execute("PRAGMA journal_mode=WAL")
    return c


def 確保店長資料表(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='manager'")
    if cursor.fetchone() is None:
        with open(SQL_INIT, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.commit()


def 驗證密碼(password, stored):
    try:
        salt_hex, hash_hex = stored.split("$", 1)
        salt = bytes.fromhex(salt_hex)
    except ValueError:
        return False
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return secrets.compare_digest(dk.hex(), hash_hex)


def 尚未實作(name):
    messagebox.showinfo("提示", f"「{name}」功能尚未實作")


def 顯示商品報表(parent):
    conn = 取得連線()
    if conn is None:
        return

    report_win = tk.Toplevel(parent)
    report_win.title("商品報表")

    columns = ("條碼", "商品名稱", "價格", "庫存", "貨架")
    tree = ttk.Treeview(report_win, columns=columns, show="headings", height=20)
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=120, anchor="center")
    tree.pack(fill="both", expand=True)

    cursor = conn.cursor()
    cursor.execute("SELECT barcode, product_name, price, stock, shelves FROM products ORDER BY id")
    for row in cursor.fetchall():
        tree.insert("", "end", values=row)

    report_win.protocol("WM_DELETE_WINDOW", lambda: (conn.close(), report_win.destroy()))


def 開啟庫存變更視窗(parent):
    conn = 取得連線()
    if conn is None:
        return None
    cursor = conn.cursor()

    stock_win = tk.Toplevel(parent)
    stock_win.title("庫存變更")
    stock_win.geometry("")

    form_frame = tk.Frame(stock_win)
    form_frame.pack(padx=12, pady=12)

    tk.Label(form_frame, text="條碼:").grid(row=0, column=0, sticky="e", padx=4, pady=4)
    barcode_entry = tk.Entry(form_frame, width=20)
    barcode_entry.grid(row=0, column=1, padx=4, pady=4)

    name_label = tk.Label(form_frame, text="商品名稱: -")
    name_label.grid(row=1, column=0, columnspan=2, sticky="w", padx=4, pady=2)
    current_stock_label = tk.Label(form_frame, text="目前庫存: -")
    current_stock_label.grid(row=2, column=0, columnspan=2, sticky="w", padx=4, pady=2)

    tk.Label(form_frame, text="新庫存數量:").grid(row=3, column=0, sticky="e", padx=4, pady=4)
    new_stock_entry = tk.Entry(form_frame, width=20)
    new_stock_entry.grid(row=3, column=1, padx=4, pady=4)

    status_label = tk.Label(stock_win, text="", fg="red")
    status_label.pack(pady=(0, 8))

    def 查詢庫存(event=None):
        barcode = barcode_entry.get().strip()
        if not barcode:
            status_label.config(text="請輸入條碼", fg="red")
            return
        cursor.execute("SELECT product_name, stock FROM products WHERE barcode = ?", (barcode,))
        row = cursor.fetchone()
        if row is None:
            name_label.config(text="商品名稱: -")
            current_stock_label.config(text="目前庫存: -")
            status_label.config(text="查無此商品", fg="red")
            return
        name, stock = row
        name_label.config(text=f"商品名稱: {name}")
        current_stock_label.config(text=f"目前庫存: {stock}")
        new_stock_entry.delete(0, tk.END)
        new_stock_entry.insert(0, str(stock))
        status_label.config(text="", fg="red")

    def 更新庫存():
        barcode = barcode_entry.get().strip()
        if not barcode:
            status_label.config(text="請輸入條碼", fg="red")
            return
        try:
            new_stock = int(new_stock_entry.get().strip())
        except ValueError:
            status_label.config(text="庫存請輸入數字", fg="red")
            return

        cursor.execute("SELECT product_name FROM products WHERE barcode = ?", (barcode,))
        row = cursor.fetchone()
        if row is None:
            status_label.config(text="查無此商品", fg="red")
            return

        cursor.execute("UPDATE products SET stock = ? WHERE barcode = ?", (new_stock, barcode))
        conn.commit()
        current_stock_label.config(text=f"目前庫存: {new_stock}")
        status_label.config(text=f"已更新「{row[0]}」庫存為 {new_stock}", fg="green")

    barcode_entry.bind("<Return>", 查詢庫存)

    button_frame = tk.Frame(stock_win)
    button_frame.pack(pady=(0, 12))
    tk.Button(button_frame, text="查詢", width=10, command=查詢庫存).pack(side="left", padx=4)
    tk.Button(button_frame, text="更新庫存", width=10, command=更新庫存).pack(side="left", padx=4)

    stock_win.protocol("WM_DELETE_WINDOW", lambda: (conn.close(), stock_win.destroy()))
    return stock_win


def 開啟登入視窗(on_success, parent=None):
    """跳出店長編號/密碼登入視窗，驗證成功後呼叫 on_success(manager_id, manager_name)。
    驗證邏輯與 check_counter_sql.py 的員工登入相同，但讀取獨立的 manager 資料表（data/manager.sql）。"""
    conn = 取得連線()
    if conn is None:
        return None
    確保店長資料表(conn)
    cursor = conn.cursor()

    login_win = tk.Toplevel(parent) if parent is not None else tk.Tk()
    login_win.title("店長登入")
    login_win.geometry("")

    login_frame = tk.LabelFrame(login_win, text="商品管理登入")
    login_frame.pack(padx=12, pady=12)

    tk.Label(login_frame, text="店長編號:").grid(row=0, column=0, sticky="e", padx=4, pady=4)
    id_entry = tk.Entry(login_frame, width=20)
    id_entry.grid(row=0, column=1, padx=4, pady=4)
    id_entry.focus()

    tk.Label(login_frame, text="店長密碼:").grid(row=1, column=0, sticky="e", padx=4, pady=4)
    pwd_entry = tk.Entry(login_frame, width=20, show="*")
    pwd_entry.grid(row=1, column=1, padx=4, pady=4)

    status_label = tk.Label(login_frame, text="請輸入店長編號與密碼", fg="blue")
    status_label.grid(row=2, column=0, columnspan=2, sticky="w", padx=4, pady=(4, 0))

    def 關閉(event=None):
        conn.close()
        login_win.destroy()

    def 登入(event=None):
        manager_id = id_entry.get().strip()
        manager_pwd = pwd_entry.get().strip()

        if not manager_id or not manager_pwd:
            status_label.config(text="請輸入店長編號與密碼", fg="red")
            return

        cursor.execute(
            "SELECT users_id, users_name, users_password FROM manager WHERE users_id = ?",
            (manager_id,),
        )
        row = cursor.fetchone()
        if row is None or not 驗證密碼(manager_pwd, row[2]):
            status_label.config(text="店長編號或密碼錯誤", fg="red")
            pwd_entry.delete(0, tk.END)
            return

        conn.close()
        if parent is None:
            login_win.withdraw()
        else:
            login_win.destroy()
        on_success(row[0], row[1])

    id_entry.bind("<Return>", lambda e: pwd_entry.focus())
    pwd_entry.bind("<Return>", 登入)
    tk.Button(login_frame, text="登入", command=登入).grid(row=0, column=2, rowspan=2, padx=8)

    login_win.protocol("WM_DELETE_WINDOW", 關閉)
    return login_win


def 開啟管理視窗(parent=None):
    """開啟商品管理主視窗前，須先以店長編號與密碼登入。"""

    def 顯示管理內容(manager_id, manager_name):
        content_win = tk.Toplevel(parent) if parent is not None else tk.Toplevel(login_win)
        content_win.title("商品管理")
        content_win.geometry("")

        tk.Label(content_win, text=f"目前登入店長:{manager_name}({manager_id})", fg="blue").pack(
            anchor="w", padx=8, pady=(8, 0)
        )

        func_frame = tk.Frame(content_win)
        func_frame.pack(padx=8, pady=8)

        tk.Button(func_frame, text="商品報表", width=14, height=3,
                  command=lambda: 顯示商品報表(content_win)).grid(row=0, column=0, padx=4, pady=4)
        tk.Button(func_frame, text="商品編輯", width=14, height=3,
                  command=lambda: Products_Edit.開啟商品編輯視窗(content_win)).grid(row=0, column=1, padx=4, pady=4)
        tk.Button(func_frame, text="訂貨系統", width=14, height=3,
                  command=lambda: 尚未實作("訂貨系統")).grid(row=0, column=2, padx=4, pady=4)
        tk.Button(func_frame, text="功能顯示", width=14, height=3,
                  command=lambda: 尚未實作("功能顯示")).grid(row=1, column=1, padx=4, pady=4)
        tk.Button(func_frame, text="庫存變更", width=14, height=3,
                  command=lambda: 開啟庫存變更視窗(content_win)).grid(row=1, column=2, padx=4, pady=4)

        if parent is None and login_win is not None:
            lw = login_win
            content_win.protocol("WM_DELETE_WINDOW", lambda lw=lw: (content_win.destroy(), lw.destroy()))

    login_win = 開啟登入視窗(顯示管理內容, parent)
    if parent is None and login_win is not None:
        login_win.mainloop()
    return login_win


if __name__ == "__main__":
    開啟管理視窗(None)
