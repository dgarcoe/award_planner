"""
Media management for public callsign content.
Files are stored on disk, metadata in database.
"""
import os
import uuid
import shutil
from typing import List, Optional, Tuple
from core.database import get_connection

# Media storage path - configurable via environment
MEDIA_PATH = os.getenv('MEDIA_PATH', '/app/media')


def ensure_media_directory(award_id: int) -> str:
    """Ensure media directory exists for an award and return the path."""
    award_dir = os.path.join(MEDIA_PATH, str(award_id))
    os.makedirs(award_dir, exist_ok=True)
    return award_dir


def save_media_file(
    award_id: int,
    filename: str,
    file_data: bytes,
    media_type: str,
    mime_type: str,
    description: str = ""
) -> Tuple[bool, str, Optional[int]]:
    """
    Save a media file to disk and record metadata in database.

    Args:
        award_id: ID of the special callsign (award)
        filename: Original filename
        file_data: File content as bytes
        media_type: 'image' or 'document'
        mime_type: MIME type (e.g., 'image/jpeg', 'application/pdf')
        description: Optional description

    Returns:
        Tuple of (success, message, media_id)
    """
    try:
        # Create unique filename to avoid conflicts
        ext = os.path.splitext(filename)[1].lower()
        unique_filename = f"{uuid.uuid4().hex}{ext}"

        # Ensure directory exists
        award_dir = ensure_media_directory(award_id)
        filepath = os.path.join(award_dir, unique_filename)

        # Write file to disk
        with open(filepath, 'wb') as f:
            f.write(file_data)

        # Store relative path in database
        relative_path = os.path.join(str(award_id), unique_filename)

        # Get current max display_order
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'SELECT COALESCE(MAX(display_order), 0) + 1 FROM callsign_media WHERE award_id = ?',
            (award_id,)
        )
        display_order = cursor.fetchone()[0]

        # Insert metadata
        cursor.execute('''
            INSERT INTO callsign_media
            (award_id, media_type, filename, filepath, mime_type, description, display_order)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (award_id, media_type, filename, relative_path, mime_type, description, display_order))

        media_id = cursor.lastrowid
        conn.commit()
        conn.close()

        return True, "Media uploaded successfully", media_id

    except Exception as e:
        return False, f"Error saving media: {str(e)}", None


def get_media_for_award(award_id: int, public_only: bool = False) -> List[dict]:
    """
    Get all media for a special callsign.

    Args:
        award_id: ID of the special callsign
        public_only: If True, only return public media

    Returns:
        List of media dictionaries
    """
    conn = get_connection()
    cursor = conn.cursor()

    if public_only:
        cursor.execute('''
            SELECT id, media_type, filename, filepath, mime_type, description, display_order
            FROM callsign_media
            WHERE award_id = ? AND is_public = 1
            ORDER BY display_order ASC
        ''', (award_id,))
    else:
        cursor.execute('''
            SELECT id, media_type, filename, filepath, mime_type, description, display_order, is_public
            FROM callsign_media
            WHERE award_id = ?
            ORDER BY display_order ASC
        ''', (award_id,))

    media = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return media


def get_media_file_path(media_id: int) -> Optional[str]:
    """Get the full file path for a media item."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT filepath FROM callsign_media WHERE id = ?', (media_id,))
    result = cursor.fetchone()
    conn.close()

    if result:
        return os.path.join(MEDIA_PATH, result['filepath'])
    return None


def get_media_by_id(media_id: int) -> Optional[dict]:
    """Get media metadata by ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, award_id, media_type, filename, filepath, mime_type, description, display_order, is_public
        FROM callsign_media
        WHERE id = ?
    ''', (media_id,))
    result = cursor.fetchone()
    conn.close()

    if result:
        return dict(result)
    return None


def read_media_file(media_id: int) -> Optional[Tuple[bytes, str, str]]:
    """
    Read media file content from disk.

    Returns:
        Tuple of (file_data, filename, mime_type) or None
    """
    media = get_media_by_id(media_id)
    if not media:
        return None

    filepath = os.path.join(MEDIA_PATH, media['filepath'])
    if not os.path.exists(filepath):
        return None

    with open(filepath, 'rb') as f:
        file_data = f.read()

    return file_data, media['filename'], media['mime_type']


def delete_media(media_id: int) -> Tuple[bool, str]:
    """
    Delete a media file from disk and database.

    Args:
        media_id: ID of the media to delete

    Returns:
        Tuple of (success, message)
    """
    try:
        media = get_media_by_id(media_id)
        if not media:
            return False, "Media not found"

        # Delete file from disk
        filepath = os.path.join(MEDIA_PATH, media['filepath'])
        if os.path.exists(filepath):
            os.remove(filepath)

        # Delete from database
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM callsign_media WHERE id = ?', (media_id,))
        conn.commit()
        conn.close()

        return True, "Media deleted successfully"

    except Exception as e:
        return False, f"Error deleting media: {str(e)}"


def update_media_order(media_id: int, new_order: int) -> Tuple[bool, str]:
    """Update the display order of a media item."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE callsign_media SET display_order = ? WHERE id = ?',
            (new_order, media_id)
        )
        conn.commit()
        conn.close()
        return True, "Order updated"
    except Exception as e:
        return False, f"Error updating order: {str(e)}"


def update_media_description(media_id: int, description: str) -> Tuple[bool, str]:
    """Update the description of a media item."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE callsign_media SET description = ? WHERE id = ?',
            (description, media_id)
        )
        conn.commit()
        conn.close()
        return True, "Description updated"
    except Exception as e:
        return False, f"Error updating description: {str(e)}"


def toggle_media_public(media_id: int) -> Tuple[bool, str]:
    """Toggle the public visibility of a media item."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            'UPDATE callsign_media SET is_public = NOT is_public WHERE id = ?',
            (media_id,)
        )
        conn.commit()
        conn.close()
        return True, "Visibility toggled"
    except Exception as e:
        return False, f"Error toggling visibility: {str(e)}"


def delete_all_media_for_award(award_id: int) -> Tuple[bool, str]:
    """
    Delete all media for a special callsign (used when deleting the callsign).

    Args:
        award_id: ID of the special callsign

    Returns:
        Tuple of (success, message)
    """
    try:
        # Delete directory and all files
        award_dir = os.path.join(MEDIA_PATH, str(award_id))
        if os.path.exists(award_dir):
            shutil.rmtree(award_dir)

        # Delete from database
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('DELETE FROM callsign_media WHERE award_id = ?', (award_id,))
        conn.commit()
        conn.close()

        return True, "All media deleted"

    except Exception as e:
        return False, f"Error deleting media: {str(e)}"
