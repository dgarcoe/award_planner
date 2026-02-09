"""
Features package - blocks, awards, announcements, and backup.
"""
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
    get_announcements_with_read_status,
)

from features.backup import (
    get_database_backup,
    restore_database_from_backup,
    get_database_info,
)

__all__ = [
    # Blocks
    'block_band_mode',
    'unblock_band_mode',
    'unblock_all_for_operator',
    'admin_unblock_band_mode',
    'get_all_blocks',
    'get_operator_blocks',
    # Awards
    'create_award',
    'get_all_awards',
    'get_active_awards',
    'get_award_by_id',
    'update_award',
    'toggle_award_status',
    'delete_award',
    # Announcements
    'create_announcement',
    'get_all_announcements',
    'get_active_announcements',
    'toggle_announcement_status',
    'delete_announcement',
    'mark_announcement_read',
    'mark_all_announcements_read',
    'get_unread_announcement_count',
    'get_announcements_with_read_status',
    # Backup
    'get_database_backup',
    'restore_database_from_backup',
    'get_database_info',
]
