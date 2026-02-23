"""
Core database module - base connection and initialization.
"""
import logging
import sqlite3
import os
from contextlib import contextmanager

logger = logging.getLogger(__name__)

DATABASE_PATH = os.getenv('DATABASE_PATH', 'ham_coordinator.db')


def get_connection():
    """Create and return a database connection."""
    conn = sqlite3.connect(DATABASE_PATH, check_same_thread=False, timeout=30.0)
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def get_db():
    """Context manager for database connections. Auto-commits on success, rolls back on error."""
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_database():
    """Initialize the database with required tables and run all migrations."""
    conn = get_connection()
    cursor = conn.cursor()
    try:
        _create_tables(cursor)
        _run_migrations(cursor, conn)
        _seed_data(cursor)
        _sync_chat_rooms(cursor)
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Table creation
# ---------------------------------------------------------------------------

def _create_tables(cursor):
    """Create all tables if they don't exist."""
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS operators (
            callsign TEXT PRIMARY KEY,
            operator_name TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

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

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            award_id INTEGER,
            operator_callsign TEXT NOT NULL,
            message TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'app',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_chat_messages_award
        ON chat_messages(award_id, created_at)
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recipient_callsign TEXT NOT NULL,
            sender_callsign TEXT NOT NULL,
            award_id INTEGER,
            message_preview TEXT NOT NULL,
            chat_message_id INTEGER,
            is_read INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (recipient_callsign) REFERENCES operators (callsign),
            FOREIGN KEY (sender_callsign) REFERENCES operators (callsign)
        )
    ''')
    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_chat_notifications_recipient
        ON chat_notifications(recipient_callsign, is_read, created_at)
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS chat_rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            description TEXT DEFAULT '',
            room_type TEXT NOT NULL DEFAULT 'custom',
            award_id INTEGER UNIQUE,
            is_admin_only INTEGER DEFAULT 0,
            created_by TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS spot_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            award_id INTEGER NOT NULL,
            operator_callsign TEXT NOT NULL,
            spotted_callsign TEXT NOT NULL,
            band TEXT,
            mode TEXT,
            frequency REAL,
            cluster_host TEXT,
            success INTEGER DEFAULT 0,
            cluster_response TEXT,
            spotted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (award_id) REFERENCES awards (id)
        )
    ''')


# ---------------------------------------------------------------------------
# Migrations
# ---------------------------------------------------------------------------

def _run_migrations(cursor, conn):
    """Run all schema migrations in order."""
    _migrate_operators_is_admin(cursor)
    _migrate_band_mode_blocks_award_id(cursor, conn)
    _migrate_awards_image_data(cursor)
    _migrate_awards_qrz_link(cursor)
    _migrate_chat_messages_reply(cursor)
    _migrate_chat_messages_room_id(cursor)
    _migrate_chat_notifications_room_id(cursor)


def _get_column_names(cursor, table):
    """Helper to get column names for a table."""
    cursor.execute(f"PRAGMA table_info({table})")
    return [col[1] for col in cursor.fetchall()]


def _migrate_operators_is_admin(cursor):
    """Add is_admin column to operators if missing."""
    if 'is_admin' not in _get_column_names(cursor, 'operators'):
        cursor.execute('ALTER TABLE operators ADD COLUMN is_admin INTEGER DEFAULT 0')


