"""
Announcement management functions.
"""
import logging
from typing import List, Tuple

from core.database import get_db

logger = logging.getLogger(__name__)


def create_announcement(title: str, content: str, created_by: str) -> Tuple[bool, str]:
    """
    Create a new announcement.

    Args:
        title: Announcement title
        content: Announcement content
        created_by: Callsign of the admin creating the announcement

    Returns:
        Tuple of (success, message)
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO announcements (title, content, created_by)
                VALUES (?, ?, ?)
            ''', (title, content, created_by))
            return True, "Announcement created successfully"
    except Exception:
        logger.exception("Error creating announcement")
        return False, "An unexpected error occurred. Please try again."


def get_all_announcements() -> List[dict]:
    """
    Get all announcements (for admin view).

    Returns:
        List of announcement dictionaries
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, title, content, created_by, created_at, is_active
            FROM announcements
            ORDER BY created_at DESC
        ''')
        return [dict(row) for row in cursor.fetchall()]


def get_active_announcements() -> List[dict]:
    """
    Get only active announcements.

    Returns:
        List of active announcement dictionaries
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, title, content, created_by, created_at, is_active
            FROM announcements
            WHERE is_active = 1
            ORDER BY created_at DESC
        ''')
        return [dict(row) for row in cursor.fetchall()]


def toggle_announcement_status(announcement_id: int) -> Tuple[bool, str]:
    """
    Toggle announcement active status.

    Args:
        announcement_id: ID of the announcement to toggle

    Returns:
        Tuple of (success, message)
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE announcements
                SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END
                WHERE id = ?
            ''', (announcement_id,))

            if cursor.rowcount == 0:
                return False, "Announcement not found"

            return True, "Announcement status updated"
    except Exception:
        logger.exception("Error updating announcement")
        return False, "An unexpected error occurred. Please try again."


def delete_announcement(announcement_id: int) -> Tuple[bool, str]:
    """
    Delete an announcement and its read records.

    Args:
        announcement_id: ID of the announcement to delete

    Returns:
        Tuple of (success, message)
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            # Delete read records first (foreign key)
            cursor.execute('DELETE FROM announcement_reads WHERE announcement_id = ?', (announcement_id,))
            # Delete the announcement
            cursor.execute('DELETE FROM announcements WHERE id = ?', (announcement_id,))

            if cursor.rowcount == 0:
                return False, "Announcement not found"

            return True, "Announcement deleted successfully"
    except Exception:
        logger.exception("Error deleting announcement")
        return False, "An unexpected error occurred. Please try again."


def mark_announcement_read(announcement_id: int, operator_callsign: str) -> Tuple[bool, str]:
    """
    Mark an announcement as read by an operator.

    Args:
        announcement_id: ID of the announcement
        operator_callsign: Callsign of the operator

    Returns:
        Tuple of (success, message)
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR IGNORE INTO announcement_reads (announcement_id, operator_callsign)
                VALUES (?, ?)
            ''', (announcement_id, operator_callsign))
            return True, "Announcement marked as read"
    except Exception:
        logger.exception("Error marking announcement as read")
        return False, "An unexpected error occurred. Please try again."


def mark_all_announcements_read(operator_callsign: str) -> Tuple[bool, str]:
    """
    Mark all active announcements as read for an operator.

    Args:
        operator_callsign: Callsign of the operator

    Returns:
        Tuple of (success, message)
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            # Get all active announcement IDs not yet read by this operator
            cursor.execute('''
                SELECT id FROM announcements
                WHERE is_active = 1 AND id NOT IN (
                    SELECT announcement_id FROM announcement_reads
                    WHERE operator_callsign = ?
                )
            ''', (operator_callsign,))

            unread_ids = [row[0] for row in cursor.fetchall()]

            # Mark each as read
            for ann_id in unread_ids:
                cursor.execute('''
                    INSERT OR IGNORE INTO announcement_reads (announcement_id, operator_callsign)
                    VALUES (?, ?)
                ''', (ann_id, operator_callsign))

            return True, f"Marked {len(unread_ids)} announcements as read"
    except Exception:
        logger.exception("Error marking announcements as read")
        return False, "An unexpected error occurred. Please try again."


def get_unread_announcement_count(operator_callsign: str) -> int:
    """
    Get count of unread active announcements for an operator.

    Args:
        operator_callsign: Callsign of the operator

    Returns:
        Number of unread announcements
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT COUNT(*) FROM announcements
            WHERE is_active = 1 AND id NOT IN (
                SELECT announcement_id FROM announcement_reads
                WHERE operator_callsign = ?
            )
        ''', (operator_callsign,))
        return cursor.fetchone()[0]


def get_unread_announcements(operator_callsign: str) -> List[dict]:
    """
    Get only unread active announcements for an operator.

    Args:
        operator_callsign: Callsign of the operator

    Returns:
        List of unread announcement dictionaries
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, title, content, created_by, created_at
            FROM announcements
            WHERE is_active = 1 AND id NOT IN (
                SELECT announcement_id FROM announcement_reads
                WHERE operator_callsign = ?
            )
            ORDER BY created_at DESC
        ''', (operator_callsign,))
        return [dict(row) for row in cursor.fetchall()]


def get_announcements_with_read_status(operator_callsign: str) -> List[dict]:
    """
    Get active announcements with read status for an operator.

    Args:
        operator_callsign: Callsign of the operator

    Returns:
        List of announcement dictionaries with 'is_read' field
    """
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT
                a.id, a.title, a.content, a.created_by, a.created_at, a.is_active,
                CASE WHEN ar.id IS NOT NULL THEN 1 ELSE 0 END as is_read
            FROM announcements a
            LEFT JOIN announcement_reads ar
                ON a.id = ar.announcement_id AND ar.operator_callsign = ?
            WHERE a.is_active = 1
            ORDER BY a.created_at DESC
        ''', (operator_callsign,))
        return [dict(row) for row in cursor.fetchall()]
