# 需求: 可以用 windows phone 連線手機鏡頭
# 鏡頭可以直接經過條碼後可以掃描結帳
# 當出了門口可以避免沒有消費到的問題
#
# ------------------------------------------------------------------
# 使用說明
# ------------------------------------------------------------------
# 1. 手機(S24 Ultra)安裝「IP Webcam」App(Google Play 免費),與電腦連上同一個 Wi-Fi,
#    App 內按「開始伺服器」後畫面會顯示一個網址,例如 http://192.168.1.23:8080
#    影像串流網址請用該網址加上 /video,例如 http://192.168.1.23:8080/video
#
# 2. 安裝套件: pip install -r requirements.txt
#
# 3. 櫃檯結帳站:掃到條碼會自動加入購物清單並累計金額
#      python camera_auto_checkout.py --mode checkout --camera http://192.168.1.23:8080/video
#
# 4. 出口防盜站:掃到條碼會比對「是否為近期已結帳的商品」,
#    沒結帳過的商品通過鏡頭會顯示紅色警示並發出警報聲
#      python camera_auto_checkout.py --mode exit --camera http://192.168.1.24:8080/video
#
# 5. 手機還沒設定好之前,可以先用電腦內建鏡頭測試(--camera 預設就是 0):
#      python camera_auto_checkout.py --mode checkout
#
# 快捷鍵: C = 完成本筆結帳(清空目前購物清單) | R = 重新載入商品資料庫 | Q = 離開
#
# 資料庫連線預設值沿用 App.config(Server=localhost;Port=3306;Database=checkout;User=root),
# 也可用環境變數 DB_HOST / DB_PORT / DB_USER / DB_PASSWORD / DB_NAME 覆蓋。
#
# 已知限制(v1):沒有做物件追蹤,同一件商品若在出口鏡頭前反覆進出畫面,
# 有可能被誤判成多筆分開的商品通過;之後有需要再加防重複判斷。
# ------------------------------------------------------------------

import argparse
import csv
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime
from typing import Any

import cv2
import numpy as np
import pymysql
from pyzbar.pyzbar import decode as decode_barcodes

try:
    import winsound
except ImportError:
    winsound = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SALES_LOG_DIR = os.path.join(BASE_DIR, "logs")
PAID_LOG_PATH = os.path.join(BASE_DIR, "paid_log.json")
ALERT_LOG_PATH = os.path.join(BASE_DIR, "alerts.csv")
PRODUCTS_SQL_PATH = os.path.join(BASE_DIR, "..", "Check Counter", "Resources", "data", "products.sql")

DB_CONFIG: dict[str, Any] = dict(
    host=os.environ.get("DB_HOST", "localhost"),
    port=int(os.environ.get("DB_PORT", "3306")),
    user=os.environ.get("DB_USER", "root"),
    password=os.environ.get("DB_PASSWORD", ""),
    database=os.environ.get("DB_NAME", "checkout"),
    charset="utf8mb4",
    cursorclass=pymysql.cursors.DictCursor,
)

SCAN_COOLDOWN_SEC = 1.5  # 同一條碼在這段時間內不會被重複加入
PAID_TTL_SEC = 30 * 60  # 出口站認定「已結帳」的有效時間(30 分鐘)


def parse_sql_values(values_part: str) -> list[str]:
    """對應 C# Employee.cs 的 ParseSqlValues:依逗號切開 VALUES(...) 內容,忽略引號內的逗號與引號本身"""
    result = []
    current = []
    in_quote = False
    for i, ch in enumerate(values_part):
        if ch == "'" and (i == 0 or values_part[i - 1] != "\\"):
            in_quote = not in_quote
        elif ch == "," and not in_quote:
            result.append("".join(current).strip())
            current = []
        else:
            current.append(ch)
    if current:
        result.append("".join(current).strip())
    return result


def load_products_from_sql_file(path: str) -> dict:
    """比照 C# Employee.cs 的 LoadProductsFromSql,直接解析 products.sql 的 INSERT 語句,
    離線(不需要啟動 MySQL)也能載入商品清單。"""
    products: dict[str, Any] = {}
    with open(path, "r", encoding="utf-8-sig") as f:
        for line in f:
            trimmed = line.lstrip()
            upper = trimmed.upper()
            if not upper.startswith("INSERT INTO"):
                continue
            start = upper.find("VALUES (")
            if start < 0:
                continue
            start += len("VALUES (")
            end = trimmed.rfind(");")
            if end < 0:
                continue

            vals = parse_sql_values(trimmed[start:end])
            if len(vals) < 5:
                continue

            barcode = vals[0].strip()
            name = vals[1]
            try:
                price = int(vals[2])
            except ValueError:
                price = 0
            try:
                stock = int(vals[3])
            except ValueError:
                stock = 0
            shelves = vals[4]
            products[barcode] = {
                "barcode": barcode,
                "product_name": name,
                "price": price,
                "stock": stock,
                "shelves": shelves,
            }
    return products


