# 商品編輯版 - 新增 / 修改 / 刪除商品
import os
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.normpath(os.path.join(BASE_DIR, "..", "..", "..", "backend", "data", "products.db"))

def 取得連線():
    if not os.path.exists(DB_PATH):
        messagebox.showerror("錯誤", "找不到商品資料庫，請先執行 main.py 建立資料庫")
        return None
    return sqlite3.connect(DB_PATH)


def 開啟商品編輯視窗(parent=None):
    win = tk.Toplevel(parent) if parent is not None else tk.Tk()
    win.title("商品編輯")
    win.geometry("")

    conn = 取得連線()
    if conn is None:
        win.destroy()
        return win
    cursor = conn.cursor()

    form_frame = tk.LabelFrame(win, text="商品資料")
    form_frame.pack(side="top", fill="x", padx=8, pady=8)

    tk.Label(form_frame, text="條碼:").grid(row=0, column=0, sticky="e", padx=4, pady=4)
    barcode_entry = tk.Entry(form_frame, width=25)
    barcode_entry.grid(row=0, column=1, padx=4, pady=4)

    tk.Label(form_frame, text="商品名稱:").grid(row=1, column=0, sticky="e", padx=4, pady=4)
    name_entry = tk.Entry(form_frame, width=25)
    name_entry.grid(row=1, column=1, padx=4, pady=4)

    tk.Label(form_frame, text="價格:").grid(row=2, column=0, sticky="e", padx=4, pady=4)
    price_entry = tk.Entry(form_frame, width=25)
    price_entry.grid(row=2, column=1, padx=4, pady=4)

    tk.Label(form_frame, text="庫存:").grid(row=3, column=0, sticky="e", padx=4, pady=4)
    stock_entry = tk.Entry(form_frame, width=25)
    stock_entry.grid(row=3, column=1, padx=4, pady=4)

    tk.Label(form_frame, text="貨架:").grid(row=4, column=0, sticky="e", padx=4, pady=4)
    shelves_entry = tk.Entry(form_frame, width=25)
    shelves_entry.grid(row=4, column=1, padx=4, pady=4)

    status_label = tk.Label(win, text="", fg="blue")
    status_label.pack(side="top", pady=(0, 4))

    columns = ("條碼", "商品名稱", "價格", "庫存", "貨架")
    tree = ttk.Treeview(win, columns=columns, show="headings", height=12)
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, width=120, anchor="center")
    tree.pack(side="top", fill="both", expand=True, padx=8, pady=(0, 8))

    def 清空欄位():
        barcode_entry.delete(0, tk.END)
        name_entry.delete(0, tk.END)
        price_entry.delete(0, tk.END)
        stock_entry.delete(0, tk.END)
        shelves_entry.delete(0, tk.END)
        status_label.config(text="")

    def 重新整理列表():
        for row in tree.get_children():
            tree.delete(row)
        cursor.execute("SELECT barcode, product_name, price, stock, shelves FROM products ORDER BY id")
        for row in cursor.fetchall():
            tree.insert("", "end", values=row)

    def 查詢商品(event=None):
        barcode = barcode_entry.get().strip()
        if not barcode:
            status_label.config(text="請輸入條碼", fg="red")
            return
        cursor.execute(
            "SELECT product_name, price, stock, shelves FROM products WHERE barcode = ?",
            (barcode,),
        )
        row = cursor.fetchone()
        if row is None:
            name_entry.delete(0, tk.END)
            price_entry.delete(0, tk.END)
            stock_entry.delete(0, tk.END)
            shelves_entry.delete(0, tk.END)
            status_label.config(text="查無此商品，可直接按「儲存」新增", fg="blue")
            return
        name, price, stock, shelves = row
        name_entry.delete(0, tk.END); name_entry.insert(0, name)
        price_entry.delete(0, tk.END); price_entry.insert(0, price)
        stock_entry.delete(0, tk.END); stock_entry.insert(0, stock)
        shelves_entry.delete(0, tk.END); shelves_entry.insert(0, shelves)
        status_label.config(text=f"已載入「{name}」，可修改後按「儲存」", fg="green")

    def 載入選取列(event=None):
        selected = tree.selection()
        if not selected:
            return
        values = tree.item(selected[0], "values")
        barcode_entry.delete(0, tk.END); barcode_entry.insert(0, values[0])
        name_entry.delete(0, tk.END); name_entry.insert(0, values[1])
        price_entry.delete(0, tk.END); price_entry.insert(0, values[2])
        stock_entry.delete(0, tk.END); stock_entry.insert(0, values[3])
        shelves_entry.delete(0, tk.END); shelves_entry.insert(0, values[4])
        status_label.config(text=f"已載入「{values[1]}」，可修改後按「儲存」", fg="green")

    def 儲存商品():
        barcode = barcode_entry.get().strip()
        name = name_entry.get().strip()
        price_text = price_entry.get().strip()
        stock_text = stock_entry.get().strip()
        shelves = shelves_entry.get().strip()

        if not barcode or not name:
            status_label.config(text="條碼與商品名稱不能為空", fg="red")
            return
        try:
            price = int(price_text)
            stock = int(stock_text)
        except ValueError:
            status_label.config(text="價格與庫存請輸入數字", fg="red")
            return

        cursor.execute("SELECT id FROM products WHERE barcode = ?", (barcode,))
        existing = cursor.fetchone()
        if existing is None:
            cursor.execute(
                "INSERT INTO products (barcode, product_name, price, stock, shelves) VALUES (?, ?, ?, ?, ?)",
                (barcode, name, price, stock, shelves),
            )
            status_label.config(text=f"已新增商品「{name}」", fg="green")
        else:
            cursor.execute(
                "UPDATE products SET product_name = ?, price = ?, stock = ?, shelves = ? WHERE barcode = ?",
                (name, price, stock, shelves, barcode),
            )
            status_label.config(text=f"已更新商品「{name}」", fg="green")

        conn.commit()
        重新整理列表()

    def 刪除商品():
        barcode = barcode_entry.get().strip()
        if not barcode:
            status_label.config(text="請先輸入或選取要刪除的條碼", fg="red")
            return
        cursor.execute("SELECT product_name FROM products WHERE barcode = ?", (barcode,))
        row = cursor.fetchone()
        if row is None:
            status_label.config(text="查無此商品，無法刪除", fg="red")
            return
        if not messagebox.askyesno("刪除確認", f"確定要刪除商品「{row[0]}」嗎？"):
            return
        cursor.execute("DELETE FROM products WHERE barcode = ?", (barcode,))
        conn.commit()
        清空欄位()
        重新整理列表()

    barcode_entry.bind("<Return>", 查詢商品)
    tree.bind("<Double-1>", 載入選取列)

    button_frame = tk.Frame(form_frame)
    button_frame.grid(row=0, column=2, rowspan=5, padx=12)
    tk.Button(button_frame, text="查詢", width=10, command=查詢商品).pack(pady=2)
    tk.Button(button_frame, text="儲存", width=10, command=儲存商品).pack(pady=2)
    tk.Button(button_frame, text="刪除", width=10, command=刪除商品).pack(pady=2)
    tk.Button(button_frame, text="清空欄位", width=10, command=清空欄位).pack(pady=2)

    重新整理列表()

    win.protocol("WM_DELETE_WINDOW", lambda: (conn.close(), win.destroy()))
    return win


if __name__ == "__main__":
    root = 開啟商品編輯視窗(None)
    root.mainloop()
