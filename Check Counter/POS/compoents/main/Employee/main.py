# sql 版
# 以下 import 模組統一以這個格式進行，避免重複 import 且不可任意修改
import hashlib, os, secrets, sqlite3, time, tkinter as tk
from tkinter import ttk, messagebox

# 資料庫位置: Check Counter/POS/data/products.db
# 第一次執行會用 products.sql / employees.sql 自動建立資料表
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.normpath(os.path.join(BASE_DIR, "..", "..", "..", "backend", "data"))
DB_PATH = os.path.join(DATA_DIR, "products.db")
PRODUCTS_SCHEMA_PATH = os.path.join(DATA_DIR, "products.sql")
EMPLOYEES_SCHEMA_PATH = os.path.join(DATA_DIR, "employees.sql")


def 初始化資料庫():
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


conn = 初始化資料庫()
cursor = conn.cursor()

STORE_NO = "6281"
current_employee = None    # (users_id, users_name)
cart = []                  # [{barcode, name, price, qty, age_limit}]
total = 0
focused_entry = None       # 數字鍵盤要打字進去的目標欄位（依最後 focus 的輸入框）

PBKDF2_ITERATIONS = 100_000


def 產生密碼雜湊(password, salt=None):
    if salt is None:
        salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return salt.hex() + "$" + dk.hex()


def 驗證密碼(password, stored):
    try:
        salt_hex, hash_hex = stored.split("$", 1)
        salt = bytes.fromhex(salt_hex)
    except ValueError:
        return False
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS)
    return secrets.compare_digest(dk.hex(), hash_hex)


def 取得商品(barcode):
    # 同一條碼若對應到多筆商品，優先取需要年齡驗證（酒類/香菸）的那一筆，避免漏檢查
    cursor.execute(
        """
        SELECT product_name, price, shelves
        FROM products
        WHERE barcode = ?
        ORDER BY (shelves LIKE '%酒%' OR shelves LIKE '%香菸%') DESC
        LIMIT 1
        """,
        (barcode,),
    )
    return cursor.fetchone()


def 判斷年齡限制(shelves):
    if "酒" in shelves:
        return 18
    if "香菸" in shelves:
        return 20
    return 0


def 重新整理購物車():
    for row in cart_tree.get_children():
        cart_tree.delete(row)
    for i, item in enumerate(cart):
        age_text = f"{item['age_limit']}歲以上" if item["age_limit"] > 0 else "無"
        cart_tree.insert(
            "", "end", iid=str(i),
            values=(item["barcode"], item["name"], item["price"], item["qty"], age_text),
        )
    sum_label.config(text=f"總計:{total}元")

def 更新商品資料庫(barcode, name, price, qty, shelves):
    cursor.execute("SELECT id FROM products WHERE barcode = ?", (barcode,))
    if cursor.fetchone():
        cursor.execute("UPDATE products SET stock = stock - ? WHERE barcode = ?", (qty, barcode))
    else:
        cursor.execute(
            "INSERT INTO products (barcode, product_name, price, stock, shelves) VALUES (?, ?, ?, 0, ?)",
            (barcode, name, price, shelves),
        )
    conn.commit()

def 掃描條碼(event=None):
    global total
    barcode = barcode_entry.get().strip()
    barcode_entry.delete(0, tk.END)

    if not barcode:
        return

    result = 取得商品(barcode)
    if result is None:
        result_label.config(text=f"查無商品：{barcode}")
        return

    name, price, shelves = result
    price = int(str(price).replace(",", "").strip())
    age_limit = 判斷年齡限制(shelves)

    if age_limit > 0:
        ok = messagebox.askyesno("年齡確認", f"商品「{name}」需年滿{age_limit}歲才能購買，是否年滿{age_limit}歲？")
        if not ok:
            result_label.config(text=f"抱歉，商品「{name}」因未成年而無法購買")
            return

    for item in cart:
        if item["barcode"] == barcode:
            item["qty"] += 1
            break
    else:
        cart.append({"barcode": barcode, "name": name, "price": price, "qty": 1, "age_limit": age_limit})

    total += price
    result_label.config(text=f"商品:{name}  價格:{price}元")
    重新整理購物車()


def 刪除選取商品(event=None):
    global total
    selected = cart_tree.selection()
    if not selected:
        return
    idx = int(selected[0])
    item = cart[idx]
    total -= item["price"] * item["qty"]
    if total < 0:
        total = 0
    cart.pop(idx)
    重新整理購物車()


