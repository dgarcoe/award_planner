"""
Chat feature module - database functions for chat message persistence and retrieval.
"""

from core.database import get_connection


def save_chat_message(award_id, callsign, message, source='app',
                      reply_to_id=None, reply_to_callsign=None, reply_to_text=None):
    """
    Save a chat message to the database.

    Args:
        award_id: Award ID (None for global chat)
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
               (award_id, operator_callsign, message, source,
                reply_to_id, reply_to_callsign, reply_to_text)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (award_id, callsign, message, source,
             reply_to_id, reply_to_callsign, reply_to_text)
        )
        conn.commit()
        return cursor.lastrowid
    finally:
        conn.close()


def get_chat_history(award_id, limit=100):
    """
    Retrieve recent chat messages for a specific award.

    Args:
        award_id: Award ID to get messages for
        limit: Maximum number of messages to return

    Returns:
        list: Messages as dicts with keys: id, award_id, operator_callsign, message, source, created_at
    """
    conn = get_connection()
    try:
        cursor = conn.execute(
            '''SELECT id, award_id, operator_callsign, message, source, created_at,
                      reply_to_id, reply_to_callsign, reply_to_text
               FROM chat_messages
               WHERE award_id = ?
               ORDER BY created_at DESC
               LIMIT ?''',
            (award_id, limit)
        )
        rows = cursor.fetchall()
        # Return in chronological order (oldest first)
        return [dict(row) for row in reversed(rows)]
    finally:
        conn.close()


def get_chat_history_global(limit=100):
    """
    Retrieve recent chat messages across all awards.

    Args:
        limit: Maximum number of messages to return

    Returns:
        list: Messages as dicts
    """
    conn = get_connection()
    try:
        cursor = conn.execute(
            '''SELECT id, award_id, operator_callsign, message, source, created_at,
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
    Return chat statistics: total count, per-award breakdown with oldest/newest dates.

    Returns:
        dict with keys:
            total: int
            per_award: list of dicts (award_id, count, oldest, newest)
    """
    conn = get_connection()
    try:
        cursor = conn.execute('SELECT COUNT(*) FROM chat_messages')
        total = cursor.fetchone()[0]

        cursor = conn.execute(
            '''SELECT cm.award_id,
                      a.name AS award_name,
                      COUNT(*) AS message_count,
                      MIN(cm.created_at) AS oldest,
                      MAX(cm.created_at) AS newest
               FROM chat_messages cm
               LEFT JOIN awards a ON a.id = cm.award_id
               GROUP BY cm.award_id
               ORDER BY message_count DESC'''
        )
        per_award = [dict(row) for row in cursor.fetchall()]
        return {'total': total, 'per_award': per_award}
    finally:
        conn.close()


def get_chat_stats_by_user():
    """
    Return message counts grouped by operator callsign across all awards.

    Returns:
        list of dicts (operator_callsign, message_count, oldest, newest)
    """
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


def delete_chat_messages_by_award(award_id):
    """Delete all chat messages for a specific award. Returns number of rows deleted."""
    conn = get_connection()
    try:
        cursor = conn.execute(
            'DELETE FROM chat_messages WHERE award_id = ?', (award_id,)
        )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()


def delete_chat_messages_older_than(days, award_id=None):
    """
    Delete messages older than `days` days, optionally filtered by award.
    Returns number of rows deleted.
    """
    conn = get_connection()
    try:
        if award_id is not None:
            cursor = conn.execute(
                '''DELETE FROM chat_messages
                   WHERE created_at < datetime('now', ? || ' days')
                   AND award_id = ?''',
                (f'-{days}', award_id)
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
            '''SELECT cn.id, cn.sender_callsign, cn.award_id, cn.message_preview,
                      cn.created_at, a.name AS award_name
               FROM chat_notifications cn
               LEFT JOIN awards a ON a.id = cn.award_id
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
