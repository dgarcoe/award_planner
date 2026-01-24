# Plan: QSO Logging System for QuendAward

## Overview

Add a QSO (contact) logging system so operators can log contacts made while operating the special callsign. Includes ADIF export for uploading to LoTW, ClubLog, eQSL, etc.

---

## Core Features

1. **Log QSOs** - Record contacts with essential fields
2. **View/Edit Logs** - See all contacts, make corrections
3. **ADIF Export** - Standard format for uploading to external services
4. **Statistics** - QSO counts by band, mode, operator
5. **Unified Log** - Admins can see all QSOs across all operators

---

## QSO Data Fields

### Required Fields
| Field | Description | Example |
|-------|-------------|---------|
| `call` | Worked station callsign | `EA1ABC` |
| `band` | Operating band | `20m` |
| `mode` | Operating mode | `CW` |
| `qso_date` | Date (UTC) | `2026-01-24` |
| `time_on` | Start time (UTC) | `15:30` |
| `rst_sent` | RST sent | `599` |
| `rst_rcvd` | RST received | `579` |

### Optional Fields
| Field | Description | Example |
|-------|-------------|---------|
| `freq` | Frequency in MHz | `14.025` |
| `name` | Operator name | `John` |
| `qth` | Location | `Madrid` |
| `gridsquare` | Maidenhead locator | `IN80` |
| `comment` | Notes | `Good signal` |
| `contest_id` | Contest name | `CQ-WW-CW` |
| `srx` | Serial received | `001` |
| `stx` | Serial sent | `042` |

### System Fields (Auto-filled)
| Field | Description |
|-------|-------------|
| `operator_callsign` | Who logged it |
| `award_id` | Special callsign being operated |
| `station_callsign` | Special callsign (from award) |
| `created_at` | When logged |
| `modified_at` | Last edit time |

---

## Database Schema

### New Table: `qso_log`

```sql
CREATE TABLE IF NOT EXISTS qso_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,

    -- System fields
    award_id INTEGER NOT NULL,
    operator_callsign TEXT NOT NULL,

    -- Required QSO fields
    call TEXT NOT NULL,                    -- Worked station
    band TEXT NOT NULL,
    mode TEXT NOT NULL,
    qso_date TEXT NOT NULL,                -- YYYY-MM-DD
    time_on TEXT NOT NULL,                 -- HH:MM
    rst_sent TEXT DEFAULT '599',
    rst_rcvd TEXT DEFAULT '599',

    -- Optional fields
    freq REAL,                             -- Frequency in MHz
    time_off TEXT,                         -- HH:MM (for long QSOs)
    name TEXT,
    qth TEXT,
    gridsquare TEXT,
    comment TEXT,

    -- Contest fields
    contest_id TEXT,
    srx TEXT,                              -- Serial received
    stx TEXT,                              -- Serial sent
    srx_string TEXT,                       -- Exchange received
    stx_string TEXT,                       -- Exchange sent

    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Foreign keys
    FOREIGN KEY (award_id) REFERENCES awards (id),
    FOREIGN KEY (operator_callsign) REFERENCES operators (callsign)
);

-- Indexes for efficient queries
CREATE INDEX idx_qso_date ON qso_log(qso_date);
CREATE INDEX idx_qso_call ON qso_log(call);
CREATE INDEX idx_qso_award ON qso_log(award_id);
CREATE INDEX idx_qso_operator ON qso_log(operator_callsign);
CREATE INDEX idx_qso_band_mode ON qso_log(band, mode);
```

---

## User Interface

### Operator View: Log Entry Tab