def 結帳(event=None):
    global total, cart
    if not cart:
        messagebox.showinfo("結帳", "購物車是空的")
        return
    try:
        money = int(money_entry.get().strip() or "0")
    except ValueError:
        messagebox.showerror("金額錯誤", "請輸入正確的金額數字")
        return

    if money < total:
        messagebox.showwarning("金額不足", f"應付金額 {total} 元，收取金額不足")
        return

    balance = money - total
    balance_label.config(text=f"找零:{balance}元")
    for item in cart:
        更新商品資料庫(item['barcode'], item['name'], item['price'], item['qty'], '')
    money_entry.delete(0, tk.END)
    cart = []
    total = 0
    重新整理購物車()


def 設定焦點(entry):
    def handler(event):
        global focused_entry
        focused_entry = entry
    return handler


def 建立數字鍵盤(parent, 取得預設目標, 動作標籤=None, 執行動作=None):
    """通用數字鍵盤：輸入打進目前 focus 的欄位（沒有就用預設目標），
    右下角可放一個動作鍵（例如登入視窗放「登入」、結帳視窗放「結帳」）。"""
    frame = tk.Frame(parent)

    def 按下(value):
        target = focused_entry or 取得預設目標()
        if target is None:
            return
        if value == "←":
            current = target.get()
            if current:
                target.delete(len(current) - 1, tk.END)
        elif value == "清除":
            target.delete(0, tk.END)
        elif value == "輸入":
            target.event_generate("<Return>")
        elif value == "__執行動作__":
            if 執行動作:
                執行動作()
        else:
            target.insert(tk.END, value)

    layout = [
        ["7", "8", "9", "←"],
        ["4", "5", "6", "清除"],
        ["1", "2", "3", "輸入"],
        ["0", "00", "", 動作標籤 or ""],
    ]
    for r, row_vals in enumerate(layout):
        for c, val in enumerate(row_vals):
            if val == "":
                continue
            按鍵值 = "__執行動作__" if (動作標籤 and val == 動作標籤) else val
            tk.Button(
                frame, text=val, width=6, height=3, font=("Arial", 14),
                command=lambda v=按鍵值: 按下(v),
            ).grid(row=r, column=c, padx=2, pady=2)
    return frame


def 登入(event=None):
    global current_employee
    emp_id = login_id_entry.get().strip()
    emp_pwd = login_pwd_entry.get().strip()

    if not emp_id or not emp_pwd:
        messagebox.showerror("登入失敗", "請輸入員工編號與密碼")
        return

    cursor.execute(
        "SELECT users_id, users_name, users_password FROM employees WHERE users_id = ?",
        (emp_id,),
    )
    row = cursor.fetchone()
    if row is None or not 驗證密碼(emp_pwd, row[2]):
        messagebox.showerror("登入失敗", "員工編號或密碼錯誤")
        return

    current_employee = (row[0], row[1])
    login_win.destroy()
    開啟結帳視窗()


def 更新時間():
    date_label.config(text="日期:" + time.strftime("%Y-%m-%d"))
    clock_label.config(text="時間:" + time.strftime("%H:%M:%S"))
    win.after(1000, 更新時間)


