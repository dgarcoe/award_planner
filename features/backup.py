"""
Database backup and restore functions.
"""
import sqlite3
import os
import shutil
import tempfile
from typing import Tuple

from core.database import get_connection, DATABASE_PATH


def get_database_backup() -> bytes:
    """
    Create a backup of the database and return it as bytes.

    Returns:
        bytes: The database file content
    """
    # Close any open connections by creating a backup using SQLite's backup API
    conn = get_connection()

    # Create a temporary file for the backup
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_file:
        tmp_path = tmp_file.name

    try:
        # Create backup connection
        backup_conn = sqlite3.connect(tmp_path)
        conn.backup(backup_conn)
        backup_conn.close()
        conn.close()

        # Read the backup file
        with open(tmp_path, 'rb') as f:
            backup_data = f.read()

        return backup_data
    finally:
        # Clean up temporary file
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
    # Validate the backup by checking if it's a valid SQLite database
    if not backup_data.startswith(b'SQLite format 3'):
        return False, "Invalid backup file: Not a valid SQLite database"

    # Create a temporary file to validate the backup
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_file:
        tmp_path = tmp_file.name
        tmp_file.write(backup_data)

    try:
        # Validate the backup by trying to open it and check for required tables
        test_conn = sqlite3.connect(tmp_path)
        test_cursor = test_conn.cursor()

        # Check for required tables
        test_cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in test_cursor.fetchall()]

        required_tables = ['operators', 'awards', 'band_mode_blocks']
        missing_tables = [t for t in required_tables if t not in tables]

        if missing_tables:
            test_conn.close()
            return False, f"Invalid backup: Missing required tables: {', '.join(missing_tables)}"

        test_conn.close()

        # Backup is valid, now restore it
        # First, create a backup of the current database
        current_backup_path = DATABASE_PATH + '.bak'
        if os.path.exists(DATABASE_PATH):
            shutil.copy2(DATABASE_PATH, current_backup_path)

        try:
            # Replace the current database with the backup
            shutil.copy2(tmp_path, DATABASE_PATH)
            return True, "Database restored successfully"
        except Exception as e:
            # Restore the original database if something went wrong
            if os.path.exists(current_backup_path):
                shutil.copy2(current_backup_path, DATABASE_PATH)
            return False, f"Error restoring database: {str(e)}"
        finally:
            # Clean up the backup of current database
            if os.path.exists(current_backup_path):
                os.remove(current_backup_path)

    except sqlite3.DatabaseError as e:
        return False, f"Invalid backup file: {str(e)}"
    except Exception as e:
        return False, f"Error validating backup: {str(e)}"
    finally:
        # Clean up temporary file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)


def get_database_info() -> dict:
    """
    Get information about the current database.

    Returns:
        dict with database statistics
    """
    conn = get_connection()
    cursor = conn.cursor()

    info = {}

    # Get table counts
    cursor.execute("SELECT COUNT(*) FROM operators")
    info['operators_count'] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM awards")
    info['awards_count'] = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM band_mode_blocks")
    info['blocks_count'] = cursor.fetchone()[0]

    # Get database file size
    if os.path.exists(DATABASE_PATH):
        info['file_size'] = os.path.getsize(DATABASE_PATH)
    else:
        info['file_size'] = 0

    conn.close()
    return info
