# Plan: Real-Time Chat via MQTT over WebSockets

## Problem

The current app uses Streamlit's 5-second auto-refresh polling. Streamlit is fundamentally a server-side framework that reruns the entire script on every interaction — it has no mechanism to push data to the client in real time. The existing Telegram chat plan (`PLAN_TELEGRAM_CHAT.md`) would still rely on this 5-second polling for in-app messages, which is not true real-time.

## Proposed Solution: Mosquitto MQTT Broker + mqtt.js in Browser

Use MQTT (a lightweight pub/sub messaging protocol) with an **embedded chat widget** inside Streamlit. Messages flow directly **browser-to-browser** through the MQTT broker — completely bypassing Streamlit's refresh cycle.

### Why MQTT?

- **True real-time**: Messages arrive in milliseconds via pub/sub, not polling
- **Lightweight**: Mosquitto is ~5MB, mqtt.js is ~30KB — perfect for this scale
- **Browser-native**: Mosquitto supports MQTT over WebSockets, which browsers can use directly via mqtt.js
- **Works within Streamlit**: The chat widget lives in an `st.components.v1.html()` block — it's a self-contained HTML/JS/CSS component that manages its own WebSocket connection, independent of Streamlit's rerun cycle
- **Extensible**: The same MQTT infrastructure can later push band/mode block notifications, Telegram bridge messages, DX cluster spots, etc.

### Architecture

```
┌───────────────┐    MQTT/WS     ┌──────────────────┐    MQTT/WS     ┌───────────────┐
│   Browser A   │◄──────────────►│    Mosquitto      │◄──────────────►│   Browser B   │
│ (mqtt.js chat │                │    Broker          │                │ (mqtt.js chat │
│   widget)     │                │  (port 9001 WS)   │                │   widget)     │
└───────────────┘                └────────┬───────────┘                └───────────────┘
                                          │
                                          │ MQTT (native, port 1883)
                                          ▼
                                ┌──────────────────┐
                                │  Python MQTT      │
                                │  Subscriber       │
                                │  (persistence     │
                                │   service)        │
                                │       │           │
                                │       ▼           │
                                │    SQLite DB      │
                                └──────────────────┘
```

**Message flow (sending):**
1. Operator types message in chat widget (HTML/JS component)
2. mqtt.js publishes to topic `quendaward/chat/{award_id}` (or `quendaward/chat/global`)
3. Mosquitto routes message to ALL subscribers on that topic

**Message flow (receiving):**
1. All browsers subscribed to the topic receive the message instantly
2. The JS widget appends the message to the chat DOM — no Streamlit rerun needed
3. Separately, a Python MQTT subscriber persists messages to SQLite for history

---

## Implementation Phases

### Phase 1: Mosquitto Broker Setup

**Add Mosquitto to Docker Compose:**

`docker-compose.yml` and `docker-compose-standalone.yml`:
```yaml
  mosquitto:
    image: eclipse-mosquitto:2
    container_name: quendaward-mosquitto
    volumes:
      - ./mosquitto/config/mosquitto.conf:/mosquitto/config/mosquitto.conf:ro
      - mosquitto_data:/mosquitto/data
      - mosquitto_log:/mosquitto/log
    expose:
      - "1883"   # MQTT native (internal only — for Python subscriber)
      - "9001"   # MQTT over WebSockets (proxied via nginx)
    restart: unless-stopped
```

**Create `mosquitto/config/mosquitto.conf`:**
```
# MQTT native protocol (for internal Python subscriber)
listener 1883
protocol mqtt
allow_anonymous true

# MQTT over WebSockets (for browser clients via nginx)
listener 9001
protocol websockets
allow_anonymous true

# Persistence
persistence true
persistence_location /mosquitto/data/

# Logging
log_dest stdout
log_type warning
log_type error
```

> **Security note**: `allow_anonymous true` is acceptable here because:
> - Port 1883 is only exposed internally between containers (not to the host)
> - Port 9001 is proxied through nginx which already handles TLS
> - Authentication is enforced at the application layer (the chat widget only activates for logged-in operators, and messages include callsign set by the app)
> - For a tighter setup, Phase 3 can add Mosquitto username/password or JWT-based auth

**Add nginx proxy for MQTT WebSocket (standalone config):**

Add to `nginx/nginx.conf` inside the HTTPS server block:
```nginx
# MQTT WebSocket proxy for real-time chat
location /mqtt {
    proxy_pass http://mosquitto:9001;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    proxy_set_header Host $host;
    proxy_read_timeout 86400;
}
```

For the non-standalone setup (external nginx), the same location block needs to be added to the external nginx config.

**Files to create/modify:**
- [ ] Create `mosquitto/config/mosquitto.conf`
- [ ] Modify `docker-compose.yml` — add mosquitto service
- [ ] Modify `docker-compose-standalone.yml` — add mosquitto service
- [ ] Modify `nginx/nginx.conf` — add `/mqtt` WebSocket proxy location

---

### Phase 2: Database Schema for Chat History

**New table: `chat_messages`**

Add to `core/database.py` `init_database()`:

```sql
CREATE TABLE IF NOT EXISTS chat_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    award_id INTEGER,                    -- NULL for global chat
    operator_callsign TEXT NOT NULL,     -- Who sent the message
    message TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'app',  -- 'app' or 'telegram' (future)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS idx_chat_messages_award ON chat_messages(award_id, created_at);
```

**New database functions** in `features/chat.py`:
- `save_chat_message(award_id, callsign, message, source='app')` — insert message
- `get_chat_history(award_id, limit=50)` — retrieve recent messages for loading history on page open
- `get_chat_history_global(limit=50)` — retrieve all messages regardless of award

**Files to create/modify:**
- [ ] Modify `core/database.py` — add `chat_messages` table creation
- [ ] Create `features/chat.py` — chat database functions

---

### Phase 3: Python MQTT Persistence Service

**New file: `services/mqtt_subscriber.py`**

A lightweight Python script that:
1. Connects to Mosquitto on port 1883 (internal)
2. Subscribes to `quendaward/chat/#` (all chat topics)
3. On each message received, parses the JSON payload and calls `save_chat_message()`
4. Runs as a background thread within the Streamlit app OR as a separate Docker service

**Message format (JSON published by browser):**
```json
{
  "callsign": "EA1ABC",
  "name": "Juan",
  "message": "I'm going to 20m SSB now",
  "award_id": 3,
  "timestamp": "2026-02-13T10:30:00Z"
}
```

**Deployment option A — Background thread (simpler):**
Start the MQTT subscriber as a daemon thread in `app.py` at startup. Uses `paho-mqtt` library. Advantage: single container, shared DB connection. Disadvantage: one subscriber per Streamlit worker (but since we use SQLite with a single file, this is fine — only one worker writes).

**Deployment option B — Separate container:**
```yaml
  mqtt-persistence:
    build:
      context: .
      dockerfile: Dockerfile
    command: python -m services.mqtt_subscriber
    environment:
      - DATABASE_PATH=/app/data/ham_coordinator.db
      - MQTT_BROKER=mosquitto
    volumes:
      - ./data:/app/data
    depends_on:
      - mosquitto
    restart: unless-stopped
```

**Recommendation:** Start with Option A (background thread). It's simpler and sufficient for the expected load. Move to Option B if scaling is needed later.

**Files to create/modify:**
- [ ] Create `services/__init__.py`
- [ ] Create `services/mqtt_subscriber.py` — MQTT listener that persists messages
- [ ] Modify `app.py` — start MQTT subscriber thread on startup
- [ ] Add `paho-mqtt>=2.0` to `requirements.txt`

---

### Phase 4: Chat UI — Embedded HTML/JS Component

This is the core of the real-time experience. The chat lives in a **self-contained HTML/JS/CSS block** rendered via `st.components.v1.html()`. It manages its own MQTT WebSocket connection, completely independent of Streamlit's rerun cycle.

**New file: `ui/chat_widget.py`**

Contains a function `render_chat_widget(callsign, operator_name, award_id, mqtt_ws_url, chat_history)` that generates and renders the HTML component.

**Key features of the widget:**
- Connects to Mosquitto via mqtt.js (loaded from CDN or bundled)
- Subscribes to `quendaward/chat/{award_id}` on connect
- Displays incoming messages in real-time (DOM append, no page reload)
- Sends messages by publishing to the same MQTT topic
- Loads chat history from SQLite (passed as initial data from Python)
- Auto-scrolls to bottom on new messages
- Shows online/offline connection status indicator
- Styled to match the app's dark theme
- Mobile-responsive

**HTML component structure:**
```html
<div id="chat-container">
  <div id="chat-header">Chat — {award_name} | Status: <span id="status">connecting...</span></div>
  <div id="chat-messages">
    <!-- History loaded from DB -->
    <!-- New messages appended by JS -->
  </div>
  <div id="chat-input-area">
    <input type="text" id="chat-input" placeholder="Type a message..." />
    <button id="chat-send">Send</button>
  </div>
</div>

<script src="https://unpkg.com/mqtt/dist/mqtt.min.js"></script>
<script>
  const client = mqtt.connect('{mqtt_ws_url}');
  const topic = 'quendaward/chat/{award_id}';
  // ... subscribe, publish, render logic
</script>
```

