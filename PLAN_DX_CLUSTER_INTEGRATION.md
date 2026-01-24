# Plan: DX Cluster Integration for QuendAward

## Overview

Automatically announce spots to DX Clusters when operators block (start operating) a band/mode combination. This lets the ham radio community know the special callsign is active.

---

## What is a DX Cluster?

A DX Cluster is a network where ham radio operators share real-time information about stations they've heard or worked ("spots"). When a special callsign is spotted, operators worldwide can see it and try to make contact.

**Spot format:**
```
DX de EA4ABC:  14025.0  EG90IARU      CW 599 UP 2           1423Z
     │            │         │          │                      │
  Spotter      Freq(kHz)  Spotted    Comment               Time(UTC)
```

---

## Integration Concept

```
┌─────────────────┐     Block Event      ┌─────────────────┐
│   QuendAward    │ ──────────────────►  │  DX Cluster     │
│   (Streamlit)   │                      │  Connector      │
└─────────────────┘                      └────────┬────────┘
                                                  │
                    ┌─────────────────────────────┼─────────────────────────────┐
                    │                             │                             │
                    ▼                             ▼                             ▼
           ┌───────────────┐            ┌───────────────┐            ┌───────────────┐
           │  Telnet Node  │            │   DXWatch API │            │  HamQTH API   │
           │  (DX Spider)  │            │   (Web-based) │            │  (Web-based)  │
           └───────────────┘            └───────────────┘            └───────────────┘
```

---

## When to Announce Spots

| Event | Action | Spot Comment |
|-------|--------|--------------|
| Operator blocks band/mode | Send spot | "QRV on {band} {mode}" |
| Operator unblocks | Optional: No action or "QRT" | - |
| Frequency change (future) | Update spot | New frequency |

---

## Integration Options

### Option A: Telnet Connection (Traditional)

**How it works:**
- Connect to a DX Cluster node via Telnet (port 7300/8000)
- Authenticate with callsign
- Send spot command: `DX 14025.0 EG90IARU QRV on 20m CW`

**Pros:**
- Direct, real-time
- Works with most clusters (DX Spider, AR-Cluster, CC Cluster)
- No API keys needed

**Cons:**
- Requires persistent connection or reconnection logic
- Firewall/network issues possible
- Need to handle disconnections

**Popular Telnet Nodes:**
| Node | Address | Port |
|------|---------|------|
| DX Spider | dxspider.your-node.net | 7300 |
| AR-Cluster | arcluster.net | 7373 |
| VE7CC | ve7cc.net | 23 |

### Option B: Web API Integration

**DXWatch/DXSummit API:**
```
POST https://dxwatch.com/spot.php
Parameters:
  - spotter: EA4ABC
  - freq: 14025.0
  - spotted: EG90IARU
  - comment: QRV on 20m CW
```

**HamQTH Spot API:**
```
POST https://www.hamqth.com/dxc_api.php
```

**Pros:**
- Simpler HTTP requests
- No persistent connection needed
- Better for containerized apps

**Cons:**
- May require API key/registration
- Rate limits
- Not all clusters connected

### Option C: Hybrid Approach (Recommended)

1. Primary: Web API (simpler, reliable)
2. Fallback: Telnet for direct cluster access
3. Configurable per deployment

---

## Implementation Plan

### Phase 1: Database & Configuration

**New config options (`config.py`):**
```python
# DX Cluster Settings
DX_CLUSTER_ENABLED = os.getenv('DX_CLUSTER_ENABLED', 'false').lower() == 'true'
DX_CLUSTER_TYPE = os.getenv('DX_CLUSTER_TYPE', 'telnet')  # 'telnet' or 'api'

# Telnet settings
DX_CLUSTER_HOST = os.getenv('DX_CLUSTER_HOST', '')
DX_CLUSTER_PORT = int(os.getenv('DX_CLUSTER_PORT', '7300'))
DX_CLUSTER_CALLSIGN = os.getenv('DX_CLUSTER_CALLSIGN', '')  # Login callsign

# API settings (alternative)
DX_CLUSTER_API_URL = os.getenv('DX_CLUSTER_API_URL', '')
DX_CLUSTER_API_KEY = os.getenv('DX_CLUSTER_API_KEY', '')

# Spot settings
DX_SPOT_COMMENT_TEMPLATE = os.getenv('DX_SPOT_COMMENT', 'QRV {mode}')
```