```
┌─────────────────────────────────────────────────────────────────────────┐
│  📝 Log QSO                                                              │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Callsign: [EA1ABC____]     Band: [20m ▼]     Mode: [CW ▼]              │
│                                                                          │
│  Date: [2026-01-24]         Time (UTC): [15:30]                         │
│                                                                          │
│  RST Sent: [599___]         RST Rcvd: [599___]                          │
│                                                                          │
│  ─── Optional ───────────────────────────────────────────────────────   │
│                                                                          │
│  Frequency: [14.025__] MHz  Name: [__________]  QTH: [__________]       │
│                                                                          │
│  Grid: [IN80__]             Comment: [________________________]         │
│                                                                          │
│                              [💾 Log QSO]                                │
│                                                                          │
├─────────────────────────────────────────────────────────────────────────┤
│  Recent QSOs (last 10)                                                   │
│  ┌────────┬───────┬──────┬───────┬───────┬────────┬────────┬─────────┐  │
│  │ Time   │ Call  │ Band │ Mode  │ RST S │ RST R  │ Name   │ Actions │  │
│  ├────────┼───────┼──────┼───────┼───────┼────────┼────────┼─────────┤  │
│  │ 15:30  │EA1ABC │ 20m  │ CW    │ 599   │ 579    │ John   │ ✏️ 🗑️   │  │
│  │ 15:25  │DL2XYZ │ 20m  │ CW    │ 599   │ 599    │ Hans   │ ✏️ 🗑️   │  │
│  │ 15:18  │G4ABC  │ 20m  │ CW    │ 599   │ 589    │        │ ✏️ 🗑️   │  │
│  └────────┴───────┴──────┴───────┴───────┴────────┴────────┴─────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

### Operator View: My Log Tab

```
┌─────────────────────────────────────────────────────────────────────────┐
│  📋 My QSO Log                                           [Export ADIF]  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Filters: Date [____] to [____]  Band [All ▼]  Mode [All ▼]  [🔍]      │
│                                                                          │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │ Date       │ Time  │ Call   │ Band │ Mode │ Freq    │ RST  │ Name  ││
│  ├─────────────────────────────────────────────────────────────────────┤│
│  │ 2026-01-24 │ 15:30 │ EA1ABC │ 20m  │ CW   │ 14.025  │ 599/579│ John ││
│  │ 2026-01-24 │ 15:25 │ DL2XYZ │ 20m  │ CW   │ 14.025  │ 599/599│ Hans ││
│  │ 2026-01-24 │ 14:45 │ W1AW   │ 40m  │ SSB  │ 7.185   │ 59/59 │ Hiram││
│  └─────────────────────────────────────────────────────────────────────┘│
│                                                                          │
│  Total: 127 QSOs                                         Page 1 of 13   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Admin View: Unified Log

```
┌─────────────────────────────────────────────────────────────────────────┐
│  📊 All QSOs - EG90IARU                                  [Export ADIF]  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  Statistics:                                                             │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐                    │
│  │ Total    │ │ Today    │ │ Operators│ │ Countries│                    │
│  │   1,247  │ │    89    │ │     12   │ │    67    │                    │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘                    │
│                                                                          │
│  QSOs by Band:        QSOs by Mode:        QSOs by Operator:            │
│  ┌─────────────┐      ┌─────────────┐      ┌─────────────────────┐      │
│  │ 20m  ████ 412│     │ CW   ████ 523│     │ EA4ABC  ████ 312   │      │
│  │ 40m  ███  298│     │ SSB  ███  401│     │ EA4DEF  ███  245   │      │
│  │ 15m  ██   187│     │ FT8  ██   198│     │ EA4GHI  ██   178   │      │
│  │ 10m  █    102│     │ RTTY █    125│     │ ...                 │      │
│  └─────────────┘      └─────────────┘      └─────────────────────┘      │
│                                                                          │
│  Full Log:                                                               │
│  ┌──────────────────────────────────────────────────────────────────────┐│
│  │ Date       │ Time │ Operator│ Call   │ Band │ Mode │ RST    │ Name  ││
│  ├──────────────────────────────────────────────────────────────────────┤│
│  │ 2026-01-24 │15:30 │ EA4ABC  │ EA1ABC │ 20m  │ CW   │ 599/579│ John  ││
│  └──────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────┘
```

---

## ADIF Export

### What is ADIF?

ADIF (Amateur Data Interchange Format) is the standard for exchanging ham radio log data. Used by:
- **LoTW** (Logbook of The World) - ARRL's QSL confirmation service
- **ClubLog** - DXCC tracking and statistics
- **eQSL** - Electronic QSL cards
- **QRZ.com** - Online logbook
- **Contest log submission**

### ADIF Format Example

