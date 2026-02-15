"""
Real-time chat widget with room selector using MQTT over WebSockets.

Renders a self-contained HTML/JS/CSS chat component via st.components.v1.html().
The widget connects directly to the Mosquitto MQTT broker from the browser,
bypassing Streamlit's rerun cycle for true real-time messaging.

Rooms are presented as a horizontal scrollable pill bar (mobile-friendly).
Room switching is handled entirely client-side: the MQTT subscription changes,
messages are cleared and re-loaded from pre-loaded history, and new incoming
messages on other rooms increment an unread badge on their pill.
"""

import json

import streamlit.components.v1 as components


def render_chat_widget(callsign, operator_name, rooms, all_histories,
                       current_room_id, mqtt_ws_url, translations,
                       operators_list=None):
    """
    Render the real-time chat widget with room selector.

    Args:
        callsign: Current operator's callsign
        operator_name: Current operator's display name
        rooms: List of room dicts ({id, name, room_type, is_admin_only})
        all_histories: Dict mapping room id (int) to list of message dicts
        current_room_id: Initially selected room ID
        mqtt_ws_url: Public WebSocket URL for MQTT broker
        translations: Dict with chat-related translation strings
        operators_list: List of operator dicts for @mention autocomplete
    """
    safe_callsign = json.dumps(callsign)
    safe_name = json.dumps(operator_name)
    safe_mqtt_url = json.dumps(mqtt_ws_url)
    safe_rooms = json.dumps([
        {'id': r['id'], 'name': r['name'], 'type': r['room_type']}
        for r in rooms
    ])
    # Convert int keys to string keys for JS object
    histories_for_js = {str(k): v for k, v in all_histories.items()}
    safe_histories = json.dumps(histories_for_js)
    safe_current = json.dumps(current_room_id)
    safe_translations = json.dumps(translations)
    safe_operators = json.dumps(operators_list or [])

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
        height: 520px;
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

    /* --- Room pill bar --- */
    #room-bar {{
        display: flex;
        gap: 6px;
        padding: 7px 14px;
        overflow-x: auto;
        -webkit-overflow-scrolling: touch;
        background: #1a1d24;
        border-bottom: 1px solid #333;
        scrollbar-width: none;
    }}
    #room-bar::-webkit-scrollbar {{ display: none; }}

    .room-pill {{
        flex-shrink: 0;
        padding: 5px 14px;
        border-radius: 16px;
        background: #262b36;
        color: #aaa;
        font-size: 12px;
        cursor: pointer;
        white-space: nowrap;
        border: 1px solid #333;
        transition: all 0.15s;
        user-select: none;
        -webkit-tap-highlight-color: transparent;
    }}

    .room-pill:hover {{
        background: #2e3440;
        color: #fff;
    }}

    .room-pill.active {{
        background: #2563eb;
        color: white;
        border-color: #2563eb;
    }}

    .room-pill .unread-badge {{
        display: inline-block;
        background: #ef4444;
        color: white;
        border-radius: 10px;
        padding: 0 5px;
        font-size: 10px;
        margin-left: 4px;
        min-width: 16px;
        text-align: center;
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
        cursor: pointer;
        transition: filter 0.1s;
    }}

    .msg:hover {{
        filter: brightness(1.15);
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

    .msg .quote-block {{
        border-left: 3px solid #4a9eff;
        padding: 3px 8px;
        margin-bottom: 4px;
        background: rgba(74, 158, 255, 0.08);
        border-radius: 0 4px 4px 0;
        font-size: 12px;
    }}

    .msg .quote-block .qb-sender {{
        font-weight: 600;
        color: #80b3ff;
        font-size: 10px;
    }}

    .msg .quote-block .qb-text {{
        color: #999;
        font-size: 11px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 280px;
    }}

    .mention {{
        color: #4a9eff;
        font-weight: 600;
    }}

    #quote-preview {{
        display: none;
        padding: 6px 14px;
        background: #1a1d24;
        border-top: 1px solid #333;
        border-left: 3px solid #4a9eff;
        font-size: 12px;
        color: #aaa;
        position: relative;
    }}

    #quote-preview .qp-sender {{
        font-weight: 600;
        color: #80b3ff;
        font-size: 11px;
    }}

    #quote-preview .qp-text {{
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: calc(100% - 30px);
    }}

    #quote-preview .qp-dismiss {{
        position: absolute;
        right: 10px;
        top: 4px;
        cursor: pointer;
        color: #888;
        font-size: 16px;
        line-height: 1;
    }}

    #quote-preview .qp-dismiss:hover {{
        color: #fff;
    }}

    #chat-input-wrapper {{
        position: relative;
    }}

    #mention-autocomplete {{
        display: none;
        position: absolute;
        bottom: 100%;
        left: 14px;
        right: 14px;
        background: #1e2230;
        border: 1px solid #444;
        border-radius: 6px;
        max-height: 150px;
        overflow-y: auto;
        z-index: 100;
    }}

    .mention-item {{
        padding: 6px 10px;
        font-size: 13px;
        color: #e0e0e0;
        cursor: pointer;
        display: flex;
        gap: 8px;
    }}

    .mention-item:hover,
    .mention-item.active {{
        background: #2563eb;
        color: white;
    }}

    .mention-item .mi-callsign {{
        font-weight: 600;
    }}

    .mention-item .mi-name {{
        color: #aaa;
        font-size: 12px;
    }}

    .mention-item:hover .mi-name,
    .mention-item.active .mi-name {{
        color: #ddd;
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
    <div id="room-bar"></div>
    <div id="chat-messages"><div id="chat-bottom"></div></div>
    <div id="quote-preview">
        <div class="qp-sender" id="qp-sender"></div>
        <div class="qp-text" id="qp-text"></div>
        <span class="qp-dismiss" id="qp-dismiss">&times;</span>
    </div>
    <div id="chat-input-wrapper">
        <div id="mention-autocomplete"></div>
        <div id="chat-input-area">
            <input type="text" id="chat-input" maxlength="500" />
            <button id="chat-send" disabled></button>
        </div>
    </div>
</div>

<script src="https://unpkg.com/mqtt@5.10.1/dist/mqtt.min.js"></script>
<script>
(function() {{
    const CALLSIGN = {safe_callsign};
    const NAME = {safe_name};
    const MQTT_URL = {safe_mqtt_url};
    const ROOMS = {safe_rooms};
    const ALL_HISTORY = {safe_histories};
    const T = {safe_translations};
    const OPERATORS = {safe_operators};

    var currentRoomId = {safe_current};
    var currentTopic = 'quendaward/chat/room/' + currentRoomId;
    var unreadCounts = {{}};

    const messagesEl = document.getElementById('chat-messages');
    const inputEl = document.getElementById('chat-input');
    const sendBtn = document.getElementById('chat-send');
    const statusDot = document.getElementById('status-dot');
    const statusText = document.getElementById('status-text');
    const titleEl = document.getElementById('chat-title');
    const quotePreview = document.getElementById('quote-preview');
    const qpSender = document.getElementById('qp-sender');
    const qpText = document.getElementById('qp-text');
    const qpDismiss = document.getElementById('qp-dismiss');
    const autocompleteEl = document.getElementById('mention-autocomplete');
    const roomBar = document.getElementById('room-bar');

    titleEl.textContent = T.chat_title || 'Chat';
    inputEl.placeholder = T.chat_placeholder || 'Type a message...';
    sendBtn.textContent = T.chat_send || 'Send';
    statusText.textContent = T.chat_connecting || 'Connecting...';

    // Rate limiting
    let lastSendTime = 0;
    const SEND_INTERVAL_MS = 1000;

    // Scroll position key (per room + user)
    var POS_KEY = 'quendaward_chat_pos_' + currentRoomId + '_' + CALLSIGN;

    function saveLastRead(msgId) {{
        if (msgId && msgId !== '0') {{
            try {{ localStorage.setItem(POS_KEY, String(msgId)); }} catch(e) {{}}
        }}
    }}

    function restoreScrollPosition() {{
        var lastId = null;
        try {{ lastId = localStorage.getItem(POS_KEY); }} catch(e) {{}}
        if (lastId) {{
            var el = messagesEl.querySelector('[data-msg-id="' + lastId + '"]');
            if (el) {{
                messagesEl.scrollTop = el.offsetTop - messagesEl.offsetTop;
                return;
            }}
        }}
        messagesEl.scrollTop = messagesEl.scrollHeight;
    }}

    // Quoting state
    let quotedMessage = null;

    // Mention autocomplete state
    let mentionActive = false;
    let mentionAtPos = -1;
    let mentionIdx = 0;
    let mentionFiltered = [];

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

    function renderMessageText(text) {{
        let escaped = escapeHtml(text);
        escaped = escaped.replace(/@([A-Z0-9\\/]{{2,12}})/gi, function(match) {{
            return '<span class="mention">' + match + '</span>';
        }});
        return escaped;
    }}

    function appendMessage(callsign, name, text, time, isSelf, replyTo, msgId) {{
        const div = document.createElement('div');
        div.className = 'msg ' + (isSelf ? 'self' : 'other');
        div.dataset.msgId = msgId || '0';
        div.dataset.msgCallsign = callsign || '';
        div.dataset.msgText = (text || '').substring(0, 100);

        const senderLabel = name ? callsign + ' (' + name + ')' : callsign;
        const timeStr = time ? formatTime(time) : formatTime(new Date().toISOString());

        let quoteHtml = '';
        if (replyTo && replyTo.callsign) {{
            const qtxt = (replyTo.text || '').substring(0, 100);
            quoteHtml =
                '<div class="quote-block">' +
                '<div class="qb-sender">' + escapeHtml(replyTo.callsign) + '</div>' +
                '<div class="qb-text">' + escapeHtml(qtxt) + '</div>' +
                '</div>';
        }}

        div.innerHTML =
            '<div class="sender">' + escapeHtml(senderLabel) + '</div>' +
            quoteHtml +
            '<div class="text">' + renderMessageText(text) + '</div>' +
            '<div class="time">' + escapeHtml(timeStr) + '</div>';

        div.addEventListener('click', function() {{
            quotedMessage = {{
                id: parseInt(div.dataset.msgId) || 0,
                callsign: div.dataset.msgCallsign,
                text: div.dataset.msgText
            }};
            qpSender.textContent = (T.chat_replying_to || 'Replying to') + ' ' + quotedMessage.callsign;
            qpText.textContent = quotedMessage.text.length > 80
                ? quotedMessage.text.substring(0, 80) + '...'
                : quotedMessage.text;
            quotePreview.style.display = 'block';
            inputEl.focus();
        }});

        const sentinel = document.getElementById('chat-bottom');
        messagesEl.insertBefore(div, sentinel);
        saveLastRead(div.dataset.msgId);
    }}

    qpDismiss.addEventListener('click', function() {{
        quotedMessage = null;
        quotePreview.style.display = 'none';
    }});

    // --- Room pills ---
    function renderRoomPills() {{
        roomBar.innerHTML = '';
        ROOMS.forEach(function(room) {{
            var pill = document.createElement('div');
            pill.className = 'room-pill' + (room.id === currentRoomId ? ' active' : '');
            pill.textContent = room.name;
            pill.dataset.roomId = room.id;

            var unread = unreadCounts[room.id] || 0;
            if (unread > 0 && room.id !== currentRoomId) {{
                var badge = document.createElement('span');
                badge.className = 'unread-badge';
                badge.textContent = unread > 99 ? '99+' : unread;
                pill.appendChild(badge);
            }}

            pill.addEventListener('click', function() {{
                switchRoom(room.id);
            }});
            roomBar.appendChild(pill);
        }});
    }}

    function loadRoomMessages(roomId) {{
        // Clear messages area
        messagesEl.innerHTML = '<div id="chat-bottom"></div>';

        var history = ALL_HISTORY[String(roomId)] || [];
        if (history.length > 0) {{
            history.forEach(function(msg) {{
                var replyTo = msg.reply_to_callsign ? {{
                    callsign: msg.reply_to_callsign,
                    text: msg.reply_to_text || ''
                }} : null;
                appendMessage(
                    msg.operator_callsign,
                    '',
                    msg.message,
                    msg.created_at,
                    msg.operator_callsign === CALLSIGN,
                    replyTo,
                    msg.id
                );
            }});
        }} else {{
            var noMsg = document.createElement('div');
            noMsg.className = 'no-messages';
            noMsg.id = 'no-messages-placeholder';
            noMsg.textContent = T.chat_no_messages || 'No messages yet. Start the conversation!';
            messagesEl.appendChild(noMsg);
        }}
    }}

    function switchRoom(roomId) {{
        if (roomId === currentRoomId) return;

        // Clear quote
        quotedMessage = null;
        quotePreview.style.display = 'none';

        currentRoomId = roomId;
        currentTopic = 'quendaward/chat/room/' + roomId;
        POS_KEY = 'quendaward_chat_pos_' + roomId + '_' + CALLSIGN;

        // Clear unread for new room
        unreadCounts[roomId] = 0;

        // Re-render pills
        renderRoomPills();

        // Load messages for new room
        loadRoomMessages(roomId);

        // Restore scroll position
        restoreScrollPosition();
    }}

    // Initial render
    renderRoomPills();
    loadRoomMessages(currentRoomId);

    // Restore scroll with ResizeObserver
    var scrollRestored = false;
    var ro = new ResizeObserver(function(entries) {{
        for (var i = 0; i < entries.length; i++) {{
            if (entries[i].contentRect.height > 0 && !scrollRestored) {{
                scrollRestored = true;
                ro.disconnect();
                restoreScrollPosition();
            }}
        }}
    }});
    ro.observe(messagesEl);

    // --- Mention autocomplete ---
    function renderAutocomplete(items) {{
        autocompleteEl.innerHTML = '';
        items.forEach(function(op, idx) {{
            const item = document.createElement('div');
            item.className = 'mention-item' + (idx === mentionIdx ? ' active' : '');
            item.innerHTML =
                '<span class="mi-callsign">' + escapeHtml(op.callsign) + '</span>' +
                (op.name ? '<span class="mi-name">' + escapeHtml(op.name) + '</span>' : '');
            item.addEventListener('mousedown', function(e) {{
                e.preventDefault();
                selectMention(op.callsign);
            }});
            autocompleteEl.appendChild(item);
        }});
        autocompleteEl.style.display = items.length > 0 ? 'block' : 'none';
    }}

    function hideAutocomplete() {{
        mentionActive = false;
        mentionAtPos = -1;
        mentionIdx = 0;
        mentionFiltered = [];
        autocompleteEl.style.display = 'none';
    }}

    function selectMention(cs) {{
        const val = inputEl.value;
        const before = val.substring(0, mentionAtPos);
        const after = val.substring(inputEl.selectionStart);
        inputEl.value = before + '@' + cs + ' ' + after;
        const newPos = mentionAtPos + cs.length + 2;
        inputEl.setSelectionRange(newPos, newPos);
        hideAutocomplete();
        inputEl.focus();
    }}

    inputEl.addEventListener('input', function() {{
        const val = inputEl.value;
        const cursorPos = inputEl.selectionStart;

        var atPos = -1;
        for (var i = cursorPos - 1; i >= 0; i--) {{
            if (val[i] === '@') {{ atPos = i; break; }}
            if (val[i] === ' ') break;
        }}

        if (atPos >= 0) {{
            var query = val.substring(atPos + 1, cursorPos).toUpperCase();
            var filtered = OPERATORS.filter(function(op) {{
                if (op.callsign === CALLSIGN) return false;
                var csMatch = op.callsign.toUpperCase().indexOf(query) >= 0;
                var nmMatch = op.name && op.name.toUpperCase().indexOf(query) >= 0;
                return csMatch || nmMatch;
            }}).slice(0, 8);

            if (filtered.length > 0) {{
                mentionActive = true;
                mentionAtPos = atPos;
                mentionFiltered = filtered;
                if (mentionIdx >= filtered.length) mentionIdx = 0;
                renderAutocomplete(filtered);
            }} else {{
                hideAutocomplete();
            }}
        }} else {{
            hideAutocomplete();
        }}
    }});

    // --- MQTT Connection ---
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
                // Subscribe to all rooms with wildcard
                client.subscribe('quendaward/chat/room/#');
            }});

            client.on('message', function(topic, payload) {{
                try {{
                    const data = JSON.parse(payload.toString());
                    if (!data.callsign || !data.message) return;
                    if (data.callsign === CALLSIGN) return;

                    // Extract room_id from topic
                    var parts = topic.split('/');
                    var msgRoomId = null;
                    if (parts.length >= 4 && parts[2] === 'room') {{
                        msgRoomId = parseInt(parts[3]);
                    }}
                    if (!msgRoomId) return;

                    if (msgRoomId === currentRoomId) {{
                        // Remove placeholder
                        var placeholder = document.getElementById('no-messages-placeholder');
                        if (placeholder) placeholder.remove();

                        var replyTo = data.reply_to || null;
                        var atBottom = messagesEl.scrollHeight - messagesEl.scrollTop - messagesEl.clientHeight < 60;
                        appendMessage(
                            data.callsign,
                            data.name || '',
                            data.message,
                            data.timestamp || null,
                            false,
                            replyTo,
                            0
                        );
                        if (atBottom) {{
                            messagesEl.scrollTop = messagesEl.scrollHeight;
                        }}
                    }} else {{
                        // Increment unread for other room
                        unreadCounts[msgRoomId] = (unreadCounts[msgRoomId] || 0) + 1;
                        renderRoomPills();

                        // Also store in ALL_HISTORY so switching shows the message
                        var key = String(msgRoomId);
                        if (!ALL_HISTORY[key]) ALL_HISTORY[key] = [];
                        ALL_HISTORY[key].push({{
                            id: 0,
                            operator_callsign: data.callsign,
                            message: data.message,
                            source: data.source || 'app',
                            created_at: data.timestamp || new Date().toISOString(),
                            reply_to_id: data.reply_to ? data.reply_to.id : null,
                            reply_to_callsign: data.reply_to ? data.reply_to.callsign : null,
                            reply_to_text: data.reply_to ? data.reply_to.text : null
                        }});
                    }}
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

        const now = Date.now();
        if (now - lastSendTime < SEND_INTERVAL_MS) return;
        lastSendTime = now;

        const ts = new Date().toISOString();

        var mentionRegex = /@([A-Z0-9\\/]{{2,12}})/gi;
        var mentions = [];
        var match;
        while ((match = mentionRegex.exec(text)) !== null) {{
            var upper = match[1].toUpperCase();
            if (OPERATORS.some(function(op) {{ return op.callsign === upper; }})) {{
                if (mentions.indexOf(upper) < 0) mentions.push(upper);
            }}
        }}

        var payloadObj = {{
            callsign: CALLSIGN,
            name: NAME,
            message: text,
            source: 'app',
            timestamp: ts
        }};

        if (mentions.length > 0) {{
            payloadObj.mentions = mentions;
        }}

        if (quotedMessage) {{
            payloadObj.reply_to = {{
                id: quotedMessage.id,
                callsign: quotedMessage.callsign,
                text: (quotedMessage.text || '').substring(0, 100)
            }};
        }}

        client.publish(currentTopic, JSON.stringify(payloadObj));

        var placeholder = document.getElementById('no-messages-placeholder');
        if (placeholder) placeholder.remove();

        appendMessage(CALLSIGN, NAME, text, ts, true, quotedMessage, 0);
        inputEl.value = '';
        messagesEl.scrollTop = messagesEl.scrollHeight;

        quotedMessage = null;
        quotePreview.style.display = 'none';
    }}

    sendBtn.addEventListener('click', sendMessage);
    inputEl.addEventListener('keydown', function(e) {{
        if (mentionActive) {{
            if (e.key === 'ArrowDown') {{
                e.preventDefault();
                mentionIdx = (mentionIdx + 1) % mentionFiltered.length;
                renderAutocomplete(mentionFiltered);
                return;
            }}
            if (e.key === 'ArrowUp') {{
                e.preventDefault();
                mentionIdx = (mentionIdx - 1 + mentionFiltered.length) % mentionFiltered.length;
                renderAutocomplete(mentionFiltered);
                return;
            }}
            if (e.key === 'Enter' || e.key === 'Tab') {{
                e.preventDefault();
                if (mentionFiltered[mentionIdx]) {{
                    selectMention(mentionFiltered[mentionIdx].callsign);
                }}
                return;
            }}
            if (e.key === 'Escape') {{
                e.preventDefault();
                hideAutocomplete();
                return;
            }}
        }}

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

    components.html(html, height=540, scrolling=False)
