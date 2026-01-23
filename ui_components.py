"""Reusable UI components for QuendAward application."""

import streamlit as st
from translations import AVAILABLE_LANGUAGES
import database as db


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
    Render award selector dropdown and award information expander.

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
        f"🏆 {t['select_award']}",
        options=[award['id'] for award in active_awards],
        format_func=lambda x: next((a['name'] for a in active_awards if a['id'] == x), ''),
        index=[award['id'] for award in active_awards].index(st.session_state.current_award_id)
              if st.session_state.current_award_id in [award['id'] for award in active_awards] else 0,
        key="award_selector"
    )

    if selected_award != st.session_state.current_award_id:
        st.session_state.current_award_id = selected_award
        st.rerun()

    # Show award details if available
    current_award = next((a for a in active_awards if a['id'] == st.session_state.current_award_id), None)
    if current_award and current_award.get('description'):
        with st.expander(f"ℹ️ {t['award_information']}", expanded=False):
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
        st.warning(f"⚠️ {t['error_no_award_selected']}")
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


def render_activity_dashboard(t, award_id):
    """
    Render the activity dashboard with heatmap and statistics.

    Args:
        t: Translations dictionary
        award_id: Current award ID

    Returns:
        None
    """
    from charts import create_availability_heatmap, create_blocks_by_band_chart

    if not award_id:
        st.warning(f"⚠️ {t['error_no_award_selected']}")
        return

    st.info(t['activity_dashboard_info'])

    all_blocks = db.get_all_blocks(award_id)

    # Display heatmap
    fig = create_availability_heatmap(all_blocks, t)
    st.plotly_chart(fig, use_container_width=True)

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
        st.plotly_chart(fig_bar, use_container_width=True)
