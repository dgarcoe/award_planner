import streamlit as st
import pandas as pd
from datetime import datetime
import database as db
import os
from translations import get_all_texts, AVAILABLE_LANGUAGES

# Common ham radio bands and modes
BANDS = ['160m', '80m', '60m', '40m', '30m', '20m', '17m', '15m', '12m', '10m', '6m', '2m', '70cm']
MODES = ['SSB', 'CW', 'FM', 'RTTY', 'FT8', 'FT4', 'PSK31', 'SSTV', 'AM']

# Admin credentials from environment variables
ADMIN_CALLSIGN = os.getenv('ADMIN_CALLSIGN', '').upper()
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', '')

def init_session_state():
    """Initialize session state variables."""
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'callsign' not in st.session_state:
        st.session_state.callsign = None
    if 'operator_name' not in st.session_state:
        st.session_state.operator_name = None
    if 'is_admin' not in st.session_state:
        st.session_state.is_admin = False
    if 'is_env_admin' not in st.session_state:
        st.session_state.is_env_admin = False
    if 'language' not in st.session_state:
        st.session_state.language = 'en'

def authenticate_admin(callsign: str, password: str) -> bool:
    """Check if credentials match admin environment variables."""
    if not ADMIN_CALLSIGN or not ADMIN_PASSWORD:
        return False
    return callsign.upper() == ADMIN_CALLSIGN and password == ADMIN_PASSWORD

def login_page():
    """Display the login page."""
    t = get_all_texts(st.session_state.language)

    st.title(f"🎙️ {t['app_title']}")
    st.subheader(t['operator_login'])

    # Language selector
    col1, col2 = st.columns([4, 1])
    with col2:
        lang = st.selectbox(
            t['language'],
            options=list(AVAILABLE_LANGUAGES.keys()),
            format_func=lambda x: AVAILABLE_LANGUAGES[x],
            index=list(AVAILABLE_LANGUAGES.keys()).index(st.session_state.language),
            key="lang_selector"
        )
        if lang != st.session_state.language:
            st.session_state.language = lang
            st.rerun()

    with st.form("login_form"):
        callsign = st.text_input(t['callsign'], max_chars=20).upper()
        password = st.text_input(t['password'], type="password", max_chars=100)
        submit = st.form_submit_button(t['login_button'], type="primary")

        if submit:
            if not callsign or not password:
                st.error(t['error_enter_credentials'])
            else:
                # Check if admin login (env-based)
                if authenticate_admin(callsign, password):
                    st.session_state.logged_in = True
                    st.session_state.callsign = callsign
                    st.session_state.operator_name = t['admin']
                    st.session_state.is_admin = True
                    st.session_state.is_env_admin = True
                    st.success(f"{t['success_welcome']}, {t['admin']}!")
                    st.rerun()
                else:
                    # Check database for regular operator (may also be admin)
                    success, message, operator = db.authenticate_operator(callsign, password)
                    if success and operator:
                        st.session_state.logged_in = True
                        st.session_state.callsign = operator['callsign']
                        st.session_state.operator_name = operator['operator_name']
                        st.session_state.is_admin = bool(operator.get('is_admin', 0))
                        st.session_state.is_env_admin = False
                        st.success(f"{t['success_welcome']}, {operator['operator_name']}!")
                        st.rerun()
                    else:
                        st.error(message)

def admin_panel():
    """Display the admin management panel."""
    t = get_all_texts(st.session_state.language)
    st.header(f"🔐 {t['admin_panel']}")

    admin_tab1, admin_tab2, admin_tab3, admin_tab4, admin_tab5, admin_tab6 = st.tabs([
        t['tab_create_operator'],
        t['tab_manage_operators'],
        t['tab_manage_admins'],
        t['tab_reset_password'],
        t['tab_manage_blocks'],
        t['tab_system_stats']
    ])

    with admin_tab1:
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

    with admin_tab2:
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

    with admin_tab3:
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

    with admin_tab4:
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

    with admin_tab5:
        st.subheader(t['manage_all_blocks'])
        st.info(t['manage_blocks_info'])

        all_blocks = db.get_all_blocks()

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
                        success, message = db.admin_unblock_band_mode(block['band'], block['mode'])
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
        else:
            st.info(t['no_blocks_to_manage'])

    with admin_tab6:
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

