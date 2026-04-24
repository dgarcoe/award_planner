"""
App-level settings stored in the app_settings key-value table.

Used by the env-admin to control which features are visible to operators.
"""

from core.database import get_db

# Feature keys and their defaults (all enabled)
FEATURE_DEFAULTS = {
    'feature_announcements': '1',
    'feature_chat': '1',
    'feature_qso_log': '1',
}


def get_app_setting(key, default=None):
    """Get a single app setting value."""
    with get_db() as conn:
        row = conn.execute(
            'SELECT value FROM app_settings WHERE key = ?', (key,)
        ).fetchone()
        return row['value'] if row else default


def set_app_setting(key, value):
    """Set a single app setting value (upsert)."""
    with get_db() as conn:
        conn.execute(
            'INSERT INTO app_settings (key, value) VALUES (?, ?) '
            'ON CONFLICT(key) DO UPDATE SET value = excluded.value',
            (key, str(value))
        )


def get_feature_flags():
    """
    Return a dict of feature visibility flags.
    Each value is a bool indicating whether the feature is enabled.

    Uses a single connection for all keys instead of opening one per key.
    """
    result = {}
    with get_db() as conn:
        for key, default in FEATURE_DEFAULTS.items():
            row = conn.execute(
                'SELECT value FROM app_settings WHERE key = ?', (key,)
            ).fetchone()
            val = row['value'] if row else default
            result[key] = val == '1'
    return result
