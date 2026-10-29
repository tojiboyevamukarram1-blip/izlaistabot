# 🚀 Telegram Media Downloader Bot (Instagram, YouTube, Pinterest)

Ishlab chiqarishga tayyor (production-ready), yuqori tezlikda ishlovchi va xavfsiz Telegram media yuklovchi bot.
Ushbu bot **Instagram** (Reels, postlar, karusellar), **YouTube** (Shorts, oddiy videolar, MP3 audio) hamda **Pinterest** (rasm va videolar) platformalaridan media fayllarni to'liq O'zbek tilidagi interfeys orqali yuklab beradi.

---

## 🌟 Asosiy imkoniyatlar (Key Features)

- **Instagram:**
  - Reels va oddiy video postlarni eng yuqori sifatda yuklash.
  - Karusel (bir nechta rasm va video bitta postda) postlarni aniqlab, barchasini to'plam (media album) sifatida yuborish.
- **YouTube:**
  - Faqatgina haqiqatda mavjud bo'lgan sifatlarni (144p, 240p, 360p, 480p, 720p, 1080p, 1440p, 2160p/4K) inline tugmalar orqali taklif qilish.
  - Video hajmini audio oqimi bilan birga aniq hisoblab ko'rsatish (`~18.5 MB`).
  - MP3 audio formatiga o'tkazish (192 kbps, avtomatik ID3 taglar).
  - Asl (original) audio oqimini alohida yuklash.
  - Telegram mosligi uchun FFmpeg orqali avtomatik ravishda `+faststart` remukslashtirish (video Telegramda kutmasdan darhol ijro etiladi).
- **Pinterest:**
  - Rasmlarni asl (original/siqilmagan) sifatda yuklash (Telegram rasmi yoki fayl/hujjat sifatida tanlash imkoni).
  - Pinterest videolarini avtomatik aniqlab yuklash.
  - Qisqa `pin.it` havolalarini xavfsiz kengaytirib ishlash.
- **Tezlik va Unumdorlik:**
  - **Redis kesh:** Oldin yuklangan videoning Telegram `file_id` qiymati keshlanadi. Ikkinchi marta o'sha havola so'ralganda serverga qayta yuklanmasdan **1 soniyada** foydalanuvchiga yuboriladi!
  - **Asinxron arxitektura:** aiogram 3.x, aiohttp va yt-dlp izolyatsiyalangan oqimlarda ishlaydi; event-loop hech qachon bloklanmaydi.
  - **Chegaralangan oqimlar (Bounded Concurrency):** Server resurslarini asrash uchun maksimal bir vaqtning o'zida yuklash chegarasi (`MAX_CONCURRENT_DOWNLOADS`).
  - **Kesh zaxirasi:** Redis ulanmagan bo'lsa ham bot to'xtab qolmaydi, avtomatik ravishda xotiradagi (In-Memory) keshga o'tadi.
- **Xavfsizlik va Ishonchlilik:**
  - **SSRF himoyasi:** Lokal tarmoq (localhost, 127.0.0.1, 10.0.0.0/8, 192.168.0.0/16, AWS metadata 169.254.169.254) manzillariga so'rov yuborish qat'iy bloklangan.
  - **Anti-flood / Rate Limiting:** Har bir foydalanuvchi uchun so'rovlar chegarasi (sliding-window).
  - Fayl nomlarini tozalash (Path traversal `../` va taqiqlangan belgilardan himoya).
  - Fayl hajmi va video davomiyligi bo'yicha qat'iy cheklovlar.
  - Vaqtinchalik fayllarni jo'natilgandan so'ng darhol o'chirish (`finally:` bloki).

---

## 🛠 Texnologiyalar (Tech Stack)

- **Python 3.12+**
- **aiogram 3.x** — Zamonaviy asinxron Telegram Bot freymvorki
- **yt-dlp** — Eng so'nggi YouTube va Instagram ekstraktori
- **FFmpeg** — Audio konvertatsiya, video birlashtirish va thumbnail olish
- **aiohttp** — Asinxron HTTP so'rovlar va Pinterest integratsiyasi
- **Redis & In-Memory fallback** — Kesh va spamdan himoya
- **Docker & Docker Compose** — Bir buyruq bilan konteynerda ishga tushirish
- **pytest & pytest-asyncio** — Avtomatlashtirilgan testlar to'plami

---

## 📋 BotFather va Shaxsiy Rejim (OWNER_ID) sozlash