```
ADIF Export from QuendAward
<adif_ver:5>3.1.4
<programid:10>QuendAward
<programversion:5>1.0.0
<eoh>

<call:6>EA1ABC<band:3>20m<mode:2>CW<qso_date:8>20260124<time_on:4>1530<rst_sent:3>599<rst_rcvd:3>579<station_callsign:8>EG90IARU<operator:6>EA4ABC<freq:6>14.025<name:4>John<eor>

<call:6>DL2XYZ<band:3>20m<mode:2>CW<qso_date:8>20260124<time_on:4>1525<rst_sent:3>599<rst_rcvd:3>599<station_callsign:8>EG90IARU<operator:6>EA4ABC<freq:6>14.025<name:4>Hans<eor>
```

### Export Function

```python
def export_qsos_to_adif(qsos: list, award_name: str) -> str:
    """
    Export QSOs to ADIF format.

    Args:
        qsos: List of QSO dictionaries
        award_name: Special callsign name (station_callsign)

    Returns:
        ADIF formatted string
    """
    lines = [
        "ADIF Export from QuendAward",
        "<adif_ver:5>3.1.4",
        f"<programid:10>QuendAward",
        f"<programversion:5>1.0.0",
        "<eoh>",
        ""
    ]

    for qso in qsos:
        record = []

        # Required fields
        record.append(f"<call:{len(qso['call'])}>{qso['call']}")
        record.append(f"<band:{len(qso['band'])}>{qso['band']}")
        record.append(f"<mode:{len(qso['mode'])}>{qso['mode']}")

        # Date/Time (ADIF format: YYYYMMDD, HHMM)
        date_str = qso['qso_date'].replace('-', '')
        time_str = qso['time_on'].replace(':', '')
        record.append(f"<qso_date:8>{date_str}")
        record.append(f"<time_on:4>{time_str}")

        # RST
        record.append(f"<rst_sent:{len(qso['rst_sent'])}>{qso['rst_sent']}")
        record.append(f"<rst_rcvd:{len(qso['rst_rcvd'])}>{qso['rst_rcvd']}")

        # Station info
        record.append(f"<station_callsign:{len(award_name)}>{award_name}")
        record.append(f"<operator:{len(qso['operator_callsign'])}>{qso['operator_callsign']}")

        # Optional fields
        if qso.get('freq'):
            freq_str = f"{qso['freq']:.3f}"
            record.append(f"<freq:{len(freq_str)}>{freq_str}")
        if qso.get('name'):
            record.append(f"<name:{len(qso['name'])}>{qso['name']}")
        if qso.get('qth'):
            record.append(f"<qth:{len(qso['qth'])}>{qso['qth']}")
        if qso.get('gridsquare'):
            record.append(f"<gridsquare:{len(qso['gridsquare'])}>{qso['gridsquare']}")
        if qso.get('comment'):
            record.append(f"<comment:{len(qso['comment'])}>{qso['comment']}")

        # End of record
        record.append("<eor>")

        lines.append("".join(record))
        lines.append("")

    return "\n".join(lines)
```

---

## Database Functions

### Add to `database.py`

