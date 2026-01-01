# GroupPulse

High-performance Telegram message forwarding system with userbot monitoring and bot control panel.

## 🚀 Features

- **🔐 Secure Session Management**: Session strings stored in database
- **📱 Multi-Group Monitoring**: Listen to 200+ groups per account
- **🔑 Keyword Filtering**: Regex and literal keyword matching
- **⚙️ Flexible Rules**: Create complex forwarding rules with conditions
- **🛡️ Rate Limiting**: Multi-layer token bucket algorithm (Telegram compliant)
- **🤖 Human-like Behavior**: Randomized delays, active hours simulation
- **📊 Deduplication**: SHA-256 hash-based message deduplication
- **⚡ Async Architecture**: Fully async for high throughput
- **🐳 Docker Ready**: Complete Docker Compose setup

## 📋 Requirements

- **Server**: 4 core, 8GB RAM Ubuntu (or similar)
- **Python**: 3.11+
- **Docker**: 20.10+ (recommended) or direct Python install
- **Telegram**:
  - API credentials from https://my.telegram.org
  - Bot token from @BotFather

## 🛠️ Installation

### Option 1: Docker Compose (Recommended)

```bash
# 1. Clone repository
cd /home/grouppulse/apps/GroupPulseApp

# 2. Initial setup
make setup

# 3. Edit .env file with your credentials
nano .env

# Required values:
# - BOT_TOKEN=your_bot_token
# - DATABASE_URL=postgresql+asyncpg://grouppulse:password@postgres:5432/grouppulse
# - REDIS_URL=redis://:password@redis:6379/0

# 4. Run database migrations
make migrate

# 5. Start all services
make start

# 6. View logs
make logs
```

### Option 2: Manual Python Install

```bash
# 1. Install Python dependencies
poetry install

# 2. Setup PostgreSQL and Redis manually

# 3. Edit .env file

# 4. Run migrations
alembic upgrade head

# 5. Start services
python -m src.bot.app  # In one terminal
python -m src.main     # In another terminal
```

## 📝 Configuration

### Environment Variables

See `.env.example` for all available options. Key settings:

**Database:**
```env
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db
DB_POOL_SIZE=10
DB_MAX_OVERFLOW=20
```

**Rate Limiting:**
```env
ACCOUNT_RATE_LIMIT=20      # Messages/second per account
DESTINATION_RATE_LIMIT=5   # Messages/second per destination
GLOBAL_RATE_LIMIT=100      # Total messages/second
```

**Performance:**
```env
MAX_WORKERS=10                 # Max Telegram accounts
MAX_CONCURRENT_FORWARDS=100    # Max concurrent forwards
MESSAGE_BATCH_SIZE=50          # DB batch size
```

## 🎯 Usage

### 1. Start Bot in Telegram

Find your bot (use token from @BotFather) and send `/start`

### 2. Connect Telegram Account

1. Click "🔐 Account" → "➕ Add Account"
2. Enter API ID and API Hash from https://my.telegram.org
3. Enter your phone number (with country code, e.g., +1234567890)
4. Enter verification code from Telegram
5. If 2FA enabled, enter password

Your session will be encrypted and stored securely.

### 3. Add Groups

**Source Groups** (listen to):
1. Click "📱 Groups" → "➕ Add Source"
2. Enter group ID or invite link
3. Bot will verify access

**Destination Groups** (forward to):
1. Click "📱 Groups" → "➕ Add Destination"
2. Enter group ID or invite link

### 4. Create Keywords (Optional)

1. Click "🔑 Keywords" → "➕ Add Keyword"
2. Enter keyword (literal or regex)
3. Choose type:
   - **Literal**: Exact match (case-insensitive by default)
   - **Regex**: Regular expression pattern

### 5. Create Forwarding Rule

1. Click "⚙️ Rules" → "➕ Create Rule"
2. Select source groups (where to listen)
3. Select destination groups (where to forward)
4. (Optional) Select keywords to filter
5. (Optional) Set conditions:
   - Only media
   - Only text
   - Min/max text length
6. Save rule

