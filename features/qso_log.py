"""
QSO log: ADIF upload ingestion, paginated queries, batch tracking, ADIF export.

The upload path is designed to stay fast on mobile:
  * parsing uses a single-pass streaming scanner (no regex over full file)
  * bulk insert runs inside ONE transaction via executemany
  * duplicates are rejected at the SQLite index level with INSERT OR IGNORE
  * parse + insert run on a dedicated ThreadPoolExecutor so the Streamlit
    script thread is not blocked while the browser tab waits
"""

import concurrent.futures
import logging
from datetime import datetime
from typing import Dict, Iterable, Iterator, List, Optional, Tuple

from core.database import get_db

logger = logging.getLogger(__name__)


# Dedicated background thread pool for QSO ingest so uploads never freeze
# the Streamlit script thread. Two workers is enough - typical activations
# produce well under a handful of concurrent uploads.
_ingest_executor = concurrent.futures.ThreadPoolExecutor(
    max_workers=2,
    thread_name_prefix="qso_ingest",
)


# ---------------------------------------------------------------------------
# Constants / limits
# ---------------------------------------------------------------------------

# Upper bound on uploaded file size. Keeps the in-memory footprint bounded
# and prevents mobile browsers from timing out the POST on huge files.
MAX_ADIF_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB ~= 50k QSOs

# Columns that the bulk insert populates - order matters for executemany.
_QSO_COLUMNS = (
    "award_id", "operator_callsign", "batch_id",
    "call", "band", "mode", "qso_date", "time_on",
    "rst_sent", "rst_rcvd", "freq",
    "name", "qth", "gridsquare", "comment",
)

# Fallback band/frequency table used when the ADIF only carries freq or band.
# Values are frequency-range -> band. Matches the bands declared in config.py.
_BAND_RANGES = [
    (1.8,    2.0,     "160m"),
    (3.5,    4.0,     "80m"),
    (5.3,    5.5,     "60m"),
    (7.0,    7.3,     "40m"),
    (10.1,   10.15,   "30m"),
    (14.0,   14.35,   "20m"),
    (18.068, 18.168,  "17m"),
    (21.0,   21.45,   "15m"),
    (24.89,  24.99,   "12m"),
    (28.0,   29.7,    "10m"),
    (40.66,  40.7,    "8m"),
    (50.0,   54.0,    "6m"),
    (144.0,  148.0,   "2m"),
    (420.0,  450.0,   "70cm"),
]


# ---------------------------------------------------------------------------
# ADIF parser
# ---------------------------------------------------------------------------

def parse_adif_stream(text: str) -> Iterator[Dict[str, str]]:
    """Yield one dict per QSO record found in an ADIF string.

    Single pass, no regex. Handles lowercase/uppercase tags, mixed whitespace,
    and skips records that lack the required call/band/mode.
    """
    if not text:
        return

    # ADIF files may start with a free-form header terminated by <eoh>.
    # Everything before <eoh> is metadata we don't need. Do a case-insensitive
    # scan so we correctly strip the header regardless of tag casing.
    lower = text.lower()
    header_end = lower.find("<eoh>")
    if header_end >= 0:
        text = text[header_end + 5:]

    # Split on EOR. Case-insensitive by folding text once for lookup.
    records = _split_records(text)
    for raw in records:
        fields = _scan_record(raw)
        if not fields:
            continue
        yield fields


def _split_records(text: str) -> Iterator[str]:
    """Yield raw record strings split on <eor>, case-insensitive."""
    lower = text.lower()
    start = 0
    while True:
        idx = lower.find("<eor>", start)
        if idx < 0:
            remainder = text[start:].strip()
            if remainder:
                yield remainder
            return
        yield text[start:idx]
        start = idx + 5


