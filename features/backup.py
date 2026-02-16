"""
Database backup and restore functions.
"""
import logging
import sqlite3
import os
import shutil
import tempfile
from typing import Tuple

from core.database import get_connection, get_db, DATABASE_PATH

logger = logging.getLogger(__name__)


def get_database_backup() -> bytes:
    """
    Create a backup of the database and return it as bytes.

    Returns:
        bytes: The database file content
    """
    conn = get_connection()

    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_file:
        tmp_path = tmp_file.name

    try:
        backup_conn = sqlite3.connect(tmp_path)
        conn.backup(backup_conn)
        backup_conn.close()
        conn.close()

        with open(tmp_path, 'rb') as f:
            backup_data = f.read()

        return backup_data
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def restore_database_from_backup(backup_data: bytes) -> Tuple[bool, str]:
    """
    Restore the database from a backup.

    Args:
        backup_data: The database file content as bytes

    Returns:
        Tuple of (success, message)
    """
    if not backup_data.startswith(b'SQLite format 3'):
        return False, "Invalid backup file: Not a valid SQLite database"

    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_file:
        tmp_path = tmp_file.name
        tmp_file.write(backup_data)

    try:
        test_conn = sqlite3.connect(tmp_path)
        test_cursor = test_conn.cursor()

        test_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in test_cursor.fetchall()]

        required_tables = ['operators', 'awards', 'band_mode_blocks']
        missing_tables = [t for t in required_tables if t not in tables]

        if missing_tables:
            test_conn.close()
            return False, f"Invalid backup: Missing required tables: {', '.join(missing_tables)}"

        test_conn.close()

        current_backup_path = DATABASE_PATH + '.bak'
        if os.path.exists(DATABASE_PATH):
            shutil.copy2(DATABASE_PATH, current_backup_path)

        try:
            shutil.copy2(tmp_path, DATABASE_PATH)
            return True, "Database restored successfully"
        except Exception:
            logger.exception("Error restoring database")
            if os.path.exists(current_backup_path):
                shutil.copy2(current_backup_path, DATABASE_PATH)
            return False, "An unexpected error occurred while restoring. Previous database has been preserved."
        finally:
            if os.path.exists(current_backup_path):
                os.remove(current_backup_path)

    except sqlite3.DatabaseError:
        logger.exception("Invalid backup file")
        return False, "Invalid backup file: could not be read as a database"
    except Exception:
        logger.exception("Error validating backup")
        return False, "An unexpected error occurred while validating the backup."
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def get_database_info() -> dict:
    """
    Get information about the current database.

    Returns:
        dict with database statistics
    """
    with get_db() as conn:
        cursor = conn.cursor()

        info = {}

        cursor.execute("SELECT COUNT(*) FROM operators")
        info['operators_count'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM awards")
        info['awards_count'] = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM band_mode_blocks")
        info['blocks_count'] = cursor.fetchone()[0]

        if os.path.exists(DATABASE_PATH):
            info['file_size'] = os.path.getsize(DATABASE_PATH)
        else:
            info['file_size'] = 0

        return info
