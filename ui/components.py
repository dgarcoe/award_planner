"""Reusable UI components for QuendAward application."""

import streamlit as st
from i18n import AVAILABLE_LANGUAGES, get_all_texts
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
                    st.session_state._click_version = st.session_state.get('_click_version', 0) + 1
                    st.rerun()
                else:
                    st.error(message)
        with col2:
            if st.button(f"❌ {t.get('cancel', 'Cancel')}", key="modal_cancel_block", use_container_width=True):
                st.session_state._click_version = st.session_state.get('_click_version', 0) + 1
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
                    st.session_state._click_version = st.session_state.get('_click_version', 0) + 1
                    st.rerun()
                else:
                    st.error(message)
        with col2:
            if st.button(f"❌ {t.get('cancel', 'Cancel')}", key="modal_cancel_unblock", use_container_width=True):
                st.session_state._click_version = st.session_state.get('_click_version', 0) + 1
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
    if current_award:
        # Check if there's an image, description, or QRZ link to show
        image_result = db.get_award_image(current_award['id'])
        has_content = current_award.get('description') or image_result or current_award.get('qrz_link')

        if has_content:
            with st.expander(f"ℹ️ {t['special_callsign_information']}", expanded=False):
                # Two-column layout: description left, image right
                if image_result:
                    col_left, col_right = st.columns([3, 2])
                    with col_left:
                        st.write(f"**{current_award['name']}**")
                        if current_award.get('description'):
                            st.write(current_award['description'])
                        if current_award.get('start_date'):
                            st.write(f"**{t['start_label']}:** {current_award['start_date']}")
                        if current_award.get('end_date'):
                            st.write(f"**{t['end_label']}:** {current_award['end_date']}")
                        if current_award.get('qrz_link'):
                            st.markdown(f"🔗 [{t['view_on_qrz']}]({current_award['qrz_link']})")
                    with col_right:
                        image_data, image_type = image_result
                        st.image(image_data, use_container_width=True)
                else:
                    # No image, single column layout
                    st.write(f"**{current_award['name']}**")
                    if current_award.get('description'):
                        st.write(current_award['description'])
                    if current_award.get('start_date'):
                        st.write(f"**{t['start_label']}:** {current_award['start_date']}")
                    if current_award.get('end_date'):
                        st.write(f"**{t['end_label']}:** {current_award['end_date']}")
                    if current_award.get('qrz_link'):
                        st.markdown(f"🔗 [{t['view_on_qrz']}]({current_award['qrz_link']})")


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


