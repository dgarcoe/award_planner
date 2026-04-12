"""
Band/mode block management functions.
"""
import json
import logging
from typing import List, Tuple, Optional

from core.database import get_db
from features.events import post_system_event_to_award_room

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Block history helpers
# ---------------------------------------------------------------------------

def _open_history_record(cursor, award_id, operator_callsign, band, mode):
    """Insert a new open history row (unblocked_at=NULL)."""
    cursor.execute(
        '''INSERT INTO block_history
             (award_id, operator_callsign, band, mode, blocked_at)
           VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)''',
        (award_id, operator_callsign.upper(), band, mode),
    )


def _close_history_records(cursor, award_id, operator_callsign, band=None, mode=None):
    """Close open history rows by setting unblocked_at + duration.

    If band/mode are None, closes ALL open rows for the operator on that award.
    """
    where = "award_id = ? AND operator_callsign = ? AND unblocked_at IS NULL"
    params = [award_id, operator_callsign.upper()]
    if band is not None:
        where += " AND band = ? AND mode = ?"
        params.extend([band, mode])
    cursor.execute(
        f'''UPDATE block_history
              SET unblocked_at = CURRENT_TIMESTAMP,
                  duration_seconds = CAST(
                      (julianday(CURRENT_TIMESTAMP) - julianday(blocked_at)) * 86400
                  AS INTEGER)
            WHERE {where}''',
        params,
    )


# ---------------------------------------------------------------------------
# Block / unblock operations
# ---------------------------------------------------------------------------

