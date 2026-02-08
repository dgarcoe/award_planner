import sqlite3
from datetime import datetime
from typing import List, Tuple, Optional
import os
import bcrypt

DATABASE_PATH = os.getenv('DATABASE_PATH', 'ham_coordinator.db')

def get_connection():
    """Create and return a database connection."""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initialize the database with required tables."""
    conn = get_connection()
    cursor = conn.cursor()

    # Create operators table with is_admin field
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS operators (
            callsign TEXT PRIMARY KEY,
            operator_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Check if is_admin column exists, if not add it (migration)
    cursor.execute("PRAGMA table_info(operators)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'is_admin' not in columns:
        cursor.execute('ALTER TABLE operators ADD COLUMN is_admin INTEGER DEFAULT 0')

    # Create awards table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS awards (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            start_date TEXT,
            end_date TEXT,
            is_active INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Create band_mode_blocks table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS band_mode_blocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operator_callsign TEXT NOT NULL,
            award_id INTEGER NOT NULL,
            band TEXT NOT NULL,
            mode TEXT NOT NULL,
            blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (operator_callsign) REFERENCES operators (callsign),
            FOREIGN KEY (award_id) REFERENCES awards (id),
            UNIQUE(award_id, band, mode)
        )
    ''')

    # Migration: Check if award_id column exists in band_mode_blocks
    cursor.execute("PRAGMA table_info(band_mode_blocks)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'award_id' not in columns:
        # Need to recreate table since SQLite doesn't support modifying constraints
        # First, check if there's a default award
        cursor.execute('SELECT id FROM awards WHERE name = ?', ('Default Award',))
        default_award = cursor.fetchone()

        if not default_award:
            # Create default award
            cursor.execute('''
                INSERT INTO awards (name, description, is_active)
                VALUES (?, ?, 1)
            ''', ('Default Award', 'Auto-created award for existing blocks'))
            default_award_id = cursor.lastrowid
        else:
            default_award_id = default_award[0]

        # Backup existing blocks
        cursor.execute('SELECT * FROM band_mode_blocks')
        existing_blocks = cursor.fetchall()

        # Drop and recreate table with new schema
        cursor.execute('DROP TABLE band_mode_blocks')
        cursor.execute('''
            CREATE TABLE band_mode_blocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                operator_callsign TEXT NOT NULL,
                award_id INTEGER NOT NULL,
                band TEXT NOT NULL,
                mode TEXT NOT NULL,
                blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (operator_callsign) REFERENCES operators (callsign),
                FOREIGN KEY (award_id) REFERENCES awards (id),
                UNIQUE(award_id, band, mode)
            )
        ''')

        # Restore blocks with default award_id
        for block in existing_blocks:
            cursor.execute('''
                INSERT INTO band_mode_blocks (id, operator_callsign, award_id, band, mode, blocked_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (block['id'], block['operator_callsign'], default_award_id,
                  block['band'], block['mode'], block['blocked_at']))

    # Create announcements table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS announcements (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_by TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active INTEGER DEFAULT 1,
            FOREIGN KEY (created_by) REFERENCES operators (callsign)
        )
    ''')

    # Create announcement_reads table to track read status per user
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS announcement_reads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            announcement_id INTEGER NOT NULL,
            operator_callsign TEXT NOT NULL,
            read_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (announcement_id) REFERENCES announcements (id),
            FOREIGN KEY (operator_callsign) REFERENCES operators (callsign),
            UNIQUE(announcement_id, operator_callsign)
        )
    ''')

    conn.commit()
    conn.close()

def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')

def verify_password(password: str, password_hash: str) -> bool:
    """Verify a password against its hash."""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), password_hash.encode('utf-8'))
    except Exception as e:
        print(f"Error verifying password: {e}")
        return False

def create_operator(callsign: str, operator_name: str, password: str, is_admin: bool = False) -> Tuple[bool, str]:
    """Create a new operator account (admin only)."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        password_hash = hash_password(password)
        cursor.execute('''
            INSERT INTO operators (callsign, operator_name, password_hash, is_admin)
            VALUES (?, ?, ?, ?)
        ''', (callsign.upper(), operator_name, password_hash, 1 if is_admin else 0))

        conn.commit()
        conn.close()
        admin_text = " (admin)" if is_admin else ""
        return True, f"Operator {callsign} created successfully{admin_text}"
    except sqlite3.IntegrityError:
        return False, "Callsign already exists"
    except Exception as e:
        print(f"Error creating operator: {e}")
        return False, str(e)

