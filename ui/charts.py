"""Chart creation functions for QuendAward application."""

import plotly.graph_objects as go
from config import BANDS, MODES, BAND_MODES, CHART_COLOR_FREE, CHART_COLOR_BLOCKED, CHART_BACKGROUND

CHART_COLOR_UNAVAILABLE = '#555555'

# Shared dark-mode layout defaults for QSO charts
_QSO_LAYOUT = dict(
    font=dict(color='white', size=11),
    plot_bgcolor=CHART_BACKGROUND,
    paper_bgcolor=CHART_BACKGROUND,
    modebar=dict(remove=[
        'zoom', 'pan', 'select', 'lasso2d', 'zoomIn2d', 'zoomOut2d',
        'autoScale2d', 'resetScale2d', 'toImage',
    ]),
)


def create_availability_heatmap(all_blocks, t):
    """
    Create a heatmap showing band/mode availability.

    Args:
        all_blocks: List of block dictionaries from database
        t: Translations dictionary for current language

    Returns:
        Plotly Figure object
    """
    # Create dictionaries for operator and date information
    blocks_dict = {(block['band'], block['mode']): block['operator_callsign'] for block in all_blocks}
    date_dict = {(block['band'], block['mode']): block['blocked_at'] for block in all_blocks}
    name_dict = {(block['band'], block['mode']): block['operator_name'] for block in all_blocks}

    # Build matrices for heatmap
    z_values = []  # For color coding (0 = free, 1 = blocked)
    text_values = []  # For display text
    hover_values = []  # For hover information
    text_colors = []  # For text colors (different for free vs blocked)

    for band in BANDS:
        z_row = []
        text_row = []
        hover_row = []
        color_row = []
        allowed = BAND_MODES.get(band, [])
        for mode in MODES:
            key = (band, mode)
            if mode not in allowed:
                z_row.append(0.5)  # Unavailable band/mode combo
                text_row.append('—')
                color_row.append('#cccccc')
                hover_row.append(f"<b>{band} / {mode}</b><br>{t.get('status_unavailable', 'Not usable on this band')}")
            elif key in blocks_dict:
                z_row.append(1)  # Blocked
                text_row.append(blocks_dict[key])
                color_row.append('white')  # White text on red background
                hover_text = f"<b>{band} / {mode}</b><br>"
                hover_text += f"{t['operator']}: {name_dict[key]} ({blocks_dict[key]})<br>"
                hover_text += f"{t['blocked_at']}: {date_dict[key]}"
                hover_row.append(hover_text)
            else:
                z_row.append(0)  # Free
                text_row.append(t['free_status'])
                color_row.append('black')  # Black text on green background
                hover_row.append(f"<b>{band} / {mode}</b><br>{t['status_available']}")

        z_values.append(z_row)
        text_values.append(text_row)
        hover_values.append(hover_row)
        text_colors.append(color_row)

    # Create Plotly heatmap
    fig = go.Figure(data=go.Heatmap(
        z=z_values,
        x=MODES,
        y=BANDS,
        hoverinfo='none',  # Disable hover - info shown in modal on tap
        colorscale=[
            [0.0, CHART_COLOR_FREE],          # Green for FREE
            [0.5, CHART_COLOR_UNAVAILABLE],   # Grey for illegal band/mode
            [1.0, CHART_COLOR_BLOCKED],       # Red for BLOCKED
        ],
        zmin=0,
        zmax=1,
        showscale=False,
        xgap=2,
        ygap=2
    ))

    # Add text annotations with appropriate colors for each cell
    annotations = []
    for i, band in enumerate(BANDS):
        for j, mode in enumerate(MODES):
            annotations.append(
                dict(
                    x=mode,
                    y=band,
                    text=text_values[i][j],
                    showarrow=False,
                    font=dict(
                        size=10,
                        color=text_colors[i][j],
                        family="Arial, sans-serif"
                    ),
                    xref='x',
                    yref='y'
                )
            )

    fig.update_layout(
        xaxis_title=t['mode_label'],
        yaxis_title=t['band_label'],
        height=420,
        margin=dict(l=50, r=5, t=40, b=5),
        font=dict(size=10, color='white'),
        plot_bgcolor=CHART_BACKGROUND,
        paper_bgcolor=CHART_BACKGROUND,
        xaxis=dict(side='top', tickfont=dict(color='white', size=10), title_font=dict(color='white'), fixedrange=True),
        yaxis=dict(tickfont=dict(color='white', size=10), title_font=dict(color='white'), fixedrange=True),
        autosize=True,
        annotations=annotations,
        modebar=dict(remove=['zoom', 'pan', 'select', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d', 'toImage'])
    )

    return fig


def create_blocks_by_band_chart(all_blocks, t):
    """
    Create a bar chart showing number of blocks per band.

    Args:
        all_blocks: List of block dictionaries from database
        t: Translations dictionary for current language

    Returns:
        Plotly Figure object
    """
    import pandas as pd

    df = pd.DataFrame(all_blocks)
    band_counts = df['band'].value_counts()
    # Ensure bands are ordered according to BANDS list
    ordered_counts = [band_counts.get(band, 0) for band in BANDS]

    # Create Plotly bar chart with fixed order
    fig = go.Figure(data=[
        go.Bar(x=BANDS, y=ordered_counts)
    ])

    fig.update_layout(
        xaxis_title=t['band_label'],
        yaxis_title=t['total_blocks_label'],
        height=220,
        margin=dict(l=40, r=5, t=25, b=35),
        font=dict(color='white', size=10),
        plot_bgcolor=CHART_BACKGROUND,
        paper_bgcolor=CHART_BACKGROUND,
        xaxis=dict(type='category', tickfont=dict(color='white', size=10), title_font=dict(color='white', size=11)),
        yaxis=dict(tickfont=dict(color='white', size=10), title_font=dict(color='white', size=11)),
        modebar=dict(remove=['zoom', 'pan', 'select', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d', 'toImage'])
    )

    return fig


# ---------------------------------------------------------------------------
# QSO Log Charts
# ---------------------------------------------------------------------------

def create_qso_timeline_chart(by_date, t):
    """Area chart of QSOs per day with cumulative overlay.

    Args:
        by_date: List of {"date": "YYYY-MM-DD", "count": int} sorted by date.
        t: Translations dict.
    Returns:
        Plotly Figure.
    """
    if not by_date:
        return None

    dates = [r['date'] for r in by_date]
    counts = [r['count'] for r in by_date]
    cumulative = []
    total = 0
    for c in counts:
        total += c
        cumulative.append(total)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=dates, y=counts,
        name=t.get('qso_chart_daily', 'Daily'),
        marker_color='#4FC3F7',
    ))
    fig.add_trace(go.Scatter(
        x=dates, y=cumulative,
        name=t.get('qso_chart_cumulative', 'Cumulative'),
        mode='lines',
        line=dict(color='#FFD54F', width=2),
        yaxis='y2',
    ))
    fig.update_layout(
        **_QSO_LAYOUT,
        height=220,
        margin=dict(l=40, r=40, t=25, b=30),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        xaxis=dict(tickfont=dict(color='white', size=10), fixedrange=True),
        yaxis=dict(
            title=t.get('qso_chart_daily', 'Daily'),
            tickfont=dict(color='white', size=10), title_font=dict(color='#4FC3F7', size=11),
            fixedrange=True,
        ),
        yaxis2=dict(
            title=t.get('qso_chart_cumulative', 'Cumulative'),
            overlaying='y', side='right',
            tickfont=dict(color='#FFD54F', size=10), title_font=dict(color='#FFD54F', size=11),
            fixedrange=True,
        ),
        bargap=0.15,
    )
    return fig


def create_qso_band_mode_heatmap(matrix, t):
    """Heatmap of QSO count per band x mode cell.

    Args:
        matrix: List of {"band": str, "mode": str, "count": int}.
        t: Translations dict.
    Returns:
        Plotly Figure.
    """
    if not matrix:
        return None

    # Build lookup
    lookup = {}
    for r in matrix:
        lookup[(r['band'], r['mode'])] = r['count']

    # Collect only bands/modes that have data (keep config order)
    active_bands = [b for b in BANDS if any((b, m) in lookup for m in MODES)]
    all_modes_in_data = {r['mode'] for r in matrix}
    active_modes = [m for m in MODES if m in all_modes_in_data]
    # Add any extra modes from the data that aren't in MODES config
    extra_modes = sorted(all_modes_in_data - set(MODES))
    active_modes.extend(extra_modes)

    # Also add bands from data not in config order
    data_bands = {r['band'] for r in matrix}
    extra_bands = sorted(data_bands - set(BANDS))
    active_bands.extend(extra_bands)

    if not active_bands or not active_modes:
        return None

    z_values = []
    text_values = []
    for band in active_bands:
        z_row = []
        text_row = []
        for mode in active_modes:
            cnt = lookup.get((band, mode), 0)
            z_row.append(cnt if cnt > 0 else None)
            text_row.append(str(cnt) if cnt > 0 else '')
        z_values.append(z_row)
        text_values.append(text_row)

    fig = go.Figure(data=go.Heatmap(
        z=z_values,
        x=active_modes,
        y=active_bands,
        text=text_values,
        texttemplate='%{text}',
        textfont=dict(size=12, color='white'),
        colorscale=[
            [0.0, '#1a237e'],
            [0.25, '#1565c0'],
            [0.5, '#42a5f5'],
            [0.75, '#ffb74d'],
            [1.0, '#ff5722'],
        ],
        hovertemplate='%{y} / %{x}: %{z} QSOs<extra></extra>',
        showscale=True,
        colorbar=dict(
            title=dict(text='QSOs', font=dict(color='white')),
            tickfont=dict(color='white'),
        ),
        xgap=2,
        ygap=2,
    ))

    fig.update_layout(
        **_QSO_LAYOUT,
        height=max(150, len(active_bands) * 28 + 60),
        margin=dict(l=50, r=5, t=25, b=5),
        xaxis=dict(
            side='top', tickfont=dict(color='white'),
            title_font=dict(color='white'), fixedrange=True,
        ),
        yaxis=dict(
            tickfont=dict(color='white'), title_font=dict(color='white'),
            fixedrange=True, autorange='reversed',
        ),
    )
    return fig


def create_qso_hourly_chart(by_hour, t):
    """Bar chart of QSOs per UTC hour (0-23).

    Args:
        by_hour: List of {"hour": int, "count": int}.
        t: Translations dict.
    Returns:
        Plotly Figure.
    """
    if not by_hour:
        return None

    hour_counts = {r['hour']: r['count'] for r in by_hour}
    hours = list(range(24))
    counts = [hour_counts.get(h, 0) for h in hours]
    labels = [f"{h:02d}" for h in hours]

    # Color gradient: darker for low activity, brighter for high
    max_cnt = max(counts) if counts else 1
    colors = [
        f'rgba(79, 195, 247, {0.3 + 0.7 * (c / max_cnt)})' if c > 0
        else 'rgba(79, 195, 247, 0.1)'
        for c in counts
    ]

    fig = go.Figure(data=go.Bar(
        x=labels, y=counts,
        marker_color=colors,
        hovertemplate='%{x}:00 UTC: %{y} QSOs<extra></extra>',
    ))
    fig.update_layout(
        **_QSO_LAYOUT,
        height=200,
        margin=dict(l=35, r=5, t=25, b=30),
        xaxis=dict(
            title='UTC',
            tickfont=dict(color='white', size=10), title_font=dict(color='white', size=11),
            fixedrange=True, dtick=2,
        ),
        yaxis=dict(
            tickfont=dict(color='white', size=10), title_font=dict(color='white'),
            fixedrange=True,
        ),
    )
    return fig


def create_qso_band_chart(by_band, t):
    """Horizontal bar chart of QSOs per band (in BANDS config order).

    Args:
        by_band: Dict[str, int] band -> count.
        t: Translations dict.
    Returns:
        Plotly Figure.
    """
    if not by_band:
        return None

    # Show only bands that have data, in config order
    ordered = [(b, by_band[b]) for b in BANDS if b in by_band]
    # Add any extra bands not in config
    config_set = set(BANDS)
    for b, cnt in sorted(by_band.items()):
        if b not in config_set:
            ordered.append((b, cnt))

    if not ordered:
        return None

    bands = [o[0] for o in ordered]
    counts = [o[1] for o in ordered]

    fig = go.Figure(data=go.Bar(
        x=counts, y=bands,
        orientation='h',
        marker_color='#4FC3F7',
        text=counts,
        textposition='outside',
        textfont=dict(color='white', size=11),
        hovertemplate='%{y}: %{x} QSOs<extra></extra>',
    ))
    fig.update_layout(
        **_QSO_LAYOUT,
        height=max(150, len(bands) * 24 + 40),
        margin=dict(l=50, r=35, t=5, b=5),
        xaxis=dict(
            tickfont=dict(color='white', size=10), fixedrange=True,
            showgrid=False,
        ),
        yaxis=dict(
            tickfont=dict(color='white', size=10), fixedrange=True,
            autorange='reversed',
        ),
    )
    return fig


def create_qso_mode_chart(by_mode, t):
    """Donut chart of QSOs per mode.

    Args:
        by_mode: Dict[str, int] mode -> count.
        t: Translations dict.
    Returns:
        Plotly Figure.
    """
    if not by_mode:
        return None

    modes = list(by_mode.keys())
    counts = list(by_mode.values())

    colors = [
        '#4FC3F7', '#FFD54F', '#81C784', '#FF8A65',
        '#BA68C8', '#4DB6AC', '#E57373', '#90A4AE',
        '#AED581', '#FFB74D',
    ]

    fig = go.Figure(data=go.Pie(
        labels=modes, values=counts,
        hole=0.45,
        marker=dict(colors=colors[:len(modes)]),
        textinfo='label+percent',
        textfont=dict(color='white', size=12),
        hovertemplate='%{label}: %{value} QSOs (%{percent})<extra></extra>',
    ))
    fig.update_layout(
        **_QSO_LAYOUT,
        height=220,
        margin=dict(l=5, r=5, t=5, b=5),
        showlegend=False,
    )
    return fig


def create_qso_operator_chart(by_operator, t):
    """Horizontal bar chart showing QSO count per operator (leaderboard).

    Args:
        by_operator: Dict[str, int] callsign -> count, sorted by count desc.
        t: Translations dict.
    Returns:
        Plotly Figure.
    """
    if not by_operator:
        return None

    # Top 15 operators
    items = list(by_operator.items())[:15]
    # Reverse for horizontal bar (bottom-up display)
    callsigns = [i[0] for i in reversed(items)]
    counts = [i[1] for i in reversed(items)]

    fig = go.Figure(data=go.Bar(
        x=counts, y=callsigns,
        orientation='h',
        marker_color='#FFD54F',
        text=counts,
        textposition='outside',
        textfont=dict(color='white', size=11),
        hovertemplate='%{y}: %{x} QSOs<extra></extra>',
    ))
    fig.update_layout(
        **_QSO_LAYOUT,
        height=max(150, len(callsigns) * 24 + 40),
        margin=dict(l=70, r=35, t=5, b=5),
        xaxis=dict(
            tickfont=dict(color='white', size=10), fixedrange=True,
            showgrid=False,
        ),
        yaxis=dict(
            tickfont=dict(color='white', size=10), fixedrange=True,
        ),
    )
    return fig


# ---------------------------------------------------------------------------
# Operator Activation Stats Charts
# ---------------------------------------------------------------------------

def _format_duration(seconds):
    """Format seconds as 'Xh Ym' string."""
    if seconds is None or seconds < 0:
        return "0m"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    if h > 0:
        return f"{h}h {m}m"
    return f"{m}m"


def create_activation_operator_chart(by_operator, t):
    """Horizontal bar chart of total activation time per operator.

    Args:
        by_operator: dict[callsign, {activations, seconds}] sorted by seconds desc.
        t: Translations dict.
    Returns:
        Plotly Figure.
    """
    if not by_operator:
        return None

    items = list(by_operator.items())[:15]
    callsigns = [i[0] for i in reversed(items)]
    hours = [i[1]['seconds'] / 3600 for i in reversed(items)]
    texts = [
        f"{_format_duration(i[1]['seconds'])} ({i[1]['activations']}x)"
        for i in reversed(items)
    ]

    fig = go.Figure(data=go.Bar(
        x=hours, y=callsigns,
        orientation='h',
        marker_color='#FFD54F',
        text=texts,
        textposition='outside',
        textfont=dict(color='white', size=11),
        hovertemplate='%{y}: %{text}<extra></extra>',
    ))
    fig.update_layout(
        **_QSO_LAYOUT,
        height=max(150, len(callsigns) * 24 + 40),
        margin=dict(l=70, r=70, t=5, b=5),
        xaxis=dict(
            title=t.get('act_chart_hours', 'Hours'),
            tickfont=dict(color='white', size=10), title_font=dict(color='white', size=11),
            fixedrange=True, showgrid=False,
        ),
        yaxis=dict(tickfont=dict(color='white', size=10), fixedrange=True),
    )
    return fig


def create_activation_band_chart(by_band, t):
    """Horizontal bar chart of activation time per band.

    Args:
        by_band: dict[band, {activations, seconds}] sorted by seconds desc.
        t: Translations dict.
    Returns:
        Plotly Figure.
    """
    if not by_band:
        return None

    ordered = [(b, by_band[b]) for b in BANDS if b in by_band]
    config_set = set(BANDS)
    for b, v in by_band.items():
        if b not in config_set:
            ordered.append((b, v))

    if not ordered:
        return None

    bands = [o[0] for o in ordered]
    hours = [o[1]['seconds'] / 3600 for o in ordered]
    texts = [
        f"{_format_duration(o[1]['seconds'])} ({o[1]['activations']}x)"
        for o in ordered
    ]

    fig = go.Figure(data=go.Bar(
        x=hours, y=bands,
        orientation='h',
        marker_color='#4FC3F7',
        text=texts,
        textposition='outside',
        textfont=dict(color='white', size=11),
        hovertemplate='%{y}: %{text}<extra></extra>',
    ))
    fig.update_layout(
        **_QSO_LAYOUT,
        height=max(150, len(bands) * 24 + 40),
        margin=dict(l=50, r=70, t=5, b=5),
        xaxis=dict(
            title=t.get('act_chart_hours', 'Hours'),
            tickfont=dict(color='white', size=10), title_font=dict(color='white', size=11),
            fixedrange=True, showgrid=False,
        ),
        yaxis=dict(
            tickfont=dict(color='white', size=10), fixedrange=True,
            autorange='reversed',
        ),
    )
    return fig


def create_activation_mode_chart(by_mode, t):
    """Donut chart of activation time per mode.

    Args:
        by_mode: dict[mode, {activations, seconds}] sorted by seconds desc.
        t: Translations dict.
    Returns:
        Plotly Figure.
    """
    if not by_mode:
        return None

    modes = list(by_mode.keys())
    hours = [v['seconds'] / 3600 for v in by_mode.values()]
    custom = [
        f"{m}: {_format_duration(by_mode[m]['seconds'])} ({by_mode[m]['activations']}x)"
        for m in modes
    ]

    colors = [
        '#4FC3F7', '#FFD54F', '#81C784', '#FF8A65',
        '#BA68C8', '#4DB6AC', '#E57373', '#90A4AE',
    ]

    fig = go.Figure(data=go.Pie(
        labels=modes, values=hours,
        hole=0.45,
        marker=dict(colors=colors[:len(modes)]),
        textinfo='label+percent',
        textfont=dict(color='white', size=12),
        customdata=custom,
        hovertemplate='%{customdata}<extra></extra>',
    ))
    fig.update_layout(
        **_QSO_LAYOUT,
        height=220,
        margin=dict(l=5, r=5, t=5, b=5),
        showlegend=False,
    )
    return fig


def create_activation_timeline_chart(by_date, t):
    """Bar chart of activation time per day.

    Args:
        by_date: list[{date, activations, seconds}] sorted by date asc.
        t: Translations dict.
    Returns:
        Plotly Figure.
    """
    if not by_date:
        return None

    dates = [r['date'] for r in by_date]
    hours = [r['seconds'] / 3600 for r in by_date]
    acts = [r['activations'] for r in by_date]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=dates, y=hours,
        name=t.get('act_chart_hours', 'Hours'),
        marker_color='#4FC3F7',
        hovertemplate='%{x}: %{y:.1f}h<extra></extra>',
    ))
    fig.add_trace(go.Scatter(
        x=dates, y=acts,
        name=t.get('act_chart_activations', 'Activations'),
        mode='lines+markers',
        line=dict(color='#FFD54F', width=2),
        marker=dict(size=5),
        yaxis='y2',
        hovertemplate='%{x}: %{y} activations<extra></extra>',
    ))
    fig.update_layout(
        **_QSO_LAYOUT,
        height=220,
        margin=dict(l=40, r=40, t=25, b=30),
        legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
        xaxis=dict(tickfont=dict(color='white', size=10), fixedrange=True),
        yaxis=dict(
            title=t.get('act_chart_hours', 'Hours'),
            tickfont=dict(color='white', size=10), title_font=dict(color='#4FC3F7', size=11),
            fixedrange=True,
        ),
        yaxis2=dict(
            title=t.get('act_chart_activations', 'Activations'),
            overlaying='y', side='right',
            tickfont=dict(color='#FFD54F', size=10), title_font=dict(color='#FFD54F', size=11),
            fixedrange=True,
        ),
        bargap=0.15,
    )
    return fig