def load_products() -> dict:
    """商品清單載入順序比照 C# Employee.cs:優先直接解析 products.sql(離線可用),
    檔案讀不到或沒有資料時才改連線 MySQL。"""
    try:
        products = load_products_from_sql_file(PRODUCTS_SQL_PATH)
        if products:
            return products
    except OSError:
        pass

    try:
        with pymysql.connect(**DB_CONFIG) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT barcode, product_name, price, stock, shelves FROM products")
                rows = cur.fetchall()
        return {str(row["barcode"]).strip(): row for row in rows}
    except pymysql.MySQLError as e:
        print(f"[錯誤] products.sql 讀取失敗,且無法連線 MySQL"
              f"({DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}): {e}")
        print(f"請確認 {PRODUCTS_SQL_PATH} 存在,或資料庫已啟動"
              "(可用環境變數 DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME 覆蓋)。")
        sys.exit(1)


def product_price(product: dict) -> int:
    try:
        return int(product["price"])
    except (TypeError, ValueError):
        return 0


def open_camera(source: str) -> cv2.VideoCapture:
    """開啟攝影機來源,source 可以是本機攝影機編號(如 "0")或手機 IP Webcam 的串流網址"""
    try:
        cap = cv2.VideoCapture(int(source), cv2.CAP_DSHOW)
    except ValueError:
        cap = cv2.VideoCapture(source)

    if not cap.isOpened():
        raise RuntimeError(
            f"無法連接攝影機來源:{source}\n"
            "手機端請安裝「IP Webcam」App 並啟動伺服器,\n"
            "再將 --camera 設定為 http://<手機IP>:8080/video"
        )
    return cap


def beep(ok: bool):
    if winsound is None:
        return
    try:
        winsound.Beep(1000, 120) if ok else winsound.Beep(600, 400)
    except RuntimeError:
        pass


def append_csv(path: str, header: list, row: list):
    is_new = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(header)
        writer.writerow(row)


def append_paid_record(barcode: str, product_name: str, price: int):
    """記錄「這件商品剛剛結帳了」,供出口防盜站比對用"""
    records = load_paid_records(apply_ttl=False)
    records.append({"barcode": barcode, "product_name": product_name, "price": price, "ts": time.time()})
    cutoff = time.time() - PAID_TTL_SEC
    records = [r for r in records if r["ts"] >= cutoff]
    with open(PAID_LOG_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)


def load_paid_records(apply_ttl: bool = True) -> list:
    if not os.path.exists(PAID_LOG_PATH):
        return []
    try:
        with open(PAID_LOG_PATH, "r", encoding="utf-8") as f:
            records = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []
    if not apply_ttl:
        return records
    cutoff = time.time() - PAID_TTL_SEC
    return [r for r in records if r["ts"] >= cutoff]


def draw_hud(frame, lines, color=(255, 255, 255)):
    y = 30
    for line in lines:
        cv2.putText(frame, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(frame, line, (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 1, cv2.LINE_AA)
        y += 28


def draw_barcode_box(frame, code):
    pts = code.polygon
    if not pts:
        return
    poly = np.array([(p.x, p.y) for p in pts], dtype=np.int32)
    cv2.polylines(frame, [poly], True, (0, 255, 255), 2)


def run_checkout(cap, products):
    os.makedirs(SALES_LOG_DIR, exist_ok=True)
    csv_path = os.path.join(SALES_LOG_DIR, "sales_" + datetime.now().strftime("%Y%m%d") + ".csv")

    cart = {}  # barcode -> {"product_name", "price", "qty"}
    last_seen = {}
    message, message_color, message_until = "", (255, 255, 255), 0.0

    print("[結帳模式] Q=離開  C=完成本筆結帳(清空清單)  R=重新載入商品")

    while True:
        ok, frame = cap.read()
        if not ok:
            print("[錯誤] 讀不到影像,攝影機可能已斷線")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        now = time.time()

        for code in decode_barcodes(gray):
            draw_barcode_box(frame, code)
            barcode = code.data.decode("utf-8", errors="ignore").strip()
            if not barcode or now - last_seen.get(barcode, 0) < SCAN_COOLDOWN_SEC:
                continue
            last_seen[barcode] = now

            product = products.get(barcode)
            if product is None:
                message, message_color = f"查無商品: {barcode}", (0, 0, 255)
                message_until = now + 2
                beep(False)
                continue

            name, price = product["product_name"], product_price(product)
            item = cart.setdefault(barcode, {"product_name": name, "price": price, "qty": 0})
            item["qty"] += 1

            append_csv(
                csv_path,
                ["日期", "時間", "條碼", "商品名稱", "價格"],
                [datetime.now().strftime("%Y/%m/%d"), datetime.now().strftime("%H:%M:%S"), barcode, name, price],
            )
            append_paid_record(barcode, name, price)

            message, message_color = f"已加入: {name}  ${price}", (0, 200, 0)
            message_until = now + 2
            beep(True)

        total = sum(i["price"] * i["qty"] for i in cart.values())
        count = sum(i["qty"] for i in cart.values())
        hud = [f"結帳模式  商品數:{count}  總金額: ${total}"]
        show_msg = now < message_until
        if show_msg:
            hud.append(message)
        draw_hud(frame, hud, message_color if show_msg else (255, 255, 255))

        cv2.imshow("Vaultix 結帳鏡頭", frame)
        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), ord("Q")):
            break
        elif key in (ord("c"), ord("C")):
            if cart:
                print(f"[結帳完成] 共 {count} 件, 總金額 ${total}")
            cart.clear()
            last_seen.clear()
        elif key in (ord("r"), ord("R")):
            products.clear()
            products.update(load_products())
            print(f"[已重新載入商品] 共 {len(products)} 筆")