def _migrate_band_mode_blocks_award_id(cursor, conn):
    """Add award_id column to band_mode_blocks, recreating the table if needed."""
    if 'award_id' not in _get_column_names(cursor, 'band_mode_blocks'):
        cursor.execute('SELECT id FROM awards WHERE name = ?', ('Default Award',))
        default_award = cursor.fetchone()

        if not default_award:
            cursor.execute('''
                INSERT INTO awards (name, description, is_active)
                VALUES (?, ?, 1)
            ''', ('Default Award', 'Auto-created award for existing blocks'))
            default_award_id = cursor.lastrowid
        else:
            default_award_id = default_award[0]

        cursor.execute('SELECT * FROM band_mode_blocks')
        existing_blocks = cursor.fetchall()

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

        for block in existing_blocks:
            cursor.execute('''
                INSERT INTO band_mode_blocks (id, operator_callsign, award_id, band, mode, blocked_at)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (block['id'], block['operator_callsign'], default_award_id,
                  block['band'], block['mode'], block['blocked_at']))


def _migrate_awards_image_data(cursor):
    """Add image_data and image_type columns to awards if missing."""
    if 'image_data' not in _get_column_names(cursor, 'awards'):
        cursor.execute('ALTER TABLE awards ADD COLUMN image_data BLOB')
        cursor.execute('ALTER TABLE awards ADD COLUMN image_type TEXT')


def _migrate_awards_qrz_link(cursor):
    """Add qrz_link column to awards if missing."""
    if 'qrz_link' not in _get_column_names(cursor, 'awards'):
        cursor.execute('ALTER TABLE awards ADD COLUMN qrz_link TEXT')


def _migrate_chat_messages_reply(cursor):
    """Add reply_to columns to chat_messages if missing."""
    if 'reply_to_id' not in _get_column_names(cursor, 'chat_messages'):
        cursor.execute('ALTER TABLE chat_messages ADD COLUMN reply_to_id INTEGER')
        cursor.execute('ALTER TABLE chat_messages ADD COLUMN reply_to_callsign TEXT')
        cursor.execute('ALTER TABLE chat_messages ADD COLUMN reply_to_text TEXT')


def _migrate_chat_messages_room_id(cursor):
    """Add room_id column to chat_messages and migrate existing data."""
    if 'room_id' not in _get_column_names(cursor, 'chat_messages'):
        cursor.execute('ALTER TABLE chat_messages ADD COLUMN room_id INTEGER')

        # Migrate existing messages: set room_id from award rooms
        cursor.execute(
            'SELECT DISTINCT cm.award_id FROM chat_messages cm WHERE cm.award_id IS NOT NULL'
        )
        for arow in cursor.fetchall():
            aid = arow[0]
            cursor.execute('SELECT id FROM chat_rooms WHERE award_id = ?', (aid,))
            room = cursor.fetchone()
            if room:
                cursor.execute(
                    'UPDATE chat_messages SET room_id = ? WHERE award_id = ?',
                    (room[0], aid)
                )

        # Assign orphan messages to General room
        cursor.execute("SELECT id FROM chat_rooms WHERE room_type = 'general'")
        gen = cursor.fetchone()
        if gen:
            cursor.execute(
                'UPDATE chat_messages SET room_id = ? WHERE room_id IS NULL',
                (gen[0],)
            )

    cursor.execute('''
        CREATE INDEX IF NOT EXISTS idx_chat_messages_room
        ON chat_messages(room_id, created_at)
    ''')


def _migrate_chat_notifications_room_id(cursor):
    """Add room_id column to chat_notifications and migrate existing data."""
    if 'room_id' not in _get_column_names(cursor, 'chat_notifications'):
        cursor.execute('ALTER TABLE chat_notifications ADD COLUMN room_id INTEGER')

        cursor.execute('''
            UPDATE chat_notifications SET room_id = (
                SELECT cr.id FROM chat_rooms cr WHERE cr.award_id = chat_notifications.award_id
            ) WHERE award_id IS NOT NULL
        ''')

        cursor.execute("SELECT id FROM chat_rooms WHERE room_type = 'general'")
        gen = cursor.fetchone()
        if gen:
            cursor.execute(
                'UPDATE chat_notifications SET room_id = ? WHERE room_id IS NULL',
                (gen[0],)
            )

    # Create app_settings key-value table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    ''')

    conn.commit()
    conn.close()

# ---------------------------------------------------------------------------
# Seed data & sync
# ---------------------------------------------------------------------------

def _seed_data(cursor):
    """Seed initial data (General chat room)."""
    cursor.execute("SELECT id FROM chat_rooms WHERE room_type = 'general'")
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO chat_rooms (name, description, room_type, is_admin_only)
            VALUES ('General', '', 'general', 0)
        ''')


def _sync_chat_rooms(cursor):
    """Ensure every active award has a corresponding chat room."""
    cursor.execute('''
        SELECT a.id, a.name FROM awards a
        WHERE NOT EXISTS (SELECT 1 FROM chat_rooms cr WHERE cr.award_id = a.id)
    ''')
    for row in cursor.fetchall():
        cursor.execute(
            "INSERT OR IGNORE INTO chat_rooms (name, description, room_type, award_id) VALUES (?, '', 'award', ?)",
            (row[1], row[0])
        )
