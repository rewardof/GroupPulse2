# GroupPulse - Lokal Setup (Docker'siz)

Bu qo'llanma GroupPulse ni Docker ishlatmasdan, to'g'ridan-to'g'ri kompyuteringizda ishga tushirish uchun.

## 🔧 Talablar

- **Python**: 3.11 yoki undan yuqori
- **PostgreSQL**: 14+ (yoki SQLite test uchun)
- **Redis**: 7+ (yoki test uchun ixtiyoriy)

---

## 📦 1. Python Dependencies ni O'rnatish

```bash
cd /home/grouppulse/apps/GroupPulseApp

# Virtual environment yarating
python3.11 -m venv venv

# Activate qiling
source venv/bin/activate

# Dependencies ni o'rnating
pip install -r requirements.txt
```

---

## 💾 2. Database Setup

### Variant A: PostgreSQL (Production)

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install postgresql postgresql-contrib

# PostgreSQL ni ishga tushiring
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Database yarating
sudo -u postgres psql

# PostgreSQL ichida:
CREATE DATABASE grouppulse;
CREATE USER grouppulse WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE grouppulse TO grouppulse;
\q
```

**.env faylida:**
```env
DATABASE_URL=postgresql+asyncpg://grouppulse:your_password@localhost:5432/grouppulse
```

### Variant B: SQLite (Test uchun - oson)

SQLite ishlatish uchun kodni ozgina o'zgartirish kerak:

**.env faylida:**
```env
DATABASE_URL=sqlite+aiosqlite:///./grouppulse.db
```

**requirements.txt ga qo'shing:**
```bash
pip install aiosqlite
```

**src/database/connection.py ni o'zgartiring** (26-qator):
```python
# PostgreSQL uchun edi:
# from sqlalchemy.pool import NullPool, QueuePool

# SQLite uchun:
from sqlalchemy.pool import NullPool, StaticPool
```

---

## 🔴 3. Redis Setup

### Variant A: Redis Server (Production)

```bash
# Ubuntu/Debian
sudo apt install redis-server

# Redis ni ishga tushiring
sudo systemctl start redis
sudo systemctl enable redis

# Password qo'ying (ixtiyoriy)
sudo nano /etc/redis/redis.conf
# Qatorni toping va o'zgartiring:
# requirepass your_redis_password

sudo systemctl restart redis
```

**.env faylida:**
```env
REDIS_URL=redis://:your_redis_password@localhost:6379/0
# Yoki password bo'lmasa:
REDIS_URL=redis://localhost:6379/0
```

### Variant B: Redis'siz (Test uchun)

Redis majburiy emas hozircha. Keyinchalik kerak bo'lganda qo'shish mumkin.

**.env faylida shunchaki:**
```env
REDIS_URL=redis://localhost:6379/0
```

---

## ⚙️ 4. Environment Configuration

```bash
# .env faylini yarating
cp .env.example .env
nano .env
```

**Minimal .env (test uchun):**

```env
# Application
APP_NAME=GroupPulse
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO

# Bot Token (BotFather dan oling)
BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# Database (PostgreSQL yoki SQLite)
DATABASE_URL=sqlite+aiosqlite:///./grouppulse.db
DB_POOL_SIZE=5
DB_MAX_OVERFLOW=10
DB_ECHO=false

# Redis (yoki ixtiyoriy)
REDIS_URL=redis://localhost:6379/0
REDIS_MAX_CONNECTIONS=10

# Encryption Key (yangi generatsiya qiling)
SESSION_ENCRYPTION_KEY=your_64_character_hex_key_here_generate_below

# Rate Limits
GLOBAL_RATE_LIMIT=100
ACCOUNT_RATE_LIMIT=20
DESTINATION_RATE_LIMIT=5

# Performance
MAX_WORKERS=3
MAX_CONCURRENT_FORWARDS=50
MESSAGE_BATCH_SIZE=20
```

---

## 🗄️ 5. Database Migratsiya

```bash
# Virtual environment aktiv bo'lishi kerak
source venv/bin/activate

# Database jadvallarini yarating
python -c "
import asyncio
from src.database.connection import get_async_engine
from src.database.models import Base

async def create_tables():
    engine = get_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('✓ Database tables created')

asyncio.run(create_tables())
"
```

Yoki Alembic ishlatish (agar PostgreSQL bo'lsa):
```bash
alembic upgrade head
```

---

## 🚀 6. Bot'ni Ishga Tushirish

### Test Mode (Bot faqat)

```bash
# Virtual environment aktiv
source venv/bin/activate

