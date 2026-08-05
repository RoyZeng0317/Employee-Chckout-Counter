CREATE TABLE IF NOT EXISTS manager (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  users_name VARCHAR(255),
  users_id INT,
  users_password VARCHAR(255),
  nfc_uid VARCHAR(64)
);

-- users_password 存的是 hash 值，格式為「鹽值(hex)$雜湊值(hex)」，由 hashlib.pbkdf2_hmac('sha256', ...) 產生，不是明文密碼
INSERT INTO manager(users_id, users_name, users_password, nfc_uid) VALUES
(624826, '曾少', '1453867b98245eaf549436cd515b16ba$de30be6c7997cd478308a54f8ed5d2355c8a10728138996b4a6c04cfa7b072c2', '');