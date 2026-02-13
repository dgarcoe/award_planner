"""
Database compatibility layer.

This module re-exports all database functions from the new package structure
for backward compatibility with existing code.
"""

# Core functions
from core.database import (
    get_connection,
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
    get_award_by_name,
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

from features.media import (
    save_media_file,
    get_media_for_award,
    get_media_file_path,
    get_media_by_id,
    read_media_file,
    delete_media,
    update_media_order,
    update_media_description,
    toggle_media_public,
    delete_all_media_for_award,
    MEDIA_PATH,
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
    'get_award_by_name',
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
    # Features - Media
    'save_media_file',
    'get_media_for_award',
    'get_media_file_path',
    'get_media_by_id',
    'read_media_file',
    'delete_media',
    'update_media_order',
    'update_media_description',
    'toggle_media_public',
    'delete_all_media_for_award',
    'MEDIA_PATH',
]
