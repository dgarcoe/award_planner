"""Shared validation functions."""

from config import MIN_PASSWORD_LENGTH


def validate_password(password: str) -> tuple[bool, str]:
    """Validate password against the configured policy.

    Returns:
        Tuple of (is_valid, error_message). error_message is empty if valid.
    """
    if len(password) < MIN_PASSWORD_LENGTH:
        return False, f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
    return True, ""
