"""
Core package - database connection and authentication.
"""
from core.database import get_connection, init_database, DATABASE_PATH
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

__all__ = [
    # Database
    'get_connection',
    'init_database',
    'DATABASE_PATH',
    # Auth
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
]