**New database table (`spot_log`):**
```sql
CREATE TABLE IF NOT EXISTS spot_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    award_id INTEGER NOT NULL,
    operator_callsign TEXT NOT NULL,
    band TEXT NOT NULL,
    mode TEXT NOT NULL,
    frequency REAL,
    spotted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    cluster_response TEXT,
    success INTEGER DEFAULT 0,
    FOREIGN KEY (award_id) REFERENCES awards (id)
)
```

### Phase 2: Frequency Mapping

Need to map bands to frequencies for spots:

```python
BAND_FREQUENCIES = {
    # Band: {Mode: Default Frequency in kHz}
    '160m': {'CW': 1820.0, 'SSB': 1845.0, 'FT8': 1840.0, 'FT4': 1840.0, 'RTTY': 1842.0, 'Other': 1840.0},
    '80m':  {'CW': 3525.0, 'SSB': 3780.0, 'FT8': 3573.0, 'FT4': 3575.0, 'RTTY': 3590.0, 'Other': 3580.0},
    '60m':  {'CW': 5351.5, 'SSB': 5357.0, 'FT8': 5357.0, 'FT4': 5357.0, 'RTTY': 5357.0, 'Other': 5357.0},
    '40m':  {'CW': 7025.0, 'SSB': 7150.0, 'FT8': 7074.0, 'FT4': 7047.5, 'RTTY': 7040.0, 'Other': 7050.0},
    '30m':  {'CW': 10115.0, 'SSB': 10130.0, 'FT8': 10136.0, 'FT4': 10140.0, 'RTTY': 10142.0, 'Other': 10130.0},
    '20m':  {'CW': 14025.0, 'SSB': 14250.0, 'FT8': 14074.0, 'FT4': 14080.0, 'RTTY': 14080.0, 'Other': 14100.0},
    '17m':  {'CW': 18080.0, 'SSB': 18145.0, 'FT8': 18100.0, 'FT4': 18104.0, 'RTTY': 18105.0, 'Other': 18100.0},
    '15m':  {'CW': 21025.0, 'SSB': 21300.0, 'FT8': 21074.0, 'FT4': 21140.0, 'RTTY': 21080.0, 'Other': 21100.0},
    '12m':  {'CW': 24905.0, 'SSB': 24950.0, 'FT8': 24915.0, 'FT4': 24919.0, 'RTTY': 24920.0, 'Other': 24920.0},
    '10m':  {'CW': 28025.0, 'SSB': 28500.0, 'FT8': 28074.0, 'FT4': 28180.0, 'RTTY': 28080.0, 'Other': 28200.0},
    '6m':   {'CW': 50100.0, 'SSB': 50150.0, 'FT8': 50313.0, 'FT4': 50318.0, 'RTTY': 50100.0, 'Other': 50150.0},
    '2m':   {'CW': 144050.0, 'SSB': 144300.0, 'FT8': 144174.0, 'FT4': 144170.0, 'RTTY': 144100.0, 'Other': 144300.0},
    '70cm': {'CW': 432100.0, 'SSB': 432200.0, 'FT8': 432174.0, 'FT4': 432170.0, 'RTTY': 432100.0, 'Other': 432200.0},
}
```

### Phase 3: Create DX Cluster Module

**New file: `dx_cluster.py`**

