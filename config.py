"""Configuration file for QuendAward application constants."""

import os

# Ham radio bands in frequency order (highest to lowest wavelength)
BANDS = ['160m', '80m', '60m', '40m', '30m', '20m', '17m', '15m', '12m', '10m', '8m', '6m', '2m', '70cm', 'SAT']

# Ham radio modes
MODES = ['SSB', 'CW', 'FT8', 'FT4', 'RTTY']

# Admin credentials from environment variables
ADMIN_CALLSIGN = os.getenv('ADMIN_CALLSIGN', '').upper()
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', '')

# UI Configuration
AUTO_REFRESH_INTERVAL_MS = 5000  # 5 seconds
DEFAULT_LANGUAGE = 'gl'  # Galician

# Chart colors
CHART_COLOR_FREE = '#90EE90'  # Green
CHART_COLOR_BLOCKED = '#FF6B6B'  # Red
CHART_BACKGROUND = 'rgba(0,0,0,0)'  # Transparent

# MQTT / Real-time chat configuration
MQTT_BROKER_HOST = os.getenv('MQTT_BROKER_HOST', 'mosquitto')
MQTT_BROKER_PORT = int(os.getenv('MQTT_BROKER_PORT', '1883'))
MQTT_WS_URL = os.getenv('MQTT_WS_URL', '')  # e.g. wss://yourdomain.com/mqtt
CHAT_ENABLED = bool(MQTT_WS_URL)
CHAT_HISTORY_LIMIT = 100
