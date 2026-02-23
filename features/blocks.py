"""
Band/mode block management functions.
"""
import json
from typing import List, Tuple, Optional

from core.database import get_connection
from features.events import post_system_event_to_award_room


def block_band_mode(operator_callsign: str, band: str, mode: str, award_id: int) -> Tuple[bool, str]:
    """Block a band/mode combination for an operator within an award. One block per operator per award."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Check if this band/mode is already blocked by someone else in this award
        cursor.execute('''
            SELECT operator_callsign FROM band_mode_blocks
            WHERE band = ? AND mode = ? AND award_id = ?
        ''', (band, mode, award_id))
        existing = cursor.fetchone()

        if existing:
            conn.close()
            return False, f"Band {band} / Mode {mode} is already blocked by {existing['operator_callsign']}"

        # Check if operator already has a block in this award (one block per operator per award rule)
        cursor.execute('''
            SELECT band, mode FROM band_mode_blocks
            WHERE operator_callsign = ? AND award_id = ?
        ''', (operator_callsign.upper(), award_id))
        existing_block = cursor.fetchone()

        if existing_block:
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

        conn.commit()
        conn.close()

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
        conn = get_connection()
        cursor = conn.cursor()

        # Check if blocked by this operator in this award
        cursor.execute('''
            SELECT operator_callsign FROM band_mode_blocks
            WHERE band = ? AND mode = ? AND award_id = ?
        ''', (band, mode, award_id))
        existing = cursor.fetchone()

        if not existing:
            conn.close()
            return False, f"Band {band} / Mode {mode} is not blocked"

        if existing['operator_callsign'] != operator_callsign.upper():
            conn.close()
            return False, f"Band {band} / Mode {mode} is blocked by {existing['operator_callsign']}, not by you"

        # Unblock the band/mode
        cursor.execute('''
            DELETE FROM band_mode_blocks
            WHERE band = ? AND mode = ? AND operator_callsign = ? AND award_id = ?
        ''', (band, mode, operator_callsign.upper(), award_id))

        conn.commit()
        conn.close()
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
        conn = get_connection()
        cursor = conn.cursor()

        # Get count of blocks before deleting
        if award_id:
            cursor.execute('''
                SELECT COUNT(*) as count FROM band_mode_blocks
                WHERE operator_callsign = ? AND award_id = ?
            ''', (operator_callsign.upper(), award_id))
        else:
            cursor.execute('''
                SELECT COUNT(*) as count FROM band_mode_blocks
                WHERE operator_callsign = ?
            ''', (operator_callsign.upper(),))
        count = cursor.fetchone()['count']

        if count == 0:
            conn.close()
            return True, "No blocks to release", 0

        # Delete blocks for this operator
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

        conn.commit()
        conn.close()
        return True, f"Released {count} block(s)", count
    except Exception as e:
        print(f"Error unblocking all: {e}")
        return False, str(e), 0


def admin_unblock_band_mode(band: str, mode: str, award_id: int,
                            admin_callsign: str = '') -> Tuple[bool, str]:
    """Admin unblock any band/mode combination for a specific award."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # Check if blocked
        cursor.execute('''
            SELECT operator_callsign FROM band_mode_blocks
            WHERE band = ? AND mode = ? AND award_id = ?
        ''', (band, mode, award_id))
        existing = cursor.fetchone()

        if not existing:
            conn.close()
            return False, f"Band {band} / Mode {mode} is not blocked"

        blocked_by = existing['operator_callsign']

        # Unblock the band/mode
        cursor.execute('''
            DELETE FROM band_mode_blocks
            WHERE band = ? AND mode = ? AND award_id = ?
        ''', (band, mode, award_id))

        conn.commit()
        conn.close()

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
    conn = get_connection()
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
    conn.close()
    return [dict(row) for row in results]


def get_operator_blocks(operator_callsign: str, award_id: Optional[int] = None) -> List[dict]:
    """Get all blocks for a specific operator, optionally filtered by award."""
    conn = get_connection()
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
    conn.close()
    return [dict(row) for row in results]