# Bot'ni ishga tushiring
python -m src.bot.app
```

Bot ishga tushsa, Telegram'da `/start` yuboring.

### Full Mode (Bot + Userbot Workers)

**Terminal 1 - Bot:**
```bash
source venv/bin/activate
python -m src.bot.app
```

**Terminal 2 - Main App (Userbot workers):**
```bash
source venv/bin/activate
python -m src.main
```

---

## 📱 7. Telegram Credentials

### Bot Token olish:
1. Telegram'da **@BotFather** ga yuboring
2. `/newbot` buyrug'ini yuboring
3. Bot nomini va username'ini kiriting
4. Token'ni `.env` fayliga `BOT_TOKEN` sifatida qo'ying

### API Credentials (Userbot uchun):
1. https://my.telegram.org ga kiring
2. **API development tools** ga boring
3. **App title** va **Short name** kiriting
4. `api_id` va `api_hash` ni oling
5. Bularni bot orqali account qo'shishda kerak bo'ladi

---

## ✅ 8. Test Qilish

### 1. Bot ishlayotganini tekshirish:
```bash
# Terminal'da ko'ring
# "✓ Bot started: @your_bot_username" deb chiqishi kerak
```

### 2. Telegram'da:
```
/start - Main menu ochilishi kerak
/help - Help message
```

### 3. Database'ni tekshirish (SQLite):
```bash
sqlite3 grouppulse.db
.tables
# users, telegram_accounts, groups, va boshqalar ko'rinishi kerak
.quit
```

---

## 🐛 Troubleshooting

### Error: `No module named 'src'`
```bash
# venv aktiv ekanini tekshiring
source venv/bin/activate

# PYTHONPATH ni to'g'ri qiling
export PYTHONPATH=/home/grouppulse/apps/GroupPulseApp:$PYTHONPATH
```

### Error: Database connection failed
```bash
# PostgreSQL ishga tushganini tekshiring
sudo systemctl status postgresql

# Yoki SQLite ishlating
# .env da: DATABASE_URL=sqlite+aiosqlite:///./grouppulse.db
```

### Error: Redis connection failed
```bash
# Redis keragi yo'q hozircha, shunchaki warning bo'ladi
# Keyinchalik kerak bo'lsa o'rnatib olasiz
```

### Bot javob bermayapti
```bash
# Token to'g'ri ekanini tekshiring
# .env faylida BOT_TOKEN ni qayta tekshiring

# Loglarni ko'ring
# Terminalda error messaglar bor-yo'qligini tekshiring
```

---

## 📊 Status Ko'rish

### Bot ishga tushganini tekshirish:
```bash
# Bot terminalida:
# "✓ Bot started: @bot_username (ID: 1234567890)" ko'rinadi
```

### Database'ni ko'rish (SQLite):
```bash
sqlite3 grouppulse.db
SELECT * FROM users;
.quit
```

### Database'ni ko'rish (PostgreSQL):
```bash
psql -U grouppulse -d grouppulse
SELECT * FROM users;
\q
```

---

## 🎯 Minimal Test Setup (SQLite + Redis'siz)

Eng oson yo'l:

```bash
# 1. Dependencies
pip install -r requirements.txt
pip install aiosqlite

# 2. .env
cat > .env << EOF
APP_NAME=GroupPulse
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=INFO
BOT_TOKEN=<BotFather_dan_token>
DATABASE_URL=sqlite+aiosqlite:///./grouppulse.db
REDIS_URL=redis://localhost:6379/0
SESSION_ENCRYPTION_KEY=$(python -c "import secrets; print(secrets.token_hex(32))")
ACCOUNT_RATE_LIMIT=20
DESTINATION_RATE_LIMIT=5
GLOBAL_RATE_LIMIT=100
MAX_WORKERS=3
EOF

# 3. Database yaratish
python -c "
import asyncio
from src.database.connection import get_async_engine
from src.database.models import Base

async def create_tables():
    engine = get_async_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print('✓ Done')

asyncio.run(create_tables())
"

# 4. Bot'ni ishga tushirish
python -m src.bot.app
```

---

## 🔄 Keyingi Qadamlar

1. ✅ Bot ishga tushdi - Telegram'da test qiling
2. ⏳ Account qo'shish - Bot handlers qo'shilishi kerak
3. ⏳ Groups va rules - Bot handlers qo'shilishi kerak

Men bot handlers'ni ham yozib berayinmi? (account.py, groups.py, keywords.py, rules.py)
