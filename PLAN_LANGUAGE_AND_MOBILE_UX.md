# Plan: Language Selector & Mobile Usability Improvements

## Overview

Two improvements:
1. Move language selector to login page only (remove from operator panel)
2. Improve smartphone usability for band/mode selection

---

## Part 1: Language Selector on Login Page Only

### Current Behavior

- Language selector appears on login page (top right)
- Language selector ALSO appears on operator panel (after login)
- Users can change language at any time

### Proposed Behavior

- Language selector ONLY on login page
- Once logged in, language is fixed for the session
- Simplifies the UI and reduces clutter on operator panel

### Files to Modify

**`app.py`**

Current code in `operator_panel()` (lines 198-200):
```python
col1, col2, col3 = st.columns([4, 1, 1])
with col2:
    render_language_selector(t, key_suffix="_panel")
with col3:
    if st.button(t['logout']):
```

Change to:
```python
col1, col2 = st.columns([5, 1])
with col2:
    if st.button(t['logout']):
```

### Estimated Effort

~5 minutes - remove 3 lines of code

---

## Part 2: Mobile Usability for Band/Mode Selection

### Current Issues

1. **Heatmap cells too small** - Difficult to tap accurately on mobile
2. **Touch targets** - Need minimum 44x44px for accessibility
3. **Accidental taps** - Easy to tap wrong cell
4. **No visual feedback** - Hard to see which cell you're tapping

### Proposed Solutions

#### Solution A: Larger Heatmap on Mobile (CSS-based)

Increase cell size on mobile screens via CSS:

```css
@media (max-width: 768px) {
    /* Make heatmap taller on mobile for bigger cells */
    [data-testid="stPlotlyChart"] {
        min-height: 600px !important;
    }
}
```

**Pros:** Simple CSS change
**Cons:** May require scrolling, cells still might be small

#### Solution B: Dropdown Selectors Instead of Heatmap Click (Recommended)

Add explicit Band/Mode dropdowns below the heatmap for mobile users:

```
┌─────────────────────────────────────────────┐
│  [Heatmap - visual reference only]          │
│                                             │
│  ┌─────────────────────────────────────┐    │
│  │ 160m  80m  60m  40m  30m  20m ...  │    │
│  │  🟢   🟢   🟢   🔴   🟢   🟢       │    │
│  └─────────────────────────────────────┘    │
│                                             │
│  ─── Quick Block/Unblock ───────────────    │
│                                             │
│  Band: [40m          ▼]                     │
│  Mode: [CW           ▼]                     │
│                                             │
│  Status: 🔴 Blocked by EA4ABC               │
│                                             │
│  [🔓 Unblock]  or  [🔒 Block]               │
│                                             │
└─────────────────────────────────────────────┘
```

**Implementation:**

```python
def render_mobile_block_controls(t, award_id, callsign):
    """Render mobile-friendly block/unblock controls."""
    st.subheader(t['quick_block_unblock'])

    col1, col2 = st.columns(2)
    with col1:
        selected_band = st.selectbox(
            t['band_label'],
            options=BANDS,
            key="mobile_band_select"
        )
    with col2:
        selected_mode = st.selectbox(
            t['mode_label'],
            options=MODES,
            key="mobile_mode_select"
        )

    # Check current status
    blocks = db.get_all_blocks(award_id)
    current_block = next(
        (b for b in blocks if b['band'] == selected_band and b['mode'] == selected_mode),
        None
    )

    if current_block:
        st.warning(f"🔴 {t['blocked_by']}: {current_block['operator_name']} ({current_block['operator_callsign']})")

        if current_block['operator_callsign'] == callsign:
            if st.button(f"🔓 {t['unblock']}", type="primary", use_container_width=True):
                success, msg = db.unblock_band_mode(callsign, selected_band, selected_mode, award_id)
                if success:
                    st.success(msg)
                    st.rerun()
        else:
            st.info(t['blocked_by_other'])
    else:
        st.success(f"🟢 {t['status_available']}")
        if st.button(f"🔒 {t['block']}", type="primary", use_container_width=True):
            success, msg = db.block_band_mode(callsign, selected_band, selected_mode, award_id)
            if success:
                st.success(msg)
                st.rerun()
```

**Pros:**
- Large touch targets (full-width dropdowns and buttons)
- Clear status indication
- Works great on mobile
- Heatmap still shows visual overview

**Cons:**
- Extra UI section
- Two ways to do same thing (heatmap click + dropdowns)

