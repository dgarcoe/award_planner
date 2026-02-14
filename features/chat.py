"""
Chat feature module - database functions for chat message persistence, retrieval,
and chat room management.
"""

from core.database import get_connection


# --- Chat rooms ---

def get_chat_rooms(is_admin=False):
    """
    Get all chat rooms, ordered by type then name.
    If not admin, exclude admin-only rooms.
    """
    conn = get_connection()
    try:
        if is_admin:
            cursor = conn.execute(
                "SELECT * FROM chat_rooms ORDER BY room_type, name"
            )
        else:
            cursor = conn.execute(
                "SELECT * FROM chat_rooms WHERE is_admin_only = 0 ORDER BY room_type, name"
            )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def create_chat_room(name, description='', room_type='custom',
                     is_admin_only=False, created_by=None, award_id=None):
    """Create a new chat room. Returns (success, message, room_id)."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            '''INSERT INTO chat_rooms (name, description, room_type, award_id,
                                      is_admin_only, created_by)
               VALUES (?, ?, ?, ?, ?, ?)''',
            (name, description, room_type, award_id,
             int(is_admin_only), created_by)
        )
        conn.commit()
        return True, 'Room created', cursor.lastrowid
    except Exception as e:
        if 'UNIQUE' in str(e):
            return False, 'A room with that name already exists', None
        return False, str(e), None
    finally:
        conn.close()


def delete_chat_room(room_id):
    """Delete a chat room and its messages. Cannot delete the General room."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            "SELECT room_type FROM chat_rooms WHERE id = ?", (room_id,)
        )
        row = cursor.fetchone()
        if not row:
            return False, 'Room not found'
        if row[0] == 'general':
            return False, 'Cannot delete the General room'
        conn.execute('DELETE FROM chat_messages WHERE room_id = ?', (room_id,))
        conn.execute('DELETE FROM chat_notifications WHERE room_id = ?', (room_id,))
        conn.execute('DELETE FROM chat_rooms WHERE id = ?', (room_id,))
        conn.commit()
        return True, 'Room deleted'
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def sync_award_rooms():
    """Ensure every active award has a corresponding chat room."""
    conn = get_connection()
    try:
        cursor = conn.execute('''
            SELECT a.id, a.name FROM awards a
            WHERE NOT EXISTS (SELECT 1 FROM chat_rooms cr WHERE cr.award_id = a.id)
        ''')
        for award in cursor.fetchall():
            conn.execute(
                "INSERT OR IGNORE INTO chat_rooms (name, description, room_type, award_id) "
                "VALUES (?, '', 'award', ?)",
                (award['name'], award['id'])
            )
        conn.commit()
    finally:
        conn.close()


# --- Chat messages ---