### 1. Bot tokenini olish:
1. Telegramda [@BotFather](https://t.me/BotFather) botiga kiring.
2. `/newbot` buyrug'ini yuboring.
3. Bot nomini kiriting (masalan: `Mening Media Botim`).
4. Bot username'ini kiriting (masalan: `MyPrivateMediaBot`).
5. BotFather bergan **HTTP API Token**ni nusxalang.

### 2. O'zingizning Telegram Numeric User ID raqamingizni aniqlash:
Bot faqat shaxsan sizga xizmat qilishi va boshqa barcha begona foydalanuvchilarni rad etishi uchun raqamli ID'ingiz kerak bo'ladi:
1. Telegramda [@userinfobot](https://t.me/userinfobot) yoki [@chatIDrobot](https://t.me/chatIDrobot) botiga xohlagan xabar yuboring (yoki `/start` bosing).
2. Bot sizga `Id: 123456789` kabi raqamli identifikatoringizni chiqarib beradi.
3. Ushbu raqamni nusxalang va `.env` faylidagi `OWNER_ID=` qatoriga yozing.

---

## 💻 Mahalliy (Local) o'rnatish va ishga tushirish

### 1. Talablar:
- Python 3.12+
- FFmpeg (tizimda o'rnatilgan bo'lishi kerak):
  - **Ubuntu / Debian:** `sudo apt update && sudo apt install ffmpeg`
  - **macOS:** `brew install ffmpeg`
  - **Windows:** [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) orqali yuklab, PATH'ga qo'shing.

### 2. Virtual muhit yaratish va kutubxonalarni o'rnatish:
```bash
# Repozitoriyga kiring
cd botinsta

# Virtual muhit yaratish
python -m venv .venv

# Virtual muhitni faollashtirish:
# Windows (PowerShell):
.\.venv\Scripts\Activate.ps1
# Linux / macOS:
source .venv/bin/activate

# Kutubxonalarni o'rnatish
pip install -r requirements.txt
```

### 3. Konfiguratsiya (.env):
`.env.example` faylidan nusxa olib `.env` yarating:
```bash
cp .env.example .env
```
`.env` faylini ochib, o'z Telegram bot tokeningizni kiriting:
```ini
BOT_TOKEN=7823456789:AAHxxxxxxxxxxxxxxxxxxxxxxxxx
OWNER_ID=123456789
REDIS_URL=redis://localhost:6379/0
MAX_FILE_SIZE_MB=50
MAX_DURATION_SECONDS=1800
```
*(Eslatma: Agar kompyuteringizda Redis o'rnatilmagan bo'lsa, bot avtomatik ravishda In-Memory xotira keshidan foydalanadi).*

### 4. Botni ishga tushirish:
```bash
python -m bot.main
```

---

## 🐳 Docker va Docker Compose orqali ishga tushirish (Tavsiya etiladi)

Docker orqali ishga tushirilganda Python, FFmpeg va Redis avtomatik sozlanadi.

```bash
# 1. .env fayliga bot tokeningizni yozing:
cp .env.example .env
nano .env

# 2. Docker konteynerlarni qurish va fonda ishga tushirish:
docker compose up -d --build

# 3. Loglarni real vaqtda kuzatish:
docker compose logs -f bot
```

To'xtatish uchun:
```bash
docker compose down
```

---

## ☁️ VPS (Ubuntu Server) da 24/7 ishlatish

### Variant A: Systemd servisi orqali (Docker ishlatilmasa)
1. `/etc/systemd/system/mediabot.service` faylini yarating:
```ini
[Unit]
Description=Telegram Media Downloader Bot
After=network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=/home/ubuntu/botinsta
ExecStart=/home/ubuntu/botinsta/.venv/bin/python -m bot.main
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```
2. Servisni faollashtiring:
```bash
sudo systemctl daemon-reload
sudo systemctl enable mediabot
sudo systemctl start mediabot
sudo systemctl status mediabot
```

### Variant B: Docker Compose orqali
VPS serverda shunchaki:
```bash
docker compose up -d
```

---

## 🧪 Avtomatlashtirilgan testlarni ishga tushirish

Loyiha URL tekshiruvi, SSRF bloklash, YouTube sifatlarini hisoblash, xavfsizlik va parallellik testlarini o'z ichiga oladi:

```bash
pytest -v
```

Natijalar:
```text
tests/test_auth.py .................. PASSED
tests/test_cache.py ................. PASSED
tests/test_callbacks.py ............. PASSED
tests/test_concurrency.py ........... PASSED
tests/test_platform_detector.py ..... PASSED
tests/test_security.py .............. PASSED
tests/test_url_validator.py ......... PASSED
tests/test_youtube_formats.py ....... PASSED
==================== 25 passed ====================
```

---

## 🛡 Xavfsizlik va Cheklovlar to'g'risida ochiq ma'lumot (Honest Limitations)

1. **Telegram Bot API Chegaralari:** Standart Telegram Bot API orqali yuboriladigan fayllarning maksimal hajmi **50 MB** ni tashkil etadi. Agar foydalanuvchi 1080p yoki 4K formatni tanlasa va video hajmi 50 MB dan oshsa, bot foydalanuvchiga 720p yoki 480p pastroq sifatni tanlashni taklif qiladi (agar shaxsiy Local Telegram Bot API Server o'rnatilsa, bu chegara 2 GB gacha oshadi).
2. **Yopiq va Shaxsiy Kontent:** Bot qat'iy ravishda mualliflik huquqi va platforma qoidalariga amal qiladi; yopiq (private) profillardagi yoki DRM himoyalangan kontent yuklanmaydi. Foydalanuvchiga do'stona xabarnoma ko'rsatiladi.
3. **Instagram va YouTube upstream tezlik cheklovlari:** Ekstraksiya tezligi va barqarorligi platformalarning (YouTube/Instagram) server javob vaqtiga hamda sizning serveringiz joylashgan hududning internet tezligiga bog'liq.
