"""
Telegram integration functions for linking operator accounts.
"""
import logging
import sqlite3
from typing import Optional, List, Tuple

from core.database import get_db

logger = logging.getLogger(__name__)


def link_telegram_account(
    operator_callsign: str,
    chat_id: int,
    username: Optional[str] = None
) -> Tuple[bool, str]:
    """Link a Telegram account to an operator."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO telegram_links (operator_callsign, telegram_chat_id, telegram_username)
                VALUES (?, ?, ?)
                ON CONFLICT(operator_callsign) DO UPDATE SET
                    telegram_chat_id = excluded.telegram_chat_id,
                    telegram_username = excluded.telegram_username,
                    linked_at = CURRENT_TIMESTAMP
            ''', (operator_callsign.upper(), chat_id, username))
            return True, "Account linked successfully"
    except sqlite3.IntegrityError:
        return False, "This Telegram account is already linked to another operator"
    except Exception:
        logger.exception("Error linking Telegram account")
        return False, "An unexpected error occurred"


def unlink_telegram_account(chat_id: int) -> Tuple[bool, str]:
    """Unlink a Telegram account."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'DELETE FROM telegram_links WHERE telegram_chat_id = ?',
                (chat_id,)
            )
            if cursor.rowcount == 0:
                return False, "No linked account found"
            return True, "Account unlinked successfully"
    except Exception:
        logger.exception("Error unlinking Telegram account")
        return False, "An unexpected error occurred"


def get_telegram_link_by_chat_id(chat_id: int) -> Optional[dict]:
    """Get linked operator info by Telegram chat ID."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT tl.*, o.operator_name, o.is_admin
                FROM telegram_links tl
                JOIN operators o ON tl.operator_callsign = o.callsign
                WHERE tl.telegram_chat_id = ?
            ''', (chat_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception:
        logger.exception("Error getting Telegram link")
        return None


def get_telegram_link_by_callsign(callsign: str) -> Optional[dict]:
    """Get Telegram link info by operator callsign."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT * FROM telegram_links WHERE operator_callsign = ?',
                (callsign.upper(),)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception:
        logger.exception("Error getting Telegram link by callsign")
        return None


def get_linked_users_for_award(award_id: int) -> List[dict]:
    """Get all Telegram-linked users who have a specific award as default."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT tl.*, o.operator_name
                FROM telegram_links tl
                JOIN operators o ON tl.operator_callsign = o.callsign
                WHERE tl.default_award_id = ? AND tl.notifications_enabled = 1
            ''', (award_id,))
            return [dict(row) for row in cursor.fetchall()]
    except Exception:
        logger.exception("Error getting linked users for award")
        return []


def set_default_award(chat_id: int, award_id: int) -> Tuple[bool, str]:
    """Set the default award for a linked user."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE telegram_links SET default_award_id = ? WHERE telegram_chat_id = ?',
                (award_id, chat_id)
            )
            if cursor.rowcount == 0:
                return False, "No linked account found"
            return True, "Default award set successfully"
    except Exception:
        logger.exception("Error setting default award")
        return False, "An unexpected error occurred"


def set_notifications_enabled(chat_id: int, enabled: bool) -> Tuple[bool, str]:
    """Toggle notifications for a linked user."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE telegram_links SET notifications_enabled = ? WHERE telegram_chat_id = ?',
                (1 if enabled else 0, chat_id)
            )
            if cursor.rowcount == 0:
                return False, "No linked account found"
            status = "enabled" if enabled else "disabled"
            return True, f"Notifications {status}"
    except Exception:
        logger.exception("Error setting notifications")
        return False, "An unexpected error occurred"


def set_language(chat_id: int, language: str) -> Tuple[bool, str]:
    """Set language preference for a linked user."""
    if language not in ('en', 'es', 'gl'):
        return False, "Invalid language. Use: en, es, gl"
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'UPDATE telegram_links SET language = ? WHERE telegram_chat_id = ?',
                (language, chat_id)
            )
            if cursor.rowcount == 0:
                return False, "No linked account found"
            return True, f"Language set to {language}"
    except Exception:
        logger.exception("Error setting language")
        return False, "An unexpected error occurred"


def get_all_linked_users_with_notifications() -> List[dict]:
    """Get all linked users with notifications enabled."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT tl.*, o.operator_name
                FROM telegram_links tl
                JOIN operators o ON tl.operator_callsign = o.callsign
                WHERE tl.notifications_enabled = 1
            ''')
            return [dict(row) for row in cursor.fetchall()]
    except Exception:
        logger.exception("Error getting all linked users")
        return []
