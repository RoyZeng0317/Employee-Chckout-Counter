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
# 6. 如果有接 NFC 讀卡機(Arduino/ESP32 + PN532,韌體在 ../感應卡讀取器/),
#    加上 --nfc-port 指定序列埠(例如 COM4),感應到的卡片 UID 會比照條碼處理
#    (商品的 NFC 標籤要把 products.sql 的 barcode 欄位設成該標籤的 UID):
#      python camera_auto_checkout.py --mode checkout --nfc-port COM4
#    留空(預設)就不啟用 NFC,沒接讀卡機一樣能正常用鏡頭掃條碼。
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
import sqlite3
from pyzbar.pyzbar import decode as decode_barcodes

try:
    import winsound
except ImportError:
    winsound = None

try:
    import serial  # pyserial,選用:沒裝也能跑,只是不能用 NFC 讀卡機
except ImportError:
    serial = None

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SALES_LOG_DIR = os.path.join(BASE_DIR, "logs")
PAID_LOG_PATH = os.path.join(BASE_DIR, "paid_log.json")
ALERT_LOG_PATH = os.path.join(BASE_DIR, "alerts.csv")
DB_PATH = os.path.normpath(os.path.join(BASE_DIR, "..", "backend", "data", "products.db"))

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


def split_value_rows(body: str) -> list[str]:
    """把 VALUES 之後的 (...),(...),...,(...) 依最外層括號切成每一列的內容,
    引號內的括號與逗號不列入計算(避免商品名稱裡有括號時被誤判)。"""
    rows = []
    depth = 0
    in_quote = False
    current = []
    for i, ch in enumerate(body):
        if ch == "'" and (i == 0 or body[i - 1] != "\\"):
            in_quote = not in_quote
        if not in_quote:
            if ch == "(":
                if depth == 0:
                    current = []
                else:
                    current.append(ch)
                depth += 1
                continue
            if ch == ")":
                depth -= 1
                if depth == 0:
                    rows.append("".join(current))
                    continue
        if depth > 0:
            current.append(ch)
    return rows


def load_products_from_sql_file(path: str) -> dict:
    """比照 C# Employee.cs 的 LoadProductsFromSql,直接解析 products.sql 的 INSERT 語句,
    離線(不需要啟動 MySQL)也能載入商品清單。products.sql 用單一 INSERT INTO ... VALUES
    後面接多列 (...) 的精簡格式,所以整段一起解析,而不是逐行解析
    (同時相容單行一筆 INSERT 的舊格式)。"""
    products: dict[str, Any] = {}
    with open(path, "r", encoding="utf-8-sig") as f:
        text = f.read()

    upper = text.upper()
    search_pos = 0
    while True:
        insert_start = upper.find("INSERT INTO", search_pos)
        if insert_start < 0:
            break
        values_start = upper.find("VALUES", insert_start)
        if values_start < 0:
            break
        stmt_end = text.find(";", values_start)
        if stmt_end < 0:
            stmt_end = len(text)

        body = text[values_start + len("VALUES"):stmt_end]
        for row in split_value_rows(body):
            vals = parse_sql_values(row)
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

        search_pos = stmt_end + 1
    return products


def load_products() -> dict:
    """商品清單從 products.db (SQLite) 載入"""
    if not os.path.exists(DB_PATH):
        print(f"[錯誤] 找不到 SQLite 資料庫: {DB_PATH}")
        sys.exit(1)
    try:
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute("SELECT barcode, product_name, price, stock, shelves FROM products")
        rows = cur.fetchall()
        conn.close()
        products = {}
        for barcode, name, price, stock, shelves in rows:
            products[str(barcode).strip()] = {
                "barcode": barcode,
                "product_name": name,
                "price": price,
                "stock": stock,
                "shelves": shelves,
            }
        return products
    except sqlite3.Error as e:
        print(f"[錯誤] 讀取 SQLite 資料庫失敗: {e}")
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

    # 解析度太低會讓條碼的線寬不足,pyzbar 掃不到,盡量拉高擷取解析度
    # (手機 IP Webcam 串流的解析度由手機端 App 設定決定,這裡的 set() 對它不會有效果,
    #  要拉遠掃描距離請直接到 App 的視訊設定裡調高解析度)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

    actual_w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    actual_h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"[攝影機] 要求解析度 1920x1080,實際取得 {actual_w}x{actual_h}"
          f"(如果遠小於要求值,代表這台攝影機/串流本身就不支援更高解析度,是掃描距離短的主因之一)")
    return cap


