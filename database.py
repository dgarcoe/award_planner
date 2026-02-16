"""
Database compatibility layer.

This module re-exports all database functions from the new package structure
for backward compatibility with existing code.
"""

# Core functions
from core.database import (
    get_connection,
    get_db,
    init_database,
    DATABASE_PATH,
)

from core.auth import (
    hash_password,
    verify_password,
    create_operator,
    authenticate_operator,
    get_operator,
    get_all_operators,
    promote_to_admin,
    demote_from_admin,
    delete_operator,
    change_password,
    admin_reset_password,
)

# Features
from features.blocks import (
    block_band_mode,
    unblock_band_mode,
    unblock_all_for_operator,
    admin_unblock_band_mode,
    get_all_blocks,
    get_operator_blocks,
)

from features.awards import (
    create_award,
    get_all_awards,
    get_active_awards,
    get_award_by_id,
    update_award,
    update_award_image,
    get_award_image,
    toggle_award_status,
    delete_award,
)

from features.announcements import (
    create_announcement,
    get_all_announcements,
    get_active_announcements,
    toggle_announcement_status,
    delete_announcement,
    mark_announcement_read,
    mark_all_announcements_read,
    get_unread_announcement_count,
    get_unread_announcements,
    get_announcements_with_read_status,
)

from features.backup import (
    get_database_backup,
    restore_database_from_backup,
    get_database_info,
)

from features.chat import (
    # Chat rooms
    get_chat_rooms,
    create_chat_room,
    delete_chat_room,
    sync_award_rooms,
    # Chat messages
    save_chat_message,
    get_chat_history,
    get_chat_history_by_room,
    get_chat_history_global,
    get_chat_stats,
    get_chat_stats_by_user,
    delete_chat_messages_by_room,
    delete_chat_messages_by_award,
    delete_chat_messages_older_than,
    delete_all_chat_messages,
    # Chat notifications
    get_unread_chat_notification_count,
    get_unread_chat_notifications,
    mark_chat_notification_read,
    mark_all_chat_notifications_read,
)

__all__ = [
    # Core - Database
    'get_connection',
    'init_database',
    'DATABASE_PATH',
    # Core - Auth
    'hash_password',
    'verify_password',
    'create_operator',
    'authenticate_operator',
    'get_operator',
    'get_all_operators',
    'promote_to_admin',
    'demote_from_admin',
    'delete_operator',
    'change_password',
    'admin_reset_password',
    # Features - Blocks
    'block_band_mode',
    'unblock_band_mode',
    'unblock_all_for_operator',
    'admin_unblock_band_mode',
    'get_all_blocks',
    'get_operator_blocks',
    # Features - Awards
    'create_award',
    'get_all_awards',
    'get_active_awards',
    'get_award_by_id',
    'update_award',
    'update_award_image',
    'get_award_image',
    'toggle_award_status',
    'delete_award',
    # Features - Announcements
    'create_announcement',
    'get_all_announcements',
    'get_active_announcements',
    'toggle_announcement_status',
    'delete_announcement',
    'mark_announcement_read',
    'mark_all_announcements_read',
    'get_unread_announcement_count',
    'get_unread_announcements',
    'get_announcements_with_read_status',
    # Features - Backup
    'get_database_backup',
    'restore_database_from_backup',
    'get_database_info',
    # Features - Chat rooms
    'get_chat_rooms',
    'create_chat_room',
    'delete_chat_room',
    'sync_award_rooms',
    # Features - Chat messages
    'save_chat_message',
    'get_chat_history',
    'get_chat_history_by_room',
    'get_chat_history_global',
    'get_chat_stats',
    'get_chat_stats_by_user',
    'delete_chat_messages_by_room',
    'delete_chat_messages_by_award',
    'delete_chat_messages_older_than',
    'delete_all_chat_messages',
    # Features - Chat notifications
    'get_unread_chat_notification_count',
    'get_unread_chat_notifications',
    'mark_chat_notification_read',
    'mark_all_chat_notifications_read',
]
