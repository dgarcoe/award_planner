"""Configuration file for QuendAward application constants."""

import os

# Ham radio bands in frequency order (highest to lowest wavelength)
BANDS = ['160m', '80m', '60m', '40m', '30m', '20m', '17m', '15m', '12m', '10m', '8m', '6m', '2m', '70cm', 'SAT']

# Ham radio modes
MODES = ['CW', 'SSB', 'FT8', 'FT4', 'RTTY']

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
