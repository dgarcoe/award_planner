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

    # Create band_mode_blocks table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS band_mode_blocks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operator_callsign TEXT NOT NULL,
            band TEXT NOT NULL,
            mode TEXT NOT NULL,
            blocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (operator_callsign) REFERENCES operators (callsign),
            UNIQUE(band, mode)
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

def block_band_mode(operator_callsign: str, band: str, mode: str) -> Tuple[bool, str]:
    """Block a band/mode combination for an operator. One block per operator."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Check if this band/mode is already blocked by someone else
        cursor.execute('''
            SELECT operator_callsign FROM band_mode_blocks
            WHERE band = ? AND mode = ?
        ''', (band, mode))
        existing = cursor.fetchone()

        if existing:
            conn.close()
            return False, f"Band {band} / Mode {mode} is already blocked by {existing['operator_callsign']}"

        # Check if operator already has a block (one block per operator rule)
        cursor.execute('''
            SELECT band, mode FROM band_mode_blocks
            WHERE operator_callsign = ?
        ''', (operator_callsign.upper(),))
        existing_block = cursor.fetchone()

        if existing_block:
            # Auto-unblock the previous block
            cursor.execute('''
                DELETE FROM band_mode_blocks
                WHERE operator_callsign = ?
            ''', (operator_callsign.upper(),))

        # Block the new band/mode
        cursor.execute('''
            INSERT INTO band_mode_blocks (operator_callsign, band, mode)
            VALUES (?, ?, ?)
        ''', (operator_callsign.upper(), band, mode))

        conn.commit()
        conn.close()

        if existing_block:
            return True, f"Successfully blocked (previous block {existing_block['band']}/{existing_block['mode']} released)"
        return True, "Successfully blocked"
    except Exception as e:
        print(f"Error blocking band/mode: {e}")
        return False, str(e)

def unblock_band_mode(operator_callsign: str, band: str, mode: str) -> Tuple[bool, str]:
    """Unblock a band/mode combination."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Check if blocked by this operator
        cursor.execute('''
            SELECT operator_callsign FROM band_mode_blocks
            WHERE band = ? AND mode = ?
        ''', (band, mode))
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
            WHERE band = ? AND mode = ? AND operator_callsign = ?
        ''', (band, mode, operator_callsign.upper()))

        conn.commit()
        conn.close()
        return True, "Successfully unblocked"
    except Exception as e:
        print(f"Error unblocking band/mode: {e}")
        return False, str(e)

def unblock_all_for_operator(operator_callsign: str) -> Tuple[bool, str, int]:
    """Unblock all band/mode combinations for an operator."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Get count of blocks before deleting
        cursor.execute('''
            SELECT COUNT(*) as count FROM band_mode_blocks
            WHERE operator_callsign = ?
        ''', (operator_callsign.upper(),))
        count = cursor.fetchone()['count']

        if count == 0:
            conn.close()
            return True, "No blocks to release", 0

        # Delete all blocks for this operator
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

def admin_unblock_band_mode(band: str, mode: str) -> Tuple[bool, str]:
    """Admin unblock any band/mode combination."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Check if blocked
        cursor.execute('''
            SELECT operator_callsign FROM band_mode_blocks
            WHERE band = ? AND mode = ?
        ''', (band, mode))
        existing = cursor.fetchone()

        if not existing:
            conn.close()
            return False, f"Band {band} / Mode {mode} is not blocked"

        # Unblock the band/mode
        cursor.execute('''
            DELETE FROM band_mode_blocks
            WHERE band = ? AND mode = ?
        ''', (band, mode))

        conn.commit()
        conn.close()
        return True, f"Successfully unblocked {band}/{mode} (was blocked by {existing['operator_callsign']})"
    except Exception as e:
        print(f"Error admin unblocking band/mode: {e}")
        return False, str(e)

def get_all_blocks() -> List[dict]:
    """Get all current band/mode blocks."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT b.*, o.operator_name
        FROM band_mode_blocks b
        JOIN operators o ON b.operator_callsign = o.callsign
        ORDER BY b.band, b.mode
    ''')
    results = cursor.fetchall()
    conn.close()
    return [dict(row) for row in results]

def get_operator_blocks(operator_callsign: str) -> List[dict]:
    """Get all blocks for a specific operator."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM band_mode_blocks
        WHERE operator_callsign = ?
        ORDER BY band, mode
    ''', (operator_callsign.upper(),))
    results = cursor.fetchall()
    conn.close()
    return [dict(row) for row in results]