```python
# QSO Logging Functions

def insert_qso(award_id: int, operator_callsign: str, qso_data: dict) -> Tuple[bool, str, int]:
    """
    Insert a new QSO into the log.

    Returns: (success, message, qso_id)
    """
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            INSERT INTO qso_log (
                award_id, operator_callsign, call, band, mode,
                qso_date, time_on, rst_sent, rst_rcvd,
                freq, time_off, name, qth, gridsquare, comment,
                contest_id, srx, stx, srx_string, stx_string
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            award_id, operator_callsign,
            qso_data['call'].upper(),
            qso_data['band'],
            qso_data['mode'],
            qso_data['qso_date'],
            qso_data['time_on'],
            qso_data.get('rst_sent', '599'),
            qso_data.get('rst_rcvd', '599'),
            qso_data.get('freq'),
            qso_data.get('time_off'),
            qso_data.get('name'),
            qso_data.get('qth'),
            qso_data.get('gridsquare'),
            qso_data.get('comment'),
            qso_data.get('contest_id'),
            qso_data.get('srx'),
            qso_data.get('stx'),
            qso_data.get('srx_string'),
            qso_data.get('stx_string')
        ))
        conn.commit()
        qso_id = cursor.lastrowid
        conn.close()
        return True, "QSO logged successfully", qso_id
    except Exception as e:
        conn.close()
        return False, str(e), None


def get_qsos(
    award_id: int = None,
    operator_callsign: str = None,
    start_date: str = None,
    end_date: str = None,
    band: str = None,
    mode: str = None,
    limit: int = 100,
    offset: int = 0
) -> list:
    """Get QSOs with optional filters."""
    conn = get_connection()
    cursor = conn.cursor()

    query = 'SELECT * FROM qso_log WHERE 1=1'
    params = []

    if award_id:
        query += ' AND award_id = ?'
        params.append(award_id)
    if operator_callsign:
        query += ' AND operator_callsign = ?'
        params.append(operator_callsign)
    if start_date:
        query += ' AND qso_date >= ?'
        params.append(start_date)
    if end_date:
        query += ' AND qso_date <= ?'
        params.append(end_date)
    if band:
        query += ' AND band = ?'
        params.append(band)
    if mode:
        query += ' AND mode = ?'
        params.append(mode)

    query += ' ORDER BY qso_date DESC, time_on DESC LIMIT ? OFFSET ?'
    params.extend([limit, offset])

    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()

    return [dict(row) for row in results]


def get_qso_stats(award_id: int) -> dict:
    """Get QSO statistics for an award."""
    conn = get_connection()
    cursor = conn.cursor()

    stats = {}

    # Total QSOs
    cursor.execute('SELECT COUNT(*) FROM qso_log WHERE award_id = ?', (award_id,))
    stats['total'] = cursor.fetchone()[0]

    # QSOs today
    cursor.execute('''
        SELECT COUNT(*) FROM qso_log
        WHERE award_id = ? AND qso_date = date('now')
    ''', (award_id,))
    stats['today'] = cursor.fetchone()[0]

    # By band
    cursor.execute('''
        SELECT band, COUNT(*) as count FROM qso_log
        WHERE award_id = ? GROUP BY band ORDER BY count DESC
    ''', (award_id,))
    stats['by_band'] = {row[0]: row[1] for row in cursor.fetchall()}

    # By mode
    cursor.execute('''
        SELECT mode, COUNT(*) as count FROM qso_log
        WHERE award_id = ? GROUP BY mode ORDER BY count DESC
    ''', (award_id,))
    stats['by_mode'] = {row[0]: row[1] for row in cursor.fetchall()}

    # By operator
    cursor.execute('''
        SELECT operator_callsign, COUNT(*) as count FROM qso_log
        WHERE award_id = ? GROUP BY operator_callsign ORDER BY count DESC
    ''', (award_id,))
    stats['by_operator'] = {row[0]: row[1] for row in cursor.fetchall()}

    # Unique callsigns (DXCCs approximation)
    cursor.execute('''
        SELECT COUNT(DISTINCT call) FROM qso_log WHERE award_id = ?
    ''', (award_id,))
    stats['unique_calls'] = cursor.fetchone()[0]

    # Active operators
    cursor.execute('''
        SELECT COUNT(DISTINCT operator_callsign) FROM qso_log WHERE award_id = ?
    ''', (award_id,))
    stats['active_operators'] = cursor.fetchone()[0]

    conn.close()
    return stats


def update_qso(qso_id: int, qso_data: dict) -> Tuple[bool, str]:
    """Update an existing QSO."""
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('''
            UPDATE qso_log SET
                call = ?, band = ?, mode = ?, qso_date = ?, time_on = ?,
                rst_sent = ?, rst_rcvd = ?, freq = ?, name = ?, qth = ?,
                gridsquare = ?, comment = ?, modified_at = CURRENT_TIMESTAMP
            WHERE id = ?
        ''', (
            qso_data['call'].upper(),
            qso_data['band'],
            qso_data['mode'],
            qso_data['qso_date'],
            qso_data['time_on'],
            qso_data.get('rst_sent', '599'),
            qso_data.get('rst_rcvd', '599'),
            qso_data.get('freq'),
            qso_data.get('name'),
            qso_data.get('qth'),
            qso_data.get('gridsquare'),
            qso_data.get('comment'),
            qso_id
        ))
        conn.commit()
        conn.close()
        return True, "QSO updated successfully"
    except Exception as e:
        conn.close()
        return False, str(e)


def delete_qso(qso_id: int, operator_callsign: str = None) -> Tuple[bool, str]:
    """
    Delete a QSO.
    If operator_callsign provided, only allow deleting own QSOs.
    """
    conn = get_connection()
    cursor = conn.cursor()

    query = 'DELETE FROM qso_log WHERE id = ?'
    params = [qso_id]

    if operator_callsign:
        query += ' AND operator_callsign = ?'
        params.append(operator_callsign)

    cursor.execute(query, params)
    deleted = cursor.rowcount
    conn.commit()
    conn.close()

    if deleted:
        return True, "QSO deleted"
    return False, "QSO not found or not authorized"
```

