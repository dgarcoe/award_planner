"""Chart creation functions for QuendAward application."""

import plotly.graph_objects as go
from config import BANDS, MODES, CHART_COLOR_FREE, CHART_COLOR_BLOCKED, CHART_BACKGROUND


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
        for mode in MODES:
            key = (band, mode)
            if key in blocks_dict:
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
        hovertemplate='%{hovertext}<extra></extra>',
        hovertext=hover_values,
        colorscale=[
            [0, CHART_COLOR_FREE],  # Green for FREE
            [1, CHART_COLOR_BLOCKED]   # Red for BLOCKED
        ],
        zmin=0,  # Force minimum of color scale
        zmax=1,  # Force maximum of color scale
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
                        size=11,  # Reduced from 13 for better mobile fit
                        color=text_colors[i][j],
                        family="Arial, sans-serif"
                    ),
                    xref='x',
                    yref='y'
                )
            )

    # Update layout with responsive height
    fig.update_layout(
        xaxis_title=t['mode_label'],
        yaxis_title=t['band_label'],
        height=450,  # Reduced from 650 for better mobile experience
        margin=dict(l=60, r=10, t=50, b=40),  # Tighter margins for mobile
        font=dict(size=11, color='white'),  # White text for dark mode
        plot_bgcolor=CHART_BACKGROUND,
        paper_bgcolor=CHART_BACKGROUND,
        xaxis=dict(side='top', tickfont=dict(color='white'), title_font=dict(color='white'), fixedrange=True),
        yaxis=dict(tickfont=dict(color='white'), title_font=dict(color='white'), fixedrange=True),
        autosize=True,
        annotations=annotations,
        # Hide modebar (toolbar) on all devices
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
        height=300,  # Reduced from 400 for better mobile experience
        margin=dict(l=50, r=10, t=30, b=40),  # Tighter margins
        font=dict(color='white'),  # White text for dark mode
        plot_bgcolor=CHART_BACKGROUND,
        paper_bgcolor=CHART_BACKGROUND,
        xaxis=dict(type='category', tickfont=dict(color='white'), title_font=dict(color='white')),
        yaxis=dict(tickfont=dict(color='white'), title_font=dict(color='white')),
        # Hide modebar (toolbar) on all devices
        modebar=dict(remove=['zoom', 'pan', 'select', 'lasso2d', 'zoomIn2d', 'zoomOut2d', 'autoScale2d', 'resetScale2d', 'toImage'])
    )

    return fig