def 開啟結帳視窗():
    global win, cart_tree, sum_label, balance_label, barcode_entry, money_entry
    global date_label, clock_label, result_label, focused_entry

    assert current_employee is not None  # 只會在 登入() 成功設定後才呼叫本函式

    win = tk.Tk()
    win.title("Employee Interface")
    win.geometry("")

    # ---- 上方狀態列：目前登入者 + 商品管理入口 ----
    status_frame = tk.Frame(win)
    status_frame.pack(side="top", fill="x", padx=8, pady=4)
    tk.Label(
        status_frame,
        text=f"店編:{STORE_NO}    目前登入:{current_employee[1]}({current_employee[0]})",
        fg="blue",
    ).pack(side="left")

    # ---- 日期時間 ----
    clock_frame = tk.Frame(win)
    clock_frame.pack(side="top", pady=4)
    date_label = tk.Label(clock_frame, text="日期", font=("Arial", 18))
    date_label.pack()
    clock_label = tk.Label(clock_frame, text="時間", font=("Arial", 18))
    clock_label.pack()

    # ---- 條碼 / 總計 / 金額 / 結帳 ----
    checkout_frame = tk.Frame(win)
    checkout_frame.pack(side="top", fill="x", padx=8, pady=4)

    tk.Label(checkout_frame, text="請輸入條碼:").grid(row=0, column=0, padx=4)
    barcode_entry = tk.Entry(checkout_frame, font=("Arial", 14), width=20)
    barcode_entry.grid(row=0, column=1, padx=4)
    barcode_entry.bind("<Return>", 掃描條碼)
    barcode_entry.bind("<FocusIn>", 設定焦點(barcode_entry))
    barcode_entry.focus()

    sum_label = tk.Label(checkout_frame, text="總計:0元", font=("Arial", 14))
    sum_label.grid(row=0, column=2, padx=12)
    balance_label = tk.Label(checkout_frame, text="找零:0元", font=("Arial", 14))
    balance_label.grid(row=0, column=3, padx=12)

    tk.Label(checkout_frame, text="請輸入金額:").grid(row=0, column=4, padx=4)
    money_entry = tk.Entry(checkout_frame, font=("Arial", 14), width=12, justify="center")
    money_entry.grid(row=0, column=5, padx=4)
    money_entry.bind("<Return>", 結帳)
    money_entry.bind("<FocusIn>", 設定焦點(money_entry))

    tk.Button(checkout_frame, text="結帳", command=結帳).grid(row=0, column=6, padx=8)

    # ---- 主體：左邊購物車 + 右邊數字鍵盤 ----
    body_frame = tk.Frame(win)
    body_frame.pack(side="top", fill="both", expand=True, padx=8, pady=4)

    cart_columns = ("條碼", "商品名稱", "價格", "數量", "年齡限制")
    cart_tree = ttk.Treeview(body_frame, columns=cart_columns, show="headings", height=18)
    for col in cart_columns:
        cart_tree.heading(col, text=col)
        cart_tree.column(col, width=110, anchor="center")
    cart_tree.pack(side="left", fill="both", expand=True)
    cart_tree.bind("<Double-1>", 刪除選取商品)

    cart_scroll = ttk.Scrollbar(body_frame, orient="vertical", command=cart_tree.yview)
    cart_tree.configure(yscrollcommand=cart_scroll.set)
    cart_scroll.pack(side="left", fill="y")

    tk.Button(body_frame, text="刪除選取\n(操作)", command=刪除選取商品).pack(side="left", anchor="n", padx=8, pady=4)

    checkout_keypad = 建立數字鍵盤(body_frame, lambda: money_entry, 動作標籤="結帳", 執行動作=結帳)
    checkout_keypad.pack(side="right", padx=8)

    result_label = tk.Label(win, text="", font=("Arial", 12))
    result_label.pack(side="bottom", pady=4)

    focused_entry = barcode_entry
    更新時間()
    win.mainloop()


# ---------------- 登入視窗（獨立視窗，登入成功後才開結帳視窗） ----------------
login_win = tk.Tk()
login_win.title("員工登入")
login_win.geometry("")

login_frame = tk.LabelFrame(login_win, text="登入")
login_frame.pack(side="top", fill="x", padx=8, pady=8)

tk.Label(login_frame, text="店編:").grid(row=0, column=0, sticky="e", padx=4, pady=2)
tk.Label(login_frame, text=STORE_NO, fg="gray").grid(row=0, column=1, sticky="w", padx=4, pady=2)

tk.Label(login_frame, text="員工編號:").grid(row=1, column=0, sticky="e", padx=4, pady=2)
login_id_entry = tk.Entry(login_frame, width=20)
login_id_entry.grid(row=1, column=1, padx=4, pady=2)
login_id_entry.bind("<FocusIn>", 設定焦點(login_id_entry))

tk.Label(login_frame, text="員工密碼:").grid(row=2, column=0, sticky="e", padx=4, pady=2)
login_pwd_entry = tk.Entry(login_frame, width=20, show="*")
login_pwd_entry.grid(row=2, column=1, padx=4, pady=2)
login_pwd_entry.bind("<FocusIn>", 設定焦點(login_pwd_entry))
login_pwd_entry.bind("<Return>", 登入)

tk.Label(login_frame, text="班別:").grid(row=3, column=0, sticky="e", padx=4, pady=2)
shift_combo = ttk.Combobox(login_frame, values=["早班", "午班", "晚班"], state="readonly", width=17)
shift_combo.grid(row=3, column=1, padx=4, pady=2)

tk.Button(login_frame, text="登入", command=登入).grid(row=1, column=2, rowspan=2, padx=8)

login_status_label = tk.Label(login_frame, text="請輸入員工編號與密碼登入", fg="blue")
login_status_label.grid(row=4, column=0, columnspan=3, sticky="w", padx=4)

login_keypad = 建立數字鍵盤(login_win, lambda: login_id_entry, 動作標籤="登入", 執行動作=登入)
login_keypad.pack(side="top", pady=(0, 8))

login_id_entry.focus()
focused_entry = login_id_entry

login_win.mainloop()
