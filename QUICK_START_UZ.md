# 🚀 GroupPulse - Tez Boshlash (Lokal, Docker'siz)

## 📋 1-Qadam: Python Dependencies

```bash
cd /home/grouppulse/apps/GroupPulseApp

# Virtual environment yarating
python3.11 -m venv venv

# Aktivlashtiring
source venv/bin/activate

# Dependencies o'rnating
pip install -r requirements.txt

# SQLite uchun qo'shimcha
pip install aiosqlite
```

## 🔑 2-Qadam: Bot Token Oling

1. Telegram'da **@BotFather** ga boring
2. `/newbot` ni yuboring
3. Bot nomi kiriting (masalan: `MyGroupPulse`)
4. Username kiriting (masalan: `mygrouppulse_bot`)
5. Token'ni saqlang (masalan: `1234567890:ABCdef...`)

## ⚙️ 3-Qadam: .env Faylini Yarating

```bash
# .env yaratish
cat > .env << 'EOF'
# Application
APP_NAME=GroupPulse
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# Bot Token (BotFather'dan)
BOT_TOKEN=SHUNGA_BOT_TOKENNI_QOYING

# Database (SQLite - test uchun oson)
DATABASE_URL=sqlite+aiosqlite:///./grouppulse.db
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_ECHO=false

# Redis (hozircha kerak emas)
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_CONNECTIONS=10

# Encryption Key (avtomatik generatsiya)
SESSION_ENCRYPTION_KEY=ENCRYPTION_KEY_SHUNGA

# Rate Limits
GLOBAL_RATE_LIMIT=100
ACCOUNT_RATE_LIMIT=20
DESTINATION_RATE_LIMIT=5

# Performance
MAX_WORKERS=3
MAX_CONCURRENT_FORWARDS=50
MESSAGE_BATCH_SIZE=20

MESSAGE_LOG_RETENTION_DAYS=30
METRICS_RETENTION_DAYS=7
EOF

# Encryption key generatsiya
python -c "import secrets; print('Generated key:', secrets.token_hex(32))"

# Natijani .env ga qo'ying:
nano .env
# SESSION_ENCRYPTION_KEY= ga yukordagi natijani qo'ying
# BOT_TOKEN= ga BotFather'dan olgan tokenni qo'ying
```

Yoki qisqaroq:

```bash
# Avtomatik .env yaratish
python3 << 'PYTHON_SCRIPT'
import secrets

bot_token = input("BotFather'dan olgan tokenni kiriting: ").strip()
encryption_key = secrets.token_hex(32)

env_content = f"""# Application
APP_NAME=GroupPulse
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# Bot Token
BOT_TOKEN={bot_token}

# Database (SQLite)
DATABASE_URL=sqlite+aiosqlite:///./grouppulse.db
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_ECHO=false

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_CONNECTIONS=10

# Encryption Key
SESSION_ENCRYPTION_KEY={encryption_key}

# Rate Limits
GLOBAL_RATE_LIMIT=100
ACCOUNT_RATE_LIMIT=20
DESTINATION_RATE_LIMIT=5

# Performance
MAX_WORKERS=3
MAX_CONCURRENT_FORWARDS=50
MESSAGE_BATCH_SIZE=20

MESSAGE_LOG_RETENTION_DAYS=30
METRICS_RETENTION_DAYS=7
"""

with open('.env', 'w') as f:
    f.write(env_content)

print("✓ .env fayli yaratildi!")
PYTHON_SCRIPT
```

## 🗄️ 4-Qadam: Database Yaratish

```bash
# Virtual environment aktiv bo'lishi kerak
source venv/bin/activate

# Database jadvallarini yaratish
python scripts/create_db.py
```

Natija:
```
Creating database tables...
✓ Database tables created successfully!

Created tables:
  - users
  - telegram_accounts
  - groups
  - keywords
  - forwarding_rules
  - message_log
```

## 🤖 5-Qadam: Bot'ni Ishga Tushirish

```bash
# Virtual environment aktiv bo'lishi kerak
source venv/bin/activate

# Bot'ni ishga tushiring
python -m src.bot.app
```

**Muvaffaqiyatli ishga tushsa:**
```
INFO - ✓ Bot handlers registered
INFO - Starting GroupPulse Bot...
INFO - ✓ Bot started: @mygrouppulse_bot (ID: 1234567890)
```

## 📱 6-Qadam: Telegram'da Test Qiling

1. Telegram'da botingizni toping (@mygrouppulse_bot)
2. `/start` ni yuboring
3. Main menu ko'rinishi kerak:

```
👋 Welcome to GroupPulse!

I'm your Telegram message forwarding assistant...

[🔐 Account] [📱 Groups]
[🔑 Keywords] [⚙️ Rules]
[📊 Statistics] [❓ Help]
```

## ✅ Test

- [ ] Bot javob beradi
- [ ] `/start` - Main menu chiqadi
- [ ] `/help` - Help message chiqadi
- [ ] Inline buttons ishlaydi

---

## 🐛 Muammolar?

### Error: `ModuleNotFoundError: No module named 'src'`

```bash
# venv aktiv ekanini tekshiring
source venv/bin/activate

# Yoki PYTHONPATH qo'shing
export PYTHONPATH=/home/grouppulse/apps/GroupPulseApp:$PYTHONPATH
python -m src.bot.app
```

### Error: `Invalid bot token`

```bash
# .env faylidagi BOT_TOKEN to'g'riligini tekshiring
cat .env | grep BOT_TOKEN

# BotFather'dan yangisini oling
```

### Bot javob bermayapti

```bash
# Terminal'da errorlar bormi?
# Bot ishga tushganini tekshiring:
# "✓ Bot started: @..." deb chiqishi kerak
```

---

## 🎯 Keyingi Qadamlar

Bot ishga tushdi! ✅

**Hozir qanday:**
- `/start`, `/help` ishlaydi
- Main menu ko'rinadi
- Buttons ishlaydi (lekin handlers yo'q)

**Keyingi:**
- Account qo'shish uchun handler kerak
- Groups, keywords, rules handlers kerak

**Men qo'shimcha handlers'ni yozib berayinmi?**

Yoki birinchi navbatda shu holatda test qilmoqchimisiz?
