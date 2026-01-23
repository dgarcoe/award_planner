import streamlit as st
import pandas as pd
from datetime import datetime
import database as db
import os
from translations import get_all_texts, AVAILABLE_LANGUAGES
from streamlit_autorefresh import st_autorefresh
import plotly.graph_objects as go

# Common ham radio bands and modes
BANDS = ['160m', '80m', '60m', '40m', '30m', '20m', '17m', '15m', '12m', '10m', '6m', '2m', '70cm']
MODES = ['CW', 'SSB', 'FT4', 'FT8', 'RTTY', 'PSK']

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
        st.session_state.language = 'gl'
    if 'current_award_id' not in st.session_state:
        st.session_state.current_award_id = None

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

    admin_tab1, admin_tab2, admin_tab3, admin_tab4, admin_tab5, admin_tab6, admin_tab7 = st.tabs([
        t['tab_create_operator'],
        t['tab_manage_operators'],
        t['tab_manage_admins'],
        t['tab_reset_password'],
        t['tab_manage_blocks'],
        t['tab_system_stats'],
        f"🏆 {t['tab_manage_awards']}"
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

        # Award filter for admin
        all_awards_admin = db.get_all_awards()
        if all_awards_admin:
            selected_admin_award = st.selectbox(
                t['filter_by_award'],
                options=[award['id'] for award in all_awards_admin],
                format_func=lambda x: next((a['name'] for a in all_awards_admin if a['id'] == x), ''),
                key="admin_award_filter"
            )
            all_blocks = db.get_all_blocks(selected_admin_award)
        else:
            all_blocks = []
            st.warning(t['no_awards_exist'])

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

    with admin_tab7:
        st.subheader(f"🏆 {t['award_management']}")
        st.info(t['award_management_info'])

        # Create new award
        st.subheader(t['create_new_award'])
        with st.form("create_award_form"):
            award_name = st.text_input(t['award_name'], max_chars=100, key="new_award_name")
            award_description = st.text_area(t['description'], max_chars=500, key="new_award_desc")
            col1, col2 = st.columns(2)
            with col1:
                start_date = st.date_input(t['start_date'], key="new_award_start")
            with col2:
                end_date = st.date_input(t['end_date'], key="new_award_end")

            submit = st.form_submit_button(t['create_award'], type="primary")

            if submit:
                if not award_name:
                    st.error(t['error_award_name_required'])
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

        # List and manage existing awards
        st.subheader(t['existing_awards'])
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
                        if st.button(t['delete_award'], key=f"delete_award_{award['id']}", type="secondary"):
                            success, message = db.delete_award(award['id'])
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)
        else:
            st.info(t['no_awards_created'])

def operator_panel():
    """Display the operator coordination panel."""
    t = get_all_texts(st.session_state.language)

    # Auto-refresh every 5 seconds to show real-time updates
    st_autorefresh(interval=5000, key="datarefresh")

    st.title(f"🎙️ {t['app_title']}")
    st.subheader(f"{t['welcome']}, {st.session_state.operator_name} ({st.session_state.callsign})")

    # Show admin indicator if admin
    if st.session_state.is_admin:
        st.info(f"🔑 {t['admin_privileges']}")

    # Award selector
    active_awards = db.get_active_awards()
    if not active_awards:
        if st.session_state.is_admin:
            st.warning(f"⚠️ {t['error_no_awards_admin']}")
            st.session_state.current_award_id = None
        else:
            st.error(f"⚠️ {t['error_no_awards_operator']}")
            st.stop()

    if active_awards:
        # Initialize current_award_id if not set
        if not st.session_state.current_award_id and active_awards:
            st.session_state.current_award_id = active_awards[0]['id']

        st.write("---")
        selected_award = st.selectbox(
            f"🏆 {t['select_award']}",
            options=[award['id'] for award in active_awards],
            format_func=lambda x: next((a['name'] for a in active_awards if a['id'] == x), ''),
            index=[award['id'] for award in active_awards].index(st.session_state.current_award_id) if st.session_state.current_award_id in [award['id'] for award in active_awards] else 0,
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
        tab1, tab_timeline, tab4, tab5 = st.tabs([
            f"📡 {t['tab_block']}",
            f"🔥 {t['tab_activity_dashboard']}",
            f"🔐 {t['admin_panel']}",
            f"⚙️ {t['tab_settings']}"
        ])
    else:
        tab1, tab_timeline, tab5 = st.tabs([
            f"📡 {t['tab_block']}",
            f"🔥 {t['tab_activity_dashboard']}",
            f"⚙️ {t['tab_settings']}"
        ])
        tab4 = None

    with tab1:
        st.header(t['block_band_mode'])

        if not st.session_state.current_award_id:
            st.warning(f"⚠️ {t['error_no_award_selected']}")
        else:
            st.info(t['block_info'])

            col1, col2 = st.columns(2)
            with col1:
                band_to_block = st.selectbox(t['select_band'], BANDS, key="block_band")
            with col2:
                mode_to_block = st.selectbox(t['select_mode'], MODES, key="block_mode")

            if st.button(t['block'], type="primary"):
                success, message = db.block_band_mode(
                    st.session_state.callsign,
                    band_to_block,
                    mode_to_block,
                    st.session_state.current_award_id
                )
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

            # Show current blocks below
            st.divider()
            st.subheader(t['your_current_blocks'])

            my_blocks = db.get_operator_blocks(st.session_state.callsign, st.session_state.current_award_id)

            if my_blocks:
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
                                block['mode'],
                                st.session_state.current_award_id
                            )
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)
            else:
                st.info(t['no_active_blocks'])

    with tab_timeline:
        st.header(f"🔥 {t['activity_dashboard']}")

        if not st.session_state.current_award_id:
            st.warning(f"⚠️ {t['error_no_award_selected']}")
        else:
            st.info(t['activity_dashboard_info'])

            all_blocks = db.get_all_blocks(st.session_state.current_award_id)

            # Create dictionaries for operator and date information
            blocks_dict = {(block['band'], block['mode']): block['operator_callsign'] for block in all_blocks}
            date_dict = {(block['band'], block['mode']): block['blocked_at'] for block in all_blocks}
            name_dict = {(block['band'], block['mode']): block['operator_name'] for block in all_blocks}

            # Build matrices for heatmap
            z_values = []  # For color coding (0 = free, 1 = blocked)
            text_values = []  # For display text
            hover_values = []  # For hover information

            for band in BANDS:
                z_row = []
                text_row = []
                hover_row = []
                for mode in MODES:
                    key = (band, mode)
                    if key in blocks_dict:
                        z_row.append(1)  # Blocked
                        text_row.append(blocks_dict[key])
                        hover_text = f"<b>{band} / {mode}</b><br>"
                        hover_text += f"{t['operator']}: {name_dict[key]} ({blocks_dict[key]})<br>"
                        hover_text += f"{t['blocked_at']}: {date_dict[key]}"
                        hover_row.append(hover_text)
                    else:
                        z_row.append(0)  # Free
                        text_row.append(t['free_status'])
                        hover_row.append(f"<b>{band} / {mode}</b><br>{t['status_available']}")

                z_values.append(z_row)
                text_values.append(text_row)
                hover_values.append(hover_row)

            # Create Plotly heatmap
            fig = go.Figure(data=go.Heatmap(
                z=z_values,
                x=MODES,
                y=BANDS,
                text=text_values,
                hovertemplate='%{hovertext}<extra></extra>',
                hovertext=hover_values,
                texttemplate='%{text}',
                textfont={"size": 12, "color": "white"},
                colorscale=[
                    [0, '#90EE90'],  # Green for FREE
                    [1, '#FF6B6B']   # Red for BLOCKED
                ],
                showscale=False,
                xgap=2,
                ygap=2
            ))

            # Update layout
            fig.update_layout(
                title=t['band_mode_matrix'],
                xaxis_title=t['mode_label'],
                yaxis_title=t['band_label'],
                height=600,
                margin=dict(l=80, r=20, t=60, b=60),
                font=dict(size=12),
                plot_bgcolor='white',
                xaxis=dict(side='top')
            )

            # Display the heatmap
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
                df = pd.DataFrame(all_blocks)
                band_counts = df['band'].value_counts().reindex(BANDS, fill_value=0)
                st.bar_chart(band_counts)

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
        page_title="QuendAward: Ham Radio Award Operator Coordination Tool",
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
