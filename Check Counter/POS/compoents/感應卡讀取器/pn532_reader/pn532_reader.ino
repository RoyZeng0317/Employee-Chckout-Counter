// ------------------------------------------------------------------
// PN532 NFC 讀卡機韌體 — 給員工登入 / 商品感應 / 出口防盜 / 顧客儲值付款共用
// ------------------------------------------------------------------
// 這是「通用韌體」:感應到的 UID 代表什麼(登入卡、商品標籤、顧客儲值卡...)
// 完全由電腦端(Employee.cs 或 camera_auto_checkout.py)當下在監聽哪個 COM
// Port、處於什麼模式來決定,韌體本身不需要知道用途。同一份程式可以重複燒錄
// 到每一台讀卡機。
//
// 接線(I2C 模式,PN532 模組上的撥動開關/跳線切到 I2C):
//   PN532 VCC -> Arduino 5V(ESP32 請用 3V3)
//   PN532 GND -> Arduino/ESP32 GND
//   PN532 SDA -> Arduino Uno A4 / ESP32 GPIO21(依板子 I2C 預設腳位而定)
//   PN532 SCL -> Arduino Uno A5 / ESP32 GPIO22(依板子 I2C 預設腳位而定)
//
// 需要安裝的函式庫(Arduino IDE:工具 -> 管理程式庫,搜尋並安裝):
//   Adafruit PN532
//   Adafruit BusIO(Adafruit PN532 的相依套件,通常會一起裝)
//
// 燒錄後怎麼確認:開「工具 -> 序列埠監控視窗」,鮑率設定 9600,把卡片靠近
// 感應區,應該會看到印出一行大寫十六進位的 UID(例如 04A3B2C1)。同一張卡
// 持續放在感應區上,1.5 秒內只會印一次;拿開再放上會重新觸發。
// ------------------------------------------------------------------

#include <Wire.h>
#include <Adafruit_PN532.h>

#define PN532_IRQ   (2)
#define PN532_RESET (3)

Adafruit_PN532 nfc(PN532_IRQ, PN532_RESET);

const unsigned long READ_COOLDOWN_MS = 1500;  // 呼應電腦端 SCAN_COOLDOWN_SEC
String lastUid = "";
unsigned long lastReadMillis = 0;

void setup() {
  Serial.begin(9600);
  nfc.begin();

  uint32_t versiondata = nfc.getFirmwareVersion();
  if (!versiondata) {
    Serial.println("[錯誤] 找不到 PN532,請檢查接線");
    while (1) { delay(1000); }
  }
  nfc.SAMConfig();
}

String uidToHex(uint8_t *uid, uint8_t uidLength) {
  String hex = "";
  for (uint8_t i = 0; i < uidLength; i++) {
    if (uid[i] < 0x10) hex += "0";
    hex += String(uid[i], HEX);
  }
  hex.toUpperCase();
  return hex;
}

void loop() {
  uint8_t uid[7];
  uint8_t uidLength;

  bool success = nfc.readPassiveTargetID(PN532_MIFARE_ISO14443A, uid, &uidLength, 100);
  if (!success) {
    return;
  }

  String uidHex = uidToHex(uid, uidLength);
  unsigned long now = millis();

  if (uidHex == lastUid && (now - lastReadMillis) < READ_COOLDOWN_MS) {
    return;
  }

  lastUid = uidHex;
  lastReadMillis = now;
  Serial.println(uidHex);
}