def authenticate_operator(callsign: str, password: str) -> Tuple[bool, str, Optional[dict]]:
    """Authenticate an operator."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM operators WHERE callsign = ?', (callsign.upper(),))
        operator = cursor.fetchone()
        conn.close()

        if not operator:
            return False, "Invalid callsign or password", None

        if not verify_password(password, operator['password_hash']):
            return False, "Invalid callsign or password", None

        return True, "Authentication successful", dict(operator)
    except Exception as e:
        print(f"Error authenticating operator: {e}")
        return False, str(e), None

def get_operator(callsign: str) -> Optional[dict]:
    """Get operator information."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM operators WHERE callsign = ?', (callsign.upper(),))
    result = cursor.fetchone()
    conn.close()
    if result:
        return dict(result)
    return None

def get_all_operators() -> List[dict]:
    """Get all operators."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT callsign, operator_name, is_admin, created_at
        FROM operators
        ORDER BY created_at DESC
    ''')
    results = cursor.fetchall()
    conn.close()
    return [dict(row) for row in results]

def promote_to_admin(callsign: str) -> Tuple[bool, str]:
    """Promote an operator to admin."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT callsign, is_admin FROM operators WHERE callsign = ?', (callsign.upper(),))
        operator = cursor.fetchone()

        if not operator:
            conn.close()
            return False, "Operator not found"

        if operator['is_admin']:
            conn.close()
            return False, f"{callsign} is already an admin"

        cursor.execute('UPDATE operators SET is_admin = 1 WHERE callsign = ?', (callsign.upper(),))
        conn.commit()
        conn.close()
        return True, f"{callsign} promoted to admin successfully"
    except Exception as e:
        print(f"Error promoting operator: {e}")
        return False, str(e)

def demote_from_admin(callsign: str) -> Tuple[bool, str]:
    """Demote an operator from admin."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT callsign, is_admin FROM operators WHERE callsign = ?', (callsign.upper(),))
        operator = cursor.fetchone()

        if not operator:
            conn.close()
            return False, "Operator not found"

        if not operator['is_admin']:
            conn.close()
            return False, f"{callsign} is not an admin"

        cursor.execute('UPDATE operators SET is_admin = 0 WHERE callsign = ?', (callsign.upper(),))
        conn.commit()
        conn.close()
        return True, f"{callsign} demoted from admin successfully"
    except Exception as e:
        print(f"Error demoting operator: {e}")
        return False, str(e)

def delete_operator(callsign: str) -> Tuple[bool, str]:
    """Delete an operator and their blocks."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Verify the operator exists
        cursor.execute('SELECT callsign FROM operators WHERE callsign = ?', (callsign.upper(),))
        operator = cursor.fetchone()

        if not operator:
            conn.close()
            return False, "Operator not found"

        # Delete the operator's blocks
        cursor.execute('DELETE FROM band_mode_blocks WHERE operator_callsign = ?', (callsign.upper(),))

        # Delete the operator
        cursor.execute('DELETE FROM operators WHERE callsign = ?', (callsign.upper(),))

        conn.commit()
        conn.close()
        return True, f"Operator {callsign} deleted successfully"
    except Exception as e:
        print(f"Error deleting operator: {e}")
        return False, str(e)