def _scan_record(raw: str) -> Dict[str, str]:
    """Scan a single raw record and return a dict of lowercased field names.

    ADIF field format: <name:length[:type]>value  where length is bytes.
    """
    fields: Dict[str, str] = {}
    i = 0
    n = len(raw)
    while i < n:
        lt = raw.find("<", i)
        if lt < 0:
            break
        gt = raw.find(">", lt + 1)
        if gt < 0:
            break
        tag = raw[lt + 1:gt]
        parts = tag.split(":")
        if len(parts) < 2:
            i = gt + 1
            continue
        name = parts[0].strip().lower()
        try:
            length = int(parts[1])
        except ValueError:
            i = gt + 1
            continue
        value_start = gt + 1
        value_end = value_start + length
        if value_end > n:
            # Malformed length - bail out for this record
            break
        value = raw[value_start:value_end]
        if name:
            fields[name] = value
        i = value_end
    return fields


def _normalize_qso(
    raw: Dict[str, str],
    award_id: int,
    operator: str,
    batch_id: Optional[int],
) -> Optional[Tuple]:
    """Turn a raw ADIF dict into a tuple ready for executemany.

    Returns None if the record is missing required fields.
    Returned tuple ordering must match _QSO_COLUMNS.
    """
    call = (raw.get("call") or "").strip().upper()
    if not call:
        return None

    # Derive band either from explicit tag or from freq.
    band = (raw.get("band") or "").strip().lower()
    freq_val: Optional[float] = None
    freq_raw = raw.get("freq") or raw.get("freq_rx")
    if freq_raw:
        try:
            freq_val = float(freq_raw)
        except ValueError:
            freq_val = None
    if not band and freq_val is not None:
        band = _band_from_freq(freq_val) or ""
    if not band:
        return None

    mode = (raw.get("mode") or "").strip().upper()
    if not mode:
        return None
    # ADIF sometimes uses SUBMODE for digital; prefer submode when present for
    # common digital modes where SUBMODE is the specific protocol.
    submode = (raw.get("submode") or "").strip().upper()
    if submode and mode in ("DATA", "DIGITAL", "MFSK", "PSK", "RTTY"):
        mode = submode

    qso_date = (raw.get("qso_date") or "").strip()
    if not qso_date or len(qso_date) != 8 or not qso_date.isdigit():
        return None
    qso_date = f"{qso_date[:4]}-{qso_date[4:6]}-{qso_date[6:]}"

    time_on_raw = (raw.get("time_on") or "").strip()
    if not time_on_raw or not time_on_raw.isdigit() or len(time_on_raw) < 4:
        return None
    time_on = f"{time_on_raw[:2]}:{time_on_raw[2:4]}"

    rst_sent = (raw.get("rst_sent") or "").strip() or None
    rst_rcvd = (raw.get("rst_rcvd") or "").strip() or None
    name = (raw.get("name") or "").strip() or None
    qth = (raw.get("qth") or "").strip() or None
    grid = (raw.get("gridsquare") or "").strip().upper() or None
    comment = (raw.get("comment") or raw.get("notes") or "").strip() or None

    return (
        award_id, operator.upper(), batch_id,
        call, band, mode, qso_date, time_on,
        rst_sent, rst_rcvd, freq_val,
        name, qth, grid, comment,
    )


def _band_from_freq(freq_mhz: float) -> Optional[str]:
    """Map an ADIF freq value in MHz to our band label, if it falls in any."""
    for lo, hi, label in _BAND_RANGES:
        if lo <= freq_mhz <= hi:
            return label
    return None


# ---------------------------------------------------------------------------
# Ingestion
# ---------------------------------------------------------------------------

def ingest_adif_async(
    award_id: int,
    operator_callsign: str,
    file_bytes: bytes,
    filename: str = "upload.adi",
) -> concurrent.futures.Future:
    """Submit an ADIF ingest to the background thread pool.

    The caller waits on the returned Future with a timeout so the Streamlit
    UI can show a spinner without freezing the script thread.
    """
    return _ingest_executor.submit(
        ingest_adif_bytes,
        award_id,
        operator_callsign,
        file_bytes,
        filename,
    )


