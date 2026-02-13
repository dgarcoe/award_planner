"""
Chat feature module - database functions for chat message persistence and retrieval.
"""

from core.database import get_connection


def save_chat_message(award_id, callsign, message, source='app'):
    """
    Save a chat message to the database.

    Args:
        award_id: Award ID (None for global chat)
        callsign: Operator callsign who sent the message
        message: Message text
        source: Message source ('app' or 'telegram')

    Returns:
        int: ID of the inserted message
    """
    conn = get_connection()
    try:
        cursor = conn.execute(
            'INSERT INTO chat_messages (award_id, operator_callsign, message, source) VALUES (?, ?, ?, ?)',
            (award_id, callsign, message, source)
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
            '''SELECT id, award_id, operator_callsign, message, source, created_at
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
            '''SELECT id, award_id, operator_callsign, message, source, created_at
               FROM chat_messages
               ORDER BY created_at DESC
               LIMIT ?''',
            (limit,)
        )
        rows = cursor.fetchall()
        return [dict(row) for row in reversed(rows)]
    finally:
        conn.close()
