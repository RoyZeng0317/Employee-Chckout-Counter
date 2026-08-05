# AGENTS.md

## Project Overview

Retail employee checkout counter system (POS). Two parallel implementations:
- **C# WinForms** (.NET Framework 4.7.2) — main POS terminal with MySQL backend
- **Python tkinter** — alternative POS, camera barcode scanner, NFC reader

## Directory Structure

```
Check Counter/
├── Check Counter/          # C# WinForms app (entry: Program.cs → Employee form)
├── main/                   # Python POS modules (entry: main.py)
├── 鏡頭結帳/               # Camera barcode scanner (camera_auto_checkout.py)
├── 感應卡讀取器/            # NFC reader firmware (Arduino/ESP32 PN532)
├── POS/backend/data/       # SQLite DB files (products.db + .sql schemas)
├── Install/                # MSI installer + PowerShell install script
├── Resources/data/         # MySQL SQL schemas (for C# app)
├── Linux/                  # Empty
└── main/                   # Python POS modules
AI_Reader/                  # Documentation logs (CLAUDE.md rules apply here)
```

## Database

**Two separate database systems — not synchronized:**

| System | Used by | Engine | Location |
|--------|---------|--------|----------|
| SQLite | Python POS (`main/*.py`) | `sqlite3` (stdlib) | `POS/backend/data/products.db` |
| MySQL | C# app + camera scanner | `MySql.Data` / `pymysql` | `localhost:3306`, db: `checkout` |

**SQLite** auto-creates on first run of `main.py` — no setup needed.

**MySQL** requires manual setup:
- Server: `localhost:3306`, database: `checkout`, user: `root`, no password (default)
- Connection config: `Check Counter/App.config` (C#) and env vars `DB_HOST/DB_PORT/DB_USER/DB_PASSWORD/DB_NAME` (Python)
- `.env` file at `POS/backend/.env` is empty; camera module reads env vars as fallback

**SQL schema files have TWO versions:**
- `POS/backend/data/*.sql` — SQLite syntax (`AUTOINCREMENT`), hashed passwords (PBKDF2)
- `Check Counter/Resources/data/*.sql` — MySQL syntax (`AUTO_INCREMENT`), plaintext passwords (security concern)

## Running

### Python POS (tkinter)
```bash
cd "Check Counter/main"
python main.py              # Employee login + checkout
python manager.py           # Manager login + product management
python Products_Edit.py     # Product CRUD editor
python Employee_change_pwd.py
python Manager_change_pwd.py
```
No pip install needed — only uses stdlib (`sqlite3`, `tkinter`, `hashlib`).

### Camera Barcode Scanner
```bash
cd "Check Counter/鏡頭結帳"
pip install -r requirements.txt   # opencv-python, pyzbar, pymysql, numpy, pyserial
python camera_auto_checkout.py --mode checkout --camera 0
python camera_auto_checkout.py --mode exit --camera http://<phone-ip>:8080/video
```
Requires MySQL running OR readable `products.sql` file (offline fallback).

### C# WinForms
Open `Check Counter.slnx` in Visual Studio. Requires:
- .NET Framework 4.7.2
- MySQL server running (same config as above)
- NuGet packages already in `packages/` folder

## Conventions

- **Chinese variable/function names** are used throughout Python code (e.g., `掃描條碼`, `購物車`). Do not rename to English.
- **Password hashing**: PBKDF2-SHA256, 100k iterations, format: `salt_hex$hash_hex`
- **No tests, no linter, no CI** for Python code
- **No README** exists
- `AI_Reader/CLAUDE.md` governs the `AI_Reader/` folder — follow its logging rules when editing there

## Gotchas

- `Check Counter/main/` is the Python POS entry dir, NOT `Check Counter/POS/`
- The camera scanner loads products from `products.sql` file first (offline), falls back to MySQL only if file unreadable
- NFC reader is optional — code gracefully degrades without it (`pyserial` import guarded)
- Two `.venv` directories exist (`.venv` and `.venv-1`) — which one is active is unclear
- `check_counter_list.py` is an early prototype using hardcoded product lists — not used in production
