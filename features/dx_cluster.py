"""
DX Cluster integration for QuendAward.

Sends spots to DX Cluster nodes via Telnet to announce special callsign activity.
"""

import logging
import socket
import time
from typing import Tuple, List, Optional

from core.database import get_db

logger = logging.getLogger(__name__)


def send_spot_to_cluster(
    host: str,
    port: int,
    login_callsign: str,
    spotted_callsign: str,
    frequency: float,
    comment: str = "",
    timeout: int = 15,
) -> Tuple[bool, str]:
    """
    Send a DX spot to a cluster node via Telnet.

    Args:
        host: DX Cluster hostname or IP
        port: DX Cluster port (typically 7300, 8000, or 23)
        login_callsign: Callsign to log in to the cluster
        spotted_callsign: The callsign being spotted (e.g. the special callsign)
        frequency: Frequency in kHz (e.g. 14025.0)
        comment: Spot comment (max ~30 chars typically)
        timeout: Connection timeout in seconds

    Returns:
        Tuple of (success: bool, message: str)
    """
    if not host or not login_callsign or not spotted_callsign:
        return False, "Missing required fields (host, login callsign, or spotted callsign)"

    if frequency <= 0:
        return False, "Frequency must be greater than 0"

    sock = None
    try:
        # Connect to the cluster
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((host, port))

        # Read initial banner/login prompt
        _read_until_prompt(sock, timeout=timeout)

        # Send login callsign
        sock.sendall(f"{login_callsign}\r\n".encode("ascii"))

        # Wait for cluster prompt after login
        login_response = _read_until_prompt(sock, timeout=timeout)
        logger.info("DX Cluster login response: %s", login_response[:200])

        # Build and send the DX spot command
        # Format: DX <frequency> <callsign> <comment>
        comment_clean = comment[:30].strip() if comment else ""
        spot_cmd = f"DX {frequency:.1f} {spotted_callsign} {comment_clean}\r\n"
        sock.sendall(spot_cmd.encode("ascii"))

        # Read the cluster response
        spot_response = _read_until_prompt(sock, timeout=timeout)
        logger.info("DX Cluster spot response: %s", spot_response[:200])

        # Send bye to disconnect cleanly
        sock.sendall(b"bye\r\n")

        return True, f"Spot sent: DX {frequency:.1f} {spotted_callsign} {comment_clean}"

    except socket.timeout:
        return False, "Connection timed out"
    except ConnectionRefusedError:
        return False, f"Connection refused by {host}:{port}"
    except OSError as e:
        return False, f"Network error: {e}"
    except Exception as e:
        logger.exception("Unexpected error sending DX spot")
        return False, f"Error: {e}"
    finally:
        if sock:
            try:
                sock.close()
            except OSError:
                pass


def _read_until_prompt(sock: socket.socket, timeout: int = 10) -> str:
    """Read data from socket until no more data arrives (simple approach)."""
    sock.settimeout(min(timeout, 5))
    data = b""
    try:
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            data += chunk
            # Brief pause to allow more data to arrive
            time.sleep(0.3)
            sock.settimeout(1)
    except socket.timeout:
        pass
    return data.decode("ascii", errors="replace")


# ---------------------------------------------------------------------------
# Spot logging (database)
# ---------------------------------------------------------------------------

def log_spot(
    award_id: int,
    operator_callsign: str,
    spotted_callsign: str,
    band: str,
    mode: str,
    frequency: float,
    cluster_host: str,
    success: bool,
    cluster_response: str,
) -> None:
    """Log a spot attempt to the database."""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO spot_log
                    (award_id, operator_callsign, spotted_callsign, band, mode,
                     frequency, cluster_host, success, cluster_response)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                award_id, operator_callsign.upper(), spotted_callsign.upper(),
                band, mode, frequency, cluster_host, 1 if success else 0,
                cluster_response[:500] if cluster_response else "",
            ))
    except Exception:
        logger.exception("Error logging spot")


def get_recent_spots(award_id: Optional[int] = None, limit: int = 10) -> List[dict]:
    """Get recent spot log entries."""
    with get_db() as conn:
        cursor = conn.cursor()
        if award_id:
            cursor.execute('''
                SELECT * FROM spot_log
                WHERE award_id = ?
                ORDER BY spotted_at DESC
                LIMIT ?
            ''', (award_id, limit))
        else:
            cursor.execute('''
                SELECT * FROM spot_log
                ORDER BY spotted_at DESC
                LIMIT ?
            ''', (limit,))
        return [dict(row) for row in cursor.fetchall()]
