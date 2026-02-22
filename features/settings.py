"""
App-level settings stored in the app_settings key-value table.

Used by the env-admin to control which features are visible to operators.
"""

from core.database import get_connection

# Feature keys and their defaults (all enabled)
FEATURE_DEFAULTS = {
    'feature_announcements': '1',
    'feature_chat': '1',
}


def get_app_setting(key, default=None):
    """Get a single app setting value."""
    conn = get_connection()
    try:
        row = conn.execute(
            'SELECT value FROM app_settings WHERE key = ?', (key,)
        ).fetchone()
        return row['value'] if row else default
    finally:
        conn.close()


def set_app_setting(key, value):
    """Set a single app setting value (upsert)."""
    conn = get_connection()
    try:
        conn.execute(
            'INSERT INTO app_settings (key, value) VALUES (?, ?) '
            'ON CONFLICT(key) DO UPDATE SET value = excluded.value',
            (key, str(value))
        )
        conn.commit()
    finally:
        conn.close()


def get_feature_flags():
    """
    Return a dict of feature visibility flags.
    Each value is a bool indicating whether the feature is enabled.
    """
    result = {}
    for key, default in FEATURE_DEFAULTS.items():
        val = get_app_setting(key, default)
        result[key] = val == '1'
    return result
