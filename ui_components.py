"""Reusable UI components for QuendAward application."""

import streamlit as st
from translations import AVAILABLE_LANGUAGES, get_all_texts
import database as db


def _show_block_modal(t, callsign, band, mode, award_id):
    """
    Show modal dialog to confirm blocking a band/mode combination.

    Args:
        t: Translations dictionary
        callsign: Operator's callsign
        band: Band to block
        mode: Mode to block
        award_id: Current award ID
    """
    @st.dialog(t.get('modal_block_title', 'Block Band/Mode'))
    def _block_dialog():
        st.write(f"### {t.get('confirm_block', 'Do you want to block')} {band}/{mode}?")
        st.write("")

        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"✅ {t.get('confirm', 'Confirm')}", key="modal_confirm_block", type="primary", use_container_width=True):
                success, message = db.block_band_mode(callsign, band, mode, award_id)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
        with col2:
            if st.button(f"❌ {t.get('cancel', 'Cancel')}", key="modal_cancel_block", use_container_width=True):
                # Set flag to ignore next click event
                st.session_state.modal_cancelled = True
                st.rerun()

    _block_dialog()


def _show_unblock_modal(t, callsign, band, mode, award_id):
    """
    Show modal dialog to confirm unblocking a band/mode combination.

    Args:
        t: Translations dictionary
        callsign: Operator's callsign
        band: Band to unblock
        mode: Mode to unblock
        award_id: Current award ID
    """
    @st.dialog(t.get('modal_unblock_title', 'Unblock Band/Mode'))
    def _unblock_dialog():
        st.write(f"### {t.get('confirm_unblock', 'Do you want to unblock')} {band}/{mode}?")
        st.write("")

        col1, col2 = st.columns(2)
        with col1:
            if st.button(f"✅ {t.get('confirm', 'Confirm')}", key="modal_confirm_unblock", type="primary", use_container_width=True):
                success, message = db.unblock_band_mode(callsign, band, mode, award_id)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
        with col2:
            if st.button(f"❌ {t.get('cancel', 'Cancel')}", key="modal_cancel_unblock", use_container_width=True):
                # Set flag to ignore next click event
                st.session_state.modal_cancelled = True
                st.rerun()

    _unblock_dialog()


def render_language_selector(t, key_suffix=""):
    """
    Render a language selector dropdown.

    Args:
        t: Translations dictionary for current language
        key_suffix: Optional suffix for unique key generation

    Returns:
        None (updates session state and triggers rerun if language changes)
    """
    lang = st.selectbox(
        t['language'],
        options=list(AVAILABLE_LANGUAGES.keys()),
        format_func=lambda x: AVAILABLE_LANGUAGES[x],
        index=list(AVAILABLE_LANGUAGES.keys()).index(st.session_state.language),
        key=f"lang_selector{key_suffix}",
        label_visibility="collapsed" if key_suffix == "_panel" else "visible"
    )
    if lang != st.session_state.language:
        st.session_state.language = lang
        st.rerun()


def render_award_selector(active_awards, t):
    """
    Render special callsign selector dropdown and information expander.

    Args:
        active_awards: List of active award dictionaries
        t: Translations dictionary for current language

    Returns:
        None (updates session state)
    """
    if not st.session_state.current_award_id and active_awards:
        st.session_state.current_award_id = active_awards[0]['id']

    st.write("---")
    selected_award = st.selectbox(
        f"🏆 {t['select_special_callsign']}",
        options=[award['id'] for award in active_awards],
        format_func=lambda x: next((a['name'] for a in active_awards if a['id'] == x), ''),
        index=[award['id'] for award in active_awards].index(st.session_state.current_award_id)
              if st.session_state.current_award_id in [award['id'] for award in active_awards] else 0,
        key="award_selector"
    )

    if selected_award != st.session_state.current_award_id:
        st.session_state.current_award_id = selected_award
        st.rerun()

    # Show special callsign details if available
    current_award = next((a for a in active_awards if a['id'] == st.session_state.current_award_id), None)
    if current_award and current_award.get('description'):
        with st.expander(f"ℹ️ {t['special_callsign_information']}", expanded=False):
            st.write(f"**{current_award['name']}**")
            st.write(current_award['description'])
            if current_award.get('start_date'):
                st.write(f"**{t['start_label']}:** {current_award['start_date']}")
            if current_award.get('end_date'):
                st.write(f"**{t['end_label']}:** {current_award['end_date']}")


