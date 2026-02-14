"""Admin panel functions for QuendAward application."""

import streamlit as st
import pandas as pd
import database as db


@st.dialog("Reset Password")
def reset_password_dialog(callsign: str, t: dict):
    """Dialog for resetting an operator's password."""
    st.write(f"**{t['reset_password_for']} {callsign}**")

    new_password = st.text_input(t['new_password'], type="password", key="dialog_new_pwd")
    confirm_password = st.text_input(t['confirm_new_password'], type="password", key="dialog_confirm_pwd")

    col1, col2 = st.columns(2)
    with col1:
        if st.button(t['cancel'], use_container_width=True):
            st.session_state.reset_password_callsign = None
            st.rerun()
    with col2:
        if st.button(t['reset_password'], type="primary", use_container_width=True):
            if not new_password:
                st.error(t['error_enter_password'])
            elif new_password != confirm_password:
                st.error(t['error_passwords_not_match'])
            elif len(new_password) < 6:
                st.error(t['error_password_min_length'])
            else:
                success, message = db.admin_reset_password(callsign, new_password)
                if success:
                    st.success(message)
                    st.info(f"**{t['new_credentials_for']} {callsign}:**\n\n{t['password']}: `{new_password}`")
                    st.session_state.reset_password_callsign = None
                else:
                    st.error(message)


def render_operators_tab(t):
    """Render the unified operator management tab."""
    st.subheader(f"👥 {t['operator_management']}")

    # Create operator section (collapsible)
    with st.expander(f"➕ {t['create_new_operator']}", expanded=False):
        st.info(t['create_operator_info'])

        new_callsign = st.text_input(t['callsign'], max_chars=20, key="new_call").upper()
        new_operator_name = st.text_input(t['operator_name'], max_chars=100)
        new_password = st.text_input(t['password'], type="password", max_chars=100, key="new_pass")
        new_password_confirm = st.text_input(t['confirm_password'], type="password", max_chars=100, key="new_pass_conf")
        is_admin = st.checkbox(t['grant_admin_privileges'], value=False)

        if st.button(t['create_operator'], type="primary", key="create_op_btn"):
            if not new_callsign or not new_operator_name or not new_password:
                st.error(t['error_fill_all_fields'])
            elif new_password != new_password_confirm:
                st.error(t['error_passwords_not_match'])
            elif len(new_password) < 6:
                st.error(t['error_password_min_length'])
            else:
                success, message = db.create_operator(new_callsign, new_operator_name, new_password, is_admin)
                if success:
                    st.success(message)
                    admin_text = f" ({t['admin_status']})" if is_admin else ""
                    st.info(f"**{t['credentials_to_provide']}**\n\n{t['callsign']}: `{new_callsign}`{admin_text}\n\n{t['password']}: `{new_password}`")
                    st.rerun()
                else:
                    st.error(message)

    st.divider()

    # Operators list
    operators = db.get_all_operators()

    if operators:
        # Header row
        header_cols = st.columns([2, 3, 2, 2, 2])
        with header_cols[0]:
            st.write(f"**{t['callsign']}**")
        with header_cols[1]:
            st.write(f"**{t['name']}**")
        with header_cols[2]:
            st.write(f"**{t['role']}**")
        with header_cols[3]:
            st.write(f"**{t['created']}**")
        with header_cols[4]:
            st.write(f"**{t['actions']}**")

        st.markdown("<hr style='margin: 0.5rem 0;'>", unsafe_allow_html=True)

        # Operator rows
        for op in operators:
            cols = st.columns([2, 3, 2, 2, 2])
            with cols[0]:
                st.write(f"**{op['callsign']}**")
            with cols[1]:
                st.write(op['operator_name'])
            with cols[2]:
                if op['is_admin']:
                    st.write("👑 Admin")
                else:
                    st.write("Operator")
            with cols[3]:
                # Show only date part
                created_date = op['created_at'][:10] if op['created_at'] else ""
                st.caption(created_date)
            with cols[4]:
                btn_col1, btn_col2, btn_col3 = st.columns(3)
                with btn_col1:
                    if op['is_admin']:
                        if st.button("⬇", key=f"demote_{op['callsign']}", help=t['demote']):
                            success, message = db.demote_from_admin(op['callsign'])
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)
                    else:
                        if st.button("⬆", key=f"promote_{op['callsign']}", help=t['promote']):
                            success, message = db.promote_to_admin(op['callsign'])
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)
                with btn_col2:
                    if st.button("🔑", key=f"reset_{op['callsign']}", help=t['reset_password']):
                        st.session_state.reset_password_callsign = op['callsign']
                        st.rerun()
                with btn_col3:
                    if st.button("🗑", key=f"delete_{op['callsign']}", help=t['delete_operator']):
                        success, message = db.delete_operator(op['callsign'])
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
    else:
        st.info(t['no_operators'])

    # Show reset password dialog if triggered (must be called unconditionally)
    if st.session_state.get('reset_password_callsign'):
        reset_password_dialog(st.session_state.reset_password_callsign, t)