#### Solution C: Hybrid Approach (Best of Both)

1. Keep heatmap for visual reference
2. Add dropdown controls below heatmap
3. On mobile, show dropdowns prominently
4. On desktop, dropdowns are secondary (heatmap click is primary)

Could detect mobile via screen width and adjust prominence.

#### Solution D: Increase Gap Between Cells

Increase `xgap` and `ygap` in heatmap to make cells more distinct:

```python
# Current
xgap=2,
ygap=2

# Proposed for mobile
xgap=4,
ygap=4
```

Combined with larger overall heatmap height on mobile.

---

## Recommended Implementation

### Phase 1: Quick Wins (CSS)

1. Remove language selector from operator panel
2. Increase heatmap height on mobile (CSS)
3. Increase cell gaps in heatmap

### Phase 2: Dropdown Controls

Add mobile-friendly dropdown selectors below heatmap:
- Band dropdown
- Mode dropdown
- Status indicator
- Block/Unblock button

### Files to Modify

| File | Changes |
|------|---------|
| `app.py` | Remove language selector from operator panel |
| `mobile_styles.py` | Add CSS for larger heatmap on mobile |
| `charts.py` | Increase xgap/ygap for cell spacing |
| `ui_components.py` | Add `render_mobile_block_controls()` function |
| `translations.py` | Add new translation keys |

---

## New Translations Needed

```python
# English
'quick_block_unblock': 'Quick Block/Unblock',
'blocked_by': 'Blocked by',
'blocked_by_other': 'This band/mode is blocked by another operator',
'block': 'Block',
'unblock': 'Unblock',

# Spanish
'quick_block_unblock': 'Bloqueo/Desbloqueo Rápido',
'blocked_by': 'Bloqueado por',
'blocked_by_other': 'Esta banda/modo está bloqueada por otro operador',
'block': 'Bloquear',
'unblock': 'Desbloquear',

# Galician
'quick_block_unblock': 'Bloqueo/Desbloqueo Rápido',
'blocked_by': 'Bloqueado por',
'blocked_by_other': 'Esta banda/modo está bloqueada por outro operador',
'block': 'Bloquear',
'unblock': 'Desbloquear',
```

---

## UI Mockup: Mobile View

```
┌─────────────────────────────────────┐
│ 🎙️ QuendAward          [Logout]    │
├─────────────────────────────────────┤
│ Welcome, Juan (EA4ABC)              │
│                                     │
│ Special Callsign: [EG90IARU ▼]      │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │     CW  SSB DIGI SAT            │ │
│ │ 160m 🟢  🟢  🟢  🟢             │ │
│ │  80m 🟢  🔴  🟢  🟢             │ │
│ │  40m 🟢  🟢  🔴  🟢             │ │
│ │  20m 🔴  🟢  🟢  🟢             │ │
│ │  ... (scrollable)               │ │
│ └─────────────────────────────────┘ │
│                                     │
│ ═══ Quick Block/Unblock ══════════  │
│                                     │
│ Band:  [    20m           ▼]        │
│                                     │
│ Mode:  [    CW            ▼]        │
│                                     │
│ ┌─────────────────────────────────┐ │
│ │ 🔴 Blocked by: Juan (EA4ABC)    │ │
│ └─────────────────────────────────┘ │
│                                     │
│ [      🔓 Unblock 20m/CW      ]     │
│                                     │
│ ─────────────────────────────────── │
│ Your Current Blocks:                │
│ • 20m / CW                          │
│ • 15m / SSB                         │
└─────────────────────────────────────┘
```

---

## Estimated Effort

| Task | Time |
|------|------|
| Remove language selector from panel | 5 min |
| CSS for larger mobile heatmap | 15 min |
| Increase cell gaps | 5 min |
| Add dropdown controls | 1-2 hours |
| Translations | 15 min |
| Testing | 30 min |

**Total: ~2-3 hours**

---

## Alternative: Touch-Friendly Heatmap Only

If dropdown controls are not desired, can focus purely on making heatmap more touch-friendly:

1. **Larger height on mobile** - 600px instead of 450px
2. **Bigger cell gaps** - 6px instead of 2px
3. **Larger font** - 14px instead of 11px on mobile
4. **Confirmation on tap** - Always show modal to confirm (already implemented)
5. **Zoom capability** - Allow pinch-to-zoom on heatmap

This would require modifying `charts.py` to accept a `mobile` parameter and adjust sizes accordingly.
