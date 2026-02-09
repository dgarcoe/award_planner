"""
Authentication and operator management functions.
"""
import sqlite3
from typing import List, Tuple, Optional
import bcrypt

from core.database import get_connection


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