def save_chat_message(room_id, callsign, message, source='app',
                      reply_to_id=None, reply_to_callsign=None, reply_to_text=None):
    """
    Save a chat message to the database.

    Args:
        room_id: Chat room ID
        callsign: Operator callsign who sent the message
        message: Message text
        source: Message source ('app' or 'telegram')
        reply_to_id: ID of the message being quoted (optional)
        reply_to_callsign: Callsign of the quoted message sender (optional)
        reply_to_text: Preview text of the quoted message (optional)

    Returns:
        int: ID of the inserted message
    """
    conn = get_connection()
    try:
        cursor = conn.execute(
            '''INSERT INTO chat_messages
               (room_id, operator_callsign, message, source,
                reply_to_id, reply_to_callsign, reply_to_text)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (room_id, callsign, message, source,
             reply_to_id, reply_to_callsign, reply_to_text)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_chat_history(award_id, limit=100):
    """
    Retrieve recent chat messages for a specific award (legacy).
    Prefer get_chat_history_by_room for new code.
    """
    conn = get_connection()
    try:
        cursor = conn.execute(
            '''SELECT id, award_id, room_id, operator_callsign, message, source, created_at,
                      reply_to_id, reply_to_callsign, reply_to_text
               FROM chat_messages
               WHERE award_id = ?
               ORDER BY created_at DESC
               LIMIT ?''',
            (award_id, limit)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in reversed(rows)]
    finally:
        conn.close()


def get_chat_history_by_room(room_id, limit=100):
    """
    Retrieve recent chat messages for a specific room.

    Args:
        room_id: Chat room ID
        limit: Maximum number of messages to return

    Returns:
        list: Messages as dicts, oldest first
    """
    conn = get_connection()
    try:
        cursor = conn.execute(
            '''SELECT id, room_id, operator_callsign, message, source, created_at,
                      reply_to_id, reply_to_callsign, reply_to_text
               FROM chat_messages
               WHERE room_id = ?
               ORDER BY created_at DESC
               LIMIT ?''',
            (room_id, limit)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in reversed(rows)]
    finally:
        conn.close()


def get_chat_history_global(limit=100):
    """Retrieve recent chat messages across all rooms."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            '''SELECT id, room_id, operator_callsign, message, source, created_at,
                      reply_to_id, reply_to_callsign, reply_to_text
               FROM chat_messages
               ORDER BY created_at DESC
               LIMIT ?''',
            (limit,)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in reversed(rows)]
    finally:
        conn.close()


def get_chat_stats():
    """
    Return chat statistics: total count, per-room breakdown.
    """
    conn = get_connection()
    try:
        cursor = conn.execute('SELECT COUNT(*) FROM chat_messages')
        total = cursor.fetchone()[0]

        cursor = conn.execute(
            '''SELECT cm.room_id,
                      cr.name AS room_name,
                      COUNT(*) AS message_count,
                      MIN(cm.created_at) AS oldest,
                      MAX(cm.created_at) AS newest
               FROM chat_messages cm
               LEFT JOIN chat_rooms cr ON cr.id = cm.room_id
               GROUP BY cm.room_id
               ORDER BY message_count DESC'''
        )
        per_room = [dict(row) for row in cursor.fetchall()]
        return {'total': total, 'per_room': per_room}
    finally:
        conn.close()


def get_chat_stats_by_user():
    """Return message counts grouped by operator callsign."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            '''SELECT operator_callsign,
                      COUNT(*) AS message_count,
                      MIN(created_at) AS oldest,
                      MAX(created_at) AS newest
               FROM chat_messages
               GROUP BY operator_callsign
               ORDER BY message_count DESC'''
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def delete_chat_messages_by_room(room_id):
    """Delete all chat messages for a specific room. Returns number of rows deleted."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            'DELETE FROM chat_messages WHERE room_id = ?', (room_id,)
        )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def delete_chat_messages_by_award(award_id):
    """Delete all chat messages for a specific award (legacy). Returns rows deleted."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            'DELETE FROM chat_messages WHERE award_id = ?', (award_id,)
        )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def delete_chat_messages_older_than(days, room_id=None):
    """
    Delete messages older than `days` days, optionally filtered by room.
    Returns number of rows deleted.
    """
    conn = get_connection()
    try:
        if room_id is not None:
            cursor = conn.execute(
                '''DELETE FROM chat_messages
                   WHERE created_at < datetime('now', ? || ' days')
                   AND room_id = ?''',
                (f'-{days}', room_id)
            )
        else:
            cursor = conn.execute(
                '''DELETE FROM chat_messages
                   WHERE created_at < datetime('now', ? || ' days')''',
                (f'-{days}',)
            )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def delete_all_chat_messages():
    """Delete every chat message. Returns number of rows deleted."""
    conn = get_connection()
    try:
        cursor = conn.execute('DELETE FROM chat_messages')
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


# --- Chat mention notifications ---

def get_unread_chat_notification_count(operator_callsign):
    """Return the number of unread chat mention notifications for an operator."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            'SELECT COUNT(*) FROM chat_notifications WHERE recipient_callsign = ? AND is_read = 0',
            (operator_callsign.upper(),)
        )
        return cursor.fetchone()[0]
    finally:
        conn.close()


def get_unread_chat_notifications(operator_callsign, limit=20):
    """Return unread chat mention notifications for an operator."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            '''SELECT cn.id, cn.sender_callsign, cn.room_id, cn.message_preview,
                      cn.created_at, cr.name AS room_name
               FROM chat_notifications cn
               LEFT JOIN chat_rooms cr ON cr.id = cn.room_id
               WHERE cn.recipient_callsign = ? AND cn.is_read = 0
               ORDER BY cn.created_at DESC
               LIMIT ?''',
            (operator_callsign.upper(), limit)
        )
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


def mark_chat_notification_read(notification_id):
    """Mark a single chat notification as read."""
    conn = get_connection()
    try:
        conn.execute(
            'UPDATE chat_notifications SET is_read = 1 WHERE id = ?',
            (notification_id,)
        )
        conn.commit()
    finally:
        conn.close()


def mark_all_chat_notifications_read(operator_callsign):
    """Mark all chat notifications as read for an operator."""
    conn = get_connection()
    try:
        conn.execute(
            'UPDATE chat_notifications SET is_read = 1 WHERE recipient_callsign = ? AND is_read = 0',
            (operator_callsign.upper(),)
        )
        conn.commit()
    finally:
        conn.close()