def rescale_barcode(code, scale: float):
    """把在放大後畫面上偵測到的座標換算回原始畫面座標,讓框線畫在正確位置"""
    rect = code.rect._replace(
        left=int(code.rect.left / scale),
        top=int(code.rect.top / scale),
        width=int(code.rect.width / scale),
        height=int(code.rect.height / scale),
    )
    polygon = [p._replace(x=int(p.x / scale), y=int(p.y / scale)) for p in code.polygon]
    return code._replace(rect=rect, polygon=polygon)


def scan_barcodes(gray, clahe):
    """三段式掃描:先用原始灰階畫面掃一次;掃不到就用 CLAHE 增強對比重試(改善光線不足、
    對比度太低的情況);還是掃不到就把畫面數位放大 2 倍再試一次(改善條碼距離較遠、
    畫面裡偏小時掃不到的情況,不需要真的把鏡頭貼近條碼)。"""
    codes = decode_barcodes(gray)
    if codes:
        return codes

    enhanced = clahe.apply(gray)
    codes = decode_barcodes(enhanced)
    if codes:
        return codes

    scale = 2.0
    zoomed = cv2.resize(enhanced, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    return [rescale_barcode(code, scale) for code in decode_barcodes(zoomed)]


def open_nfc_reader(port: str, baud: int):
    """開啟 NFC 讀卡機(Arduino/ESP32 + PN532)的序列埠,開不起來/沒裝 pyserial
    只印警告訊息並回傳 None,不讓整支程式因為沒接讀卡機就掛掉。"""
    if not port:
        return None
    if serial is None:
        print("[NFC] 尚未安裝 pyserial,略過 NFC 讀卡機(pip install pyserial)")
        return None
    try:
        ser = serial.Serial(port, baud, timeout=0)
        print(f"[NFC] 已開啟讀卡機 {port} ({baud} baud)")
        return ser
    except Exception as e:
        print(f"[NFC] 無法開啟讀卡機 {port}: {e}")
        return None


def poll_nfc(ser):
    """non-blocking 讀取讀卡機送來的一行 UID,沒有新資料就回傳 None"""
    if ser is None:
        return None
    try:
        if ser.in_waiting == 0:
            return None
        line = ser.readline().decode("utf-8", errors="ignore").strip()
    except Exception:
        return None
    return line or None


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


def handle_checkout_code(code_str, products, cart, csv_path, last_seen, now):
    """處理一次讀到的商品識別碼——不管是攝影機掃到的條碼,還是 NFC 標籤的 UID,
    做法完全一樣(NFC 標籤代表哪個商品,是把該商品 products.sql 的 barcode 欄位
    直接設成標籤的 UID)。冷卻時間內的重複讀取回傳 None,呼叫端應略過不處理。"""
    if not code_str or now - last_seen.get(code_str, 0) < SCAN_COOLDOWN_SEC:
        return None
    last_seen[code_str] = now

    product = products.get(code_str)
    if product is None:
        return f"查無商品: {code_str}", (0, 0, 255), False

    name, price = product["product_name"], product_price(product)
    item = cart.setdefault(code_str, {"product_name": name, "price": price, "qty": 0})
    item["qty"] += 1

    append_csv(
        csv_path,
        ["日期", "時間", "條碼", "商品名稱", "價格"],
        [datetime.now().strftime("%Y/%m/%d"), datetime.now().strftime("%H:%M:%S"), code_str, name, price],
    )
    append_paid_record(code_str, name, price)

    return f"已加入: {name}  ${price}", (0, 200, 0), True


def handle_exit_code(code_str, products, available, consumed, last_seen, now):
    """出口站處理一次讀到的識別碼(條碼或 NFC UID),邏輯同 handle_checkout_code
    共用冷卻機制。回傳 (message, color, beep_ok);冷卻時間內重複讀到回傳 None。"""
    if not code_str or now - last_seen.get(code_str, 0) < SCAN_COOLDOWN_SEC:
        return None
    last_seen[code_str] = now

    product = products.get(code_str)
    name = product["product_name"] if product else "未知商品"

    if available.get(code_str, 0) > 0:
        available[code_str] -= 1
        consumed[code_str] += 1
        message, color, status, ok = f"通過: {name}", (0, 200, 0), "PASS", True
    else:
        message, color, status, ok = f"警示! 未結帳: {name} ({code_str})", (0, 0, 255), "ALERT", False
        print(f"[警示] {datetime.now().strftime('%H:%M:%S')} 疑似未結帳商品通過: {code_str} {name}")

    append_csv(
        ALERT_LOG_PATH,
        ["日期", "時間", "條碼", "商品名稱", "狀態"],
        [datetime.now().strftime("%Y/%m/%d"), datetime.now().strftime("%H:%M:%S"), code_str, name, status],
    )
    return message, color, ok


def run_checkout(cap, products, nfc_ser=None):
    os.makedirs(SALES_LOG_DIR, exist_ok=True)
    csv_path = os.path.join(SALES_LOG_DIR, "sales_" + datetime.now().strftime("%Y%m%d") + ".csv")

    cart = {}  # barcode -> {"product_name", "price", "qty"}
    last_seen = {}
    message, message_color, message_until = "", (255, 255, 255), 0.0
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

    print("[結帳模式] Q=離開  C=完成本筆結帳(清空清單)  R=重新載入商品")

    while True:
        ok, frame = cap.read()
        if not ok:
            print("[錯誤] 讀不到影像,攝影機可能已斷線")
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        now = time.time()

        for code in scan_barcodes(gray, clahe):
            draw_barcode_box(frame, code)
            barcode = code.data.decode("utf-8", errors="ignore").strip()
            result = handle_checkout_code(barcode, products, cart, csv_path, last_seen, now)
            if result is None:
                continue
            message, message_color, ok = result
            message_until = now + 2
            beep(ok)

        nfc_uid = poll_nfc(nfc_ser)
        if nfc_uid:
            result = handle_checkout_code(nfc_uid, products, cart, csv_path, last_seen, now)
            if result is not None:
                message, message_color, ok = result
                message_until = now + 2
                beep(ok)

        total = sum(i["price"] * i["qty"] for i in cart.values())
        count = sum(i["qty"] for i in cart.values())
        hud = [f"結帳模式  商品數:{count}  總金額: ${total}"]
        show_msg = now < message_until
        if show_msg:
            hud.append(message)
        draw_hud(frame, hud, message_color if show_msg else (255, 255, 255))

        cv2.imshow("鏡頭POS機", frame)
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


def run_exit_guard(cap, products, nfc_ser=None):
    consumed = Counter()  # 這次執行已核銷過的條碼次數
    last_seen = {}
    last_reload = 0.0
    paid_records = []
    message, message_color, message_until = "", (255, 255, 255), 0.0
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))

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
        for code in scan_barcodes(gray, clahe):
            draw_barcode_box(frame, code)
            barcode = code.data.decode("utf-8", errors="ignore").strip()
            result = handle_exit_code(barcode, products, available, consumed, last_seen, now)
            if result is None:
                continue
            message, message_color, ok = result
            beep(ok)
            message_until = now + 3

        nfc_uid = poll_nfc(nfc_ser)
        if nfc_uid:
            result = handle_exit_code(nfc_uid, products, available, consumed, last_seen, now)
            if result is not None:
                message, message_color, ok = result
                beep(ok)
                message_until = now + 3

        hud = ["出口防盜模式"]
        show_msg = now < message_until
        if show_msg:
            hud.append(message)
        draw_hud(frame, hud, message_color if show_msg else (255, 255, 255))

        cv2.imshow("鏡頭POS機", frame)
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
    parser.add_argument("--nfc-port", default="",
                         help='NFC 讀卡機(Arduino/ESP32 + PN532)的序列埠,例如 "COM4";留空則不啟用 NFC')
    parser.add_argument("--nfc-baud", type=int, default=9600,
                         help="NFC 讀卡機序列埠的鮑率,預設 9600")
    args = parser.parse_args()

    products = load_products()
    print(f"[已載入商品] 共 {len(products)} 筆 (來源: {DB_PATH})")

    nfc_ser = open_nfc_reader(args.nfc_port, args.nfc_baud)

    cap = open_camera(args.camera)
    try:
        if args.mode == "checkout":
            run_checkout(cap, products, nfc_ser)
        else:
            run_exit_guard(cap, products, nfc_ser)
    finally:
        cap.release()
        cv2.destroyAllWindows()
        if nfc_ser is not None:
            nfc_ser.close()

if __name__ == "__main__":
    main()