def ingest_adif_bytes(
    award_id: int,
    operator_callsign: str,
    file_bytes: bytes,
    filename: str = "upload.adi",
) -> Dict[str, int]:
    """Parse the given ADIF bytes and bulk insert the QSOs.

    Returns a dict with counts: parsed / inserted / duplicates / errors /
    batch_id. Raises ValueError on hard validation errors (empty file, etc.).
    """
    if not file_bytes:
        raise ValueError("Empty file")
    if len(file_bytes) > MAX_ADIF_UPLOAD_BYTES:
        raise ValueError(
            f"File too large ({len(file_bytes)} bytes); "
            f"limit is {MAX_ADIF_UPLOAD_BYTES} bytes"
        )

    try:
        text = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text = file_bytes.decode("ascii", errors="replace")

    _INGEST_BATCH_SIZE = 500

    # First pass: parse + normalize into a flat list.
    parsed_rows: List[Tuple] = []
    parsed_total = 0
    errors = 0
    for raw in parse_adif_stream(text):
        parsed_total += 1
        row = _normalize_qso(raw, award_id, operator_callsign, batch_id=None)
        if row is None:
            errors += 1
            continue
        parsed_rows.append(row)

    # Second pass: open a write transaction, create the batch row so we can
    # tag each QSO with it, then insert in chunks to bound peak memory.
    # INSERT OR IGNORE silently drops duplicates caught by idx_qso_dedup.
    batch_id: Optional[int] = None
    inserted = 0
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''INSERT INTO qso_upload_batch
                 (award_id, operator_callsign, filename, parsed,
                  inserted, duplicates, errors)
               VALUES (?, ?, ?, ?, 0, 0, ?)''',
            (award_id, operator_callsign.upper(), filename or "upload.adi",
             parsed_total, errors)
        )
        batch_id = cursor.lastrowid

        insert_sql = (
            f'''INSERT OR IGNORE INTO qso_log
                 ({", ".join(_QSO_COLUMNS)})
                VALUES ({", ".join("?" * len(_QSO_COLUMNS))})'''
        )

        for i in range(0, len(parsed_rows), _INGEST_BATCH_SIZE):
            chunk = [
                (r[0], r[1], batch_id) + r[3:]
                for r in parsed_rows[i:i + _INGEST_BATCH_SIZE]
            ]
            cursor.executemany(insert_sql, chunk)
            inserted += cursor.rowcount

        duplicates = len(parsed_rows) - inserted
        cursor.execute(
            '''UPDATE qso_upload_batch
                 SET inserted = ?, duplicates = ?
               WHERE id = ?''',
            (inserted, duplicates, batch_id),
        )

    logger.info(
        "QSO ingest: award=%s op=%s parsed=%s inserted=%s dup=%s err=%s",
        award_id, operator_callsign, parsed_total, inserted,
        parsed_total - inserted - errors, errors,
    )

    return {
        "parsed": parsed_total,
        "inserted": inserted,
        "duplicates": max(0, parsed_total - inserted - errors),
        "errors": errors,
        "batch_id": batch_id or 0,
    }


# ---------------------------------------------------------------------------
# Queries
# ---------------------------------------------------------------------------

def get_qso_stats(award_id: int, operator_callsign: Optional[str] = None) -> Dict:
    """Get total / by-band / by-mode / unique-call counts for an award.

    Passing operator_callsign scopes everything to that operator.
    """
    with get_db() as conn:
        c = conn.cursor()
        base = "FROM qso_log WHERE award_id = ?"
        params: List = [award_id]
        if operator_callsign:
            base += " AND operator_callsign = ?"
            params.append(operator_callsign.upper())

        total = c.execute(f"SELECT COUNT(*) {base}", params).fetchone()[0]
        unique_calls = c.execute(
            f"SELECT COUNT(DISTINCT call) {base}", params
        ).fetchone()[0]
        by_band = {
            row[0]: row[1]
            for row in c.execute(
                f"SELECT band, COUNT(*) {base} GROUP BY band ORDER BY 2 DESC",
                params,
            )
        }
        by_mode = {
            row[0]: row[1]
            for row in c.execute(
                f"SELECT mode, COUNT(*) {base} GROUP BY mode ORDER BY 2 DESC",
                params,
            )
        }
        by_operator: Dict[str, int] = {}
        if not operator_callsign:
            by_operator = {
                row[0]: row[1]
                for row in c.execute(
                    "SELECT operator_callsign, COUNT(*) FROM qso_log "
                    "WHERE award_id = ? GROUP BY operator_callsign "
                    "ORDER BY 2 DESC",
                    [award_id],
                )
            }
        return {
            "total": total,
            "unique_calls": unique_calls,
            "by_band": by_band,
            "by_mode": by_mode,
            "by_operator": by_operator,
        }


def get_qsos_by_date(
    award_id: int, operator_callsign: Optional[str] = None
) -> List[Dict]:
    """QSO count per date, oldest first. For the activity timeline chart."""
    base = "FROM qso_log WHERE award_id = ?"
    params: List = [award_id]
    if operator_callsign:
        base += " AND operator_callsign = ?"
        params.append(operator_callsign.upper())
    with get_db() as conn:
        rows = conn.execute(
            f"SELECT qso_date, COUNT(*) AS cnt {base} "
            "GROUP BY qso_date ORDER BY qso_date",
            params,
        ).fetchall()
        return [{"date": r[0], "count": r[1]} for r in rows]


def get_qsos_by_hour(
    award_id: int, operator_callsign: Optional[str] = None
) -> List[Dict]:
    """QSO count per UTC hour (0-23). For the hourly activity chart."""
    base = "FROM qso_log WHERE award_id = ?"
    params: List = [award_id]
    if operator_callsign:
        base += " AND operator_callsign = ?"
        params.append(operator_callsign.upper())
    with get_db() as conn:
        rows = conn.execute(
            f"SELECT CAST(SUBSTR(time_on, 1, 2) AS INTEGER) AS hour, "
            f"COUNT(*) AS cnt {base} GROUP BY hour ORDER BY hour",
            params,
        ).fetchall()
        return [{"hour": r[0], "count": r[1]} for r in rows]


def get_qsos_band_mode_matrix(
    award_id: int, operator_callsign: Optional[str] = None
) -> List[Dict]:
    """QSO count per band/mode pair. For the band×mode heatmap."""
    base = "FROM qso_log WHERE award_id = ?"
    params: List = [award_id]
    if operator_callsign:
        base += " AND operator_callsign = ?"
        params.append(operator_callsign.upper())
    with get_db() as conn:
        rows = conn.execute(
            f"SELECT band, mode, COUNT(*) AS cnt {base} "
            "GROUP BY band, mode ORDER BY cnt DESC",
            params,
        ).fetchall()
        return [{"band": r[0], "mode": r[1], "count": r[2]} for r in rows]


def get_qsos_page(
    award_id: int,
    operator_callsign: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    band: Optional[str] = None,
    mode: Optional[str] = None,
) -> List[dict]:
    """Paginated QSO view for an award, most-recent first.

    `operator_callsign=None` returns everyone's QSOs (admin view).
    """
    where = "WHERE award_id = ?"
    params: List = [award_id]
    if operator_callsign:
        where += " AND operator_callsign = ?"
        params.append(operator_callsign.upper())
    if band:
        where += " AND band = ?"
        params.append(band)
    if mode:
        where += " AND mode = ?"
        params.append(mode)
    params.extend([limit, offset])

    with get_db() as conn:
        cursor = conn.execute(
            f"""SELECT * FROM qso_log {where}
                ORDER BY qso_date DESC, time_on DESC, id DESC
                LIMIT ? OFFSET ?""",
            params,
        )
        return [dict(row) for row in cursor.fetchall()]


def count_qsos(
    award_id: int,
    operator_callsign: Optional[str] = None,
    band: Optional[str] = None,
    mode: Optional[str] = None,
) -> int:
    """Return the total number of QSOs matching the filters (for pagination)."""
    where = "WHERE award_id = ?"
    params: List = [award_id]
    if operator_callsign:
        where += " AND operator_callsign = ?"
        params.append(operator_callsign.upper())
    if band:
        where += " AND band = ?"
        params.append(band)
    if mode:
        where += " AND mode = ?"
        params.append(mode)
    with get_db() as conn:
        row = conn.execute(
            f"SELECT COUNT(*) FROM qso_log {where}", params
        ).fetchone()
        return row[0] if row else 0


def get_upload_batches(
    award_id: int,
    operator_callsign: Optional[str] = None,
    limit: int = 20,
) -> List[dict]:
    """Return recent upload batches (newest first) for display/undo."""
    where = "WHERE award_id = ?"
    params: List = [award_id]
    if operator_callsign:
        where += " AND operator_callsign = ?"
        params.append(operator_callsign.upper())
    params.append(limit)
    with get_db() as conn:
        cursor = conn.execute(
            f"""SELECT * FROM qso_upload_batch {where}
                ORDER BY uploaded_at DESC, id DESC LIMIT ?""",
            params,
        )
        return [dict(row) for row in cursor.fetchall()]


def delete_batch(
    batch_id: int, operator_callsign: Optional[str] = None
) -> Tuple[bool, int]:
    """Delete a batch and all QSOs tagged with it.

    If operator_callsign is provided, only the owning operator can delete
    the batch (non-admin safety check).
    Returns (ok, qsos_removed).
    """
    with get_db() as conn:
        cursor = conn.cursor()
        row = cursor.execute(
            "SELECT operator_callsign FROM qso_upload_batch WHERE id = ?",
            (batch_id,),
        ).fetchone()
        if not row:
            return False, 0
        if operator_callsign and row["operator_callsign"] != operator_callsign.upper():
            return False, 0
        deleted = cursor.execute(
            "DELETE FROM qso_log WHERE batch_id = ?", (batch_id,)
        ).rowcount
        cursor.execute("DELETE FROM qso_upload_batch WHERE id = ?", (batch_id,))
        return True, deleted


def delete_all_qsos_for_award(award_id: int) -> int:
    """Admin helper: wipe every QSO (and batch) for a given award."""
    with get_db() as conn:
        cursor = conn.cursor()
        deleted = cursor.execute(
            "DELETE FROM qso_log WHERE award_id = ?", (award_id,)
        ).rowcount
        cursor.execute(
            "DELETE FROM qso_upload_batch WHERE award_id = ?", (award_id,)
        )
        return deleted


# ---------------------------------------------------------------------------
# ADIF export
# ---------------------------------------------------------------------------

def _adif_field(name: str, value) -> str:
    """Format a single ADIF field: <name:len>value"""
    if value is None:
        return ""
    s = str(value)
    return f"<{name}:{len(s)}>{s}"


def export_qsos_to_adif(
    qsos: Iterable[dict],
    station_callsign: str = "",
    program_version: str = "1.0.0",
) -> str:
    """Format a list of QSO rows as a valid ADIF 3.1.4 document."""
    now = datetime.utcnow().strftime("%Y%m%d %H%M%S")
    lines = [
        f"ADIF export from QuendAward - {now}",
        "<adif_ver:5>3.1.4",
        "<programid:10>QuendAward",
        f"<programversion:{len(program_version)}>{program_version}",
        "<eoh>",
        "",
    ]
    for q in qsos:
        record: List[str] = []
        record.append(_adif_field("call", q.get("call")))
        record.append(_adif_field("band", q.get("band")))
        record.append(_adif_field("mode", q.get("mode")))

        qdate = (q.get("qso_date") or "").replace("-", "")
        if qdate:
            record.append(_adif_field("qso_date", qdate))
        ton = (q.get("time_on") or "").replace(":", "")
        if ton:
            record.append(_adif_field("time_on", ton))

        if q.get("rst_sent"):
            record.append(_adif_field("rst_sent", q["rst_sent"]))
        if q.get("rst_rcvd"):
            record.append(_adif_field("rst_rcvd", q["rst_rcvd"]))
        if q.get("freq") is not None:
            record.append(_adif_field("freq", f"{float(q['freq']):.5f}".rstrip("0").rstrip(".")))
        if q.get("name"):
            record.append(_adif_field("name", q["name"]))
        if q.get("qth"):
            record.append(_adif_field("qth", q["qth"]))
        if q.get("gridsquare"):
            record.append(_adif_field("gridsquare", q["gridsquare"]))
        if q.get("comment"):
            record.append(_adif_field("comment", q["comment"]))
        if station_callsign:
            record.append(_adif_field("station_callsign", station_callsign))
        if q.get("operator_callsign"):
            record.append(_adif_field("operator", q["operator_callsign"]))

        record.append("<eor>")
        lines.append("".join(r for r in record if r))
    return "\n".join(lines) + "\n"