def render_manage_blocks_tab(t):
    """Render the manage all blocks tab."""
    st.subheader(t['manage_all_blocks'])
    st.info(t['manage_blocks_info'])

    # Special callsign filter for admin
    all_awards_admin = db.get_all_awards()
    if all_awards_admin:
        selected_admin_award = st.selectbox(
            t['filter_by_special_callsign'],
            options=[award['id'] for award in all_awards_admin],
            format_func=lambda x: next((a['name'] for a in all_awards_admin if a['id'] == x), ''),
            key="admin_award_filter"
        )
        all_blocks = db.get_all_blocks(selected_admin_award)
    else:
        all_blocks = []
        st.warning(t['no_special_callsigns_exist'])

    if all_blocks:
        for block in all_blocks:
            col1, col2, col3, col4 = st.columns([2, 2, 3, 1])
            with col1:
                st.write(f"**{block['band']}**")
            with col2:
                st.write(f"**{block['mode']}**")
            with col3:
                st.write(f"{block['operator_name']} ({block['operator_callsign']})")
            with col4:
                if st.button(t['unblock_selected'], key=f"admin_unblock_{block['id']}"):
                    success, message = db.admin_unblock_band_mode(block['band'], block['mode'], block['award_id'])
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
    else:
        st.info(t['no_blocks_to_manage'])


def render_system_stats_tab(t):
    """Render the system statistics tab."""
    st.subheader(t['system_statistics'])
    operators = db.get_all_operators()
    blocks = db.get_all_blocks()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(t['total_operators'], len(operators))
    with col2:
        active_operators = len(set(block['operator_callsign'] for block in blocks))
        st.metric(t['active_operators'], active_operators)
    with col3:
        st.metric(t['active_blocks'], len(blocks))
    with col4:
        total_admins = len([op for op in operators if op['is_admin']])
        st.metric(t['total_admins'], total_admins)


