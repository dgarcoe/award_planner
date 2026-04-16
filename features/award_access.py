"""
Award access control: per-award managers and member rosters.

Each award has an ``is_restricted`` flag (default off). When restricted,
only members, managers, and global admins can block bands on that award.
Managers are designated by global admins and can manage the member roster,
unblock anyone's block on that award, and edit award details.
"""
import logging
from typing import List, Optional, Tuple

from core.database import get_db

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lookups
# ---------------------------------------------------------------------------

def is_manager(operator_callsign: str, award_id: int) -> bool:
    """True if the operator is a designated manager of the given award."""
    if not operator_callsign:
        return False
    with get_db() as conn:
        row = conn.execute(
            'SELECT 1 FROM award_managers WHERE award_id = ? AND operator_callsign = ?',
            (award_id, operator_callsign.upper()),
        ).fetchone()
        return row is not None


def is_member(operator_callsign: str, award_id: int) -> bool:
    """True if the operator is on the member roster for the award."""
    if not operator_callsign:
        return False
    with get_db() as conn:
        row = conn.execute(
            'SELECT 1 FROM award_members WHERE award_id = ? AND operator_callsign = ?',
            (award_id, operator_callsign.upper()),
        ).fetchone()
        return row is not None


def is_restricted(award_id: int) -> bool:
    """True if the award currently has restricted access enabled."""
    with get_db() as conn:
        row = conn.execute(
            'SELECT is_restricted FROM awards WHERE id = ?', (award_id,)
        ).fetchone()
        return bool(row and row['is_restricted'])


def can_block_on_award(operator_callsign: str, award_id: int, is_admin: bool = False) -> bool:
    """Whether this operator is allowed to block bands/modes on this award."""
    if is_admin:
        return True
    if not is_restricted(award_id):
        return True
    return is_manager(operator_callsign, award_id) or is_member(operator_callsign, award_id)


def can_manage_award(operator_callsign: str, award_id: int, is_admin: bool = False) -> bool:
    """Whether this operator can manage the award (members, edit, unblock)."""
    if is_admin:
        return True
    return is_manager(operator_callsign, award_id)


# ---------------------------------------------------------------------------
# Manager roster (admin-only writes)
# ---------------------------------------------------------------------------

