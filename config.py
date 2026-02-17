"""Configuration file for QuendAward application constants."""

import os

import bcrypt


def _safe_int(value: str, default: int) -> int:
    """Safely convert a string to int, returning default on failure."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


# Ham radio bands in frequency order (highest to lowest wavelength)
BANDS = ['160m', '80m', '60m', '40m', '30m', '20m', '17m', '15m', '12m', '10m', '8m', '6m', '2m', '70cm', 'SAT']

# Ham radio modes
MODES = ['SSB', 'CW', 'FT8', 'FT4', 'RTTY']

# Admin credentials from environment variables
ADMIN_CALLSIGN = os.getenv('ADMIN_CALLSIGN', '').upper()
_raw_admin_password = os.getenv('ADMIN_PASSWORD', '')
ADMIN_PASSWORD_HASH = bcrypt.hashpw(
    _raw_admin_password.encode('utf-8'), bcrypt.gensalt()
).decode('utf-8') if _raw_admin_password else ''
del _raw_admin_password  # Remove plaintext from module namespace

# Password policy
MIN_PASSWORD_LENGTH = 6

# Login rate limiting
MAX_LOGIN_ATTEMPTS = 5
LOGIN_LOCKOUT_SECONDS = 300  # 5 minutes

# UI Configuration
AUTO_REFRESH_INTERVAL_MS = 5000  # 5 seconds
DEFAULT_LANGUAGE = 'gl'  # Galician

# Chart colors
CHART_COLOR_FREE = '#90EE90'  # Green
CHART_COLOR_BLOCKED = '#FF6B6B'  # Red
CHART_BACKGROUND = 'rgba(0,0,0,0)'  # Transparent

# MQTT / Real-time chat configuration
MQTT_BROKER_HOST = os.getenv('MQTT_BROKER_HOST', 'mosquitto')
MQTT_BROKER_PORT = _safe_int(os.getenv('MQTT_BROKER_PORT', '1883'), 1883)
MQTT_WS_URL = os.getenv('MQTT_WS_URL', '')  # e.g. wss://yourdomain.com/mqtt
CHAT_ENABLED = bool(MQTT_WS_URL)
CHAT_HISTORY_LIMIT = 100
MAX_CHAT_MESSAGE_LENGTH = 2000

# DX Cluster Configuration
DX_CLUSTER_ENABLED = os.getenv('DX_CLUSTER_ENABLED', 'false').lower() == 'true'
DX_CLUSTER_HOST = os.getenv('DX_CLUSTER_HOST', '')
DX_CLUSTER_PORT = _safe_int(os.getenv('DX_CLUSTER_PORT', '7300'), 7300)
DX_CLUSTER_CALLSIGN = os.getenv('DX_CLUSTER_CALLSIGN', '')  # Login callsign for cluster
DX_CLUSTER_PASSWORD = os.getenv('DX_CLUSTER_PASSWORD', '')  # Optional password for cluster auth

# Default band-to-frequency mapping (kHz) used as defaults in the spot form
BAND_FREQUENCIES = {
    '160m': {'SSB': 1845.0, 'CW': 1820.0, 'FT8': 1840.0, 'FT4': 1840.0, 'RTTY': 1842.0},
    '80m':  {'SSB': 3780.0, 'CW': 3525.0, 'FT8': 3573.0, 'FT4': 3575.0, 'RTTY': 3590.0},
    '60m':  {'SSB': 5357.0, 'CW': 5351.5, 'FT8': 5357.0, 'FT4': 5357.0, 'RTTY': 5357.0},
    '40m':  {'SSB': 7150.0, 'CW': 7025.0, 'FT8': 7074.0, 'FT4': 7047.5, 'RTTY': 7040.0},
    '30m':  {'SSB': 10130.0, 'CW': 10115.0, 'FT8': 10136.0, 'FT4': 10140.0, 'RTTY': 10142.0},
    '20m':  {'SSB': 14250.0, 'CW': 14025.0, 'FT8': 14074.0, 'FT4': 14080.0, 'RTTY': 14080.0},
    '17m':  {'SSB': 18145.0, 'CW': 18080.0, 'FT8': 18100.0, 'FT4': 18104.0, 'RTTY': 18105.0},
    '15m':  {'SSB': 21300.0, 'CW': 21025.0, 'FT8': 21074.0, 'FT4': 21140.0, 'RTTY': 21080.0},
    '12m':  {'SSB': 24950.0, 'CW': 24905.0, 'FT8': 24915.0, 'FT4': 24919.0, 'RTTY': 24920.0},
    '10m':  {'SSB': 28500.0, 'CW': 28025.0, 'FT8': 28074.0, 'FT4': 28180.0, 'RTTY': 28080.0},
    '8m':   {'SSB': 40680.0, 'CW': 40680.0, 'FT8': 40680.0, 'FT4': 40680.0, 'RTTY': 40680.0},
    '6m':   {'SSB': 50150.0, 'CW': 50100.0, 'FT8': 50313.0, 'FT4': 50318.0, 'RTTY': 50100.0},
    '2m':   {'SSB': 144300.0, 'CW': 144050.0, 'FT8': 144174.0, 'FT4': 144170.0, 'RTTY': 144100.0},
    '70cm': {'SSB': 432200.0, 'CW': 432100.0, 'FT8': 432174.0, 'FT4': 432170.0, 'RTTY': 432100.0},
    'SAT':  {'SSB': 145900.0, 'CW': 145900.0, 'FT8': 145900.0, 'FT4': 145900.0, 'RTTY': 145900.0},
}