def change_password(callsign: str, old_password: str, new_password: str) -> Tuple[bool, str]:
    """Change operator's password."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT password_hash FROM operators WHERE callsign = ?', (callsign.upper(),))
        operator = cursor.fetchone()

        if not operator:
            conn.close()
            return False, "Operator not found"

        if not verify_password(old_password, operator['password_hash']):
            conn.close()
            return False, "Invalid current password"

        new_password_hash = hash_password(new_password)
        cursor.execute('UPDATE operators SET password_hash = ? WHERE callsign = ?',
                      (new_password_hash, callsign.upper()))

        conn.commit()
        conn.close()
        return True, "Password changed successfully"
    except Exception as e:
        print(f"Error changing password: {e}")
        return False, str(e)

def admin_reset_password(callsign: str, new_password: str) -> Tuple[bool, str]:
    """Admin reset of operator's password."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Verify operator exists
        cursor.execute('SELECT callsign FROM operators WHERE callsign = ?', (callsign.upper(),))
        operator = cursor.fetchone()

        if not operator:
            conn.close()
            return False, "Operator not found"

        new_password_hash = hash_password(new_password)
        cursor.execute('UPDATE operators SET password_hash = ? WHERE callsign = ?',
                      (new_password_hash, callsign.upper()))

        conn.commit()
        conn.close()
        return True, f"Password reset successfully for {callsign}"
    except Exception as e:
        print(f"Error resetting password: {e}")
        return False, str(e)

def block_band_mode(operator_callsign: str, band: str, mode: str, award_id: int) -> Tuple[bool, str]:
    """Block a band/mode combination for an operator within an award. One block per operator per award."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Check if this band/mode is already blocked by someone else in this award
        cursor.execute('''
            SELECT operator_callsign FROM band_mode_blocks
            WHERE band = ? AND mode = ? AND award_id = ?
        ''', (band, mode, award_id))
        existing = cursor.fetchone()

        if existing:
            conn.close()
            return False, f"Band {band} / Mode {mode} is already blocked by {existing['operator_callsign']}"

        # Check if operator already has a block in this award (one block per operator per award rule)
        cursor.execute('''
            SELECT band, mode FROM band_mode_blocks
            WHERE operator_callsign = ? AND award_id = ?
        ''', (operator_callsign.upper(), award_id))
        existing_block = cursor.fetchone()

        if existing_block:
            # Auto-unblock the previous block
            cursor.execute('''
                DELETE FROM band_mode_blocks
                WHERE operator_callsign = ? AND award_id = ?
            ''', (operator_callsign.upper(), award_id))

        # Block the new band/mode
        cursor.execute('''
            INSERT INTO band_mode_blocks (operator_callsign, award_id, band, mode)
            VALUES (?, ?, ?, ?)
        ''', (operator_callsign.upper(), award_id, band, mode))

        conn.commit()
        conn.close()

        if existing_block:
            return True, f"Successfully blocked (previous block {existing_block['band']}/{existing_block['mode']} released)"
        return True, "Successfully blocked"
    except Exception as e:
        print(f"Error blocking band/mode: {e}")
        return False, str(e)

def unblock_band_mode(operator_callsign: str, band: str, mode: str, award_id: int) -> Tuple[bool, str]:
    """Unblock a band/mode combination for a specific award."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Check if blocked by this operator in this award
        cursor.execute('''
            SELECT operator_callsign FROM band_mode_blocks
            WHERE band = ? AND mode = ? AND award_id = ?
        ''', (band, mode, award_id))
        existing = cursor.fetchone()

        if not existing:
            conn.close()
            return False, f"Band {band} / Mode {mode} is not blocked"

        if existing['operator_callsign'] != operator_callsign.upper():
            conn.close()
            return False, f"Band {band} / Mode {mode} is blocked by {existing['operator_callsign']}, not by you"

        # Unblock the band/mode
        cursor.execute('''
            DELETE FROM band_mode_blocks
            WHERE band = ? AND mode = ? AND operator_callsign = ? AND award_id = ?
        ''', (band, mode, operator_callsign.upper(), award_id))

        conn.commit()
        conn.close()
        return True, "Successfully unblocked"
    except Exception as e:
        print(f"Error unblocking band/mode: {e}")
        return False, str(e)