def render_award_management_tab(t):
    """Render the special callsign management tab."""
    st.subheader(f"🏆 {t['special_callsign_management']}")
    st.info(t['special_callsign_management_info'])

    # Create new special callsign
    st.subheader(t['create_new_special_callsign'])

    # Use session state to track form values (file_uploader doesn't work inside st.form)
    award_name = st.text_input(t['special_callsign_name'], max_chars=100, key="new_award_name")
    award_description = st.text_area(t['description'], max_chars=500, key="new_award_desc")
    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input(t['start_date'], key="new_award_start", value=None)
    with col2:
        end_date = st.date_input(t['end_date'], key="new_award_end", value=None)

    # QRZ link
    qrz_link = st.text_input(
        t['qrz_link'],
        placeholder=t['qrz_link_placeholder'],
        key="new_award_qrz"
    )

    # Image upload
    st.write(f"**{t['special_callsign_image']}**")
    st.caption(t['allowed_image_types'])
    uploaded_image = st.file_uploader(
        t['upload_image'],
        type=['jpg', 'jpeg', 'png', 'gif'],
        key="new_award_image",
        label_visibility="collapsed"
    )

    if st.button(t['create_special_callsign'], type="primary", key="create_award_btn"):
        if not award_name:
            st.error(t['error_special_callsign_name_required'])
        else:
            start_str = start_date.strftime("%Y-%m-%d") if start_date else ""
            end_str = end_date.strftime("%Y-%m-%d") if end_date else ""

            # Process image if uploaded
            image_data = None
            image_type = None
            if uploaded_image is not None:
                # Check file size (max 5MB)
                if uploaded_image.size > 5 * 1024 * 1024:
                    st.error("Image file too large. Maximum size is 5MB.")
                else:
                    image_data = uploaded_image.read()
                    image_type = uploaded_image.type

            success, message, award_id = db.create_award(
                award_name, award_description, start_str, end_str,
                image_data=image_data, image_type=image_type,
                qrz_link=qrz_link
            )
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

    st.divider()

    # List and manage existing special callsigns
    st.subheader(t['existing_special_callsigns'])
    awards = db.get_all_awards()

    if awards:
        from datetime import datetime
        for award in awards:
            with st.expander(f"{'✅' if award['is_active'] else '❌'} {award['name']}", expanded=False):
                # Show current image if exists
                image_result = db.get_award_image(award['id'])
                if image_result:
                    image_data, image_type = image_result
                    st.write(f"**{t['current_image']}:**")
                    st.image(image_data, width=300)

                # Editable fields
                st.write(f"**{t['edit_special_callsign']}**")

                edit_name = st.text_input(
                    t['special_callsign_name'],
                    value=award['name'],
                    max_chars=100,
                    key=f"edit_name_{award['id']}"
                )

                edit_description = st.text_area(
                    t['description'],
                    value=award['description'] or "",
                    max_chars=500,
                    key=f"edit_desc_{award['id']}"
                )

                date_col1, date_col2 = st.columns(2)
                with date_col1:
                    # Parse existing date or use None
                    start_val = None
                    if award['start_date']:
                        try:
                            start_val = datetime.strptime(award['start_date'], "%Y-%m-%d").date()
                        except ValueError:
                            pass
                    edit_start = st.date_input(
                        t['start_date'],
                        value=start_val,
                        key=f"edit_start_{award['id']}"
                    )
                with date_col2:
                    end_val = None
                    if award['end_date']:
                        try:
                            end_val = datetime.strptime(award['end_date'], "%Y-%m-%d").date()
                        except ValueError:
                            pass
                    edit_end = st.date_input(
                        t['end_date'],
                        value=end_val,
                        key=f"edit_end_{award['id']}"
                    )

                # QRZ link
                edit_qrz = st.text_input(
                    t['qrz_link'],
                    value=award.get('qrz_link') or "",
                    placeholder=t['qrz_link_placeholder'],
                    key=f"edit_qrz_{award['id']}"
                )

                # Save changes button
                if st.button(t['save_changes'], key=f"save_award_{award['id']}", type="primary"):
                    if not edit_name:
                        st.error(t['error_special_callsign_name_required'])
                    else:
                        start_str = edit_start.strftime("%Y-%m-%d") if edit_start else ""
                        end_str = edit_end.strftime("%Y-%m-%d") if edit_end else ""
                        success, message = db.update_award(award['id'], edit_name, edit_description, start_str, end_str, edit_qrz)
                        if success:
                            st.success(t['changes_saved'])
                            st.rerun()
                        else:
                            st.error(message)

                st.write(f"**{t['status']}:** {t['active'] if award['is_active'] else t['inactive']}")
                st.write(f"**{t['created_label']}:** {award['created_at']}")

                # Image management section
                st.write("---")
                st.write(f"**{t['special_callsign_image']}**")
                st.caption(t['allowed_image_types'])

                new_image = st.file_uploader(
                    t['upload_image'],
                    type=['jpg', 'jpeg', 'png', 'gif'],
                    key=f"update_image_{award['id']}",
                    label_visibility="collapsed"
                )

                img_col1, img_col2 = st.columns(2)
                with img_col1:
                    if st.button(t['upload_image'], key=f"save_image_{award['id']}", disabled=new_image is None):
                        if new_image is not None:
                            if new_image.size > 5 * 1024 * 1024:
                                st.error("Image file too large. Maximum size is 5MB.")
                            else:
                                img_data = new_image.read()
                                img_type = new_image.type
                                success, message = db.update_award_image(award['id'], img_data, img_type)
                                if success:
                                    st.success(t['image_updated'])
                                    st.rerun()
                                else:
                                    st.error(message)
                with img_col2:
                    if image_result:
                        if st.button(t['remove_image'], key=f"remove_image_{award['id']}", type="secondary"):
                            success, message = db.update_award_image(award['id'], None, None)
                            if success:
                                st.success(t['image_removed'])
                                st.rerun()
                            else:
                                st.error(message)

                st.write("---")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button(t['toggle_status'], key=f"toggle_award_{award['id']}"):
                        success, message = db.toggle_award_status(award['id'])
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
                with col2:
                    if st.button(t['delete_special_callsign'], key=f"delete_award_{award['id']}", type="secondary"):
                        success, message = db.delete_award(award['id'])
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
    else:
        st.info(t['no_special_callsigns_created'])