**How the widget receives the callsign securely:**
- The callsign and operator name are injected server-side by Python into the HTML template
- The browser JS can only send messages as the logged-in operator
- This is NOT editable by the client (it's baked into the rendered HTML from session state)
- Note: A determined user could still forge messages via direct MQTT publish. For this use case (small trusted operator group), this is acceptable. Phase 5 addresses hardening.

**Chat history loading:**
- On tab open, Python fetches last N messages from SQLite via `get_chat_history()`
- These are serialized to JSON and injected into the HTML template
- The widget renders them on load, then appends new real-time messages after

**Files to create/modify:**
- [ ] Create `ui/chat_widget.py` — HTML/JS/CSS chat component
- [ ] Modify `app.py` — add Chat tab to operator panel
- [ ] Modify `ui/components.py` — add `render_chat_tab()` if needed

---

### Phase 5: Translations

**Add to `i18n/translations.py`:**
- `tab_chat` — "Chat" / "Chat" / "Chat"
- `chat_placeholder` — "Type a message..." / "Escribe un mensaje..." / "Escribe unha mensaxe..."
- `chat_send` — "Send" / "Enviar" / "Enviar"
- `chat_connected` — "Connected" / "Conectado" / "Conectado"
- `chat_disconnected` — "Disconnected" / "Desconectado" / "Desconectado"
- `chat_no_messages` — "No messages yet" / etc.

**Files to modify:**
- [ ] Modify `i18n/translations.py` — add chat-related translation keys

---

### Phase 6: Config & Environment

**Add to `config.py`:**
```python
MQTT_BROKER_HOST = os.getenv('MQTT_BROKER_HOST', 'mosquitto')  # Internal Docker hostname
MQTT_BROKER_PORT = int(os.getenv('MQTT_BROKER_PORT', '1883'))  # Native MQTT
MQTT_WS_URL = os.getenv('MQTT_WS_URL', '')  # Public WebSocket URL, e.g. wss://yourdomain.com/mqtt
CHAT_ENABLED = bool(MQTT_WS_URL)
CHAT_HISTORY_LIMIT = 100  # Messages to load on tab open
```

**Add to `.env.example`:**
```
MQTT_WS_URL=wss://yourdomain.com/mqtt
MQTT_BROKER_HOST=mosquitto
MQTT_BROKER_PORT=1883
```

**Files to modify:**
- [ ] Modify `config.py` — add MQTT/chat configuration
- [ ] Modify `.env.example` — add MQTT environment variables
- [ ] Modify `docker-compose.yml` — pass MQTT env vars to app
- [ ] Modify `docker-compose-standalone.yml` — pass MQTT env vars to app

---

## MQTT Topic Structure

```
quendaward/
├── chat/
│   ├── global          # Global chat (cross-award)
│   ├── {award_id}      # Per-award chat rooms
│   └── system          # System notifications (future: block changes, etc.)
```

This structure allows operators to subscribe to their active award's chat, and also enables future features like real-time block notifications without any architectural changes.

---

## Security Considerations

1. **Callsign injection**: The callsign in each message is set server-side by Python — the browser JS uses it but can't modify the variable injected into the template. A technically savvy user could connect directly to MQTT and forge messages, but this is a small trusted operator group. If hardening is needed:
   - Add Mosquitto ACLs with per-user credentials
   - Generate short-lived MQTT tokens on login, passed to the widget

2. **Message sanitization**: The JS widget must HTML-escape all message content before inserting into the DOM to prevent XSS.

3. **Rate limiting**: Implement client-side rate limiting in the JS widget (e.g., max 1 message per second). Server-side rate limiting can be added via Mosquitto plugins if needed.

4. **TLS**: All MQTT WebSocket traffic goes through nginx with TLS (wss://). Internal Docker traffic (port 1883) stays within the container network.

5. **Message size**: Limit message length in the JS widget (e.g., 500 characters).

---

## Future Extensions (enabled by this MQTT infrastructure)

- **Real-time block notifications**: When an operator blocks a band/mode, publish to `quendaward/chat/system` — all browsers show an instant notification without waiting for the 5s refresh
- **Telegram bridge**: A bot subscribes to MQTT topics and forwards to Telegram, and vice versa — messages from Telegram get published to MQTT and appear instantly in-app
- **DX Cluster integration**: Spots published to MQTT topics, displayed in real-time
- **Typing indicators**: Publish to `quendaward/typing/{award_id}` for "X is typing..." UX
- **Online presence**: Use MQTT Last Will & Testament to track who's online

---

## Dependencies to Add

```
paho-mqtt>=2.0
```

mqtt.js for the browser is loaded from CDN (`https://unpkg.com/mqtt/dist/mqtt.min.js`) — no npm/build step needed.

---

## Summary of All File Changes

| Action | File | Description |
|--------|------|-------------|
| Create | `mosquitto/config/mosquitto.conf` | Mosquitto broker configuration |
| Create | `services/__init__.py` | Services package init |
| Create | `services/mqtt_subscriber.py` | Python MQTT subscriber for persistence |
| Create | `features/chat.py` | Chat database functions |
| Create | `ui/chat_widget.py` | HTML/JS/CSS real-time chat component |
| Modify | `core/database.py` | Add `chat_messages` table |
| Modify | `app.py` | Add chat tab, start MQTT subscriber thread |
| Modify | `config.py` | Add MQTT/chat configuration |
| Modify | `docker-compose.yml` | Add mosquitto service + env vars |
| Modify | `docker-compose-standalone.yml` | Add mosquitto service + env vars |
| Modify | `nginx/nginx.conf` | Add `/mqtt` WebSocket proxy |
| Modify | `i18n/translations.py` | Add chat translation keys |
| Modify | `requirements.txt` | Add `paho-mqtt>=2.0` |
| Modify | `.env.example` | Add MQTT env vars |