def run_exit_guard(cap, products):
    consumed = Counter()  # 這次執行已核銷過的條碼次數
    last_seen = {}
    last_reload = 0.0
    paid_records = []
    message, message_color, message_until = "", (255, 255, 255), 0.0

    print("[出口防盜模式] Q=離開  R=重新載入商品")

    while True:
        ok, frame = cap.read()
        if not ok:
            print("[錯誤] 讀不到影像,攝影機可能已斷線")
            break

        now = time.time()
        if now - last_reload > 2:
            paid_records = load_paid_records()
            last_reload = now

        available = Counter(r["barcode"] for r in paid_records)
        available.subtract(consumed)

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        for code in decode_barcodes(gray):
            draw_barcode_box(frame, code)
            barcode = code.data.decode("utf-8", errors="ignore").strip()
            if not barcode or now - last_seen.get(barcode, 0) < SCAN_COOLDOWN_SEC:
                continue
            last_seen[barcode] = now

            product = products.get(barcode)
            name = product["product_name"] if product else "未知商品"

            if available.get(barcode, 0) > 0:
                available[barcode] -= 1
                consumed[barcode] += 1
                message, message_color, status = f"通過: {name}", (0, 200, 0), "PASS"
                beep(True)
            else:
                message, message_color, status = f"警示! 未結帳: {name} ({barcode})", (0, 0, 255), "ALERT"
                beep(False)
                print(f"[警示] {datetime.now().strftime('%H:%M:%S')} 疑似未結帳商品通過: {barcode} {name}")

            append_csv(
                ALERT_LOG_PATH,
                ["日期", "時間", "條碼", "商品名稱", "狀態"],
                [datetime.now().strftime("%Y/%m/%d"), datetime.now().strftime("%H:%M:%S"), barcode, name, status],
            )
            message_until = now + 3

        hud = ["出口防盜模式"]
        show_msg = now < message_until
        if show_msg:
            hud.append(message)
        draw_hud(frame, hud, message_color if show_msg else (255, 255, 255))

        cv2.imshow("Vaultix 出口防盜鏡頭", frame)
        key = cv2.waitKey(1) & 0xFF
        if key in (ord("q"), ord("Q")):
            break
        elif key in (ord("r"), ord("R")):
            products.clear()
            products.update(load_products())
            print(f"[已重新載入商品] 共 {len(products)} 筆")


def main():
    parser = argparse.ArgumentParser(description="S24 Ultra 鏡頭條碼結帳 / 出口防盜偵測")
    parser.add_argument("--mode", choices=["checkout", "exit"], default="checkout",
                         help="checkout=櫃檯結帳站, exit=出口防盜站")
    parser.add_argument("--camera", default="0",
                         help='本機攝影機編號(如 "0")或手機 IP Webcam 串流網址(如 http://192.168.1.23:8080/video)')
    args = parser.parse_args()

    products = load_products()
    print(f"[已載入商品] 共 {len(products)} 筆 (來源: {DB_CONFIG['database']}.products)")

    cap = open_camera(args.camera)
    try:
        if args.mode == "checkout":
            run_checkout(cap, products)
        else:
            run_exit_guard(cap, products)
    finally:
        cap.release()
        cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
