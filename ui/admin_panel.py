"""Admin panel functions for QuendAward application."""

import streamlit as st
import pandas as pd
import database as db


def render_create_operator_tab(t):
    """Render the create operator tab."""
    st.subheader(t['create_new_operator'])
    st.info(t['create_operator_info'])

    with st.form("create_operator_form"):
        new_callsign = st.text_input(t['callsign'], max_chars=20, key="new_call").upper()
        new_operator_name = st.text_input(t['operator_name'], max_chars=100)
        new_password = st.text_input(t['password'], type="password", max_chars=100, key="new_pass")
        new_password_confirm = st.text_input(t['confirm_password'], type="password", max_chars=100, key="new_pass_conf")
        is_admin = st.checkbox(t['grant_admin_privileges'], value=False)

        submit = st.form_submit_button(t['create_operator'], type="primary")

        if submit:
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
                else:
                    st.error(message)


def render_manage_operators_tab(t):
    """Render the manage operators tab."""
    st.subheader(t['all_operators'])
    operators = db.get_all_operators()

    if operators:
        df = pd.DataFrame(operators)
        df['is_admin'] = df['is_admin'].apply(lambda x: t['yes'] if x else t['no'])
        df = df[['callsign', 'operator_name', 'is_admin', 'created_at']]
        df.columns = [t['callsign'], t['name'], t['admin_status'], t['created']]

        st.dataframe(df, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader(t['delete_operator'])
        st.warning(t['delete_operator_warning'])

        if operators:
            callsign_to_delete = st.selectbox(
                t['select_operator_to_delete'],
                options=[op['callsign'] for op in operators],
                key="delete_select"
            )

            if st.button(t['delete_operator'], type="secondary"):
                success, message = db.delete_operator(callsign_to_delete)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
    else:
        st.info(t['no_operators'])


def render_manage_admins_tab(t):
    """Render the manage admin roles tab."""
    st.subheader(t['manage_admin_roles'])
    operators = db.get_all_operators()

    # Promote section
    st.subheader(t['promote_operator'])
    st.info(t['promote_info'])

    regular_ops = [op for op in operators if not op['is_admin']]
    if regular_ops:
        callsign_to_promote = st.selectbox(
            t['select_operator_to_promote'],
            options=[op['callsign'] for op in regular_ops],
            key="promote_select"
        )

        if st.button(t['promote'], type="primary"):
            success, message = db.promote_to_admin(callsign_to_promote)
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)
    else:
        st.info(t['no_operators_to_promote'])

    st.divider()

    # Demote section
    st.subheader(t['demote_operator'])
    st.info(t['demote_info'])

    admin_ops = [op for op in operators if op['is_admin']]
    if admin_ops:
        callsign_to_demote = st.selectbox(
            t['select_operator_to_demote'],
            options=[op['callsign'] for op in admin_ops],
            key="demote_select"
        )

        if st.button(t['demote'], type="secondary"):
            success, message = db.demote_from_admin(callsign_to_demote)
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)
    else:
        st.info(t['no_operators_to_demote'])


def render_reset_password_tab(t):
    """Render the reset password tab."""
    st.subheader(t['reset_operator_password'])
    st.info(t['reset_password_info'])

    operators = db.get_all_operators()

    if operators:
        callsign_to_reset = st.selectbox(
            t['select_operator'],
            options=[op['callsign'] for op in operators],
            key="reset_select"
        )

        with st.form("reset_password_form"):
            new_password = st.text_input(t['new_password'], type="password", key="new_pwd")
            new_password_confirm = st.text_input(t['confirm_new_password'], type="password", key="new_pwd_confirm")

            submit = st.form_submit_button(t['reset_password'])

            if submit:
                if not new_password:
                    st.error(t['error_enter_password'])
                elif new_password != new_password_confirm:
                    st.error(t['error_passwords_not_match'])
                elif len(new_password) < 6:
                    st.error(t['error_password_min_length'])
                else:
                    success, message = db.admin_reset_password(callsign_to_reset, new_password)
                    if success:
                        st.success(message)
                        st.info(f"**{t['new_credentials_for']} {callsign_to_reset}:**\n\n{t['password']}: `{new_password}`")
                    else:
                        st.error(message)
    else:
        st.info(t['no_operators'])


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