def render_database_management_tab(t):
    """Render the database backup and restore tab."""
    from datetime import datetime

    st.subheader(f"💾 {t['database_management']}")
    st.info(t['database_management_info'])

    # Database info section
    st.subheader(t['database_info'])
    db_info = db.get_database_info()

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric(t['total_operators'], db_info['operators_count'])
    with col2:
        st.metric(t['total_special_callsigns'], db_info['awards_count'])
    with col3:
        st.metric(t['total_blocks'], db_info['blocks_count'])
    with col4:
        # Format file size
        size_kb = db_info['file_size'] / 1024
        if size_kb < 1024:
            size_str = f"{size_kb:.1f} KB"
        else:
            size_str = f"{size_kb/1024:.1f} MB"
        st.metric(t['database_size'], size_str)

    st.divider()

    # Backup section
    st.subheader(t['backup_database'])
    st.info(t['backup_info'])

    if st.button(t['download_backup'], type="primary"):
        try:
            backup_data = db.get_database_backup()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"quendaward_backup_{timestamp}.db"

            st.download_button(
                label=t['click_to_download'],
                data=backup_data,
                file_name=filename,
                mime="application/x-sqlite3",
                key="download_db_backup"
            )
            st.success(t['backup_ready'])
        except Exception as e:
            st.error(f"{t['backup_error']}: {str(e)}")

    st.divider()

    # Restore section
    st.subheader(t['restore_database'])
    st.warning(t['restore_warning'])

    uploaded_file = st.file_uploader(
        t['upload_backup_file'],
        type=['db'],
        key="restore_db_upload"
    )

    if uploaded_file is not None:
        st.info(f"{t['file_selected']}: {uploaded_file.name} ({uploaded_file.size / 1024:.1f} KB)")

        # Confirmation checkbox
        confirm_restore = st.checkbox(t['confirm_restore_checkbox'], key="confirm_restore")

        if confirm_restore:
            if st.button(t['restore_now'], type="secondary"):
                try:
                    backup_data = uploaded_file.read()
                    success, message = db.restore_database_from_backup(backup_data)

                    if success:
                        st.success(t['restore_success'])
                        st.info(t['restore_relogin'])
                        st.rerun()
                    else:
                        st.error(f"{t['restore_error']}: {message}")
                except Exception as e:
                    st.error(f"{t['restore_error']}: {str(e)}")