def unblock_all_for_operator(operator_callsign: str, award_id: Optional[int] = None) -> Tuple[bool, str, int]:
    """Unblock all band/mode combinations for an operator, optionally for a specific award."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Get count of blocks before deleting
        if award_id:
            cursor.execute('''
                SELECT COUNT(*) as count FROM band_mode_blocks
                WHERE operator_callsign = ? AND award_id = ?
            ''', (operator_callsign.upper(), award_id))
        else:
            cursor.execute('''
                SELECT COUNT(*) as count FROM band_mode_blocks
                WHERE operator_callsign = ?
            ''', (operator_callsign.upper(),))
        count = cursor.fetchone()['count']

        if count == 0:
            conn.close()
            return True, "No blocks to release", 0

        # Delete blocks for this operator
        if award_id:
            cursor.execute('''
                DELETE FROM band_mode_blocks
                WHERE operator_callsign = ? AND award_id = ?
            ''', (operator_callsign.upper(), award_id))
        else:
            cursor.execute('''
                DELETE FROM band_mode_blocks
                WHERE operator_callsign = ?
            ''', (operator_callsign.upper(),))

        conn.commit()
        conn.close()
        return True, f"Released {count} block(s)", count
    except Exception as e:
        print(f"Error unblocking all: {e}")
        return False, str(e), 0

def admin_unblock_band_mode(band: str, mode: str, award_id: int) -> Tuple[bool, str]:
    """Admin unblock any band/mode combination for a specific award."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Check if blocked
        cursor.execute('''
            SELECT operator_callsign FROM band_mode_blocks
            WHERE band = ? AND mode = ? AND award_id = ?
        ''', (band, mode, award_id))
        existing = cursor.fetchone()

        if not existing:
            conn.close()
            return False, f"Band {band} / Mode {mode} is not blocked"

        # Unblock the band/mode
        cursor.execute('''
            DELETE FROM band_mode_blocks
            WHERE band = ? AND mode = ? AND award_id = ?
        ''', (band, mode, award_id))

        conn.commit()
        conn.close()
        return True, f"Successfully unblocked {band}/{mode} (was blocked by {existing['operator_callsign']})"
    except Exception as e:
        print(f"Error admin unblocking band/mode: {e}")
        return False, str(e)

def get_all_blocks(award_id: Optional[int] = None) -> List[dict]:
    """Get all current band/mode blocks, optionally filtered by award."""
    conn = get_connection()
    cursor = conn.cursor()
    if award_id:
        cursor.execute('''
            SELECT b.*, o.operator_name
            FROM band_mode_blocks b
            JOIN operators o ON b.operator_callsign = o.callsign
            WHERE b.award_id = ?
            ORDER BY b.band, b.mode
        ''', (award_id,))
    else:
        cursor.execute('''
            SELECT b.*, o.operator_name
            FROM band_mode_blocks b
            JOIN operators o ON b.operator_callsign = o.callsign
            ORDER BY b.band, b.mode
        ''')
    results = cursor.fetchall()
    conn.close()
    return [dict(row) for row in results]

def get_operator_blocks(operator_callsign: str, award_id: Optional[int] = None) -> List[dict]:
    """Get all blocks for a specific operator, optionally filtered by award."""
    conn = get_connection()
    cursor = conn.cursor()
    if award_id:
        cursor.execute('''
            SELECT * FROM band_mode_blocks
            WHERE operator_callsign = ? AND award_id = ?
            ORDER BY band, mode
        ''', (operator_callsign.upper(), award_id))
    else:
        cursor.execute('''
            SELECT * FROM band_mode_blocks
            WHERE operator_callsign = ?
            ORDER BY band, mode
        ''', (operator_callsign.upper(),))
    results = cursor.fetchall()
    conn.close()
    return [dict(row) for row in results]

# Award Management Functions

