import hashlib
import os
import secrets
import sqlite3
import tkinter as tk
from tkinter import messagebox

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 資料庫位置: Check Counter/backend/data/employees.sql
SQL_INIT = os.path.normpath(os.path.join(BASE_DIR, "..", "..", "backend", "data", "employees.sql"))
DB_PATH = os.path.normcase(os.path.join(BASE_DIR, "..", "..", "backend", "data", "products.db"))

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


def 取得連線():
    if not os.path.exists(DB_PATH):
        messagebox.showerror("錯誤", "找不到資料庫檔案")
        return None
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='employees'")
    if cur.fetchone() is None:
        with open(SQL_INIT, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        conn.commit()
    return conn


def 修改密碼():
    emp_id = account_entry.get().strip()
    old_pwd = old_pwd_entry.get().strip()
    new_pwd = new_pwd_entry.get().strip()
    new_pwd_confirm = new_pwd_confirm_entry.get().strip()

    if not emp_id or not old_pwd or not new_pwd or not new_pwd_confirm:
        status_label.config(text="請完整輸入所有欄位", fg="red")
        return

    if new_pwd != new_pwd_confirm:
        status_label.config(text="兩次輸入的新密碼不一致，請重新輸入", fg="red")
        return

    if len(new_pwd) < 4:
        status_label.config(text="新密碼長度至少需要4個字元", fg="red")
        return

    conn = 取得連線()
    if conn is None:
        return

    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT users_name, users_password FROM employees WHERE users_id = ?",
            (emp_id,),
        )
        row = cur.fetchone()
        if row is None:
            status_label.config(text="找不到此員工編號", fg="red")
            return

        name, stored_hash = row
        if not 驗證密碼(old_pwd, stored_hash):
            status_label.config(text="舊密碼輸入錯誤", fg="red")
            return

        new_hash = 產生密碼雜湊(new_pwd)
        cur.execute(
            "UPDATE employees SET users_password = ? WHERE users_id = ?",
            (new_hash, emp_id),
        )
        conn.commit()

        status_label.config(text=f"{name} 密碼修改成功", fg="green")
        old_pwd_entry.delete(0, tk.END)
        new_pwd_entry.delete(0, tk.END)
        new_pwd_confirm_entry.delete(0, tk.END)
    finally:
        conn.close()


win = tk.Tk()
win.title("修改員工密碼")
win.geometry("400x320")

form_frame = tk.Frame(win)
form_frame.pack(pady=20, padx=20, fill="x")

tk.Label(form_frame, text="員工編號:").grid(row=0, column=0, sticky="e", padx=4, pady=8)
account_entry = tk.Entry(form_frame, width=25)
account_entry.grid(row=0, column=1, padx=4, pady=8)

tk.Label(form_frame, text="舊密碼:").grid(row=1, column=0, sticky="e", padx=4, pady=8)
old_pwd_entry = tk.Entry(form_frame, width=25, show="*")
old_pwd_entry.grid(row=1, column=1, padx=4, pady=8)

tk.Label(form_frame, text="新密碼:").grid(row=2, column=0, sticky="e", padx=4, pady=8)
new_pwd_entry = tk.Entry(form_frame, width=25, show="*")
new_pwd_entry.grid(row=2, column=1, padx=4, pady=8)

tk.Label(form_frame, text="再次輸入新密碼:").grid(row=3, column=0, sticky="e", padx=4, pady=8)
new_pwd_confirm_entry = tk.Entry(form_frame, width=25, show="*")
new_pwd_confirm_entry.grid(row=3, column=1, padx=4, pady=8)
new_pwd_confirm_entry.bind("<Return>", lambda event: 修改密碼())

tk.Button(win, text="確認修改", width=15, command=修改密碼).pack(pady=10)

status_label = tk.Label(win, text="", fg="red")
status_label.pack(pady=4)

win.mainloop()
