# Simple Telegram Message Listener

Oddiy Telegram message listener - keyword'lar bo'yicha xabarlarni destination group'ga forward qiladi.

## Features

✅ Bitta account uchun
✅ Keyword-based filtering
✅ Rate limiter (FloodWait prevention)
✅ Group/Channel only (private chat'larni ignore)
✅ Bot message'larni skip qiladi
✅ Robust connection settings

## Installation

```bash
cd /home/grouppulse/apps/GroupPulseApp/SimpleListener

# Telethon allaqachon o'rnatilgan bo'lishi kerak
# Agar yo'q bo'lsa:
pip install telethon
```

## Usage

### 1. Generate Session String

Birinchi marta ishga tushirishdan oldin session string olish kerak:

```bash
python3 login.py
```

Bu sizdan:
1. Phone number so'raydi
2. Verification code so'raydi
3. Session string chiqaradi

Session string'ni copy qiling va `listener.py` faylidagi `SESSION_STRING` ga qo'ying.

### 2. Configure

`listener.py` faylini oching va sozlang:

```python
# API credentials (already set)
API_ID = 28524826
API_HASH = "7f2ce73d335735fe428df68cd6de48db"

# Session string (from login.py)
SESSION_STRING = "YOUR_SESSION_STRING_HERE"

# Destination group ID
DESTINATION_GROUP_ID = -1001234567890  # O'zgartiring!

# Keywords to match
KEYWORDS = ["python", "telethon", "bot"]  # O'z keyword'laringizni qo'shing

# Rate limit (messages per second)
RATE_LIMIT = 5
```

### 3. Run

```bash
python3 listener.py
```

## Configuration Options

| Parameter | Description | Default |
|-----------|-------------|---------|
| `API_ID` | Telegram API ID | 28524826 |
| `API_HASH` | Telegram API Hash | (from project) |
| `SESSION_STRING` | Session string | Empty (generate first) |
| `DESTINATION_GROUP_ID` | Where to forward messages | -1001234567890 |
| `KEYWORDS` | Keywords to match (case-insensitive) | ["python", "telethon", "bot"] |
| `RATE_LIMIT` | Max messages per second | 5 |

## How It Works

1. **Connects** to Telegram using Telethon
2. **Listens** to ALL groups and channels (ignores private chats)
3. **Filters** messages by keywords (case-insensitive)
4. **Rate limits** forwarding to prevent FloodWait
5. **Forwards** matching messages to destination group

## Logs

```
============================================================
🚀 Starting Simple Message Listener
============================================================
✅ Logged in as: John (@john_doe)
✅ Destination group: My Forward Group
✅ Listening for keywords: ['python', 'telethon', 'bot']
✅ Rate limit: 5 msg/sec
============================================================
👂 Listening for messages... (Press Ctrl+C to stop)
📩 Match found in 'Python Developers': Keywords=['python'] | Text='Check out this python tutorial...'
✅ Forwarded in 0.23s | From: Python Developers
```

## Getting Destination Group ID

1. Add bot [@userinfobot](https://t.me/userinfobot) to your group
2. Bot will send group ID
3. Copy ID to `DESTINATION_GROUP_ID`

## Rate Limiting

Rate limiter uses **token bucket algorithm**:
- `RATE_LIMIT = 5` means max 5 messages per second
- If limit reached, automatically waits before forwarding
- Prevents Telegram FloodWait errors

## Difference from GroupPulse

| Feature | SimpleListener | GroupPulse |
|---------|---------------|------------|
| Accounts | 1 | Multiple |
| Database | No | Yes (PostgreSQL) |
| Web UI | No | Yes (Bot commands) |
| Rules | Simple keywords | Complex rules |
| Destinations | 1 group | Multiple |
| Config | File | Database |

## Troubleshooting

### "Not authorized" error
Run `python3 login.py` to generate session string.

### "Failed to get destination group" error
Check `DESTINATION_GROUP_ID` - make sure it's correct and negative (e.g., -1001234567890).

### No messages being forwarded
1. Check keywords are correct
2. Make sure account is in the source groups
3. Check logs for errors

## License

MIT