def block_band_mode(operator_callsign: str, band: str, mode: str, award_id: int) -> Tuple[bool, str]:
    """Block a band/mode combination for an operator within an award. One block per operator per award."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            # Check if this band/mode is already blocked by someone else in this award
            cursor.execute('''
                SELECT operator_callsign FROM band_mode_blocks
                WHERE band = ? AND mode = ? AND award_id = ?
            ''', (band, mode, award_id))
            existing = cursor.fetchone()

            if existing:
                return False, f"Band {band} / Mode {mode} is already blocked by {existing['operator_callsign']}"

            # Check if operator already has a block in this award (one block per operator per award rule)
            cursor.execute('''
                SELECT band, mode FROM band_mode_blocks
                WHERE operator_callsign = ? AND award_id = ?
            ''', (operator_callsign.upper(), award_id))
            existing_block = cursor.fetchone()

            if existing_block:
                # Close the history record for the old block
                _close_history_records(
                    cursor, award_id, operator_callsign,
                    existing_block['band'], existing_block['mode'],
                )
                # Auto-unblock the previous block
                cursor.execute('''
                    DELETE FROM band_mode_blocks
                    WHERE operator_callsign = ? AND award_id = ?
                ''', (operator_callsign.upper(), award_id))

            # Block the new band/mode
            cursor.execute('''
                INSERT INTO band_mode_blocks (operator_callsign, award_id, band, mode)
                VALUES (?, ?, ?, ?)
            ''', (operator_callsign.upper(), award_id, band, mode))

            # Open a new history record
            _open_history_record(cursor, award_id, operator_callsign, band, mode)

        if existing_block:
            event_data = json.dumps({
                'event': 'switched',
                'callsign': operator_callsign.upper(),
                'old_band': existing_block['band'],
                'old_mode': existing_block['mode'],
                'band': band,
                'mode': mode,
            })
            post_system_event_to_award_room(award_id, event_data)
            return True, f"Successfully blocked (previous block {existing_block['band']}/{existing_block['mode']} released)"

        event_data = json.dumps({
            'event': 'blocked',
            'callsign': operator_callsign.upper(),
            'band': band,
            'mode': mode,
        })
        post_system_event_to_award_room(award_id, event_data)
        return True, "Successfully blocked"
    except Exception as e:
        print(f"Error blocking band/mode: {e}")
        return False, str(e)


def unblock_band_mode(operator_callsign: str, band: str, mode: str, award_id: int) -> Tuple[bool, str]:
    """Unblock a band/mode combination for a specific award."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT operator_callsign FROM band_mode_blocks
                WHERE band = ? AND mode = ? AND award_id = ?
            ''', (band, mode, award_id))
            existing = cursor.fetchone()

            if not existing:
                return False, f"Band {band} / Mode {mode} is not blocked"

            if existing['operator_callsign'] != operator_callsign.upper():
                return False, f"Band {band} / Mode {mode} is blocked by {existing['operator_callsign']}, not by you"

            # Close the history record
            _close_history_records(cursor, award_id, operator_callsign, band, mode)

            cursor.execute('''
                DELETE FROM band_mode_blocks
                WHERE band = ? AND mode = ? AND award_id = ?
            ''', (band, mode, award_id))

        event_data = json.dumps({
            'event': 'unblocked',
            'callsign': operator_callsign.upper(),
            'band': band,
            'mode': mode,
        })
        post_system_event_to_award_room(award_id, event_data)
        return True, "Successfully unblocked"
    except Exception as e:
        print(f"Error unblocking band/mode: {e}")
        return False, str(e)


def unblock_all_for_operator(operator_callsign: str, award_id: Optional[int] = None) -> Tuple[bool, str, int]:
    """Unblock all band/mode combinations for an operator, optionally for a specific award."""
    try:
        blocks_removed = []
        with get_db() as conn:
            cursor = conn.cursor()

            if award_id:
                cursor.execute('''
                    SELECT band, mode, award_id FROM band_mode_blocks
                    WHERE operator_callsign = ? AND award_id = ?
                ''', (operator_callsign.upper(), award_id))
            else:
                cursor.execute('''
                    SELECT band, mode, award_id FROM band_mode_blocks
                    WHERE operator_callsign = ?
                ''', (operator_callsign.upper(),))
            blocks_removed = [dict(row) for row in cursor.fetchall()]
            count = len(blocks_removed)

            if count == 0:
                return True, "No blocks to release", 0

            # Close all history records for these blocks
            if award_id:
                _close_history_records(cursor, award_id, operator_callsign)
            else:
                # Close records across all awards
                for block in blocks_removed:
                    _close_history_records(
                        cursor, block['award_id'], operator_callsign,
                        block['band'], block['mode'],
                    )

            if award_id:
                cursor.execute('''
                    DELETE FROM band_mode_blocks
                    WHERE operator_callsign = ? AND award_id = ?
                ''', (operator_callsign.upper(), award_id))
            else:
                cursor.execute('''
                    DELETE FROM band_mode_blocks
                    WHERE operator_callsign = ?
                ''', (operator_callsign.upper(),))

        for block in blocks_removed:
            event_data = json.dumps({
                'event': 'unblocked',
                'callsign': operator_callsign.upper(),
                'band': block['band'],
                'mode': block['mode'],
            })
            post_system_event_to_award_room(block['award_id'], event_data)

        return True, f"Released {count} block(s)", count
    except Exception:
        logger.exception("Error unblocking all")
        return False, "An unexpected error occurred. Please try again.", 0


def admin_unblock_band_mode(band: str, mode: str, award_id: int,
                            admin_callsign: str = '') -> Tuple[bool, str]:
    """Admin unblock any band/mode combination for a specific award."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()

            cursor.execute('''
                SELECT operator_callsign FROM band_mode_blocks
                WHERE band = ? AND mode = ? AND award_id = ?
            ''', (band, mode, award_id))
            existing = cursor.fetchone()

            blocked_by = existing['operator_callsign']

            # Close the history record for the blocked operator
            _close_history_records(cursor, award_id, blocked_by, band, mode)

            cursor.execute('''
                DELETE FROM band_mode_blocks
                WHERE band = ? AND mode = ? AND award_id = ?
            ''', (band, mode, award_id))

        event = {
            'event': 'admin_unblocked',
            'band': band,
            'mode': mode,
            'blocked_by': blocked_by,
        }
        if admin_callsign:
            event['callsign'] = admin_callsign.upper()
        post_system_event_to_award_room(award_id, json.dumps(event))

        return True, f"Successfully unblocked {band}/{mode} (was blocked by {blocked_by})"
    except Exception as e:
        print(f"Error admin unblocking band/mode: {e}")
        return False, str(e)


def get_all_blocks(award_id: Optional[int] = None) -> List[dict]:
    """Get all current band/mode blocks, optionally filtered by award."""
    with get_db() as conn:
        cursor = conn.cursor()
        if award_id:
            cursor.execute('''
                SELECT b.*, o.operator_name
                FROM band_mode_blocks b
                JOIN operators o ON b.operator_callsign = o.callsign
                WHERE b.award_id = ?
                ORDER BY b.band, b.mode
            ''', (award_id,))
        else:
            cursor.execute('''
                SELECT b.*, o.operator_name
                FROM band_mode_blocks b
                JOIN operators o ON b.operator_callsign = o.callsign
                ORDER BY b.band, b.mode
            ''')
        results = cursor.fetchall()
        return [dict(row) for row in results]


def get_operator_blocks(operator_callsign: str, award_id: Optional[int] = None) -> List[dict]:
    """Get all blocks for a specific operator, optionally filtered by award."""
    with get_db() as conn:
        cursor = conn.cursor()
        if award_id:
            cursor.execute('''
                SELECT * FROM band_mode_blocks
                WHERE operator_callsign = ? AND award_id = ?
                ORDER BY band, mode
            ''', (operator_callsign.upper(), award_id))
        else:
            cursor.execute('''
                SELECT * FROM band_mode_blocks
                WHERE operator_callsign = ?
                ORDER BY band, mode
            ''', (operator_callsign.upper(),))
        results = cursor.fetchall()
        return [dict(row) for row in results]


# ---------------------------------------------------------------------------
# Block history queries
# ---------------------------------------------------------------------------

def get_activation_stats(award_id: int) -> dict:
    """Aggregate activation statistics for an award.

    Returns dict with:
      - total_activations: int
      - total_seconds: int (total activation time across all operators)
      - by_operator: dict[callsign, {activations, seconds}] sorted by seconds desc
      - by_band: dict[band, {activations, seconds}] sorted by seconds desc
      - by_mode: dict[mode, {activations, seconds}] sorted by seconds desc
      - by_date: list[{date, activations, seconds}] sorted by date asc
      - by_hour: list[{hour, activations}] sorted by hour asc
      - recent: list[dict] last 20 completed activations
    """
    with get_db() as conn:
        c = conn.cursor()
        base = "FROM block_history WHERE award_id = ? AND duration_seconds IS NOT NULL"
        params = [award_id]

        # Totals
        row = c.execute(
            f"SELECT COUNT(*), COALESCE(SUM(duration_seconds), 0) {base}",
            params,
        ).fetchone()
        total_activations = row[0]
        total_seconds = row[1]

        # By operator
        by_operator = {}
        for r in c.execute(
            f"SELECT operator_callsign, COUNT(*) AS cnt, "
            f"SUM(duration_seconds) AS secs {base} "
            "GROUP BY operator_callsign ORDER BY secs DESC",
            params,
        ):
            by_operator[r[0]] = {'activations': r[1], 'seconds': r[2]}

        # By band
        by_band = {}
        for r in c.execute(
            f"SELECT band, COUNT(*) AS cnt, "
            f"SUM(duration_seconds) AS secs {base} "
            "GROUP BY band ORDER BY secs DESC",
            params,
        ):
            by_band[r[0]] = {'activations': r[1], 'seconds': r[2]}

        # By mode
        by_mode = {}
        for r in c.execute(
            f"SELECT mode, COUNT(*) AS cnt, "
            f"SUM(duration_seconds) AS secs {base} "
            "GROUP BY mode ORDER BY secs DESC",
            params,
        ):
            by_mode[r[0]] = {'activations': r[1], 'seconds': r[2]}

        # By date (use blocked_at date)
        by_date = []
        for r in c.execute(
            f"SELECT DATE(blocked_at) AS d, COUNT(*) AS cnt, "
            f"SUM(duration_seconds) AS secs {base} "
            "GROUP BY d ORDER BY d",
            params,
        ):
            by_date.append({'date': r[0], 'activations': r[1], 'seconds': r[2]})

        # By hour of day (hour when activation started)
        by_hour = []
        for r in c.execute(
            f"SELECT CAST(STRFTIME('%H', blocked_at) AS INTEGER) AS h, "
            f"COUNT(*) AS cnt {base} GROUP BY h ORDER BY h",
            params,
        ):
            by_hour.append({'hour': r[0], 'activations': r[1]})

        # Recent completed activations
        recent = []
        for r in c.execute(
            "SELECT operator_callsign, band, mode, blocked_at, "
            "unblocked_at, duration_seconds "
            "FROM block_history WHERE award_id = ? AND unblocked_at IS NOT NULL "
            "ORDER BY unblocked_at DESC LIMIT 20",
            [award_id],
        ):
            recent.append(dict(r))

        return {
            'total_activations': total_activations,
            'total_seconds': total_seconds,
            'by_operator': by_operator,
            'by_band': by_band,
            'by_mode': by_mode,
            'by_date': by_date,
            'by_hour': by_hour,
            'recent': recent,
        }
