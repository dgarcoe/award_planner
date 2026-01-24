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
    with st.form("create_award_form"):
        award_name = st.text_input(t['special_callsign_name'], max_chars=100, key="new_award_name")
        award_description = st.text_area(t['description'], max_chars=500, key="new_award_desc")
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(t['start_date'], key="new_award_start")
        with col2:
            end_date = st.date_input(t['end_date'], key="new_award_end")

        submit = st.form_submit_button(t['create_special_callsign'], type="primary")

        if submit:
            if not award_name:
                st.error(t['error_special_callsign_name_required'])
            else:
                start_str = start_date.strftime("%Y-%m-%d") if start_date else ""
                end_str = end_date.strftime("%Y-%m-%d") if end_date else ""
                success, message = db.create_award(award_name, award_description, start_str, end_str)
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
        for award in awards:
            with st.expander(f"{'✅' if award['is_active'] else '❌'} {award['name']}", expanded=False):
                st.write(f"**{t['description']}:** {award['description'] or t['no_description']}")
                st.write(f"**{t['start_date']}:** {award['start_date'] or t['not_set']}")
                st.write(f"**{t['end_date']}:** {award['end_date'] or t['not_set']}")
                st.write(f"**{t['status']}:** {t['active'] if award['is_active'] else t['inactive']}")
                st.write(f"**{t['created_label']}:** {award['created_at']}")

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