def create_activation_hourly_chart(by_hour, t):
    """Bar chart of activation count by hour of day.

    Args:
        by_hour: list[{hour, activations}] sorted by hour asc.
        t: Translations dict.
    Returns:
        Plotly Figure.
    """
    if not by_hour:
        return None

    hour_counts = {r['hour']: r['activations'] for r in by_hour}
    hours = list(range(24))
    counts = [hour_counts.get(h, 0) for h in hours]
    labels = [f"{h:02d}" for h in hours]

    max_cnt = max(counts) if counts else 1
    colors = [
        f'rgba(79, 195, 247, {0.3 + 0.7 * (c / max_cnt)})' if c > 0
        else 'rgba(79, 195, 247, 0.1)'
        for c in counts
    ]

    fig = go.Figure(data=go.Bar(
        x=labels, y=counts,
        marker_color=colors,
        hovertemplate='%{x}:00 UTC: %{y} activations<extra></extra>',
    ))
    fig.update_layout(
        **_QSO_LAYOUT,
        height=200,
        margin=dict(l=35, r=5, t=25, b=30),
        xaxis=dict(
            title='UTC',
            tickfont=dict(color='white', size=10), title_font=dict(color='white', size=11),
            fixedrange=True, dtick=2,
        ),
        yaxis=dict(
            tickfont=dict(color='white', size=10), title_font=dict(color='white'),
            fixedrange=True,
        ),
    )
    return fig