## 📊 Architecture

```
┌─────────────────────────────────────────────────────┐
│              AIOGRAM BOT (Control UI)               │
│         - User management (FSM)                     │
│         - Account setup                             │
│         - Group/keyword/rule management             │
└──────────────────┬──────────────────────────────────┘
                   │
       ┌───────────▼─────────────────┐
       │   CORE SERVICE LAYER        │
       │   - Rule matching engine    │
       │   - Rate limiter            │
       │   - Forwarding service      │
       └───────────┬─────────────────┘
                   │
       ┌───────────┴────────────┬─────────────┐
       │                        │             │
┌──────▼──────────┐   ┌─────────▼───────┐   ┌▼────────┐
│ TELETHON        │   │  POSTGRESQL     │   │  REDIS  │
│ USERBOT WORKERS │   │  (Async Pool)   │   │ (Cache) │
│ (2-3 accounts)  │   │  - User data    │   │         │
│                 │   │  - Groups       │   │         │
│ - Listen 200+   │   │  - Keywords     │   │         │
│   groups each   │   │  - Rules        │   │         │
│ - Filter msgs   │   │  - Msg log      │   │         │
│ - Forward       │   └─────────────────┘   └─────────┘
└─────────────────┘
```

## 🔒 Security

- ✅ Session strings stored securely in database
- ✅ PostgreSQL password protected
- ✅ Redis password enabled
- ✅ Docker containers run as non-root
- ✅ Input validation on all user inputs
- ✅ Rate limiting on bot commands

**NEVER commit .env file to git!**

## 📈 Performance

**Expected capacity (4 core, 8GB RAM):**
- **Accounts**: 2-3 initially, up to 10 with optimization
- **Groups**: 400-600 (200 per account)
- **Throughput**: 50-100 messages/second
- **Database**: ~100MB/month (30-day retention)
- **Memory**: ~6GB used, 2GB free
- **CPU**: 30-50% average usage

## 🚨 Troubleshooting

### Bot not responding
```bash
# Check bot logs
make logs

# Restart bot service
docker-compose restart bot
```

### Userbot not forwarding
```bash
# Check userbot worker logs
docker-compose logs userbot-worker

# Verify account is active in database
make shell
SELECT * FROM telegram_accounts WHERE is_active = true;
```

### Database connection errors
```bash
# Check PostgreSQL status
docker-compose ps postgres

# Restart database
docker-compose restart postgres

# Run migrations again
make migrate
```

### Flood wait issues
- Reduce `ACCOUNT_RATE_LIMIT` in .env
- Wait for flood wait to expire (check logs for duration)
- Telegram limits: ~20 msg/sec sustained

## 📚 Commands Reference

| Command | Description |
|---------|-------------|
| `make setup` | Initial project setup |
| `make start` | Start all services |
| `make stop` | Stop all services |
| `make restart` | Restart services |
| `make logs` | View logs (follow mode) |
| `make migrate` | Run database migrations |
| `make shell` | Open database shell |
| `make test` | Run tests |
| `make clean` | Clean temporary files |

## 🔧 Development

### Project Structure

```
grouppulse/
├── config/           # Configuration (settings.py)
├── src/
│   ├── bot/          # aiogram bot (FSM, handlers, keyboards)
│   ├── userbot/      # Telethon userbot (client, worker pool)
│   ├── core/         # Business logic (rule matcher, rate limiter)
│   ├── database/     # ORM models, repositories
│   ├── services/     # Forwarding service
│   └── utils/        # Utilities (crypto, validators)
├── alembic/          # Database migrations
├── tests/            # Test suite
├── docker-compose.yml
├── Dockerfile
└── pyproject.toml
```

### Running Tests

```bash
# Run all tests
make test

# Run specific test file
pytest tests/unit/test_rule_matcher.py -v

# Run with coverage
pytest --cov=src tests/
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

## 📄 License

Private project. All rights reserved.

## 🤝 Support

For issues or questions, contact the development team.

---

**GroupPulse** v1.0.0 - High-Performance Telegram Forwarding System
