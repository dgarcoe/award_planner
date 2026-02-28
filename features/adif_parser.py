"""
ADIF file parser for QSO log imports.

Handles ADIF 3.x format:
- Tags: <FIELD_NAME:LENGTH[:TYPE]>VALUE
- End of header: <eoh>
- End of record: <eor>
"""
import re
import logging

logger = logging.getLogger(__name__)

# Fields we extract from ADIF records
KNOWN_FIELDS = {
    'call', 'band', 'mode', 'qso_date', 'time_on', 'time_off',
    'rst_sent', 'rst_rcvd', 'freq', 'name', 'qth', 'gridsquare',
    'comment', 'contest_id', 'srx', 'stx', 'srx_string', 'stx_string',
}

REQUIRED_FIELDS = {'call', 'qso_date', 'time_on'}

# Regex to match ADIF tags: <TAG_NAME:LENGTH[:TYPE]>
_TAG_RE = re.compile(r'<(\w+):(\d+)(?::\w)?>', re.IGNORECASE)


def parse_adif(content: str) -> tuple[list[dict], list[str]]:
    """Parse ADIF content and return (records, warnings).

    Args:
        content: Raw ADIF file content as string.

    Returns:
        Tuple of (list of parsed QSO dicts, list of warning strings).
    """
    warnings: list[str] = []
    records: list[dict] = []

    if not content or not content.strip():
        warnings.append("Empty ADIF content")
        return records, warnings

    # Skip header: everything before <eoh>
    eoh_match = re.search(r'<eoh>', content, re.IGNORECASE)
    if eoh_match:
        body = content[eoh_match.end():]
    else:
        # No header found — treat entire content as records
        body = content

    # Split by <eor> to get individual records
    raw_records = re.split(r'<eor>', body, flags=re.IGNORECASE)

    for idx, raw in enumerate(raw_records, start=1):
        raw = raw.strip()
        if not raw:
            continue

        record = _parse_record(raw)
        if record is None:
            continue

        # Validate required fields
        missing = [f for f in REQUIRED_FIELDS if not record.get(f)]
        if missing:
            warnings.append(f"Record {idx}: missing required fields: {', '.join(missing)}")
            continue

        # Normalize fields
        record = _normalize_record(record, idx, warnings)
        if record is not None:
            records.append(record)

    return records, warnings


def _parse_record(raw: str) -> dict | None:
    """Extract field values from a single ADIF record string."""
    fields: dict = {}
    pos = 0

    while pos < len(raw):
        match = _TAG_RE.search(raw, pos)
        if not match:
            break

        tag_name = match.group(1).lower()
        length = int(match.group(2))
        value_start = match.end()
        value = raw[value_start:value_start + length]

        if tag_name in KNOWN_FIELDS:
            fields[tag_name] = value.strip()

        pos = value_start + length

    return fields if fields else None


def _normalize_record(record: dict, idx: int, warnings: list[str]) -> dict | None:
    """Normalize and validate field values."""
    # Normalize callsign to uppercase
    record['call'] = record['call'].upper()

    # Normalize date: YYYYMMDD -> YYYY-MM-DD
    raw_date = record.get('qso_date', '')
    if len(raw_date) == 8 and raw_date.isdigit():
        record['qso_date'] = f"{raw_date[:4]}-{raw_date[4:6]}-{raw_date[6:8]}"
    elif len(raw_date) == 10 and raw_date[4] == '-' and raw_date[7] == '-':
        pass  # Already in correct format
    else:
        warnings.append(f"Record {idx} ({record['call']}): invalid date format '{raw_date}'")
        return None

    # Normalize time: HHMM or HHMMSS -> HH:MM
    raw_time = record.get('time_on', '')
    record['time_on'] = _normalize_time(raw_time)
    if record['time_on'] is None:
        warnings.append(f"Record {idx} ({record['call']}): invalid time format '{raw_time}'")
        return None

    # Normalize time_off if present
    if record.get('time_off'):
        record['time_off'] = _normalize_time(record['time_off'])

    # Normalize band to lowercase then map common formats
    if record.get('band'):
        record['band'] = record['band'].upper()
        record['band'] = _normalize_band(record['band'])
    else:
        # Try to derive band from frequency
        if record.get('freq'):
            derived = _freq_to_band(record['freq'])
            if derived:
                record['band'] = derived
            else:
                warnings.append(f"Record {idx} ({record['call']}): no band and could not derive from freq")
                return None
        else:
            warnings.append(f"Record {idx} ({record['call']}): missing band")
            return None

    # Normalize mode to uppercase
    if record.get('mode'):
        record['mode'] = record['mode'].upper()

    # Normalize frequency to float
    if record.get('freq'):
        try:
            record['freq'] = float(record['freq'])
        except (ValueError, TypeError):
            record['freq'] = None

    # Default RST values
    if not record.get('rst_sent'):
        record['rst_sent'] = '599' if record.get('mode') in ('CW', 'RTTY', 'FT8', 'FT4') else '59'
    if not record.get('rst_rcvd'):
        record['rst_rcvd'] = '599' if record.get('mode') in ('CW', 'RTTY', 'FT8', 'FT4') else '59'

    return record


def _normalize_time(raw_time: str) -> str | None:
    """Normalize HHMM or HHMMSS to HH:MM."""
    if not raw_time:
        return None
    t = raw_time.strip()
    if len(t) == 4 and t.isdigit():
        return f"{t[:2]}:{t[2:4]}"
    elif len(t) == 6 and t.isdigit():
        return f"{t[:2]}:{t[2:4]}"
    elif len(t) == 5 and t[2] == ':':
        return t  # Already HH:MM
    elif len(t) == 8 and t[2] == ':' and t[5] == ':':
        return t[:5]  # HH:MM:SS -> HH:MM
    return None


def _normalize_band(band: str) -> str:
    """Normalize ADIF band strings to app format (e.g., '20M' -> '20m')."""
    band_map = {
        '160M': '160m', '80M': '80m', '60M': '60m', '40M': '40m',
        '30M': '30m', '20M': '20m', '17M': '17m', '15M': '15m',
        '12M': '12m', '10M': '10m', '8M': '8m', '6M': '6m',
        '2M': '2m', '70CM': '70cm', 'SAT': 'SAT',
    }
    return band_map.get(band, band.lower())


def _freq_to_band(freq_str: str) -> str | None:
    """Derive band from frequency in MHz."""
    try:
        freq = float(freq_str)
    except (ValueError, TypeError):
        return None

    # Frequency ranges in MHz -> band
    ranges = [
        (1.8, 2.0, '160m'), (3.5, 4.0, '80m'), (5.3, 5.4, '60m'),
        (7.0, 7.3, '40m'), (10.1, 10.15, '30m'), (14.0, 14.35, '20m'),
        (18.068, 18.168, '17m'), (21.0, 21.45, '15m'), (24.89, 24.99, '12m'),
        (28.0, 29.7, '10m'), (40.0, 41.0, '8m'), (50.0, 54.0, '6m'),
        (144.0, 148.0, '2m'), (420.0, 450.0, '70cm'),
    ]
    for low, high, band in ranges:
        if low <= freq <= high:
            return band
    return None
