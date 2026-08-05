# 匯入視窗庫、資料庫與系統庫
import tkinter as tk, sqlite3, os, secrets, hashlib
# 使用 tkinter 的 messagebox 來顯示訊息
from tkinter import ttk, messagebox
# 資料庫位置: Check Counter/POS/backend/data/products.db
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.normpath(os.path.join(BASE_DIR, "..", "..", "..", "backend", "data"))
DB_PATH = os.path.join(DATA_DIR, "products.db")
PRODUCTS_SCHEMA_PATH = os.path.join(DATA_DIR, "products.sql")
EMPLOYEES_SCHEMA_PATH = os.path.join(DATA_DIR, "employees.sql")
# 初始化資料庫
def init_db():
    is_new = not os.path.exists(DB_PATH)
    conn = sqlite3.connect(DB_PATH)
    if is_new:
        with open(PRODUCTS_SCHEMA_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.commit()

    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='employees'")
    if cur.fetchone() is None:
        with open(EMPLOYEES_SCHEMA_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.commit()

    conn.execute("PRAGMA journal_mode=WAL")
    return conn

conn = init_db()
cursor = conn.cursor()
# 定義全域變數 current_user 用來儲存目前登入的使用者資訊
current_user = None
# 定義全域變數購物車 cart 用來儲存使用者選購的商品資訊
cart = []
# 定義全域變數 total 用來計算購物車總金額
total = 0
PBKDF2_ITERATIONS = 100_000
# 定義密碼雜湊函式，使用 PBKDF2-HMAC-SHA256 進行密碼雜湊，並返回包含鹽值和雜湊值的字串
def pwd_hash(pwd, salt=None):
    if salt is None:
        salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", pwd.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return salt.hex() + "$" + dk.hex()
# 定義密碼驗證函式，將使用者輸入的密碼與資料庫中存儲的雜湊值進行比對，返回布林值表示驗證結果
def pwd_verify(pwd, hashed):
    try:
        salt_hex, hash_hex = hashed.split("$", 1)
        salt = bytes.fromhex(salt_hex)
    except ValueError:
        return False
    dk = hashlib.pbkdf2_hmac("sha256", pwd.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return secrets.compare_digest(dk.hex(), hash_hex)
# 定義購物車總金額計算函式，遍歷購物車中的商品資訊，計算總金額並返回
def cart_reload():
    for row in cart_tree.get_children():
        cart_tree.delete(row)
        for i, item in enumerate(cart):
            cart_tree.insert("", "end", values=(i + 1, item["name"], item["price"], item["quantity"]))
        # sum_label.config(text=f"總金額: {total} 元")

def login(event=None):
    global current_user
    

def open_windows():
    global win, cart_tree, sum_label, balance_label, barcode_entry, money_entry
    global date_label, clock_label, result_label, focused_entry

    assert current_user is not None
    
    win = tk.Tk()
    win.title("結帳視窗")
    win.geometry("800x600")

    #  --- 上方狀態列: 目前使用者
    status_frame = tk.Frame(win)
    status_frame.pack(side="top", fill="x", padx=8, pady=4)
    tk.Label(
        status_frame,
        text=f"目前登入: {current_user[1]}({current_user[0]})",
        fg="blue",
    ).pack(side="left")


    cart_tree = ttk.Treeview(win, columns=("No", "Name", "Price", "Quantity"), show="headings")
