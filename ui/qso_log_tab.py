"""QSO Log tab — upload ADIF, view stats, browse consolidated log."""

import streamlit as st
import pandas as pd

import database as db
from features.adif_parser import parse_adif


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

PAGE_SIZE = 50


def _render_stats(t: dict, award_id: int):
    """Render stats cards and bar charts."""
    stats = db.get_qso_stats(award_id)

    # Metric cards row
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(t['qso_total'], f"{stats['total']:,}")
    c2.metric(t['qso_today'], f"{stats['today']:,}")
    c3.metric(t['qso_unique_calls'], f"{stats['unique_calls']:,}")
    c4.metric(t['qso_active_operators'], f"{stats['active_operators']:,}")

    if stats['total'] == 0:
        return

    # Bar charts row
    col_band, col_mode, col_op = st.columns(3)

    with col_band:
        st.markdown(f"**{t['qso_by_band']}**")
        if stats['by_band']:
            df = pd.DataFrame(
                list(stats['by_band'].items()), columns=['Band', 'QSOs']
            )
            st.bar_chart(df, x='Band', y='QSOs', height=250)

    with col_mode:
        st.markdown(f"**{t['qso_by_mode']}**")
        if stats['by_mode']:
            df = pd.DataFrame(
                list(stats['by_mode'].items()), columns=['Mode', 'QSOs']
            )
            st.bar_chart(df, x='Mode', y='QSOs', height=250)

    with col_op:
        st.markdown(f"**{t['qso_by_operator']}**")
        if stats['by_operator']:
            df = pd.DataFrame(
                list(stats['by_operator'].items()), columns=['Operator', 'QSOs']
            )
            st.bar_chart(df, x='Operator', y='QSOs', height=250)


def _render_upload_section(t: dict, award_id: int, callsign: str):
    """Render ADIF file upload area."""
    st.markdown(f"### {t['qso_upload_title']}")
    st.info(t['qso_upload_info'])

    uploaded_file = st.file_uploader(
        t['qso_upload_title'],
        type=['adi', 'adif'],
        key=f"adif_upload_{award_id}",
        label_visibility="collapsed",
    )

    if uploaded_file is not None:
        try:
            content = uploaded_file.read().decode('utf-8', errors='replace')
        except Exception as e:
            st.error(f"{t['qso_upload_error']}: {e}")
            return

        records, warnings = parse_adif(content)

        if warnings:
            with st.expander(t['qso_upload_warnings'].format(count=len(warnings))):
                for w in warnings:
                    st.warning(w)

        if not records:
            st.warning(t['qso_upload_no_records'])
            return

        st.success(t['qso_upload_preview'].format(count=len(records)))

        # Show a small preview table
        preview_data = []
        for r in records[:10]:
            preview_data.append({
                t['qso_col_date']: r.get('qso_date', ''),
                t['qso_col_time']: r.get('time_on', ''),
                t['qso_col_call']: r.get('call', ''),
                t['qso_col_band']: r.get('band', ''),
                t['qso_col_mode']: r.get('mode', ''),
            })
        st.dataframe(pd.DataFrame(preview_data), use_container_width=True, hide_index=True)
        if len(records) > 10:
            st.caption(f"... and {len(records) - 10} more")

        if st.button(t['qso_upload_button'], type="primary", key=f"import_btn_{award_id}"):
            success, message, count = db.insert_qsos_bulk(award_id, callsign, records)
            if success:
                st.success(f"{t['qso_upload_success']}: {message}")
                st.rerun()
            else:
                st.error(f"{t['qso_upload_error']}: {message}")


