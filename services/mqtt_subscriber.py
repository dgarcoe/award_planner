"""
MQTT subscriber service for persisting chat messages to SQLite.

Connects to the Mosquitto broker and listens on quendaward/chat/# topics.
When a message arrives, it parses the JSON payload and saves it to the database.

Can run as a background thread within the Streamlit app or standalone.
"""

import json
import logging
import os
import threading

import paho.mqtt.client as mqtt

from core.database import get_connection

logger = logging.getLogger(__name__)

MQTT_BROKER_HOST = os.getenv('MQTT_BROKER_HOST', 'mosquitto')
MQTT_BROKER_PORT = int(os.getenv('MQTT_BROKER_PORT', '1883'))

# Track whether the subscriber is already running (one per process)
_subscriber_started = False
_subscriber_lock = threading.Lock()


def _save_chat_message(award_id, callsign, message, source='app',
                       reply_to_id=None, reply_to_callsign=None, reply_to_text=None):
    """Persist a chat message to the database. Returns the inserted message ID."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            '''INSERT INTO chat_messages
               (award_id, operator_callsign, message, source,
                reply_to_id, reply_to_callsign, reply_to_text)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (award_id, callsign, message, source,
             reply_to_id, reply_to_callsign, reply_to_text)
        )
        conn.commit()
        return cursor.lastrowid
    except Exception:
        logger.exception("Failed to save chat message")
        return None
    finally:
        conn.close()


def _create_mention_notifications(award_id, sender_callsign, message, mentions, chat_message_id):
    """Create a chat_notification row for each mentioned callsign."""
    if not mentions:
        return
    conn = get_connection()
    try:
        preview = message[:80] + '...' if len(message) > 80 else message
        for callsign in mentions:
            if callsign.upper() == sender_callsign.upper():
                continue
            existing = conn.execute(
                'SELECT callsign FROM operators WHERE callsign = ?',
                (callsign.upper(),)
            ).fetchone()
            if existing:
                conn.execute(
                    '''INSERT INTO chat_notifications
                       (recipient_callsign, sender_callsign, award_id,
                        message_preview, chat_message_id)
                       VALUES (?, ?, ?, ?, ?)''',
                    (callsign.upper(), sender_callsign.upper(),
                     award_id, preview, chat_message_id)
                )
        conn.commit()
    except Exception:
        logger.exception("Failed to create mention notifications")
    finally:
        conn.close()


def _on_connect(client, userdata, flags, reason_code, properties=None):
    """Called when the client connects to the broker."""
    logger.info("MQTT subscriber connected to broker (rc=%s)", reason_code)
    client.subscribe("quendaward/chat/#")


def _on_message(client, userdata, msg):
    """Called when a message is received from the broker."""
    try:
        payload = json.loads(msg.payload.decode('utf-8'))
        callsign = payload.get('callsign', '')
        message = payload.get('message', '')
        source = payload.get('source', 'app')

        if not callsign or not message:
            return

        # Extract award_id from topic: quendaward/chat/{award_id_or_global}
        topic_parts = msg.topic.split('/')
        award_id = None
        if len(topic_parts) >= 3 and topic_parts[2] != 'global':
            try:
                award_id = int(topic_parts[2])
            except ValueError:
                pass

        # Extract quote data
        reply_to = payload.get('reply_to')
        reply_to_id = None
        reply_to_callsign = None
        reply_to_text = None
        if reply_to and isinstance(reply_to, dict):
            reply_to_id = reply_to.get('id')
            reply_to_callsign = reply_to.get('callsign')
            reply_to_text = (reply_to.get('text') or '')[:100]

        msg_id = _save_chat_message(
            award_id, callsign, message, source,
            reply_to_id, reply_to_callsign, reply_to_text
        )

        # Process @mentions
        mentions = payload.get('mentions', [])
        if mentions and msg_id:
            _create_mention_notifications(award_id, callsign, message, mentions, msg_id)
    except json.JSONDecodeError:
        logger.warning("Received non-JSON MQTT message on %s", msg.topic)
    except Exception:
        logger.exception("Error processing MQTT message")


def start_subscriber_thread():
    """
    Start the MQTT subscriber as a daemon thread.

    Safe to call multiple times — only starts once per process.
    """
    global _subscriber_started

    with _subscriber_lock:
        if _subscriber_started:
            return
        _subscriber_started = True

    def _run():
        client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        client.on_connect = _on_connect
        client.on_message = _on_message

        try:
            client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, keepalive=60)
            logger.info("MQTT subscriber thread started (broker=%s:%s)", MQTT_BROKER_HOST, MQTT_BROKER_PORT)
            client.loop_forever()
        except Exception:
            logger.exception("MQTT subscriber failed to connect")
            with _subscriber_lock:
                global _subscriber_started
                _subscriber_started = False

    thread = threading.Thread(target=_run, daemon=True, name="mqtt-subscriber")
    thread.start()


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting MQTT subscriber (standalone mode)")
    start_subscriber_thread()

    # Keep the main thread alive
    import time
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        logger.info("MQTT subscriber stopped")
