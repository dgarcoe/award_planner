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

    # Create operators table with authentication fields
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS operators (
            callsign TEXT PRIMARY KEY,
            operator_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            is_approved INTEGER DEFAULT 0,
            approved_by TEXT,
            approved_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (approved_by) REFERENCES operators (callsign)
        )
    ''')

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

def create_admin(callsign: str, operator_name: str, password: str) -> Tuple[bool, str]:
    """Create an admin account."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Check if admin already exists
        cursor.execute('SELECT callsign FROM operators WHERE is_admin = 1')
        existing_admin = cursor.fetchone()

        password_hash = hash_password(password)
        cursor.execute('''
            INSERT INTO operators (callsign, operator_name, password_hash, is_admin, is_approved)
            VALUES (?, ?, ?, 1, 1)
        ''', (callsign.upper(), operator_name, password_hash))

        conn.commit()
        conn.close()

        if existing_admin:
            return True, f"Admin account created. Note: Another admin already exists ({existing_admin['callsign']})"
        return True, "Admin account created successfully"
    except sqlite3.IntegrityError:
        return False, "Callsign already exists"
    except Exception as e:
        print(f"Error creating admin: {e}")
        return False, str(e)

def register_operator(callsign: str, operator_name: str, password: str) -> Tuple[bool, str]:
    """Register a new operator (awaiting admin approval)."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        password_hash = hash_password(password)
        cursor.execute('''
            INSERT INTO operators (callsign, operator_name, password_hash, is_admin, is_approved)
            VALUES (?, ?, ?, 0, 0)
        ''', (callsign.upper(), operator_name, password_hash))

        conn.commit()
        conn.close()
        return True, "Registration submitted. Awaiting admin approval."
    except sqlite3.IntegrityError:
        return False, "Callsign already registered"
    except Exception as e:
        print(f"Error registering operator: {e}")
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

        if not operator['is_approved'] and not operator['is_admin']:
            return False, "Account pending admin approval", None

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
        SELECT callsign, operator_name, is_admin, is_approved,
               approved_by, approved_at, created_at
        FROM operators
        ORDER BY created_at DESC
    ''')
    results = cursor.fetchall()
    conn.close()
    return [dict(row) for row in results]

def get_pending_operators() -> List[dict]:
    """Get all operators pending approval."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT callsign, operator_name, created_at
        FROM operators
        WHERE is_approved = 0 AND is_admin = 0
        ORDER BY created_at ASC
    ''')
    results = cursor.fetchall()
    conn.close()
    return [dict(row) for row in results]

def approve_operator(callsign: str, admin_callsign: str) -> Tuple[bool, str]:
    """Approve an operator's registration."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Verify the operator exists and is not already approved
        cursor.execute('SELECT is_approved FROM operators WHERE callsign = ?', (callsign.upper(),))
        operator = cursor.fetchone()

        if not operator:
            conn.close()
            return False, "Operator not found"

        if operator['is_approved']:
            conn.close()
            return False, "Operator already approved"

        # Approve the operator
        cursor.execute('''
            UPDATE operators
            SET is_approved = 1, approved_by = ?, approved_at = CURRENT_TIMESTAMP
            WHERE callsign = ?
        ''', (admin_callsign.upper(), callsign.upper()))

        conn.commit()
        conn.close()
        return True, f"Operator {callsign} approved successfully"
    except Exception as e:
        print(f"Error approving operator: {e}")
        return False, str(e)

def reject_operator(callsign: str) -> Tuple[bool, str]:
    """Reject and delete an operator's registration."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Verify the operator exists and is not approved
        cursor.execute('SELECT is_approved, is_admin FROM operators WHERE callsign = ?', (callsign.upper(),))
        operator = cursor.fetchone()

        if not operator:
            conn.close()
            return False, "Operator not found"

        if operator['is_admin']:
            conn.close()
            return False, "Cannot reject admin account"

        if operator['is_approved']:
            conn.close()
            return False, "Cannot reject approved operator. Use revoke access instead."

        # Delete the operator
        cursor.execute('DELETE FROM operators WHERE callsign = ?', (callsign.upper(),))

        conn.commit()
        conn.close()
        return True, f"Operator {callsign} rejected and removed"
    except Exception as e:
        print(f"Error rejecting operator: {e}")
        return False, str(e)

def revoke_operator_access(callsign: str) -> Tuple[bool, str]:
    """Revoke an approved operator's access."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Verify the operator exists
        cursor.execute('SELECT is_admin, is_approved FROM operators WHERE callsign = ?', (callsign.upper(),))
        operator = cursor.fetchone()

        if not operator:
            conn.close()
            return False, "Operator not found"

        if operator['is_admin']:
            conn.close()
            return False, "Cannot revoke admin access"

        # Revoke access and remove their blocks
        cursor.execute('UPDATE operators SET is_approved = 0 WHERE callsign = ?', (callsign.upper(),))
        cursor.execute('DELETE FROM band_mode_blocks WHERE operator_callsign = ?', (callsign.upper(),))

        conn.commit()
        conn.close()
        return True, f"Access revoked for {callsign}"
    except Exception as e:
        print(f"Error revoking access: {e}")
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

def admin_reset_password(callsign: str, new_password: str, admin_callsign: str) -> Tuple[bool, str]:
    """Admin reset of operator's password."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Verify admin
        cursor.execute('SELECT is_admin FROM operators WHERE callsign = ?', (admin_callsign.upper(),))
        admin = cursor.fetchone()

        if not admin or not admin['is_admin']:
            conn.close()
            return False, "Unauthorized: Admin access required"

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
    """Block a band/mode combination for an operator."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Check if already blocked
        cursor.execute('''
            SELECT operator_callsign FROM band_mode_blocks
            WHERE band = ? AND mode = ?
        ''', (band, mode))
        existing = cursor.fetchone()

        if existing:
            conn.close()
            return False, f"Band {band} / Mode {mode} is already blocked by {existing['operator_callsign']}"

        # Block the band/mode
        cursor.execute('''
            INSERT INTO band_mode_blocks (operator_callsign, band, mode)
            VALUES (?, ?, ?)
        ''', (operator_callsign.upper(), band, mode))

        conn.commit()
        conn.close()
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