def get_managers(award_id: int) -> List[dict]:
    """List managers of an award with operator display name."""
    with get_db() as conn:
        rows = conn.execute(
            '''SELECT am.operator_callsign, am.created_at, o.operator_name
               FROM award_managers am
               JOIN operators o ON o.callsign = am.operator_callsign
               WHERE am.award_id = ?
               ORDER BY am.operator_callsign''',
            (award_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def add_manager(operator_callsign: str, award_id: int) -> Tuple[bool, str]:
    """Grant manager role. Caller must verify is_admin upstream."""
    callsign = operator_callsign.upper().strip()
    if not callsign:
        return False, "Callsign is required"
    try:
        with get_db() as conn:
            op = conn.execute(
                'SELECT 1 FROM operators WHERE callsign = ?', (callsign,)
            ).fetchone()
            if not op:
                return False, f"Operator {callsign} does not exist"
            award = conn.execute(
                'SELECT 1 FROM awards WHERE id = ?', (award_id,)
            ).fetchone()
            if not award:
                return False, "Award not found"
            conn.execute(
                'INSERT OR IGNORE INTO award_managers (award_id, operator_callsign) VALUES (?, ?)',
                (award_id, callsign),
            )
        return True, f"{callsign} is now a manager"
    except Exception:
        logger.exception("Error adding manager")
        return False, "Unexpected error adding manager"


def remove_manager(operator_callsign: str, award_id: int) -> Tuple[bool, str]:
    """Revoke manager role. Caller must verify is_admin upstream."""
    callsign = operator_callsign.upper().strip()
    try:
        with get_db() as conn:
            cur = conn.execute(
                'DELETE FROM award_managers WHERE award_id = ? AND operator_callsign = ?',
                (award_id, callsign),
            )
            if cur.rowcount == 0:
                return False, f"{callsign} is not a manager of this award"
        return True, f"{callsign} is no longer a manager"
    except Exception:
        logger.exception("Error removing manager")
        return False, "Unexpected error removing manager"


def filter_visible_awards(awards: List[dict], operator_callsign: str,
                          is_admin: bool = False) -> List[dict]:
    """Hide restricted awards from operators who are neither members nor managers.

    Admins and non-restricted awards always pass through.
    """
    if is_admin:
        return list(awards)
    callsign = (operator_callsign or '').upper()
    if not callsign:
        return [a for a in awards if not a.get('is_restricted')]
    restricted_ids = [a['id'] for a in awards if a.get('is_restricted')]
    if not restricted_ids:
        return list(awards)
    placeholders = ','.join('?' * len(restricted_ids))
    with get_db() as conn:
        allowed_member = {
            row[0] for row in conn.execute(
                f'SELECT award_id FROM award_members '
                f'WHERE operator_callsign = ? AND award_id IN ({placeholders})',
                [callsign, *restricted_ids],
            )
        }
        allowed_mgr = {
            row[0] for row in conn.execute(
                f'SELECT award_id FROM award_managers '
                f'WHERE operator_callsign = ? AND award_id IN ({placeholders})',
                [callsign, *restricted_ids],
            )
        }
    allowed = allowed_member | allowed_mgr
    return [a for a in awards if not a.get('is_restricted') or a['id'] in allowed]


def get_managed_awards(operator_callsign: str) -> List[dict]:
    """Awards the given operator manages (empty for non-managers)."""
    if not operator_callsign:
        return []
    with get_db() as conn:
        rows = conn.execute(
            '''SELECT a.id, a.name, a.description, a.is_active, a.is_restricted
               FROM award_managers am
               JOIN awards a ON a.id = am.award_id
               WHERE am.operator_callsign = ?
               ORDER BY a.name''',
            (operator_callsign.upper(),),
        ).fetchall()
        return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Member roster (manager/admin writes)
# ---------------------------------------------------------------------------

def get_members(award_id: int) -> List[dict]:
    """List members of an award with operator display name."""
    with get_db() as conn:
        rows = conn.execute(
            '''SELECT am.operator_callsign, am.added_by, am.created_at, o.operator_name
               FROM award_members am
               JOIN operators o ON o.callsign = am.operator_callsign
               WHERE am.award_id = ?
               ORDER BY am.operator_callsign''',
            (award_id,),
        ).fetchall()
        return [dict(r) for r in rows]


def add_member(operator_callsign: str, award_id: int,
               added_by: Optional[str] = None) -> Tuple[bool, str]:
    """Add an operator to the award's member roster."""
    callsign = operator_callsign.upper().strip()
    if not callsign:
        return False, "Callsign is required"
    try:
        with get_db() as conn:
            op = conn.execute(
                'SELECT 1 FROM operators WHERE callsign = ?', (callsign,)
            ).fetchone()
            if not op:
                return False, f"Operator {callsign} does not exist"
            award = conn.execute(
                'SELECT 1 FROM awards WHERE id = ?', (award_id,)
            ).fetchone()
            if not award:
                return False, "Award not found"
            conn.execute(
                'INSERT OR IGNORE INTO award_members (award_id, operator_callsign, added_by) '
                'VALUES (?, ?, ?)',
                (award_id, callsign, (added_by or '').upper() or None),
            )
        return True, f"{callsign} added as member"
    except Exception:
        logger.exception("Error adding member")
        return False, "Unexpected error adding member"


def remove_member(operator_callsign: str, award_id: int) -> Tuple[bool, str]:
    """Remove an operator from the member roster."""
    callsign = operator_callsign.upper().strip()
    try:
        with get_db() as conn:
            cur = conn.execute(
                'DELETE FROM award_members WHERE award_id = ? AND operator_callsign = ?',
                (award_id, callsign),
            )
            if cur.rowcount == 0:
                return False, f"{callsign} is not a member of this award"
        return True, f"{callsign} removed from members"
    except Exception:
        logger.exception("Error removing member")
        return False, "Unexpected error removing member"


# ---------------------------------------------------------------------------
# Restriction toggle (admin/manager writes)
# ---------------------------------------------------------------------------

def set_award_restricted(award_id: int, restricted: bool) -> Tuple[bool, str]:
    """Toggle the is_restricted flag for an award."""
    try:
        with get_db() as conn:
            cur = conn.execute(
                'UPDATE awards SET is_restricted = ? WHERE id = ?',
                (1 if restricted else 0, award_id),
            )
            if cur.rowcount == 0:
                return False, "Award not found"
        return True, "Access mode updated"
    except Exception:
        logger.exception("Error updating restricted flag")
        return False, "Unexpected error updating access mode"
