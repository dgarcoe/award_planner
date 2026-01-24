# Plan: Telegram Group Integration for QuendAward Chat

## Overview

Integrate QuendAward with a Telegram group so operators can communicate via the app or Telegram, with messages synced between both platforms.

---

## Architecture Options

### Option A: One Global Telegram Group (Recommended for simplicity)
- Single Telegram group for all operators
- All messages visible to everyone
- Simpler setup and management

### Option B: Per-Special Callsign Groups
- One Telegram group per special callsign
- More complex but better organization
- Requires dynamic group management

**Recommendation**: Start with Option A, expand later if needed.

---

## How It Works

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│   QuendAward    │◄───────►│   Telegram Bot  │◄───────►│  Telegram Group │
│   (Streamlit)   │         │   (Python)      │         │  (Operators)    │
└─────────────────┘         └─────────────────┘         └─────────────────┘
        │                          │
        │                          │
        ▼                          ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        SQLite Database                                   │
│                     (chat_messages table)                               │
└─────────────────────────────────────────────────────────────────────────┘
```

### Message Flow

**App → Telegram:**
1. User sends message in QuendAward app
2. Message saved to database
3. Bot sends message to Telegram group (with sender's callsign)

**Telegram → App:**
1. User sends message in Telegram group
2. Bot receives via webhook/polling
3. Message saved to database (linked to Telegram user)
4. App displays on next refresh (5 seconds)

---

## Implementation Steps

### Phase 1: Telegram Bot Setup

1. **Create Telegram Bot**
   - Talk to @BotFather on Telegram
   - Create new bot, get API token
   - Store token in environment variable: `TELEGRAM_BOT_TOKEN`

2. **Create Telegram Group**
   - Create group for operators
   - Add bot to group as admin
   - Get group chat ID: `TELEGRAM_CHAT_ID`

### Phase 2: Database Changes

**New table: `chat_messages`**
```sql
CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    award_id INTEGER,                    -- NULL for global chat
    operator_callsign TEXT,              -- NULL if from Telegram-only user
    telegram_user_id INTEGER,            -- Telegram user ID
    telegram_username TEXT,              -- @username for display
    message TEXT NOT NULL,
    source TEXT NOT NULL,                -- 'app' or 'telegram'
    telegram_message_id INTEGER,         -- For message linking
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

**New table: `telegram_links`** (optional, for verified operators)
```sql
CREATE TABLE IF NOT EXISTS telegram_links (
    operator_callsign TEXT PRIMARY KEY,
    telegram_user_id INTEGER NOT NULL,
    telegram_username TEXT,
    verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (operator_callsign) REFERENCES operators (callsign)
)
```

### Phase 3: New Files to Create

**`telegram_bot.py`** - Bot handler
```python
# Dependencies: python-telegram-bot

from telegram import Update, Bot
from telegram.ext import Application, MessageHandler, filters
import database as db
import os

TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

bot = Bot(token=TELEGRAM_BOT_TOKEN)

async def handle_telegram_message(update: Update, context):
    """Handle incoming Telegram messages."""
    message = update.message

    # Only process messages from the configured group
    if str(message.chat_id) != TELEGRAM_CHAT_ID:
        return

    # Save to database
    db.insert_chat_message(
        award_id=None,  # Global chat
        operator_callsign=None,  # Will lookup from telegram_links
        telegram_user_id=message.from_user.id,
        telegram_username=message.from_user.username,
        message_text=message.text,
        source='telegram',
        telegram_message_id=message.message_id
    )

def send_to_telegram(callsign: str, message: str):
    """Send message from app to Telegram group."""
    formatted = f"📻 *{callsign}*: {message}"
    bot.send_message(
        chat_id=TELEGRAM_CHAT_ID,
        text=formatted,
        parse_mode='Markdown'
    )
```

### Phase 4: Modify Existing Files

**`database.py`** - Add functions:
- `insert_chat_message()` - Save message from either source
- `get_chat_messages()` - Retrieve messages for display
- `link_telegram_account()` - Link operator callsign to Telegram
- `get_operator_by_telegram_id()` - Lookup operator from Telegram user

**`ui_components.py`** - Add chat UI:
- `render_chat_tab()` - Display messages and input form
- Show message source (app icon vs Telegram icon)
- Display callsign or @username

**`app.py`** - Add chat tab:
- Add to `operator_panel()` tabs
- Import and call `render_chat_tab()`

**`config.py`** - Add configuration:
```python
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
TELEGRAM_ENABLED = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)
```

**`translations.py`** - Add translations for:
- Chat tab name
- Message input placeholder
- Send button
- "via Telegram" / "via App" labels
- Link Telegram account option

### Phase 5: Bot Deployment Options

**Option A: Run bot in same container (simpler)**
- Add bot as background thread in Streamlit app
- Pros: Single deployment
- Cons: Bot restarts when app restarts

**Option B: Separate bot service (recommended)**
- Run bot as separate Docker container
- Share database volume
- Pros: Independent, more reliable
- Cons: More complex setup

**Docker Compose addition:**
```yaml
services:
  app:
    # ... existing config ...

  telegram-bot:
    build:
      context: .
      dockerfile: Dockerfile.bot
    environment:
      - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
      - TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}
      - DATABASE_PATH=/app/data/ham_coordinator.db
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

---

## Features

### Basic Features (Phase 1)
- [x] Messages from app appear in Telegram
- [x] Messages from Telegram appear in app
- [x] Show sender callsign/@username
- [x] Show message source icon
- [x] Timestamps

### Advanced Features (Phase 2)
- [ ] Link Telegram account to operator callsign
- [ ] Verify operator identity via bot command
- [ ] Admin moderation (delete from both platforms)
- [ ] Per-special callsign channels
- [ ] Notifications for band/mode blocks

### Optional Features (Phase 3)
- [ ] Bot commands: `/status`, `/blocks`, `/help`
- [ ] Inline buttons for quick actions
- [ ] Photo/file sharing
- [ ] Message threading

---

## Environment Variables

Add to `.env`:
```
TELEGRAM_BOT_TOKEN=your_bot_token_here
TELEGRAM_CHAT_ID=-1001234567890
```

Add to `docker-compose.yml`:
```yaml
environment:
  - TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
  - TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}
```

---

## Dependencies

Add to `requirements.txt`:
```
python-telegram-bot>=20.0
```

---

## Security Considerations

1. **Bot token**: Keep secret, use environment variables
2. **Group access**: Make group private, bot adds verified operators
3. **Message validation**: Sanitize messages before display
4. **Rate limiting**: Prevent spam from either direction
5. **Admin controls**: Allow admins to mute/ban users

---

## Estimated Effort

| Phase | Description | Complexity |
|-------|-------------|------------|
| 1 | Bot setup + basic send/receive | 2-3 hours |
| 2 | Database + UI integration | 2-3 hours |
| 3 | Docker deployment | 1 hour |
| 4 | Testing + polish | 1-2 hours |

**Total: ~6-9 hours**

---

## Fallback: App-Only Chat

If Telegram integration is too complex, can implement standalone chat:
- Messages stored in database only
- No external dependencies
- Works with existing 5-second auto-refresh
- Simpler but no mobile notifications

---

## Next Steps

1. Decide: Global chat vs per-special callsign
2. Create Telegram bot with @BotFather
3. Create private Telegram group
4. Implement Phase 1 (basic integration)
5. Test with a few operators
6. Expand features based on feedback
