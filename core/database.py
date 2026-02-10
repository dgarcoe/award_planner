"""
Core database module - base connection and initialization.
"""
import sqlite3
import os

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

    # Migration: Add image_data column to awards table if not exists
    cursor.execute("PRAGMA table_info(awards)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'image_data' not in columns:
        cursor.execute('ALTER TABLE awards ADD COLUMN image_data BLOB')
        cursor.execute('ALTER TABLE awards ADD COLUMN image_type TEXT')

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