```python
"""DX Cluster integration for QuendAward."""

import telnetlib
import requests
import threading
from datetime import datetime
from config import (
    DX_CLUSTER_ENABLED, DX_CLUSTER_TYPE,
    DX_CLUSTER_HOST, DX_CLUSTER_PORT, DX_CLUSTER_CALLSIGN,
    DX_CLUSTER_API_URL, DX_CLUSTER_API_KEY,
    BAND_FREQUENCIES
)
import database as db


class DXClusterTelnet:
    """Telnet-based DX Cluster connection."""

    def __init__(self):
        self.connection = None
        self.connected = False

    def connect(self):
        """Establish connection to DX Cluster."""
        try:
            self.connection = telnetlib.Telnet(
                DX_CLUSTER_HOST,
                DX_CLUSTER_PORT,
                timeout=10
            )
            # Wait for login prompt and send callsign
            self.connection.read_until(b"login:", timeout=5)
            self.connection.write(f"{DX_CLUSTER_CALLSIGN}\n".encode())
            self.connected = True
            return True
        except Exception as e:
            print(f"DX Cluster connection error: {e}")
            self.connected = False
            return False

    def send_spot(self, callsign, frequency, comment=""):
        """Send a spot to the cluster."""
        if not self.connected:
            if not self.connect():
                return False, "Connection failed"

        try:
            spot_cmd = f"DX {frequency:.1f} {callsign} {comment}\n"
            self.connection.write(spot_cmd.encode())
            return True, "Spot sent"
        except Exception as e:
            self.connected = False
            return False, str(e)

    def disconnect(self):
        """Close the connection."""
        if self.connection:
            try:
                self.connection.write(b"bye\n")
                self.connection.close()
            except:
                pass
        self.connected = False


class DXClusterAPI:
    """Web API-based DX Cluster posting."""

    def send_spot(self, spotter, spotted_call, frequency, comment=""):
        """Send spot via web API."""
        try:
            data = {
                'spotter': spotter,
                'spotted': spotted_call,
                'freq': frequency,
                'comment': comment,
            }
            if DX_CLUSTER_API_KEY:
                data['api_key'] = DX_CLUSTER_API_KEY

            response = requests.post(
                DX_CLUSTER_API_URL,
                data=data,
                timeout=10
            )
            return response.ok, response.text
        except Exception as e:
            return False, str(e)


def send_spot_async(award_name, operator_callsign, band, mode):
    """Send spot in background thread."""
    if not DX_CLUSTER_ENABLED:
        return

    def _send():
        frequency = BAND_FREQUENCIES.get(band, {}).get(mode, 14000.0)
        comment = f"QRV {mode}"

        if DX_CLUSTER_TYPE == 'telnet':
            cluster = DXClusterTelnet()
            success, message = cluster.send_spot(
                award_name, frequency, comment
            )
            cluster.disconnect()
        else:
            cluster = DXClusterAPI()
            success, message = cluster.send_spot(
                operator_callsign, award_name, frequency, comment
            )

        # Log the spot attempt
        db.log_spot(award_name, operator_callsign, band, mode,
                    frequency, success, message)

    thread = threading.Thread(target=_send)
    thread.daemon = True
    thread.start()
```

### Phase 4: Integrate with Block Function

**Modify `database.py` - `block_band_mode()`:**

```python
def block_band_mode(callsign, band, mode, award_id):
    """Block a band/mode combination."""
    # ... existing code ...

    if success:
        # Send DX spot if enabled
        from dx_cluster import send_spot_async
        award = get_award_by_id(award_id)
        if award:
            send_spot_async(
                award['name'],  # Special callsign name
                callsign,       # Operator callsign
                band,
                mode
            )

    return success, message
```

### Phase 5: Admin Configuration UI

**Add to admin panel - new tab or section:**

