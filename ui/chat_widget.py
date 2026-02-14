"""
Real-time chat widget using MQTT over WebSockets.

Renders a self-contained HTML/JS/CSS chat component via st.components.v1.html().
The widget connects directly to the Mosquitto MQTT broker from the browser,
bypassing Streamlit's rerun cycle for true real-time messaging.
"""

import json

import streamlit.components.v1 as components


def render_chat_widget(callsign, operator_name, award_id, mqtt_ws_url, chat_history, translations):
    """
    Render the real-time chat widget.

    Args:
        callsign: Current operator's callsign
        operator_name: Current operator's display name
        award_id: Current award ID for the chat room
        mqtt_ws_url: Public WebSocket URL for MQTT broker (e.g. wss://domain/mqtt)
        chat_history: List of message dicts from DB for initial history load
        translations: Dict with chat-related translation strings
    """
    # Sanitize inputs for safe JS embedding
    safe_callsign = json.dumps(callsign)
    safe_name = json.dumps(operator_name)
    safe_topic = json.dumps(f"quendaward/chat/{award_id}")
    safe_mqtt_url = json.dumps(mqtt_ws_url)
    safe_history = json.dumps(chat_history)
    safe_translations = json.dumps(translations)

    html = f"""
<!DOCTYPE html>
<html>
<head>
<style>
    * {{
        box-sizing: border-box;
        margin: 0;
        padding: 0;
    }}

    body {{
        font-family: 'Source Sans Pro', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        background: transparent;
        color: #fafafa;
    }}

    #chat-container {{
        display: flex;
        flex-direction: column;
        height: 480px;
        border: 1px solid #333;
        border-radius: 8px;
        overflow: hidden;
        background: #0e1117;
    }}

    #chat-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 8px 14px;
        background: #1a1d24;
        border-bottom: 1px solid #333;
        font-size: 13px;
    }}

    #chat-header .status {{
        display: flex;
        align-items: center;
        gap: 6px;
        font-size: 12px;
    }}

    #chat-header .status .dot {{
        width: 8px;
        height: 8px;
        border-radius: 50%;
        background: #666;
    }}

    #chat-header .status .dot.connected {{
        background: #4caf50;
    }}

    #chat-header .status .dot.error {{
        background: #f44336;
    }}

    #chat-messages {{
        flex: 1;
        overflow-y: auto;
        padding: 10px 14px;
        display: flex;
        flex-direction: column;
        gap: 6px;
    }}

    #chat-messages::-webkit-scrollbar {{
        width: 6px;
    }}

    #chat-messages::-webkit-scrollbar-track {{
        background: transparent;
    }}

    #chat-messages::-webkit-scrollbar-thumb {{
        background: #444;
        border-radius: 3px;
    }}

    .msg {{
        max-width: 85%;
        padding: 6px 10px;
        border-radius: 8px;
        font-size: 13px;
        line-height: 1.4;
        word-wrap: break-word;
    }}

    .msg.other {{
        align-self: flex-start;
        background: #1e2230;
    }}

    .msg.self {{
        align-self: flex-end;
        background: #1a3a5c;
    }}

    .msg .sender {{
        font-weight: 600;
        font-size: 11px;
        margin-bottom: 2px;
        color: #80b3ff;
    }}

    .msg.self .sender {{
        color: #66ccff;
        text-align: right;
    }}

    .msg .text {{
        color: #e0e0e0;
    }}

    .msg .time {{
        font-size: 10px;
        color: #888;
        margin-top: 2px;
        text-align: right;
    }}

    .msg-system {{
        align-self: center;
        font-size: 11px;
        color: #888;
        padding: 4px 0;
    }}

    #chat-input-area {{
        display: flex;
        gap: 8px;
        padding: 10px 14px;
        border-top: 1px solid #333;
        background: #1a1d24;
    }}

    #chat-input {{
        flex: 1;
        padding: 8px 12px;
        border: 1px solid #444;
        border-radius: 6px;
        background: #0e1117;
        color: #fafafa;
        font-size: 14px;
        outline: none;
    }}

    #chat-input:focus {{
        border-color: #4a9eff;
    }}

    #chat-input::placeholder {{
        color: #666;
    }}

    #chat-send {{
        padding: 8px 18px;
        border: none;
        border-radius: 6px;
        background: #2563eb;
        color: white;
        font-size: 13px;
        font-weight: 600;
        cursor: pointer;
        white-space: nowrap;
    }}

    #chat-send:hover {{
        background: #1d4ed8;
    }}

    #chat-send:disabled {{
        background: #444;
        cursor: not-allowed;
    }}

    .no-messages {{
        color: #666;
        text-align: center;
        padding: 40px 0;
        font-size: 13px;
    }}
</style>
</head>
<body>

<div id="chat-container">
    <div id="chat-header">
        <span id="chat-title"></span>
        <div class="status">
            <span id="status-text"></span>
            <span class="dot" id="status-dot"></span>
        </div>
    </div>
    <div id="chat-messages"></div>
    <div id="chat-input-area">
        <input type="text" id="chat-input" maxlength="500" />
        <button id="chat-send" disabled></button>
    </div>
</div>

<script src="https://unpkg.com/mqtt@5.10.1/dist/mqtt.min.js"></script>
<script>
(function() {{
    const CALLSIGN = {safe_callsign};
    const NAME = {safe_name};
    const TOPIC = {safe_topic};
    const MQTT_URL = {safe_mqtt_url};
    const HISTORY = {safe_history};
    const T = {safe_translations};

    const messagesEl = document.getElementById('chat-messages');
    const inputEl = document.getElementById('chat-input');
    const sendBtn = document.getElementById('chat-send');
    const statusDot = document.getElementById('status-dot');
    const statusText = document.getElementById('status-text');
    const titleEl = document.getElementById('chat-title');

    // Set translated text
    titleEl.textContent = T.chat_title || 'Chat';
    inputEl.placeholder = T.chat_placeholder || 'Type a message...';
    sendBtn.textContent = T.chat_send || 'Send';
    statusText.textContent = T.chat_connecting || 'Connecting...';

    // Rate limiting: 1 message per second
    let lastSendTime = 0;
    const SEND_INTERVAL_MS = 1000;

    function escapeHtml(text) {{
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }}

    function formatTime(isoStr) {{
        try {{
            const d = new Date(isoStr);
            if (isNaN(d.getTime())) return '';
            return d.toLocaleTimeString([], {{ hour: '2-digit', minute: '2-digit' }});
        }} catch(e) {{
            return '';
        }}
    }}

    function appendMessage(callsign, name, text, time, isSelf) {{
        const div = document.createElement('div');
        div.className = 'msg ' + (isSelf ? 'self' : 'other');

        const senderLabel = name ? callsign + ' (' + name + ')' : callsign;
        const timeStr = time ? formatTime(time) : formatTime(new Date().toISOString());

        div.innerHTML =
            '<div class="sender">' + escapeHtml(senderLabel) + '</div>' +
            '<div class="text">' + escapeHtml(text) + '</div>' +
            '<div class="time">' + escapeHtml(timeStr) + '</div>';

        messagesEl.appendChild(div);
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }}

    // Load history
    if (HISTORY && HISTORY.length > 0) {{
        HISTORY.forEach(function(msg) {{
            appendMessage(
                msg.operator_callsign,
                '',
                msg.message,
                msg.created_at,
                msg.operator_callsign === CALLSIGN
            );
        }});
    }} else {{
        const noMsg = document.createElement('div');
        noMsg.className = 'no-messages';
        noMsg.id = 'no-messages-placeholder';
        noMsg.textContent = T.chat_no_messages || 'No messages yet. Start the conversation!';
        messagesEl.appendChild(noMsg);
    }}

    // MQTT Connection
    let client = null;

    function connectMqtt() {{
        if (!MQTT_URL) {{
            statusText.textContent = T.chat_not_configured || 'Chat not configured';
            statusDot.className = 'dot error';
            return;
        }}

        try {{
            client = mqtt.connect(MQTT_URL, {{
                reconnectPeriod: 3000,
                connectTimeout: 10000
            }});

            client.on('connect', function() {{
                statusText.textContent = T.chat_connected || 'Connected';
                statusDot.className = 'dot connected';
                sendBtn.disabled = false;
                client.subscribe(TOPIC);
            }});

            client.on('message', function(topic, payload) {{
                try {{
                    const data = JSON.parse(payload.toString());
                    if (!data.callsign || !data.message) return;

                    // Skip our own messages (already rendered locally on send)
                    if (data.callsign === CALLSIGN) return;

                    // Remove "no messages" placeholder if present
                    const placeholder = document.getElementById('no-messages-placeholder');
                    if (placeholder) placeholder.remove();

                    appendMessage(
                        data.callsign,
                        data.name || '',
                        data.message,
                        data.timestamp || null,
                        false
                    );
                }} catch(e) {{ /* ignore malformed */ }}
            }});

            client.on('error', function() {{
                statusText.textContent = T.chat_disconnected || 'Disconnected';
                statusDot.className = 'dot error';
                sendBtn.disabled = true;
            }});

            client.on('offline', function() {{
                statusText.textContent = T.chat_disconnected || 'Disconnected';
                statusDot.className = 'dot error';
                sendBtn.disabled = true;
            }});

            client.on('reconnect', function() {{
                statusText.textContent = T.chat_connecting || 'Connecting...';
                statusDot.className = 'dot';
            }});
        }} catch(e) {{
            statusText.textContent = T.chat_disconnected || 'Disconnected';
            statusDot.className = 'dot error';
        }}
    }}

    function sendMessage() {{
        const text = inputEl.value.trim();
        if (!text || !client || !client.connected) return;

        // Rate limit
        const now = Date.now();
        if (now - lastSendTime < SEND_INTERVAL_MS) return;
        lastSendTime = now;

        const ts = new Date().toISOString();
        const payload = JSON.stringify({{
            callsign: CALLSIGN,
            name: NAME,
            message: text,
            source: 'app',
            timestamp: ts
        }});

        client.publish(TOPIC, payload);

        // Remove "no messages" placeholder if present
        const placeholder = document.getElementById('no-messages-placeholder');
        if (placeholder) placeholder.remove();

        // Render locally immediately (don't wait for echo)
        appendMessage(CALLSIGN, NAME, text, ts, true);
        inputEl.value = '';
    }}

    sendBtn.addEventListener('click', sendMessage);
    inputEl.addEventListener('keydown', function(e) {{
        if (e.key === 'Enter' && !e.shiftKey) {{
            e.preventDefault();
            sendMessage();
        }}
    }});

    connectMqtt();
}})();
</script>

</body>
</html>
"""

    components.html(html, height=500, scrolling=False)
