# Plan: Unified Logging System for QuendAward

## Overview

Implement a centralized logging system to track all application activities, errors, and user actions. Provides audit trail, debugging capability, and operational insights.

---

## Current State

Currently the application has:
- No structured logging
- `print()` statements for debugging
- No audit trail of user actions
- No error tracking
- No way for admins to review activity

---

## Proposed Log Categories

| Category | Description | Examples |
|----------|-------------|----------|
| `AUTH` | Authentication events | Login, logout, failed attempts |
| `BLOCK` | Band/mode operations | Block, unblock actions |
| `ADMIN` | Admin actions | Create/delete operators, change roles |
| `AWARD` | Special callsign management | Create, delete, toggle status |
| `SYSTEM` | System events | Startup, database operations, errors |
| `SPOT` | DX Cluster spots (future) | Spot sent, spot failed |
| `CHAT` | Chat messages (future) | Message sent, deleted |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        QuendAward Application                        │
├──────────┬──────────┬──────────┬──────────┬──────────┬──────────────┤
│  app.py  │ database │  admin   │    ui    │  charts  │   future     │
│          │   .py    │ _funcs   │ _comps   │   .py    │  modules     │
└────┬─────┴────┬─────┴────┬─────┴────┬─────┴────┬─────┴──────┬───────┘
     │          │          │          │          │            │
     └──────────┴──────────┴──────────┴──────────┴────────────┘
                                   │
                                   ▼
                    ┌──────────────────────────┐
                    │      logger.py           │
                    │  (Unified Logging Module)│
                    └────────────┬─────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
              ▼                  ▼                  ▼
     ┌─────────────┐    ┌─────────────┐    ┌─────────────┐
     │   SQLite    │    │  Log Files  │    │   Console   │
     │  (activity  │    │ (rotating)  │    │  (debug)    │
     │    _logs)   │    │             │    │             │
     └─────────────┘    └─────────────┘    └─────────────┘
```

---

## Database Schema

### New Table: `activity_logs`

```sql
CREATE TABLE IF NOT EXISTS activity_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    level TEXT NOT NULL,              -- INFO, WARNING, ERROR, DEBUG
    category TEXT NOT NULL,           -- AUTH, BLOCK, ADMIN, AWARD, SYSTEM
    operator_callsign TEXT,           -- Who performed the action (NULL for system)
    action TEXT NOT NULL,             -- Short action identifier
    details TEXT,                     -- JSON with additional details
    award_id INTEGER,                 -- Related award (if applicable)
    ip_address TEXT,                  -- Client IP (if available)
    user_agent TEXT,                  -- Browser info (if available)
    FOREIGN KEY (award_id) REFERENCES awards (id)
)

-- Index for efficient querying
CREATE INDEX idx_logs_timestamp ON activity_logs(timestamp);
CREATE INDEX idx_logs_category ON activity_logs(category);
CREATE INDEX idx_logs_operator ON activity_logs(operator_callsign);
```

---

## Logger Module

### New File: `logger.py`

```python
"""Unified logging system for QuendAward."""

import logging
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any
from logging.handlers import RotatingFileHandler

# Configuration
LOG_TO_DATABASE = os.getenv('LOG_TO_DATABASE', 'true').lower() == 'true'
LOG_TO_FILE = os.getenv('LOG_TO_FILE', 'true').lower() == 'true'
LOG_FILE_PATH = os.getenv('LOG_FILE_PATH', '/app/data/quendaward.log')
LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
LOG_MAX_SIZE_MB = int(os.getenv('LOG_MAX_SIZE_MB', '10'))
LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', '5'))

# Categories
class LogCategory:
    AUTH = 'AUTH'
    BLOCK = 'BLOCK'
    ADMIN = 'ADMIN'
    AWARD = 'AWARD'
    SYSTEM = 'SYSTEM'
    SPOT = 'SPOT'
    CHAT = 'CHAT'
    ERROR = 'ERROR'