def render_block_unblock_section(t, callsign, award_id):
    """
    Render the block/unblock band/mode section for operators.

    Args:
        t: Translations dictionary
        callsign: Operator's callsign
        award_id: Current award ID

    Returns:
        None
    """
    from config import BANDS, MODES

    if not award_id:
        st.warning(f"⚠️ {t['error_no_special_callsign_selected']}")
        return

    st.info(t['block_info'])

    col1, col2 = st.columns(2)
    with col1:
        band_to_block = st.selectbox(t['select_band'], BANDS, key="block_band")
    with col2:
        mode_to_block = st.selectbox(t['select_mode'], MODES, key="block_mode")

    if st.button(t['block'], type="primary"):
        success, message = db.block_band_mode(callsign, band_to_block, mode_to_block, award_id)
        if success:
            st.success(message)
            st.rerun()
        else:
            st.error(message)

    # Show current blocks
    st.divider()
    st.subheader(t['your_current_blocks'])

    my_blocks = db.get_operator_blocks(callsign, award_id)

    if my_blocks:
        for block in my_blocks:
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                st.write(f"**{block['band']}**")
            with col2:
                st.write(f"**{block['mode']}**")
            with col3:
                if st.button(t['unblock'], key=f"unblock_{block['id']}"):
                    success, message = db.unblock_band_mode(callsign, block['band'], block['mode'], award_id)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
    else:
        st.info(t['no_active_blocks'])


def render_activity_dashboard(t, award_id, callsign=None):
    """
    Render the activity dashboard with heatmap and statistics.
    Includes interactive click-to-block/unblock functionality.

    Args:
        t: Translations dictionary
        award_id: Current award ID
        callsign: Current user's callsign (optional, for click handling)

    Returns:
        None
    """
    from charts import create_availability_heatmap, create_blocks_by_band_chart
    from streamlit_plotly_events import plotly_events
    from config import BANDS, MODES

    if not award_id:
        st.warning(f"⚠️ {t['error_no_special_callsign_selected']}")
        return

    all_blocks = db.get_all_blocks(award_id)

    # Display heatmap with click events
    fig = create_availability_heatmap(all_blocks, t)

    # Disable modebar in figure config
    fig.update_layout(
        modebar={'orientation': 'v', 'bgcolor': 'rgba(0,0,0,0)', 'color': 'rgba(0,0,0,0)', 'activecolor': 'rgba(0,0,0,0)'}
    )

    # Use plotly_events to capture clicks
    # Height reduced from 650 to 450 for better mobile experience
    selected_points = plotly_events(
        fig,
        click_event=True,
        hover_event=False,
        select_event=False,
        override_height=450,
        override_width="100%",
        key="heatmap_events"
    )

    # Handle click events
    if selected_points and callsign:
        # Check if we just cancelled a modal - if so, skip this click
        if st.session_state.get('modal_cancelled', False):
            st.session_state.modal_cancelled = False
        else:
            point = selected_points[0]
            # Get the clicked band and mode from pointIndex
            # plotly_events returns pointIndex as [y, x] for heatmaps
            if 'pointIndex' in point:
                y_idx = point['pointIndex'][0]
                x_idx = point['pointIndex'][1]
            else:
                # Fallback to x, y if pointIndex not available
                y_idx = point.get('y', 0)
                x_idx = point.get('x', 0)

            clicked_band = BANDS[y_idx]
            clicked_mode = MODES[x_idx]

            # Check if this combination is blocked
            block_info = next((b for b in all_blocks if b['band'] == clicked_band and b['mode'] == clicked_mode), None)

            if block_info:
                # Cell is blocked
                if block_info['operator_callsign'] == callsign:
                    # User's own block - show unblock modal
                    _show_unblock_modal(t, callsign, clicked_band, clicked_mode, award_id)
                else:
                    # Someone else's block
                    st.warning(f"⚠️ {clicked_band}/{clicked_mode} {t.get('already_blocked_by', 'is already blocked by')} {block_info['operator_name']} ({block_info['operator_callsign']})")
            else:
                # Cell is free - show block modal
                _show_block_modal(t, callsign, clicked_band, clicked_mode, award_id)

    # Show summary statistics
    st.divider()
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric(t['total_blocks_label'], len(all_blocks))
    with col2:
        unique_operators = set(block['operator_callsign'] for block in all_blocks)
        st.metric(t['active_operators_label'], len(unique_operators))
    with col3:
        unique_bands = set(block['band'] for block in all_blocks)
        st.metric(t['bands_in_use_label'], len(unique_bands))

    # Blocks by band chart
    if all_blocks:
        st.subheader(t['blocks_by_band_label'])
        fig_bar = create_blocks_by_band_chart(all_blocks, t)
        st.plotly_chart(fig_bar, use_container_width=True, config={'displayModeBar': False})