def render_chat_management_tab(t):
    """Render the chat management tab for admins (rooms + messages)."""
    st.subheader(f"💬 {t['chat_management_title']}")
    st.info(t['chat_management_info'])

    all_rooms = db.get_chat_rooms(is_admin=True)
    room_type_labels = {
        'general': t.get('chat_room_type_general', 'General'),
        'award': t.get('chat_room_type_award', 'Special Callsign'),
        'admin': t.get('chat_room_type_admin', 'Admin'),
        'custom': t.get('chat_room_type_custom', 'Custom'),
    }

    # --- Room Management ---
    st.subheader(t.get('chat_room_management', 'Room Management'))

    with st.expander(t.get('chat_create_room', 'Create Room'), expanded=False):
        room_name = st.text_input(
            t.get('chat_room_name', 'Room Name'),
            max_chars=50,
            key="new_room_name"
        )
        room_desc = st.text_input(
            t.get('description', 'Description'),
            max_chars=200,
            key="new_room_desc"
        )
        room_admin_only = st.checkbox(
            t.get('chat_room_admin_only', 'Admin only'),
            key="new_room_admin_only"
        )
        if st.button(t.get('chat_create_room', 'Create Room'), type="primary", key="btn_create_room"):
            if not room_name.strip():
                st.error(t.get('chat_room_name_required', 'Room name is required'))
            else:
                rtype = 'admin' if room_admin_only else 'custom'
                success, message, _ = db.create_chat_room(
                    room_name.strip(), room_desc.strip(), rtype,
                    room_admin_only, st.session_state.callsign
                )
                if success:
                    st.success(t.get('chat_room_created', 'Room created'))
                    st.rerun()
                else:
                    st.error(message)

    # List existing rooms
    if all_rooms:
        for room in all_rooms:
            rtype = room_type_labels.get(room['room_type'], room['room_type'])
            admin_tag = " [Admin]" if room['is_admin_only'] else ""
            label = f"{room['name']} ({rtype}){admin_tag}"
            cols = st.columns([6, 2])
            with cols[0]:
                st.write(label)
            with cols[1]:
                # Only allow deleting custom/admin rooms (not general or award)
                if room['room_type'] in ('custom', 'admin'):
                    if st.button(
                        t.get('chat_delete_room', 'Delete'),
                        key=f"del_room_{room['id']}",
                        type="secondary"
                    ):
                        success, message = db.delete_chat_room(room['id'])
                        if success:
                            st.success(t.get('chat_room_deleted', 'Room deleted'))
                            st.rerun()
                        else:
                            st.error(message)

    st.divider()

    # --- Statistics ---
    stats = db.get_chat_stats()
    st.subheader(t['chat_stats_title'])
    st.metric(t['chat_total_messages'], stats['total'])

    if stats['per_room']:
        col_left, col_right = st.columns(2)

        with col_left:
            st.caption(t.get('chat_per_room', 'Messages per Room'))
            rows_rm = []
            for row in stats['per_room']:
                rows_rm.append({
                    t.get('chat_room_col', 'Room'): row['room_name'] or f"ID {row['room_id']}",
                    t['chat_count_col']: row['message_count'],
                    t['chat_oldest_col']: (row['oldest'] or '')[:16],
                    t['chat_newest_col']: (row['newest'] or '')[:16],
                })
            st.dataframe(rows_rm, use_container_width=True, hide_index=True)

        with col_right:
            st.caption(t['chat_per_user'])
            user_stats = db.get_chat_stats_by_user()
            if user_stats:
                rows_usr = []
                for row in user_stats:
                    rows_usr.append({
                        t['chat_user_col']: row['operator_callsign'],
                        t['chat_count_col']: row['message_count'],
                        t['chat_oldest_col']: (row['oldest'] or '')[:16],
                        t['chat_newest_col']: (row['newest'] or '')[:16],
                    })
                st.dataframe(rows_usr, use_container_width=True, hide_index=True)
    else:
        st.info(t['chat_no_messages_db'])

    st.divider()

    # --- Delete by room ---
    st.subheader(t.get('chat_clean_by_room', 'Delete by Room'))
    st.caption(t.get('chat_clean_by_room_info', 'Delete all messages for a specific room.'))

    if all_rooms:
        room_options = {r['name']: r['id'] for r in all_rooms}
        selected_room_name = st.selectbox(
            t.get('chat_select_room', 'Select room'),
            options=list(room_options.keys()),
            key="chat_mgmt_room_select"
        )
        if st.button(t.get('chat_delete_room_btn', 'Delete messages for this room'), key="chat_del_by_room", type="secondary"):
            room_id = room_options[selected_room_name]
            deleted = db.delete_chat_messages_by_room(room_id)
            if deleted:
                st.success(f"{deleted} {t['chat_deleted_count']}")
            else:
                st.info(t['chat_nothing_to_delete'])
            st.rerun()
    else:
        st.info(t['chat_no_messages_db'])

    st.divider()

    # --- Delete old messages ---
    st.subheader(t['chat_clean_old'])
    st.caption(t['chat_clean_old_info'])

    days = st.number_input(
        t['chat_days_to_keep'],
        min_value=1, max_value=3650, value=30, step=1,
        key="chat_mgmt_days"
    )

    room_filter_options = [t.get('chat_all_rooms', 'All rooms')] + [r['name'] for r in all_rooms]
    room_filter_name = st.selectbox(
        t.get('chat_filter_room_optional', 'Filter by room (optional)'),
        options=room_filter_options,
        key="chat_mgmt_old_room"
    )

    if st.button(t['chat_delete_old_btn'], key="chat_del_old", type="secondary"):
        if room_filter_name == t.get('chat_all_rooms', 'All rooms'):
            deleted = db.delete_chat_messages_older_than(days)
        else:
            room_id = next(r['id'] for r in all_rooms if r['name'] == room_filter_name)
            deleted = db.delete_chat_messages_older_than(days, room_id)
        if deleted:
            st.success(f"{deleted} {t['chat_deleted_count']}")
        else:
            st.info(t['chat_nothing_to_delete'])
        st.rerun()

    st.divider()

    # --- Delete all ---
    st.subheader(t['chat_delete_all'])
    st.warning(t['chat_delete_all_warning'])
    confirm = st.checkbox(t['chat_confirm_delete_all'], key="chat_mgmt_confirm_all")
    if confirm:
        if st.button(t['chat_delete_all_btn'], key="chat_del_all", type="primary"):
            deleted = db.delete_all_chat_messages()
            st.success(f"{deleted} {t['chat_deleted_count']}")
            st.rerun()


