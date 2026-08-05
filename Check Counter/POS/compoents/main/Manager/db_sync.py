# 資料庫同步模組（純 SQLite3）
# 從 products.sql 檔案更新 products.db
import os, re, sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.normpath(os.path.join(BASE_DIR, "..", "..", "..", "backend", "data", "products.db"))
SQL_PATH = os.path.normpath(os.path.join(BASE_DIR, "..", "..", "..", "backend", "data", "products.sql"))


def _解析SQLValues(values_part):
    """解析 VALUES(...) 內的每一筆資料，回傳 list of tuple"""
    pattern = r"\('[^']*'\s*,\s*'[^']*'\s*,\s*'[^']*'\s*,\s*[^,)]+\s*,\s*'[^']*'\)"
    rows_raw = re.findall(pattern, values_part)
    rows = []
    for row in rows_raw:
        # 去掉括號後依逗號拆分
        inner = row.strip("()")
        parts = []
        buf = []
        in_q = False
        for c in inner:
            if c == "'":
                in_q = not in_q
            elif c == "," and not in_q:
                parts.append("".join(buf).strip().strip("'"))
                buf = []
            else:
                buf.append(c)
        if buf:
            parts.append("".join(buf).strip().strip("'"))
        if len(parts) == 5:
            rows.append(tuple(parts))
    return rows


def 從SQL檔載入商品():
    """從 products.sql 解析商品資料，回傳 (商品list, 錯誤訊息)"""
    if not os.path.exists(SQL_PATH):
        return [], f"找不到 {SQL_PATH}"
    try:
        with open(SQL_PATH, "r", encoding="utf-8") as f:
            content = f.read()
    except Exception as e:
        return [], f"讀取 SQL 檔失敗: {e}"

    pattern = r"INSERT\s+INTO\s+products\s*\([^)]+\)\s*VALUES\s*(.*?);"
    match = re.search(pattern, content, re.IGNORECASE | re.DOTALL)
    if not match:
        return [], "SQL 檔中找不到 INSERT 語句"

    values_text = match.group(1).strip()
    return _解析SQLValues(values_text), ""


def 從SQL檔更新資料庫():
    """從 products.sql 更新 SQLite 資料庫，回傳 (更新筆數, 錯誤訊息)"""
    rows, err = 從SQL檔載入商品()
    if err:
        return 0, err
    if not rows:
        return 0, "SQL 檔中沒有商品資料"

    if not os.path.exists(DB_PATH):
        return 0, "SQLite 資料庫不存在"

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    count = 0
    try:
        for barcode, name, price, stock, shelves in rows:
            if not barcode:
                continue
            price_clean = re.sub(r"[^\d]", "", price)
            stock_clean = re.sub(r"[^\d]", "", stock)
            if not price_clean or not stock_clean:
                continue
            price_val = int(price_clean)
            stock_val = int(stock_clean)
            cur.execute("SELECT id FROM products WHERE barcode = ?", (barcode,))
            exists = cur.fetchone()
            if exists is None:
                cur.execute(
                    "INSERT INTO products (barcode, product_name, price, stock, shelves) VALUES (?, ?, ?, ?, ?)",
                    (barcode, name, price_val, stock_val, shelves),
                )
            else:
                cur.execute(
                    "UPDATE products SET product_name = ?, price = ?, stock = ?, shelves = ? WHERE barcode = ?",
                    (name, price_val, stock_val, shelves, barcode),
                )
            count += 1
        conn.commit()
    except Exception as e:
        conn.rollback()
        conn.close()
        return 0, f"寫入失敗: {e}"
    conn.close()
    return count, ""


def 雙向同步():
    """執行資料庫更新，回傳狀態訊息字串"""
    count, err = 從SQL檔更新資料庫()
    if err:
        return f"更新失敗: {err}"
    return f"從 SQL 檔更新: {count} 筆商品"
