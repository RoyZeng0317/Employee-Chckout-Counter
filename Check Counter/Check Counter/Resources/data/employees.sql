CREATE TABLE IF NOT EXISTS employees(
    id INT AUTO_INCREMENT PRIMARY KEY,
    users_name VARCHAR(255),
    users_id INT,
    users_password VARCHAR(255),
    nfc_uid VARCHAR(64)
);

INSERT INTO employees(users_id, users_name, users_password, nfc_uid) VALUES(624826, '曾少', '624826', '');
INSERT INTO employees(users_id, users_name, users_password, nfc_uid) VALUES(100002, '陳小花', '7577157', '');
INSERT INTO employees(users_id, users_name, users_password, nfc_uid) VALUES(100003, '李大華', '9544154', '');
INSERT INTO employees(users_id, users_name, users_password, nfc_uid) VALUES(147526, '王大明', '7575135', '');
INSERT INTO employees(users_id, users_name, users_password, nfc_uid) VALUES(286876, '胡二狗', '6954238', '');
INSERT INTO employees(users_id, users_name, users_password, nfc_uid) VALUES(973145, '劉一一', '1945867', '');