def render_announcements_admin_tab(t):
    """
    Render the announcements management tab for admins.

    Args:
        t: Translations dictionary
    """
    st.subheader(f"📢 {t['announcements_management']}")
    st.info(t['announcements_management_info'])

    # Create new announcement form
    st.markdown(f"### {t['create_new_announcement']}")
    with st.form("create_announcement_form"):
        title = st.text_input(t['announcement_title'], max_chars=200)
        content = st.text_area(t['announcement_content'], max_chars=2000, height=150)
        submit = st.form_submit_button(t['create_announcement'], type="primary")

        if submit:
            if not title or not content:
                st.error(t['error_fill_all_fields'])
            else:
                success, message = db.create_announcement(
                    title, content, st.session_state.callsign
                )
                if success:
                    st.success(t['announcement_created'])
                    st.rerun()
                else:
                    st.error(message)

    st.divider()

    # List existing announcements
    st.markdown(f"### {t['existing_announcements']}")
    announcements = db.get_all_announcements()

    if announcements:
        for ann in announcements:
            status_icon = "✅" if ann['is_active'] else "❌"
            with st.expander(f"{status_icon} {ann['title']}", expanded=False):
                st.write(f"**{t['content']}:** {ann['content']}")
                st.write(f"**{t['created_by_label']}:** {ann['created_by']}")
                st.write(f"**{t['created_label']}:** {ann['created_at']}")
                st.write(f"**{t['status']}:** {t['active'] if ann['is_active'] else t['inactive']}")

                col1, col2 = st.columns(2)
                with col1:
                    if st.button(t['toggle_status'], key=f"toggle_ann_{ann['id']}"):
                        success, message = db.toggle_announcement_status(ann['id'])
                        if success:
                            st.success(t['announcement_status_updated'])
                            st.rerun()
                        else:
                            st.error(message)
                with col2:
                    if st.button(t['delete_announcement'], key=f"delete_ann_{ann['id']}", type="secondary"):
                        success, message = db.delete_announcement(ann['id'])
                        if success:
                            st.success(t['announcement_deleted'])
                            st.rerun()
                        else:
                            st.error(message)
    else:
        st.info(t['no_announcements'])
