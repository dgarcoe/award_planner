"""
QSO Log business logic — CRUD operations, stats, and ADIF export.
"""
import logging
from datetime import date

from core.database import get_db

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Insert
# ---------------------------------------------------------------------------

def insert_qso(award_id: int, operator_callsign: str, qso: dict) -> tuple[bool, str, int]:
    """Insert a single QSO record. Returns (success, message, qso_id)."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO qso_log
                    (award_id, operator_callsign, call, band, mode, qso_date, time_on,
                     rst_sent, rst_rcvd, freq, time_off, name, qth, gridsquare,
                     comment, contest_id, srx, stx, srx_string, stx_string)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                award_id, operator_callsign,
                qso.get('call', ''), qso.get('band', ''), qso.get('mode', ''),
                qso.get('qso_date', ''), qso.get('time_on', ''),
                qso.get('rst_sent', '599'), qso.get('rst_rcvd', '599'),
                qso.get('freq'), qso.get('time_off'),
                qso.get('name'), qso.get('qth'), qso.get('gridsquare'),
                qso.get('comment'), qso.get('contest_id'),
                qso.get('srx'), qso.get('stx'),
                qso.get('srx_string'), qso.get('stx_string'),
            ))
            return True, "QSO inserted", cursor.lastrowid
    except Exception as e:
        logger.error("insert_qso error: %s", e)
        return False, str(e), 0


def insert_qsos_bulk(award_id: int, operator_callsign: str,
                     qso_list: list[dict]) -> tuple[bool, str, int]:
    """Bulk-insert QSOs, skipping duplicates. Returns (success, message, count_inserted)."""
    inserted = 0
    skipped = 0
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            for qso in qso_list:
                # Duplicate check: same operator, award, call, band, mode, date, time
                cursor.execute('''
                    SELECT 1 FROM qso_log
                    WHERE award_id = ? AND operator_callsign = ?
                      AND call = ? AND band = ? AND mode = ?
                      AND qso_date = ? AND time_on = ?
                    LIMIT 1
                ''', (
                    award_id, operator_callsign,
                    qso.get('call', ''), qso.get('band', ''),
                    qso.get('mode', ''), qso.get('qso_date', ''),
                    qso.get('time_on', ''),
                ))
                if cursor.fetchone():
                    skipped += 1
                    continue

                cursor.execute('''
                    INSERT INTO qso_log
                        (award_id, operator_callsign, call, band, mode, qso_date, time_on,
                         rst_sent, rst_rcvd, freq, time_off, name, qth, gridsquare,
                         comment, contest_id, srx, stx, srx_string, stx_string)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    award_id, operator_callsign,
                    qso.get('call', ''), qso.get('band', ''), qso.get('mode', ''),
                    qso.get('qso_date', ''), qso.get('time_on', ''),
                    qso.get('rst_sent', '599'), qso.get('rst_rcvd', '599'),
                    qso.get('freq'), qso.get('time_off'),
                    qso.get('name'), qso.get('qth'), qso.get('gridsquare'),
                    qso.get('comment'), qso.get('contest_id'),
                    qso.get('srx'), qso.get('stx'),
                    qso.get('srx_string'), qso.get('stx_string'),
                ))
                inserted += 1

        msg = f"{inserted} QSOs imported"
        if skipped:
            msg += f", {skipped} duplicates skipped"
        return True, msg, inserted
    except Exception as e:
        logger.error("insert_qsos_bulk error: %s", e)
        return False, str(e), inserted


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

def get_qsos(award_id: int, operator_callsign: str | None = None,
             band: str | None = None, mode: str | None = None,
             limit: int = 50, offset: int = 0) -> list[dict]:
    """Get filtered QSOs for an award. Returns list of dicts."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            sql = "SELECT * FROM qso_log WHERE award_id = ?"
            params: list = [award_id]

            if operator_callsign:
                sql += " AND operator_callsign = ?"
                params.append(operator_callsign)
            if band:
                sql += " AND band = ?"
                params.append(band)
            if mode:
                sql += " AND mode = ?"
                params.append(mode)

            sql += " ORDER BY qso_date DESC, time_on DESC LIMIT ? OFFSET ?"
            params.extend([limit, offset])

            cursor.execute(sql, params)
            columns = [desc[0] for desc in cursor.description]
            return [dict(zip(columns, row)) for row in cursor.fetchall()]
    except Exception as e:
        logger.error("get_qsos error: %s", e)
        return []


