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

    # Migration: Add qrz_link column to awards table if not exists
    cursor.execute("PRAGMA table_info(awards)")
    columns = [column[1] for column in cursor.fetchall()]
    if 'qrz_link' not in columns:
        cursor.execute('ALTER TABLE awards ADD COLUMN qrz_link TEXT')

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

    # Create chat_messages table for real-time chat persistence
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

    # Migration: Add reply columns to chat_messages if not exists
    cursor.execute("PRAGMA table_info(chat_messages)")
    chat_columns = [column[1] for column in cursor.fetchall()]
    if 'reply_to_id' not in chat_columns:
        cursor.execute('ALTER TABLE chat_messages ADD COLUMN reply_to_id INTEGER')
        cursor.execute('ALTER TABLE chat_messages ADD COLUMN reply_to_callsign TEXT')
        cursor.execute('ALTER TABLE chat_messages ADD COLUMN reply_to_text TEXT')

    # Create chat_notifications table for @mention notifications
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

    # Create chat_rooms table
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

    # Seed the General room if it doesn't exist
    cursor.execute("SELECT id FROM chat_rooms WHERE room_type = 'general'")
    if not cursor.fetchone():
        cursor.execute('''
            INSERT INTO chat_rooms (name, description, room_type, is_admin_only)
            VALUES ('General', '', 'general', 0)
        ''')

    # Sync: create a chat room for each active award that doesn't have one yet
    cursor.execute('''
        SELECT a.id, a.name FROM awards a
        WHERE NOT EXISTS (SELECT 1 FROM chat_rooms cr WHERE cr.award_id = a.id)
    ''')
    for row in cursor.fetchall():
        cursor.execute(
            "INSERT OR IGNORE INTO chat_rooms (name, description, room_type, award_id) VALUES (?, '', 'award', ?)",
            (row[1], row[0])
        )

    # Migration: Add room_id column to chat_messages if not exists
    cursor.execute("PRAGMA table_info(chat_messages)")
    msg_cols = [col[1] for col in cursor.fetchall()]
    if 'room_id' not in msg_cols:
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
        # Assign orphan messages (no award_id) to General room
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

    # Migration: Add room_id column to chat_notifications if not exists
    cursor.execute("PRAGMA table_info(chat_notifications)")
    notif_cols = [col[1] for col in cursor.fetchall()]
    if 'room_id' not in notif_cols:
        cursor.execute('ALTER TABLE chat_notifications ADD COLUMN room_id INTEGER')
        # Migrate: set room_id from award_id mapping
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

    conn.commit()
    conn.close()