def _render_dx_cluster_spot_section(t, award_id, callsign):
    """
    Render the DX Cluster spotting section below the heatmap.

    Operators can send spots only when they have an active block.
    Band/mode are autofilled from the block; frequency and comment are manual.
    Cluster connection settings come from environment variables.

    Args:
        t: Translations dictionary
        award_id: Current award ID
        callsign: Current user's callsign
    """
    from config import (
        DX_CLUSTER_HOST, DX_CLUSTER_PORT, DX_CLUSTER_CALLSIGN,
        DX_CLUSTER_PASSWORD, BAND_FREQUENCIES,
    )

    if not callsign or not award_id:
        return

    # Get operator's active block for this award
    my_blocks = db.get_operator_blocks(callsign, award_id)
    active_block = my_blocks[0] if my_blocks else None

    st.divider()
    with st.expander(f"📡 {t.get('dx_cluster_spot', 'DX Cluster Spot')}", expanded=False):
        st.caption(t.get('dx_cluster_spot_info', 'Send a spot to a DX Cluster node to announce activity.'))

        # Gate: require an active block
        if not active_block:
            st.warning(t.get('dx_no_block_warning', 'You must block a band/mode before sending a spot.'))
        else:
            blocked_band = active_block['band']
            blocked_mode = active_block['mode']

            # Show autofilled band/mode (read-only)
            info_col1, info_col2 = st.columns(2)
            with info_col1:
                st.text_input(
                    t.get('band_label', 'Band'),
                    value=blocked_band,
                    disabled=True,
                    key="dx_block_band",
                )
            with info_col2:
                st.text_input(
                    t.get('mode_label', 'Mode'),
                    value=blocked_mode,
                    disabled=True,
                    key="dx_block_mode",
                )

            # Spotted callsign (manual for testing; future: auto from award)
            spotted_callsign = st.text_input(
                t.get('dx_spotted_callsign', 'Spotted Callsign'),
                value=st.session_state.get('dx_spotted_cs', ''),
                help=t.get('dx_spotted_callsign_help', 'The callsign to spot (e.g. the special callsign)'),
                key="dx_input_spotted_cs",
            ).upper().strip()

            # Frequency (manual input, default from band/mode mapping)
            default_freq = BAND_FREQUENCIES.get(blocked_band, {}).get(blocked_mode, 14000.0)
            frequency = st.number_input(
                t.get('dx_frequency', 'Frequency (kHz)'),
                value=default_freq,
                min_value=0.1,
                max_value=999999.9,
                step=0.1,
                format="%.1f",
                key="dx_input_freq",
            )

            # Comment
            comment = st.text_input(
                t.get('dx_comment', 'Comment'),
                value=f"QRV {blocked_mode}",
                max_chars=30,
                help=t.get('dx_comment_help', 'Max 30 characters'),
                key="dx_input_comment",
            )

            # Send button
            if st.button(f"📡 {t.get('dx_send_spot', 'Send Spot')}", type="primary", key="dx_send_btn"):
                if not DX_CLUSTER_HOST or not DX_CLUSTER_CALLSIGN:
                    st.error(t.get('dx_cluster_not_configured', 'DX Cluster not configured. Set DX_CLUSTER_HOST and DX_CLUSTER_CALLSIGN environment variables.'))
                elif not spotted_callsign:
                    st.error(t.get('dx_fill_required', 'Please fill in the spotted callsign.'))
                else:
                    with st.spinner("Connecting to DX Cluster..."):
                        from features.dx_cluster import send_spot_to_cluster, log_spot
                        success, message = send_spot_to_cluster(
                            host=DX_CLUSTER_HOST,
                            port=DX_CLUSTER_PORT,
                            login_callsign=DX_CLUSTER_CALLSIGN,
                            spotted_callsign=spotted_callsign,
                            frequency=frequency,
                            comment=comment,
                            password=DX_CLUSTER_PASSWORD,
                        )

                        # Log the spot attempt
                        log_spot(
                            award_id=award_id,
                            operator_callsign=callsign,
                            spotted_callsign=spotted_callsign,
                            band=blocked_band,
                            mode=blocked_mode,
                            frequency=frequency,
                            cluster_host=f"{DX_CLUSTER_HOST}:{DX_CLUSTER_PORT}",
                            success=success,
                            cluster_response=message,
                        )

                        if success:
                            st.success(f"{t.get('dx_spot_success', 'Spot sent successfully!')} {message}")
                        else:
                            st.error(f"{t.get('dx_spot_error', 'Error sending spot')}: {message}")

        # Recent spots log (always visible)
        recent_spots = db.get_recent_spots(award_id=award_id, limit=5)
        if recent_spots:
            st.caption(t.get('dx_recent_spots', 'Recent Spots'))
            for spot in recent_spots:
                status_icon = "✅" if spot['success'] else "❌"
                time_str = spot['spotted_at'][:16] if spot.get('spotted_at') else ""
                freq_str = f"{spot['frequency']:.1f}" if spot.get('frequency') else ""
                st.caption(
                    f"{status_icon} {time_str} | "
                    f"{spot.get('spotted_callsign', '')} | "
                    f"{freq_str} kHz | "
                    f"{spot.get('cluster_response', '')[:60]}"
                )


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
    from ui.charts import create_availability_heatmap, create_blocks_by_band_chart
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
    # Versioned key forces component reset after each confirm/cancel,
    # eliminating stale click data that caused wrong modals to appear
    click_version = st.session_state.get('_click_version', 0)
    selected_points = plotly_events(
        fig,
        click_event=True,
        hover_event=False,
        select_event=False,
        override_height=550,
        override_width="100%",
        key=f"heatmap_events_{click_version}"
    )

    # Handle click events
    if selected_points and callsign:
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

    # DX Cluster spotting section
    _render_dx_cluster_spot_section(t, award_id, callsign)

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


def render_announcements_operator_tab(t, operator_callsign):
    """
    Render the announcements tab for operators.
    Marks announcements as read when tab is viewed.

    Args:
        t: Translations dictionary
        operator_callsign: Current operator's callsign
    """
    st.subheader(f"📢 {t['announcements']}")

    # Get announcements with read status
    announcements = db.get_announcements_with_read_status(operator_callsign)

    if not announcements:
        st.info(t['no_announcements_available'])
        return

    # Display announcements - user can click to mark individual ones as read
    for ann in announcements:
        is_read = ann.get('is_read')
        read_indicator = "" if is_read else "🔵 "

        with st.expander(f"{read_indicator}{ann['title']}", expanded=not is_read):
            st.write(ann['content'])
            st.caption(f"{t['posted_on']}: {ann['created_at']} | {t['by']}: {ann['created_by']}")

            # Only show "Mark as read" button for unread announcements
            if not is_read:
                if st.button(t.get('mark_as_read', 'Mark as read'), key=f"mark_read_{ann['id']}"):
                    db.mark_announcement_read(ann['id'], operator_callsign)
                    st.rerun()