# Setup Python logger
_logger = logging.getLogger('quendaward')
_logger.setLevel(getattr(logging, LOG_LEVEL))

# Console handler
_console_handler = logging.StreamHandler()
_console_handler.setFormatter(logging.Formatter(
    '%(asctime)s [%(levelname)s] %(message)s'
))
_logger.addHandler(_console_handler)

# File handler (rotating)
if LOG_TO_FILE:
    os.makedirs(os.path.dirname(LOG_FILE_PATH), exist_ok=True)
    _file_handler = RotatingFileHandler(
        LOG_FILE_PATH,
        maxBytes=LOG_MAX_SIZE_MB * 1024 * 1024,
        backupCount=LOG_BACKUP_COUNT
    )
    _file_handler.setFormatter(logging.Formatter(
        '%(asctime)s [%(levelname)s] [%(category)s] %(message)s'
    ))
    _logger.addHandler(_file_handler)


def log(
    level: str,
    category: str,
    action: str,
    details: Optional[Dict[str, Any]] = None,
    operator_callsign: Optional[str] = None,
    award_id: Optional[int] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None
):
    """
    Log an event to all configured outputs.

    Args:
        level: INFO, WARNING, ERROR, DEBUG
        category: LogCategory constant
        action: Short action identifier (e.g., 'LOGIN_SUCCESS')
        details: Additional data as dictionary
        operator_callsign: Who performed the action
        award_id: Related award ID
        ip_address: Client IP
        user_agent: Browser info
    """
    # Format message for text loggers
    message = f"[{category}] {action}"
    if operator_callsign:
        message += f" | User: {operator_callsign}"
    if details:
        message += f" | {json.dumps(details)}"

    # Log to Python logger (console + file)
    log_func = getattr(_logger, level.lower(), _logger.info)
    log_func(message, extra={'category': category})

    # Log to database
    if LOG_TO_DATABASE:
        _log_to_database(
            level, category, action, details,
            operator_callsign, award_id, ip_address, user_agent
        )


