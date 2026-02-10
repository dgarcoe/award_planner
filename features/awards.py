"""
Award management functions.
"""
import sqlite3
from typing import List, Tuple, Optional

from core.database import get_connection


def create_award(name: str, description: str = "", start_date: str = "", end_date: str = "",
                 image_data: Optional[bytes] = None, image_type: Optional[str] = None) -> Tuple[bool, str, Optional[int]]:
    """Create a new award with optional image."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO awards (name, description, start_date, end_date, image_data, image_type)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, description, start_date, end_date, image_data, image_type))

        award_id = cursor.lastrowid
        conn.commit()
        conn.close()
        return True, f"Award '{name}' created successfully", award_id
    except sqlite3.IntegrityError:
        return False, "Award name already exists", None
    except Exception as e:
        print(f"Error creating award: {e}")
        return False, str(e), None


def get_all_awards() -> List[dict]:
    """Get all awards."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM awards
        ORDER BY created_at DESC
    ''')
    results = cursor.fetchall()
    conn.close()
    return [dict(row) for row in results]


def get_active_awards() -> List[dict]:
    """Get only active awards."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM awards
        WHERE is_active = 1
        ORDER BY created_at DESC
    ''')
    results = cursor.fetchall()
    conn.close()
    return [dict(row) for row in results]


def get_award_by_id(award_id: int) -> Optional[dict]:
    """Get a specific award by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM awards WHERE id = ?', (award_id,))
    result = cursor.fetchone()
    conn.close()
    return dict(result) if result else None


def update_award(award_id: int, name: str, description: str, start_date: str, end_date: str) -> Tuple[bool, str]:
    """Update an existing award (without changing image)."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE awards
            SET name = ?, description = ?, start_date = ?, end_date = ?
            WHERE id = ?
        ''', (name, description, start_date, end_date, award_id))

        if cursor.rowcount == 0:
            conn.close()
            return False, "Award not found"

        conn.commit()
        conn.close()
        return True, f"Award '{name}' updated successfully"
    except sqlite3.IntegrityError:
        return False, "Award name already exists"
    except Exception as e:
        print(f"Error updating award: {e}")
        return False, str(e)


def update_award_image(award_id: int, image_data: Optional[bytes], image_type: Optional[str]) -> Tuple[bool, str]:
    """Update the image for an existing award."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE awards
            SET image_data = ?, image_type = ?
            WHERE id = ?
        ''', (image_data, image_type, award_id))

        if cursor.rowcount == 0:
            conn.close()
            return False, "Award not found"

        conn.commit()
        conn.close()
        return True, "Image updated successfully"
    except Exception as e:
        print(f"Error updating award image: {e}")
        return False, str(e)


def get_award_image(award_id: int) -> Optional[Tuple[bytes, str]]:
    """Get the image data and type for an award."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT image_data, image_type FROM awards WHERE id = ?', (award_id,))
    result = cursor.fetchone()
    conn.close()
    if result and result['image_data']:
        return result['image_data'], result['image_type']
    return None


def toggle_award_status(award_id: int) -> Tuple[bool, str]:
    """Toggle award active status."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT is_active, name FROM awards WHERE id = ?', (award_id,))
        award = cursor.fetchone()

        if not award:
            conn.close()
            return False, "Award not found"

        new_status = 0 if award['is_active'] else 1
        cursor.execute('UPDATE awards SET is_active = ? WHERE id = ?', (new_status, award_id))

        conn.commit()
        conn.close()

        status_text = "activated" if new_status else "deactivated"
        return True, f"Award '{award['name']}' {status_text}"
    except Exception as e:
        print(f"Error toggling award status: {e}")
        return False, str(e)


def delete_award(award_id: int) -> Tuple[bool, str]:
    """Delete an award and all its associated blocks."""
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

        # Delete the award
        cursor.execute('DELETE FROM awards WHERE id = ?', (award_id,))

        conn.commit()
        conn.close()
        return True, f"Award '{award['name']}' and all associated blocks deleted"
    except Exception as e:
        print(f"Error deleting award: {e}")
        return False, str(e)