def operator_panel():
    """Display the operator coordination panel."""
    t = get_all_texts(st.session_state.language)

    st.title(f"🎙️ {t['app_title']}")
    st.subheader(f"{t['welcome']}, {st.session_state.operator_name} ({st.session_state.callsign})")

    # Show admin indicator if admin
    if st.session_state.is_admin:
        st.info(f"🔑 {t['admin_privileges']}")

    # Logout and language selector
    col1, col2, col3 = st.columns([4, 1, 1])
    with col2:
        lang = st.selectbox(
            t['language'],
            options=list(AVAILABLE_LANGUAGES.keys()),
            format_func=lambda x: AVAILABLE_LANGUAGES[x],
            index=list(AVAILABLE_LANGUAGES.keys()).index(st.session_state.language),
            key="lang_selector_panel",
            label_visibility="collapsed"
        )
        if lang != st.session_state.language:
            st.session_state.language = lang
            st.rerun()
    with col3:
        if st.button(t['logout']):
            # Auto-liberate all blocks when logging out
            if st.session_state.callsign:
                db.unblock_all_for_operator(st.session_state.callsign)
            st.session_state.logged_in = False
            st.session_state.callsign = None
            st.session_state.operator_name = None
            st.session_state.is_admin = False
            st.session_state.is_env_admin = False
            st.rerun()

    # Main tabs - add admin tab if user is admin
    if st.session_state.is_admin:
        tab1, tab2, tab3, tab_timeline, tab4, tab5 = st.tabs([
            f"📡 {t['tab_block']}",
            f"🔓 {t['tab_unblock']}",
            f"📊 {t['tab_status']}",
            f"📈 {t['tab_timeline']}",
            f"🔐 {t['admin_panel']}",
            f"⚙️ {t['tab_settings']}"
        ])
    else:
        tab1, tab2, tab3, tab_timeline, tab5 = st.tabs([
            f"📡 {t['tab_block']}",
            f"🔓 {t['tab_unblock']}",
            f"📊 {t['tab_status']}",
            f"📈 {t['tab_timeline']}",
            f"⚙️ {t['tab_settings']}"
        ])
        tab4 = None

    with tab1:
        st.header(t['block_band_mode'])
        st.info(t['block_info'])

        col1, col2 = st.columns(2)
        with col1:
            band_to_block = st.selectbox(t['select_band'], BANDS, key="block_band")
        with col2:
            mode_to_block = st.selectbox(t['select_mode'], MODES, key="block_mode")

        if st.button(t['block'], type="primary"):
            success, message = db.block_band_mode(st.session_state.callsign, band_to_block, mode_to_block)
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

    with tab2:
        st.header(t['unblock_band_mode'])
        st.info(t['unblock_info'])

        my_blocks = db.get_operator_blocks(st.session_state.callsign)

        if my_blocks:
            st.write(f"**{t['your_current_blocks']}**")
            for block in my_blocks:
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    st.write(f"**{block['band']}**")
                with col2:
                    st.write(f"**{block['mode']}**")
                with col3:
                    if st.button(t['unblock'], key=f"unblock_{block['id']}"):
                        success, message = db.unblock_band_mode(
                            st.session_state.callsign,
                            block['band'],
                            block['mode']
                        )
                        if success:
                            st.success(message)
                            st.rerun()
                        else:
                            st.error(message)
        else:
            st.info(t['no_active_blocks'])

    with tab3:
        st.header(t['current_status'])
        st.info(t['status_info'])

        all_blocks = db.get_all_blocks()

        if all_blocks:
            df = pd.DataFrame(all_blocks)
            df = df[['band', 'mode', 'operator_callsign', 'operator_name', 'blocked_at']]
            df.columns = [t['band'], t['mode'], t['callsign'], t['operator'], t['blocked_at']]

            st.dataframe(df, use_container_width=True, hide_index=True)

            st.subheader(t['summary'])
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(t['total_blocks'], len(all_blocks))
            with col2:
                unique_operators = df[t['callsign']].nunique()
                st.metric(t['active_operators'], unique_operators)
            with col3:
                unique_bands = df[t['band']].nunique()
                st.metric(t['bands_in_use'], unique_bands)

            st.subheader(t['blocks_by_band'])
            band_counts = df[t['band']].value_counts()
            st.bar_chart(band_counts)
        else:
            st.success(t['no_blocks_active'])

    with tab_timeline:
        st.header(t['timeline_title'])
        st.info(t['timeline_info'])

        all_blocks = db.get_all_blocks()

        # Create a matrix view of bands vs modes
        # Create a dictionary mapping (band, mode) to operator
        blocks_dict = {(block['band'], block['mode']): block['operator_callsign'] for block in all_blocks}

        # Create data for visualization
        timeline_data = []
        for band in BANDS:
            for mode in MODES:
                key = (band, mode)
                if key in blocks_dict:
                    timeline_data.append({
                        t['band']: band,
                        t['mode']: mode,
                        t['operator']: blocks_dict[key],
                        'Status': blocks_dict[key]
                    })
                else:
                    timeline_data.append({
                        t['band']: band,
                        t['mode']: mode,
                        t['operator']: t['free'],
                        'Status': t['free']
                    })

        # Create DataFrame
        if timeline_data:
            df_timeline = pd.DataFrame(timeline_data)

            # Create a pivot table for better visualization
            pivot_table = df_timeline.pivot_table(
                index=t['band'],
                columns=t['mode'],
                values='Status',
                aggfunc='first',
                fill_value=t['free']
            )

            # Reorder to match BANDS order
            pivot_table = pivot_table.reindex(BANDS)

            # Display as a styled dataframe
            st.dataframe(pivot_table, use_container_width=True)

            # Show legend
            st.subheader("Legend")
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**{t['free']}**: Available for use")
            with col2:
                unique_operators = set(block['operator_callsign'] for block in all_blocks)
                if unique_operators:
                    st.write("**Active operators**: " + ", ".join(sorted(unique_operators)))

    if tab4 and st.session_state.is_admin:
        with tab4:
            admin_panel()

    with tab5:
        st.header(t['settings'])

        # Admin cannot change password if env-based admin
        if st.session_state.is_env_admin:
            st.info(t['admin_password_env'])
        else:
            st.subheader(t['change_password'])

            with st.form("change_password_form"):
                old_password = st.text_input(t['current_password'], type="password")
                new_password = st.text_input(t['new_password'], type="password")
                new_password_confirm = st.text_input(t['confirm_new_password'], type="password")

                submit = st.form_submit_button(t['change_password'])

                if submit:
                    if not old_password or not new_password:
                        st.error(t['error_fill_all_fields'])
                    elif new_password != new_password_confirm:
                        st.error(t['error_passwords_not_match'])
                    elif len(new_password) < 6:
                        st.error(t['error_password_min_length'])
                    else:
                        success, message = db.change_password(
                            st.session_state.callsign,
                            old_password,
                            new_password
                        )
                        if success:
                            st.success(message)
                        else:
                            st.error(message)

def main():
    """Main application entry point."""
    st.set_page_config(
        page_title="Ham Radio Award Coordinator",
        page_icon="🎙️",
        layout="wide"
    )

    # Initialize session state
    init_session_state()

    # Check if admin credentials are configured
    if not ADMIN_CALLSIGN or not ADMIN_PASSWORD:
        t = get_all_texts(st.session_state.language)
        st.error(f"⚠️ {t['error_admin_not_configured']}")
        st.info(f"{t['error_set_env_vars']}\n\n- `ADMIN_CALLSIGN`\n- `ADMIN_PASSWORD`")
        st.stop()

    # Initialize database
    db.init_database()

    # Show appropriate page
    if st.session_state.logged_in:
        operator_panel()
    else:
        login_page()

if __name__ == "__main__":
    main()