def get_qso_count(award_id: int, operator_callsign: str | None = None,
                  band: str | None = None, mode: str | None = None) -> int:
    """Get count of QSOs matching filters."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            sql = "SELECT COUNT(*) FROM qso_log WHERE award_id = ?"
            params: list = [award_id]

            if operator_callsign:
                sql += " AND operator_callsign = ?"
                params.append(operator_callsign)
            if band:
                sql += " AND band = ?"
                params.append(band)
            if mode:
                sql += " AND mode = ?"
                params.append(mode)

            cursor.execute(sql, params)
            return cursor.fetchone()[0]
    except Exception as e:
        logger.error("get_qso_count error: %s", e)
        return 0


def get_qso_stats(award_id: int) -> dict:
    """Get statistics for an award's QSO log."""
    stats = {
        'total': 0, 'today': 0, 'unique_calls': 0,
        'active_operators': 0, 'by_band': {}, 'by_mode': {},
        'by_operator': {},
    }
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # Total
            cursor.execute("SELECT COUNT(*) FROM qso_log WHERE award_id = ?", (award_id,))
            stats['total'] = cursor.fetchone()[0]

            if stats['total'] == 0:
                return stats

            # Today
            today_str = date.today().strftime('%Y-%m-%d')
            cursor.execute(
                "SELECT COUNT(*) FROM qso_log WHERE award_id = ? AND qso_date = ?",
                (award_id, today_str),
            )
            stats['today'] = cursor.fetchone()[0]

            # Unique callsigns worked
            cursor.execute(
                "SELECT COUNT(DISTINCT call) FROM qso_log WHERE award_id = ?",
                (award_id,),
            )
            stats['unique_calls'] = cursor.fetchone()[0]

            # Active operators
            cursor.execute(
                "SELECT COUNT(DISTINCT operator_callsign) FROM qso_log WHERE award_id = ?",
                (award_id,),
            )
            stats['active_operators'] = cursor.fetchone()[0]

            # By band
            cursor.execute(
                "SELECT band, COUNT(*) FROM qso_log WHERE award_id = ? GROUP BY band ORDER BY COUNT(*) DESC",
                (award_id,),
            )
            stats['by_band'] = {row[0]: row[1] for row in cursor.fetchall()}

            # By mode
            cursor.execute(
                "SELECT mode, COUNT(*) FROM qso_log WHERE award_id = ? GROUP BY mode ORDER BY COUNT(*) DESC",
                (award_id,),
            )
            stats['by_mode'] = {row[0]: row[1] for row in cursor.fetchall()}

            # By operator
            cursor.execute(
                "SELECT operator_callsign, COUNT(*) FROM qso_log WHERE award_id = ? GROUP BY operator_callsign ORDER BY COUNT(*) DESC",
                (award_id,),
            )
            stats['by_operator'] = {row[0]: row[1] for row in cursor.fetchall()}

    except Exception as e:
        logger.error("get_qso_stats error: %s", e)
    return stats


# ---------------------------------------------------------------------------
# Update / Delete
# ---------------------------------------------------------------------------

def update_qso(qso_id: int, qso_data: dict) -> tuple[bool, str]:
    """Update an existing QSO record."""
    allowed_fields = {
        'call', 'band', 'mode', 'qso_date', 'time_on', 'rst_sent', 'rst_rcvd',
        'freq', 'time_off', 'name', 'qth', 'gridsquare', 'comment',
        'contest_id', 'srx', 'stx', 'srx_string', 'stx_string',
    }
    updates = {k: v for k, v in qso_data.items() if k in allowed_fields}
    if not updates:
        return False, "No valid fields to update"

    try:
        with get_db() as conn:
            cursor = conn.cursor()
            set_clause = ", ".join(f"{k} = ?" for k in updates)
            set_clause += ", modified_at = CURRENT_TIMESTAMP"
            params = list(updates.values()) + [qso_id]
            cursor.execute(f"UPDATE qso_log SET {set_clause} WHERE id = ?", params)
            if cursor.rowcount == 0:
                return False, "QSO not found"
            return True, "QSO updated"
    except Exception as e:
        logger.error("update_qso error: %s", e)
        return False, str(e)


def delete_qso(qso_id: int) -> tuple[bool, str]:
    """Delete a single QSO."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM qso_log WHERE id = ?", (qso_id,))
            if cursor.rowcount == 0:
                return False, "QSO not found"
            return True, "QSO deleted"
    except Exception as e:
        logger.error("delete_qso error: %s", e)
        return False, str(e)


def delete_qsos_by_operator(award_id: int, operator_callsign: str) -> tuple[bool, str, int]:
    """Delete all QSOs for an operator on an award."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM qso_log WHERE award_id = ? AND operator_callsign = ?",
                (award_id, operator_callsign),
            )
            count = cursor.rowcount
            return True, f"{count} QSOs deleted", count
    except Exception as e:
        logger.error("delete_qsos_by_operator error: %s", e)
        return False, str(e), 0


# ---------------------------------------------------------------------------
# ADIF Export
# ---------------------------------------------------------------------------

def export_qsos_to_adif(qsos: list[dict], station_callsign: str = '') -> str:
    """Generate ADIF 3.x content from a list of QSO dicts."""
    lines = []
    # Header
    lines.append("ADIF Export from QuendAward")
    lines.append(f"<adif_ver:5>3.1.4")
    lines.append(f"<programid:10>QuendAward")
    lines.append("<eoh>\n")

    for qso in qsos:
        record_parts = []

        # Station callsign (the special callsign)
        if station_callsign:
            record_parts.append(_adif_field('station_callsign', station_callsign))

        # Operator
        op = qso.get('operator_callsign', '')
        if op:
            record_parts.append(_adif_field('operator', op))

        # Required fields
        record_parts.append(_adif_field('call', qso.get('call', '')))
        record_parts.append(_adif_field('band', qso.get('band', '')))
        record_parts.append(_adif_field('mode', qso.get('mode', '')))

        # Date: YYYY-MM-DD -> YYYYMMDD
        qso_date = qso.get('qso_date', '').replace('-', '')
        record_parts.append(_adif_field('qso_date', qso_date))

        # Time: HH:MM -> HHMM
        time_on = qso.get('time_on', '').replace(':', '')
        record_parts.append(_adif_field('time_on', time_on))

        # Optional fields
        for field in ('rst_sent', 'rst_rcvd', 'name', 'qth', 'gridsquare',
                      'comment', 'contest_id', 'srx', 'stx', 'srx_string', 'stx_string'):
            val = qso.get(field)
            if val:
                record_parts.append(_adif_field(field, str(val)))

        if qso.get('freq'):
            record_parts.append(_adif_field('freq', str(qso['freq'])))

        if qso.get('time_off'):
            time_off = qso['time_off'].replace(':', '')
            record_parts.append(_adif_field('time_off', time_off))

        lines.append(" ".join(record_parts) + " <eor>\n")

    return "\n".join(lines)


def _adif_field(name: str, value: str) -> str:
    """Format a single ADIF field tag."""
    return f"<{name}:{len(value)}>{value}"
