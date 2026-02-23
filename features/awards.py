"""
Award management functions.
"""
import logging
import sqlite3
from typing import List, Tuple, Optional

from core.database import get_db

logger = logging.getLogger(__name__)


def create_award(name: str, description: str = "", start_date: str = "", end_date: str = "",
                 image_data: Optional[bytes] = None, image_type: Optional[str] = None,
                 qrz_link: str = "") -> Tuple[bool, str, Optional[int]]:
    """Create a new award with optional image and QRZ link."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO awards (name, description, start_date, end_date, image_data, image_type, qrz_link)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (name, description, start_date, end_date, image_data, image_type, qrz_link))
            award_id = cursor.lastrowid
            return True, f"Award '{name}' created successfully", award_id
    except sqlite3.IntegrityError:
        return False, "Award name already exists", None
    except Exception:
        logger.exception("Error creating award")
        return False, "An unexpected error occurred. Please try again.", None


def get_all_awards() -> List[dict]:
    """Get all awards."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM awards
            ORDER BY created_at DESC
        ''')
        results = cursor.fetchall()
        return [dict(row) for row in results]


def get_active_awards() -> List[dict]:
    """Get only active awards."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT * FROM awards
            WHERE is_active = 1
            ORDER BY created_at DESC
        ''')
        results = cursor.fetchall()
        return [dict(row) for row in results]


def get_award_by_id(award_id: int) -> Optional[dict]:
    """Get a specific award by ID."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM awards WHERE id = ?', (award_id,))
        result = cursor.fetchone()
        return dict(result) if result else None


def update_award(award_id: int, name: str, description: str, start_date: str, end_date: str, qrz_link: str = "") -> Tuple[bool, str]:
    """Update an existing award (without changing image)."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE awards
                SET name = ?, description = ?, start_date = ?, end_date = ?, qrz_link = ?
                WHERE id = ?
            ''', (name, description, start_date, end_date, qrz_link, award_id))

            if cursor.rowcount == 0:
                return False, "Award not found"

            return True, f"Award '{name}' updated successfully"
    except sqlite3.IntegrityError:
        return False, "Award name already exists"
    except Exception:
        logger.exception("Error updating award")
        return False, "An unexpected error occurred. Please try again."


def update_award_image(award_id: int, image_data: Optional[bytes], image_type: Optional[str]) -> Tuple[bool, str]:
    """Update the image for an existing award."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE awards
                SET image_data = ?, image_type = ?
                WHERE id = ?
            ''', (image_data, image_type, award_id))

            if cursor.rowcount == 0:
                return False, "Award not found"

            return True, "Image updated successfully"
    except Exception:
        logger.exception("Error updating award image")
        return False, "An unexpected error occurred. Please try again."


def get_award_image(award_id: int) -> Optional[Tuple[bytes, str]]:
    """Get the image data and type for an award."""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT image_data, image_type FROM awards WHERE id = ?', (award_id,))
        result = cursor.fetchone()
        if result and result['image_data']:
            return result['image_data'], result['image_type']
        return None


def toggle_award_status(award_id: int) -> Tuple[bool, str]:
    """Toggle award active status."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT is_active, name FROM awards WHERE id = ?', (award_id,))
            award = cursor.fetchone()

            if not award:
                return False, "Award not found"

            new_status = 0 if award['is_active'] else 1
            cursor.execute('UPDATE awards SET is_active = ? WHERE id = ?', (new_status, award_id))

            status_text = "activated" if new_status else "deactivated"
            return True, f"Award '{award['name']}' {status_text}"
    except Exception:
        logger.exception("Error toggling award status")
        return False, "An unexpected error occurred. Please try again."


def delete_award(award_id: int) -> Tuple[bool, str]:
    """Delete an award and all its associated blocks, chat room and chat messages."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT name FROM awards WHERE id = ?', (award_id,))
        award = cursor.fetchone()

        if not award:
            conn.close()
            return False, "Award not found"

        # Delete all blocks associated with this award
        cursor.execute('DELETE FROM band_mode_blocks WHERE award_id = ?', (award_id,))

        # Delete the linked chat room and its messages/notifications
        cursor.execute('SELECT id FROM chat_rooms WHERE award_id = ?', (award_id,))
        room = cursor.fetchone()
        if room:
            room_id = room[0]
            cursor.execute('DELETE FROM chat_notifications WHERE room_id = ?', (room_id,))
            cursor.execute('DELETE FROM chat_messages WHERE room_id = ?', (room_id,))
            cursor.execute('DELETE FROM chat_rooms WHERE id = ?', (room_id,))

        # Delete the award
        cursor.execute('DELETE FROM awards WHERE id = ?', (award_id,))

        conn.commit()
        conn.close()
        return True, f"Award '{award['name']}' and all associated data deleted"
    except Exception as e:
        print(f"Error deleting award: {e}")
        return False, str(e)
