import sqlite3
from datetime import datetime
from typing import List, Tuple, Optional
import os

DATABASE_PATH = os.getenv('DATABASE_PATH', 'ham_coordinator.db')

def get_connection():
    """Create and return a database connection."""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initialize the database with required tables."""
    conn = get_connection()
    cursor = conn.cursor()

    # Create operators table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS operators (
            callsign TEXT PRIMARY KEY,
            operator_name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

def register_operator(callsign: str, operator_name: str) -> bool:
    """Register a new operator or update existing one."""
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO operators (callsign, operator_name)
            VALUES (?, ?)
            ON CONFLICT(callsign) DO UPDATE SET operator_name = ?
        ''', (callsign.upper(), operator_name, operator_name))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error registering operator: {e}")
        return False

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
