"""
從 users_pwd.csv 讀取使用者密碼，自動 bcrypt hash 後輸出 hash.sql。
用法：python gen_hash.py
"""
import bcrypt
import csv
import os

csv_path = os.path.join(os.path.dirname(__file__), "employees.sql")
sql_path = os.path.join(os.path.dirname(__file__), "hash.sql")

statements = []
with open(csv_path, newline="", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for row in reader:
        user_id = int(row["員工編號"])
        plain = row["初始密碼"]
        hashed = bcrypt.hashpw(plain.encode(), bcrypt.gensalt(rounds=12)).decode()
        statements.append(
            f"UPDATE users SET password_hash = '{hashed}' WHERE user_id = {user_id};"
        )
        print(f"  user_id={user_id}  →  {hashed}")

sql_content = (
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);\n\n"
    + "\n".join(statements)
    + "\n"
)

with open(sql_path, "w", encoding="utf-8") as f:
    f.write(sql_content)

print(f"\n共 {len(statements)} 筆 hash，已輸出至：{sql_path}")