def create_award(name: str, description: str = "", start_date: str = "", end_date: str = "") -> Tuple[bool, str]:
    """Create a new award."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            INSERT INTO awards (name, description, start_date, end_date)
            VALUES (?, ?, ?, ?)
        ''', (name, description, start_date, end_date))

        conn.commit()
        conn.close()
        return True, f"Award '{name}' created successfully"
    except sqlite3.IntegrityError:
        return False, "Award name already exists"
    except Exception as e:
        print(f"Error creating award: {e}")
        return False, str(e)

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
    """Update an existing award."""
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


# Database Backup and Restore Functions

def get_database_backup() -> bytes:
    """
    Create a backup of the database and return it as bytes.

    Returns:
        bytes: The database file content
    """
    import shutil
    import tempfile

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
    import tempfile
    import shutil

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


# ============================================
# Announcement Functions
# ============================================

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
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO announcements (title, content, created_by)
            VALUES (?, ?, ?)
        ''', (title, content, created_by))
        conn.commit()
        return True, "Announcement created successfully"
    except Exception as e:
        return False, f"Error creating announcement: {str(e)}"
    finally:
        conn.close()


def get_all_announcements() -> List[dict]:
    """
    Get all announcements (for admin view).

    Returns:
        List of announcement dictionaries
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, title, content, created_by, created_at, is_active
        FROM announcements
        ORDER BY created_at DESC
    ''')

    announcements = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return announcements


def get_active_announcements() -> List[dict]:
    """
    Get only active announcements.

    Returns:
        List of active announcement dictionaries
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, title, content, created_by, created_at, is_active
        FROM announcements
        WHERE is_active = 1
        ORDER BY created_at DESC
    ''')

    announcements = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return announcements


def toggle_announcement_status(announcement_id: int) -> Tuple[bool, str]:
    """
    Toggle announcement active status.

    Args:
        announcement_id: ID of the announcement to toggle

    Returns:
        Tuple of (success, message)
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            UPDATE announcements
            SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END
            WHERE id = ?
        ''', (announcement_id,))

        if cursor.rowcount == 0:
            return False, "Announcement not found"

        conn.commit()
        return True, "Announcement status updated"
    except Exception as e:
        return False, f"Error updating announcement: {str(e)}"
    finally:
        conn.close()


def delete_announcement(announcement_id: int) -> Tuple[bool, str]:
    """
    Delete an announcement and its read records.

    Args:
        announcement_id: ID of the announcement to delete

    Returns:
        Tuple of (success, message)
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Delete read records first (foreign key)
        cursor.execute('DELETE FROM announcement_reads WHERE announcement_id = ?', (announcement_id,))

        # Delete the announcement
        cursor.execute('DELETE FROM announcements WHERE id = ?', (announcement_id,))

        if cursor.rowcount == 0:
            return False, "Announcement not found"

        conn.commit()
        return True, "Announcement deleted successfully"
    except Exception as e:
        return False, f"Error deleting announcement: {str(e)}"
    finally:
        conn.close()


def mark_announcement_read(announcement_id: int, operator_callsign: str) -> Tuple[bool, str]:
    """
    Mark an announcement as read by an operator.

    Args:
        announcement_id: ID of the announcement
        operator_callsign: Callsign of the operator

    Returns:
        Tuple of (success, message)
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT OR IGNORE INTO announcement_reads (announcement_id, operator_callsign)
            VALUES (?, ?)
        ''', (announcement_id, operator_callsign))
        conn.commit()
        return True, "Announcement marked as read"
    except Exception as e:
        return False, f"Error marking announcement as read: {str(e)}"
    finally:
        conn.close()


def mark_all_announcements_read(operator_callsign: str) -> Tuple[bool, str]:
    """
    Mark all active announcements as read for an operator.

    Args:
        operator_callsign: Callsign of the operator

    Returns:
        Tuple of (success, message)
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
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

        conn.commit()
        return True, f"Marked {len(unread_ids)} announcements as read"
    except Exception as e:
        return False, f"Error marking announcements as read: {str(e)}"
    finally:
        conn.close()


def get_unread_announcement_count(operator_callsign: str) -> int:
    """
    Get count of unread active announcements for an operator.

    Args:
        operator_callsign: Callsign of the operator

    Returns:
        Number of unread announcements
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT COUNT(*) FROM announcements
        WHERE is_active = 1 AND id NOT IN (
            SELECT announcement_id FROM announcement_reads
            WHERE operator_callsign = ?
        )
    ''', (operator_callsign,))

    count = cursor.fetchone()[0]
    conn.close()
    return count


def get_announcements_with_read_status(operator_callsign: str) -> List[dict]:
    """
    Get active announcements with read status for an operator.

    Args:
        operator_callsign: Callsign of the operator

    Returns:
        List of announcement dictionaries with 'is_read' field
    """
    conn = get_connection()
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

    announcements = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return announcements