def _log_to_database(level, category, action, details,
                      operator_callsign, award_id, ip_address, user_agent):
    """Store log entry in database."""
    try:
        import database as db
        db.insert_log_entry(
            level=level,
            category=category,
            action=action,
            details=json.dumps(details) if details else None,
            operator_callsign=operator_callsign,
            award_id=award_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
    except Exception as e:
        _logger.error(f"Failed to log to database: {e}")


# Convenience functions
def info(category: str, action: str, **kwargs):
    log('INFO', category, action, **kwargs)

def warning(category: str, action: str, **kwargs):
    log('WARNING', category, action, **kwargs)

def error(category: str, action: str, **kwargs):
    log('ERROR', category, action, **kwargs)

def debug(category: str, action: str, **kwargs):
    log('DEBUG', category, action, **kwargs)


# Specific logging functions for common actions
def log_login(callsign: str, success: bool, reason: str = None):
    """Log authentication attempt."""
    action = 'LOGIN_SUCCESS' if success else 'LOGIN_FAILED'
    details = {'reason': reason} if reason else None
    level = 'INFO' if success else 'WARNING'
    log(level, LogCategory.AUTH, action, details, operator_callsign=callsign)

def log_logout(callsign: str):
    """Log user logout."""
    info(LogCategory.AUTH, 'LOGOUT', operator_callsign=callsign)

def log_block(callsign: str, band: str, mode: str, award_id: int, award_name: str):
    """Log band/mode block action."""
    info(LogCategory.BLOCK, 'BLOCK_CREATED',
         details={'band': band, 'mode': mode, 'award': award_name},
         operator_callsign=callsign, award_id=award_id)

def log_unblock(callsign: str, band: str, mode: str, award_id: int, award_name: str):
    """Log band/mode unblock action."""
    info(LogCategory.BLOCK, 'BLOCK_REMOVED',
         details={'band': band, 'mode': mode, 'award': award_name},
         operator_callsign=callsign, award_id=award_id)

def log_operator_created(admin_callsign: str, new_callsign: str, is_admin: bool):
    """Log operator creation."""
    info(LogCategory.ADMIN, 'OPERATOR_CREATED',
         details={'new_operator': new_callsign, 'is_admin': is_admin},
         operator_callsign=admin_callsign)

def log_operator_deleted(admin_callsign: str, deleted_callsign: str):
    """Log operator deletion."""
    warning(LogCategory.ADMIN, 'OPERATOR_DELETED',
            details={'deleted_operator': deleted_callsign},
            operator_callsign=admin_callsign)

def log_award_created(admin_callsign: str, award_name: str, award_id: int):
    """Log award/special callsign creation."""
    info(LogCategory.AWARD, 'AWARD_CREATED',
         details={'award_name': award_name},
         operator_callsign=admin_callsign, award_id=award_id)

def log_award_deleted(admin_callsign: str, award_name: str):
    """Log award deletion."""
    warning(LogCategory.AWARD, 'AWARD_DELETED',
            details={'award_name': award_name},
            operator_callsign=admin_callsign)

def log_database_backup(admin_callsign: str):
    """Log database backup."""
    info(LogCategory.SYSTEM, 'DATABASE_BACKUP',
         operator_callsign=admin_callsign)

def log_database_restore(admin_callsign: str, success: bool):
    """Log database restore attempt."""
    action = 'DATABASE_RESTORE_SUCCESS' if success else 'DATABASE_RESTORE_FAILED'
    level = 'WARNING'  # Always warning for restore operations
    log(level, LogCategory.SYSTEM, action, operator_callsign=admin_callsign)

def log_error(error_message: str, exception: Exception = None, **kwargs):
    """Log application error."""
    details = {'message': error_message}
    if exception:
        details['exception'] = str(exception)
        details['type'] = type(exception).__name__
    error(LogCategory.ERROR, 'APPLICATION_ERROR', details=details, **kwargs)

def log_system_start():
    """Log application startup."""
    info(LogCategory.SYSTEM, 'APPLICATION_START')
```

---

## Database Functions

### Add to `database.py`

```python
def insert_log_entry(level, category, action, details=None,
                     operator_callsign=None, award_id=None,
                     ip_address=None, user_agent=None):
    """Insert a log entry into the database."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO activity_logs
        (level, category, operator_callsign, action, details,
         award_id, ip_address, user_agent)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (level, category, operator_callsign, action, details,
          award_id, ip_address, user_agent))
    conn.commit()
    conn.close()


def get_logs(
    limit: int = 100,
    offset: int = 0,
    category: str = None,
    operator_callsign: str = None,
    level: str = None,
    start_date: str = None,
    end_date: str = None,
    award_id: int = None
) -> list:
    """
    Retrieve logs with optional filters.

    Returns list of log entries as dictionaries.
    """
    conn = get_connection()
    cursor = conn.cursor()

    query = 'SELECT * FROM activity_logs WHERE 1=1'
    params = []

    if category:
        query += ' AND category = ?'
        params.append(category)
    if operator_callsign:
        query += ' AND operator_callsign = ?'
        params.append(operator_callsign)
    if level:
        query += ' AND level = ?'
        params.append(level)
    if start_date:
        query += ' AND timestamp >= ?'
        params.append(start_date)
    if end_date:
        query += ' AND timestamp <= ?'
        params.append(end_date)
    if award_id:
        query += ' AND award_id = ?'
        params.append(award_id)

    query += ' ORDER BY timestamp DESC LIMIT ? OFFSET ?'
    params.extend([limit, offset])

    cursor.execute(query, params)
    results = cursor.fetchall()
    conn.close()

    return [dict(row) for row in results]


def get_log_stats() -> dict:
    """Get logging statistics."""
    conn = get_connection()
    cursor = conn.cursor()

    stats = {}

    # Total count
    cursor.execute('SELECT COUNT(*) FROM activity_logs')
    stats['total_entries'] = cursor.fetchone()[0]

    # Count by category
    cursor.execute('''
        SELECT category, COUNT(*) as count
        FROM activity_logs
        GROUP BY category
    ''')
    stats['by_category'] = {row[0]: row[1] for row in cursor.fetchall()}

    # Count by level
    cursor.execute('''
        SELECT level, COUNT(*) as count
        FROM activity_logs
        GROUP BY level
    ''')
    stats['by_level'] = {row[0]: row[1] for row in cursor.fetchall()}

    # Recent errors count (last 24h)
    cursor.execute('''
        SELECT COUNT(*) FROM activity_logs
        WHERE level = 'ERROR'
        AND timestamp > datetime('now', '-1 day')
    ''')
    stats['recent_errors'] = cursor.fetchone()[0]

    conn.close()
    return stats


def cleanup_old_logs(days: int = 90) -> int:
    """Delete logs older than specified days. Returns count deleted."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        DELETE FROM activity_logs
        WHERE timestamp < datetime('now', ? || ' days')
    ''', (f'-{days}',))
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted


def export_logs_csv(filters: dict = None) -> str:
    """Export logs to CSV format."""
    import csv
    import io

    logs = get_logs(limit=10000, **filters) if filters else get_logs(limit=10000)

    output = io.StringIO()
    if logs:
        writer = csv.DictWriter(output, fieldnames=logs[0].keys())
        writer.writeheader()
        writer.writerows(logs)

    return output.getvalue()
```

---

## Admin UI for Logs

### Add to `admin_functions.py`

```python
def render_logs_tab(t):
    """Render the activity logs tab."""
    import pandas as pd
    from datetime import datetime, timedelta

    st.subheader(f"📋 {t['activity_logs']}")

    # Log statistics
    stats = db.get_log_stats()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(t['total_log_entries'], stats['total_entries'])
    with col2:
        st.metric(t['errors_24h'], stats['recent_errors'])
    with col3:
        auth_count = stats['by_category'].get('AUTH', 0)
        st.metric(t['auth_events'], auth_count)
    with col4:
        block_count = stats['by_category'].get('BLOCK', 0)
        st.metric(t['block_events'], block_count)

    st.divider()

    # Filters
    st.subheader(t['filter_logs'])

    col1, col2, col3 = st.columns(3)
    with col1:
        category_filter = st.selectbox(
            t['category'],
            options=['All', 'AUTH', 'BLOCK', 'ADMIN', 'AWARD', 'SYSTEM', 'ERROR'],
            key='log_category_filter'
        )
    with col2:
        level_filter = st.selectbox(
            t['level'],
            options=['All', 'INFO', 'WARNING', 'ERROR', 'DEBUG'],
            key='log_level_filter'
        )
    with col3:
        operator_filter = st.text_input(
            t['operator_callsign_filter'],
            key='log_operator_filter'
        ).upper() or None

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(
            t['start_date'],
            value=datetime.now() - timedelta(days=7),
            key='log_start_date'
        )
    with col2:
        end_date = st.date_input(
            t['end_date'],
            value=datetime.now(),
            key='log_end_date'
        )

    # Fetch logs with filters
    filters = {}
    if category_filter != 'All':
        filters['category'] = category_filter
    if level_filter != 'All':
        filters['level'] = level_filter
    if operator_filter:
        filters['operator_callsign'] = operator_filter
    if start_date:
        filters['start_date'] = start_date.strftime('%Y-%m-%d')
    if end_date:
        filters['end_date'] = (end_date + timedelta(days=1)).strftime('%Y-%m-%d')

    logs = db.get_logs(limit=500, **filters)

    st.divider()

    # Display logs
    st.subheader(f"{t['log_entries']} ({len(logs)})")

    if logs:
        df = pd.DataFrame(logs)

        # Format timestamp
        df['timestamp'] = pd.to_datetime(df['timestamp']).dt.strftime('%Y-%m-%d %H:%M:%S')

        # Select columns to display
        display_cols = ['timestamp', 'level', 'category', 'operator_callsign', 'action', 'details']
        df_display = df[display_cols]

        # Color code by level
        def highlight_level(row):
            colors = {
                'ERROR': 'background-color: #ffcccc',
                'WARNING': 'background-color: #fff3cd',
                'INFO': '',
                'DEBUG': 'background-color: #e8e8e8'
            }
            return [colors.get(row['level'], '')] * len(row)

        st.dataframe(
            df_display.style.apply(highlight_level, axis=1),
            use_container_width=True,
            hide_index=True
        )

        # Export button
        col1, col2 = st.columns([1, 4])
        with col1:
            csv_data = db.export_logs_csv(filters)
            st.download_button(
                label=t['export_csv'],
                data=csv_data,
                file_name=f"quendaward_logs_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    else:
        st.info(t['no_logs_found'])

    st.divider()

    # Log maintenance
    st.subheader(t['log_maintenance'])

    col1, col2 = st.columns(2)
    with col1:
        retention_days = st.number_input(
            t['retention_days'],
            min_value=7,
            max_value=365,
            value=90,
            key='log_retention'
        )
    with col2:
        if st.button(t['cleanup_old_logs'], type='secondary'):
            deleted = db.cleanup_old_logs(retention_days)
            st.success(f"{t['logs_deleted']}: {deleted}")
```

---

## Integration Points

### Files to Modify

| File | Changes |
|------|---------|
| `app.py` | Add startup log, login/logout logging |
| `database.py` | Add log table creation, log functions |
| `admin_functions.py` | Add logging to admin actions, add logs tab |
| `ui_components.py` | Add logging to block/unblock actions |
| `config.py` | Add logging configuration |
| `translations.py` | Add log-related translations |

### Example Integrations

**Login (`app.py`):**
```python
from logger import log_login, log_logout

# After successful login
log_login(callsign, success=True)

# After failed login
log_login(callsign, success=False, reason=message)

# On logout
log_logout(st.session_state.callsign)
```

**Block/Unblock (`database.py`):**
```python
from logger import log_block, log_unblock

def block_band_mode(callsign, band, mode, award_id):
    # ... existing code ...
    if success:
        award = get_award_by_id(award_id)
        log_block(callsign, band, mode, award_id, award['name'])
    return success, message
```

**Admin Actions (`admin_functions.py`):**
```python
from logger import log_operator_created, log_operator_deleted

# After creating operator
log_operator_created(
    st.session_state.callsign,
    new_callsign,
    is_admin
)
```

---

## Environment Variables

```bash
# Logging Configuration
LOG_TO_DATABASE=true        # Store logs in SQLite
LOG_TO_FILE=true            # Write to rotating log files
LOG_FILE_PATH=/app/data/quendaward.log
LOG_LEVEL=INFO              # DEBUG, INFO, WARNING, ERROR
LOG_MAX_SIZE_MB=10          # Max size before rotation
LOG_BACKUP_COUNT=5          # Number of backup files to keep
LOG_RETENTION_DAYS=90       # Auto-cleanup after X days
```

---

## Translations

### English
```python
# Activity Logs
'tab_logs': 'Activity Logs',
'activity_logs': 'Activity Logs',
'total_log_entries': 'Total Entries',
'errors_24h': 'Errors (24h)',
'auth_events': 'Auth Events',
'block_events': 'Block Events',
'filter_logs': 'Filter Logs',
'category': 'Category',
'level': 'Level',
'operator_callsign_filter': 'Operator Callsign',
'log_entries': 'Log Entries',
'no_logs_found': 'No logs found matching the filters',
'export_csv': 'Export CSV',
'log_maintenance': 'Log Maintenance',
'retention_days': 'Retention (days)',
'cleanup_old_logs': 'Cleanup Old Logs',
'logs_deleted': 'Logs deleted',
```

### Spanish
```python
'tab_logs': 'Registros de Actividad',
'activity_logs': 'Registros de Actividad',
'total_log_entries': 'Total de Entradas',
'errors_24h': 'Errores (24h)',
'auth_events': 'Eventos de Auth',
'block_events': 'Eventos de Bloqueo',
'filter_logs': 'Filtrar Registros',
'category': 'Categoría',
'level': 'Nivel',
'operator_callsign_filter': 'Indicativo del Operador',
'log_entries': 'Entradas de Registro',
'no_logs_found': 'No se encontraron registros con los filtros aplicados',
'export_csv': 'Exportar CSV',
'log_maintenance': 'Mantenimiento de Registros',
'retention_days': 'Retención (días)',
'cleanup_old_logs': 'Limpiar Registros Antiguos',
'logs_deleted': 'Registros eliminados',
```

---

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `logger.py` | **Create** | Unified logging module |
| `database.py` | Modify | Add logs table + CRUD functions |
| `app.py` | Modify | Add startup log, auth logging |
| `admin_functions.py` | Modify | Add logs tab, log admin actions |
| `ui_components.py` | Modify | Log block/unblock actions |
| `config.py` | Modify | Add logging config |
| `translations.py` | Modify | Add translations (EN/ES/GL) |
| `Dockerfile` | Modify | Add logger.py to COPY |

---

## Log Output Examples

### Console/File Output
```
2026-01-24 15:30:45 [INFO] [AUTH] LOGIN_SUCCESS | User: EA4ABC
2026-01-24 15:31:02 [INFO] [BLOCK] BLOCK_CREATED | User: EA4ABC | {"band": "20m", "mode": "CW", "award": "EG90IARU"}
2026-01-24 15:35:18 [WARNING] [AUTH] LOGIN_FAILED | User: EA4XYZ | {"reason": "Invalid password"}
2026-01-24 15:40:00 [INFO] [ADMIN] OPERATOR_CREATED | User: EA4ABC | {"new_operator": "EA4DEF", "is_admin": false}
2026-01-24 16:00:00 [ERROR] [ERROR] APPLICATION_ERROR | {"message": "Database connection failed", "type": "sqlite3.OperationalError"}
```

### Database View (Admin UI)
```
┌────────────────────┬─────────┬──────────┬───────────┬─────────────────┬─────────────────────────────────────┐
│ Timestamp          │ Level   │ Category │ Operator  │ Action          │ Details                             │
├────────────────────┼─────────┼──────────┼───────────┼─────────────────┼─────────────────────────────────────┤
│ 2026-01-24 15:30:45│ INFO    │ AUTH     │ EA4ABC    │ LOGIN_SUCCESS   │                                     │
│ 2026-01-24 15:31:02│ INFO    │ BLOCK    │ EA4ABC    │ BLOCK_CREATED   │ {"band":"20m","mode":"CW",...}      │
│ 2026-01-24 15:35:18│ WARNING │ AUTH     │ EA4XYZ    │ LOGIN_FAILED    │ {"reason":"Invalid password"}       │
│ 2026-01-24 15:40:00│ INFO    │ ADMIN    │ EA4ABC    │ OPERATOR_CREATED│ {"new_operator":"EA4DEF",...}       │
└────────────────────┴─────────┴──────────┴───────────┴─────────────────┴─────────────────────────────────────┘
```

---

## Estimated Effort

| Phase | Description | Time |
|-------|-------------|------|
| 1 | Create logger.py module | 1-2 hours |
| 2 | Database functions | 1 hour |
| 3 | Integrate with existing code | 2-3 hours |
| 4 | Admin UI for logs | 2 hours |
| 5 | Translations | 30 min |
| 6 | Testing | 1 hour |

**Total: ~8-10 hours**

---

## Future Enhancements

1. **Real-time log streaming** - WebSocket-based live log view
2. **Alert system** - Email/Telegram on errors
3. **Log analytics** - Charts showing activity patterns
4. **Audit reports** - Generate PDF reports for specific periods
5. **Log archiving** - Compress and store old logs
6. **External logging** - Send to ELK stack, Datadog, etc.

---

## Dependencies

No new dependencies required - uses Python standard library:
- `logging` - Built-in
- `json` - Built-in
- `csv` - Built-in
- `io` - Built-in