---

## UI Components

### Add to `ui_components.py`

```python
def render_qso_entry_form(t, award_id, callsign):
    """Render QSO entry form."""
    from datetime import datetime

    st.subheader(f"📝 {t['log_qso']}")

    with st.form("qso_entry_form", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)

        with col1:
            qso_call = st.text_input(
                t['worked_callsign'],
                max_chars=15,
                key="qso_call"
            ).upper()

        with col2:
            qso_band = st.selectbox(
                t['band_label'],
                options=BANDS,
                key="qso_band"
            )

        with col3:
            qso_mode = st.selectbox(
                t['mode_label'],
                options=MODES,
                key="qso_mode"
            )

        col1, col2 = st.columns(2)
        with col1:
            qso_date = st.date_input(
                t['qso_date'],
                value=datetime.utcnow(),
                key="qso_date"
            )
        with col2:
            qso_time = st.time_input(
                t['qso_time_utc'],
                value=datetime.utcnow().time(),
                key="qso_time"
            )

        col1, col2 = st.columns(2)
        with col1:
            rst_sent = st.text_input(t['rst_sent'], value="599", max_chars=3)
        with col2:
            rst_rcvd = st.text_input(t['rst_rcvd'], value="599", max_chars=3)

        # Optional fields in expander
        with st.expander(t['optional_fields']):
            col1, col2, col3 = st.columns(3)
            with col1:
                freq = st.number_input(
                    t['frequency_mhz'],
                    min_value=0.0,
                    max_value=500.0,
                    step=0.001,
                    format="%.3f",
                    key="qso_freq"
                )
            with col2:
                name = st.text_input(t['name'], max_chars=50)
            with col3:
                qth = st.text_input(t['qth'], max_chars=50)

            col1, col2 = st.columns(2)
            with col1:
                grid = st.text_input(t['gridsquare'], max_chars=6)
            with col2:
                comment = st.text_input(t['comment'], max_chars=200)

        submit = st.form_submit_button(f"💾 {t['log_qso']}", type="primary")

        if submit:
            if not qso_call:
                st.error(t['error_callsign_required'])
            else:
                qso_data = {
                    'call': qso_call,
                    'band': qso_band,
                    'mode': qso_mode,
                    'qso_date': qso_date.strftime('%Y-%m-%d'),
                    'time_on': qso_time.strftime('%H:%M'),
                    'rst_sent': rst_sent,
                    'rst_rcvd': rst_rcvd,
                    'freq': freq if freq > 0 else None,
                    'name': name or None,
                    'qth': qth or None,
                    'gridsquare': grid.upper() or None,
                    'comment': comment or None
                }

                success, message, qso_id = db.insert_qso(award_id, callsign, qso_data)
                if success:
                    st.success(f"{t['qso_logged']}: {qso_call}")
                    st.rerun()
                else:
                    st.error(message)


def render_qso_log_view(t, award_id, operator_callsign=None, is_admin=False):
    """Render QSO log view with filters and export."""
    st.subheader(f"📋 {t['qso_log']}")

    # Get stats
    stats = db.get_qso_stats(award_id)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(t['total_qsos'], stats['total'])
    with col2:
        st.metric(t['qsos_today'], stats['today'])
    with col3:
        st.metric(t['unique_callsigns'], stats['unique_calls'])
    with col4:
        st.metric(t['active_operators'], stats['active_operators'])

    # Filters
    col1, col2, col3 = st.columns(3)
    with col1:
        filter_band = st.selectbox(
            t['band_label'],
            options=['All'] + BANDS,
            key="qso_filter_band"
        )
    with col2:
        filter_mode = st.selectbox(
            t['mode_label'],
            options=['All'] + MODES,
            key="qso_filter_mode"
        )
    with col3:
        if is_admin:
            operators = list(stats['by_operator'].keys())
            filter_operator = st.selectbox(
                t['operator'],
                options=['All'] + operators,
                key="qso_filter_operator"
            )
        else:
            filter_operator = operator_callsign

    # Get QSOs
    filters = {'award_id': award_id, 'limit': 500}
    if filter_band != 'All':
        filters['band'] = filter_band
    if filter_mode != 'All':
        filters['mode'] = filter_mode
    if filter_operator and filter_operator != 'All':
        filters['operator_callsign'] = filter_operator

    qsos = db.get_qsos(**filters)

    # Display
    if qsos:
        import pandas as pd
        df = pd.DataFrame(qsos)
        display_cols = ['qso_date', 'time_on', 'call', 'band', 'mode', 'rst_sent', 'rst_rcvd']
        if is_admin:
            display_cols.insert(2, 'operator_callsign')

        st.dataframe(
            df[display_cols],
            use_container_width=True,
            hide_index=True
        )

        # Export button
        award = db.get_award_by_id(award_id)
        adif_data = export_qsos_to_adif(qsos, award['name'])

        st.download_button(
            label=f"📥 {t['export_adif']}",
            data=adif_data,
            file_name=f"{award['name']}_log.adi",
            mime="text/plain"
        )
    else:
        st.info(t['no_qsos'])
```