```python
def render_dx_cluster_settings(t):
    """Render DX Cluster configuration."""
    st.subheader(t['dx_cluster_settings'])

    # Status indicator
    if DX_CLUSTER_ENABLED:
        st.success(t['dx_cluster_enabled'])
    else:
        st.warning(t['dx_cluster_disabled'])

    # Recent spots log
    st.subheader(t['recent_spots'])
    spots = db.get_recent_spots(limit=20)
    if spots:
        df = pd.DataFrame(spots)
        st.dataframe(df, use_container_width=True)
    else:
        st.info(t['no_spots_yet'])

    # Manual spot button (for testing)
    if st.button(t['send_test_spot']):
        # Send test spot
        pass
```

---

## Environment Variables

Add to `.env`:
```bash
# DX Cluster Integration
DX_CLUSTER_ENABLED=true
DX_CLUSTER_TYPE=telnet          # 'telnet' or 'api'

# For Telnet connection
DX_CLUSTER_HOST=dxspider.example.com
DX_CLUSTER_PORT=7300
DX_CLUSTER_CALLSIGN=EA4ABC      # Login callsign for cluster

# For API connection (alternative)
DX_CLUSTER_API_URL=https://dxwatch.com/spot.php
DX_CLUSTER_API_KEY=your_api_key_here

# Spot customization
DX_SPOT_COMMENT=QRV {mode}
```

---

## Files to Create/Modify

| File | Action | Description |
|------|--------|-------------|
| `dx_cluster.py` | Create | DX Cluster connection module |
| `config.py` | Modify | Add DX cluster config variables |
| `database.py` | Modify | Add spot logging, integrate with block_band_mode |
| `admin_functions.py` | Modify | Add DX cluster settings tab |
| `translations.py` | Modify | Add translations (EN/ES/GL) |
| `Dockerfile` | Modify | Add new file to COPY |
| `requirements.txt` | Modify | Add `requests` if not present |

---

## Advanced Features (Future)

### Real-time Frequency Input
Allow operators to enter actual operating frequency:
```
┌─────────────────────────────────┐
│ Block 20m / CW                  │
│                                 │
│ Frequency: [14.025___] MHz      │
│ ☑ Announce to DX Cluster        │
│                                 │
│ [Confirm]  [Cancel]             │
└─────────────────────────────────┘
```

### Automatic QRT Announcement
When operator unblocks, send "QRT" notice to cluster.

### Spot Scheduling
Pre-schedule operating times and auto-spot at start time.

### Multi-Cluster Support
Send spots to multiple clusters simultaneously.

### Spot Rate Limiting
Prevent spam by limiting spots per callsign per time period.

### RBN Integration (Reverse)
Pull spots FROM Reverse Beacon Network to show who's hearing the special callsign.

---

## Security Considerations

1. **Callsign Verification**: Only allow verified operators to trigger spots
2. **Rate Limiting**: Max 1 spot per band/mode per 10 minutes
3. **Abuse Prevention**: Log all spots, admin can disable per-operator
4. **Credential Security**: Store cluster credentials in env vars only

---

## Estimated Effort

| Phase | Description | Complexity |
|-------|-------------|------------|
| 1 | Config & database setup | 1 hour |
| 2 | Frequency mapping | 30 min |
| 3 | DX Cluster module | 2-3 hours |
| 4 | Integration with blocking | 1 hour |
| 5 | Admin UI | 1-2 hours |
| 6 | Testing with real cluster | 1-2 hours |

**Total: ~7-10 hours**

---

## Testing Strategy

1. **Mock Mode**: Test without real cluster connection
2. **Local Cluster**: Set up test DX Spider instance
3. **Rate Limited Testing**: Use test cluster node
4. **Production**: Start with API method (less intrusive)

---

## Dependencies

```
# requirements.txt additions
requests>=2.28.0  # For API-based spotting (likely already present)
# telnetlib is built into Python standard library
```

---

## Next Steps

1. Decide: Telnet vs API vs Hybrid approach
2. Choose a test DX Cluster node
3. Get cluster login credentials
4. Implement Phase 1-3 (core functionality)
5. Test with real cluster
6. Add admin UI and monitoring
