"""
System event helpers — post automated messages to chat rooms.

Used by block/unblock operations to notify room participants in real-time.
If MQTT is not configured, messages are still persisted to the database.
"""

import json
import logging
import os
from datetime import datetime, timezone

from core.database import get_connection

logger = logging.getLogger(__name__)

MQTT_BROKER_HOST = os.getenv('MQTT_BROKER_HOST', 'mosquitto')
MQTT_BROKER_PORT = int(os.getenv('MQTT_BROKER_PORT', '1883'))


def post_system_event_to_award_room(award_id: int, message_text: str) -> None:
    """
    Persist a system event message to the chat room linked to the given award,
    then publish it via MQTT so connected clients see it in real-time.

    Silently no-ops if the award has no linked chat room or MQTT is unavailable.
    """
    try:
        conn = get_connection()
        try:
            row = conn.execute(
                'SELECT id FROM chat_rooms WHERE award_id = ? AND room_type = "award"',
                (award_id,)
            ).fetchone()
            if not row:
                return
            room_id = row['id']

            conn.execute(
                '''INSERT INTO chat_messages (room_id, operator_callsign, message, source)
                   VALUES (?, ?, ?, ?)''',
                (room_id, 'SYSTEM', message_text, 'system')
            )
            conn.commit()
        finally:
            conn.close()

        _publish_system_mqtt(room_id, message_text)

    except Exception:
        logger.warning("post_system_event_to_award_room failed", exc_info=True)


def _publish_system_mqtt(room_id: int, message_text: str) -> None:
    """Publish a system message to the MQTT broker (best-effort)."""
    try:
        import paho.mqtt.publish as mqtt_publish
        topic = f'quendaward/chat/room/{room_id}'
        ts = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.000Z')
        payload = json.dumps({
            'callsign': 'SYSTEM',
            'message': message_text,
            'source': 'system',
            'timestamp': ts,
        })
        mqtt_publish.single(topic, payload, hostname=MQTT_BROKER_HOST, port=MQTT_BROKER_PORT)
    except Exception:
        logger.debug("MQTT publish for system event failed (non-critical)", exc_info=True)