---

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `database.py` | Modify | Add qso_log table + CRUD functions |
| `ui_components.py` | Modify | Add QSO entry form + log view |
| `app.py` | Modify | Add QSO tab to operator panel |
| `admin_functions.py` | Modify | Add unified log view for admins |
| `translations.py` | Modify | Add QSO-related translations |
| `adif_export.py` | Create | ADIF export utilities (optional, can be in database.py) |

---

## Translations (Key Additions)

### English
```python
# QSO Logging
'tab_log_qso': 'Log QSO',
'tab_my_log': 'My Log',
'log_qso': 'Log QSO',
'qso_log': 'QSO Log',
'worked_callsign': 'Worked Callsign',
'qso_date': 'Date (UTC)',
'qso_time_utc': 'Time (UTC)',
'rst_sent': 'RST Sent',
'rst_rcvd': 'RST Received',
'frequency_mhz': 'Frequency (MHz)',
'gridsquare': 'Grid Square',
'comment': 'Comment',
'optional_fields': 'Optional Fields',
'qso_logged': 'QSO Logged',
'error_callsign_required': 'Callsign is required',
'total_qsos': 'Total QSOs',
'qsos_today': 'QSOs Today',
'unique_callsigns': 'Unique Calls',
'export_adif': 'Export ADIF',
'no_qsos': 'No QSOs logged yet',
```

---

## Future Enhancements

1. **ADIF Import** - Import existing logs
2. **Duplicate checking** - Warn on duplicate QSOs
3. **Real-time sync** - Sync with N1MM, Log4OM, etc.
4. **LoTW upload** - Direct upload to LoTW
5. **ClubLog upload** - Direct upload to ClubLog
6. **QSL tracking** - Track sent/received QSLs
7. **DXCC tracking** - Show new DXCC entities
8. **Contest mode** - Serial numbers, exchanges
9. **Cabrillo export** - For contest submissions

---

## Estimated Effort

| Phase | Description | Time |
|-------|-------------|------|
| 1 | Database schema + functions | 2 hours |
| 2 | QSO entry form UI | 2 hours |
| 3 | QSO log view + filters | 2 hours |
| 4 | ADIF export | 1 hour |
| 5 | Admin unified view | 1-2 hours |
| 6 | Translations | 30 min |
| 7 | Testing | 1-2 hours |

**Total: ~10-12 hours**

---

## Dependencies

No new dependencies required - uses Python standard library only.