def _render_log_table(t: dict, award_id: int, callsign: str, is_admin: bool):
    """Render the consolidated QSO log with filters and pagination."""
    st.markdown(f"### {t['qso_consolidated_log']}")

    # Filters
    filter_cols = st.columns(3)
    with filter_cols[0]:
        band_filter = st.selectbox(
            t['qso_filter_band'],
            [t['qso_filter_all']] + _get_distinct_values(award_id, 'band'),
            key=f"qso_band_filter_{award_id}",
        )
    with filter_cols[1]:
        mode_filter = st.selectbox(
            t['qso_filter_mode'],
            [t['qso_filter_all']] + _get_distinct_values(award_id, 'mode'),
            key=f"qso_mode_filter_{award_id}",
        )
    with filter_cols[2]:
        op_filter = st.selectbox(
            t['qso_filter_operator'],
            [t['qso_filter_all']] + _get_distinct_values(award_id, 'operator_callsign'),
            key=f"qso_op_filter_{award_id}",
        )

    band_val = None if band_filter == t['qso_filter_all'] else band_filter
    mode_val = None if mode_filter == t['qso_filter_all'] else mode_filter
    op_val = None if op_filter == t['qso_filter_all'] else op_filter

    total = db.get_qso_count(award_id, operator_callsign=op_val, band=band_val, mode=mode_val)

    if total == 0:
        st.info(t['qso_no_qsos'])
        return

    # Pagination
    page_key = f"qso_page_{award_id}"
    if page_key not in st.session_state:
        st.session_state[page_key] = 0
    page = st.session_state[page_key]
    max_page = max(0, (total - 1) // PAGE_SIZE)
    page = min(page, max_page)

    offset = page * PAGE_SIZE
    qsos = db.get_qsos(award_id, operator_callsign=op_val, band=band_val,
                        mode=mode_val, limit=PAGE_SIZE, offset=offset)

    # Build display dataframe
    rows = []
    for q in qsos:
        rows.append({
            'ID': q['id'],
            t['qso_col_date']: q['qso_date'],
            t['qso_col_time']: q['time_on'],
            t['qso_col_operator']: q['operator_callsign'],
            t['qso_col_call']: q['call'],
            t['qso_col_band']: q['band'],
            t['qso_col_mode']: q['mode'],
            t['qso_col_rst_sent']: q.get('rst_sent', ''),
            t['qso_col_rst_rcvd']: q.get('rst_rcvd', ''),
            t['qso_col_freq']: q.get('freq', ''),
            t['qso_col_name']: q.get('name', '') or '',
            t['qso_col_comment']: q.get('comment', '') or '',
        })

    df = pd.DataFrame(rows)

    # Show page info
    start = offset + 1
    end = min(offset + PAGE_SIZE, total)
    st.caption(t['qso_page_info'].format(start=start, end=end, total=total))

    # Navigation
    if max_page > 0:
        nav_cols = st.columns([1, 1, 3])
        with nav_cols[0]:
            if st.button("⬅️", key=f"prev_{award_id}", disabled=page == 0):
                st.session_state[page_key] = page - 1
                st.rerun()
        with nav_cols[1]:
            if st.button("➡️", key=f"next_{award_id}", disabled=page >= max_page):
                st.session_state[page_key] = page + 1
                st.rerun()

    # Display table (hide ID column from display)
    display_df = df.drop(columns=['ID'])
    st.dataframe(display_df, use_container_width=True, hide_index=True)

    # Admin edit/delete section
    if is_admin and qsos:
        _render_admin_controls(t, award_id, qsos, df)

    # Export and delete own QSOs
    _render_operator_actions(t, award_id, callsign, is_admin)


def _render_admin_controls(t: dict, award_id: int, qsos: list[dict], df: pd.DataFrame):
    """Render admin-only QSO management controls."""
    st.markdown("---")
    st.markdown(f"**{t['admin_panel']}**")

    admin_cols = st.columns(2)

    # Edit QSO
    with admin_cols[0]:
        qso_options = {
            f"{q['qso_date']} {q['time_on']} — {q['call']} ({q['band']}/{q['mode']})": q['id']
            for q in qsos
        }
        selected_edit = st.selectbox(
            t['qso_admin_edit'],
            options=list(qso_options.keys()),
            key=f"admin_edit_select_{award_id}",
        )
        if selected_edit:
            qso_id = qso_options[selected_edit]
            _render_edit_form(t, qso_id, qsos, award_id)

    # Delete QSO
    with admin_cols[1]:
        selected_del = st.selectbox(
            t['qso_admin_delete'],
            options=list(qso_options.keys()),
            key=f"admin_del_select_{award_id}",
        )
        if selected_del:
            qso_id = qso_options[selected_del]
            if st.button(
                t['qso_admin_delete'],
                key=f"admin_del_btn_{award_id}_{qso_id}",
                type="primary",
            ):
                st.session_state[f"confirm_del_{qso_id}"] = True

            if st.session_state.get(f"confirm_del_{qso_id}"):
                st.warning(t['qso_admin_delete_confirm'])
                cc1, cc2 = st.columns(2)
                with cc1:
                    if st.button(t['qso_cancel'], key=f"cancel_del_{qso_id}"):
                        st.session_state[f"confirm_del_{qso_id}"] = False
                        st.rerun()
                with cc2:
                    if st.button(t['qso_admin_delete'], key=f"confirm_del_btn_{qso_id}", type="primary"):
                        success, msg = db.delete_qso(qso_id)
                        if success:
                            st.success(t['qso_delete_success'])
                            st.session_state[f"confirm_del_{qso_id}"] = False
                            st.rerun()
                        else:
                            st.error(msg)

    # Bulk delete by operator
    st.markdown("---")
    operators = _get_distinct_values(award_id, 'operator_callsign')
    if operators:
        bulk_cols = st.columns([2, 1])
        with bulk_cols[0]:
            bulk_op = st.selectbox(
                t['qso_admin_delete_operator'],
                operators,
                key=f"bulk_del_op_{award_id}",
            )
        with bulk_cols[1]:
            if st.button(
                t['qso_admin_delete_operator'],
                key=f"bulk_del_btn_{award_id}",
                type="primary",
            ):
                st.session_state[f"confirm_bulk_del_{award_id}"] = True

        if st.session_state.get(f"confirm_bulk_del_{award_id}"):
            st.warning(t['qso_admin_delete_operator_confirm'].format(callsign=bulk_op))
            cc1, cc2 = st.columns(2)
            with cc1:
                if st.button(t['qso_cancel'], key=f"cancel_bulk_{award_id}"):
                    st.session_state[f"confirm_bulk_del_{award_id}"] = False
                    st.rerun()
            with cc2:
                if st.button(t['qso_admin_delete_operator'], key=f"confirm_bulk_{award_id}", type="primary"):
                    success, msg, count = db.delete_qsos_by_operator(award_id, bulk_op)
                    if success:
                        st.success(f"{t['qso_delete_success']}: {msg}")
                        st.session_state[f"confirm_bulk_del_{award_id}"] = False
                        st.rerun()
                    else:
                        st.error(msg)


def _render_edit_form(t: dict, qso_id: int, qsos: list[dict], award_id: int):
    """Render inline edit form for a QSO."""
    qso = next((q for q in qsos if q['id'] == qso_id), None)
    if not qso:
        return

    with st.expander(f"{t['qso_admin_edit']} — {qso['call']}", expanded=False):
        ec1, ec2 = st.columns(2)
        with ec1:
            new_call = st.text_input("Call", value=qso['call'], key=f"edit_call_{qso_id}")
            new_band = st.text_input("Band", value=qso['band'], key=f"edit_band_{qso_id}")
            new_mode = st.text_input("Mode", value=qso['mode'], key=f"edit_mode_{qso_id}")
            new_date = st.text_input("Date", value=qso['qso_date'], key=f"edit_date_{qso_id}")
            new_time = st.text_input("Time", value=qso['time_on'], key=f"edit_time_{qso_id}")
        with ec2:
            new_rst_s = st.text_input("RST Sent", value=qso.get('rst_sent', ''), key=f"edit_rsts_{qso_id}")
            new_rst_r = st.text_input("RST Rcvd", value=qso.get('rst_rcvd', ''), key=f"edit_rstr_{qso_id}")
            new_freq = st.text_input("Freq", value=str(qso.get('freq', '') or ''), key=f"edit_freq_{qso_id}")
            new_name = st.text_input("Name", value=qso.get('name', '') or '', key=f"edit_name_{qso_id}")
            new_comment = st.text_input("Comment", value=qso.get('comment', '') or '', key=f"edit_comment_{qso_id}")

        if st.button(t['qso_save'], key=f"save_edit_{qso_id}", type="primary"):
            update_data = {
                'call': new_call.upper(),
                'band': new_band,
                'mode': new_mode.upper(),
                'qso_date': new_date,
                'time_on': new_time,
                'rst_sent': new_rst_s,
                'rst_rcvd': new_rst_r,
                'name': new_name,
                'comment': new_comment,
            }
            if new_freq:
                try:
                    update_data['freq'] = float(new_freq)
                except ValueError:
                    pass
            success, msg = db.update_qso(qso_id, update_data)
            if success:
                st.success(t['qso_edit_success'])
                st.rerun()
            else:
                st.error(msg)


def _render_operator_actions(t: dict, award_id: int, callsign: str, is_admin: bool):
    """Render export and delete buttons for the current operator."""
    st.markdown("---")
    action_cols = st.columns(4 if is_admin else 3)

    # Export own ADIF
    with action_cols[0]:
        my_qsos = db.get_qsos(award_id, operator_callsign=callsign, limit=100000)
        if my_qsos:
            award = db.get_award_by_id(award_id)
            station_call = award['name'] if award else ''
            adif_content = db.export_qsos_to_adif(my_qsos, station_call)
            st.download_button(
                t['qso_export_my_adif'],
                data=adif_content,
                file_name=f"qso_log_{callsign}_{award_id}.adi",
                mime="text/plain",
                key=f"export_my_{award_id}",
            )

    # Export all ADIF (admin)
    if is_admin:
        with action_cols[1]:
            all_qsos = db.get_qsos(award_id, limit=100000)
            if all_qsos:
                award = db.get_award_by_id(award_id)
                station_call = award['name'] if award else ''
                adif_all = db.export_qsos_to_adif(all_qsos, station_call)
                st.download_button(
                    t['qso_export_all_adif'],
                    data=adif_all,
                    file_name=f"qso_log_all_{award_id}.adi",
                    mime="text/plain",
                    key=f"export_all_{award_id}",
                )

    # Delete own QSOs
    del_col_idx = 2 if is_admin else 1
    with action_cols[del_col_idx]:
        my_count = db.get_qso_count(award_id, operator_callsign=callsign)
        if my_count > 0:
            if st.button(
                f"{t['qso_delete_my_qsos']} ({my_count})",
                key=f"del_my_qsos_{award_id}",
            ):
                st.session_state[f"confirm_del_my_{award_id}"] = True

            if st.session_state.get(f"confirm_del_my_{award_id}"):
                st.warning(t['qso_delete_my_qsos_confirm'])
                cc1, cc2 = st.columns(2)
                with cc1:
                    if st.button(t['qso_cancel'], key=f"cancel_del_my_{award_id}"):
                        st.session_state[f"confirm_del_my_{award_id}"] = False
                        st.rerun()
                with cc2:
                    if st.button(t['qso_delete_my_qsos'], key=f"confirm_del_my_{award_id}", type="primary"):
                        success, msg, count = db.delete_qsos_by_operator(award_id, callsign)
                        if success:
                            st.success(f"{t['qso_delete_success']}: {msg}")
                            st.session_state[f"confirm_del_my_{award_id}"] = False
                            st.rerun()
                        else:
                            st.error(msg)


def _get_distinct_values(award_id: int, column: str) -> list[str]:
    """Get distinct values for a column in qso_log for an award."""
    allowed = {'band', 'mode', 'operator_callsign'}
    if column not in allowed:
        return []
    try:
        from core.database import get_db
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT DISTINCT {column} FROM qso_log WHERE award_id = ? ORDER BY {column}",
                (award_id,),
            )
            return [row[0] for row in cursor.fetchall()]
    except Exception:
        return []


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def render_qso_log_tab(t: dict, award_id: int | None, callsign: str, is_admin: bool):
    """Render the full QSO Log tab."""
    if not award_id:
        st.warning(t['qso_upload_select_award'])
        return

    # Stats section
    with st.expander(f"📊 {t['qso_stats_title']}", expanded=True):
        _render_stats(t, award_id)

    # Upload section
    with st.expander(f"📤 {t['qso_upload_title']}", expanded=False):
        _render_upload_section(t, award_id, callsign)

    # Consolidated log
    _render_log_table(t, award_id, callsign, is_admin)
