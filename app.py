import streamlit as st
import pandas as pd
from datetime import datetime
import database as db
import os
from translations import get_all_texts, AVAILABLE_LANGUAGES
import plotly.graph_objects as go
import plotly.express as px
import time
import json
import hashlib
from pathlib import Path

# Common ham radio bands and modes
BANDS = ['160m', '80m', '60m', '40m', '30m', '20m', '17m', '15m', '12m', '10m', '6m', '2m', '70cm']
MODES = ['SSB', 'CW', 'FM', 'RTTY', 'FT8', 'FT4', 'PSK31', 'SSTV', 'AM']

# Admin credentials from environment variables
ADMIN_CALLSIGN = os.getenv('ADMIN_CALLSIGN', '').upper()
ADMIN_PASSWORD = os.getenv('ADMIN_PASSWORD', '')

# Session management
SESSION_DIR = Path('.sessions')
SESSION_DIR.mkdir(exist_ok=True)

def generate_session_id(callsign: str, timestamp: float) -> str:
    """Generate a unique session ID."""
    data = f"{callsign}{timestamp}{os.urandom(16).hex()}"
    return hashlib.sha256(data.encode()).hexdigest()

def save_session(session_id: str, data: dict) -> None:
    """Save session data to file."""
    try:
        session_file = SESSION_DIR / f"{session_id}.json"
        with open(session_file, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error saving session: {e}")

def load_session(session_id: str) -> dict:
    """Load session data from file."""
    try:
        session_file = SESSION_DIR / f"{session_id}.json"
        if session_file.exists():
            with open(session_file, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"Error loading session: {e}")
    return {}

def delete_session(session_id: str) -> None:
    """Delete session file."""
    try:
        session_file = SESSION_DIR / f"{session_id}.json"
        if session_file.exists():
            session_file.unlink()
    except Exception as e:
        print(f"Error deleting session: {e}")

def init_session_state():
    """Initialize session state variables."""
    # Check for existing session from query params
    query_params = st.query_params
    session_id = query_params.get('sid', None)

    # Try to restore session if not already logged in
    if session_id and 'session_restored' not in st.session_state:
        session_data = load_session(session_id)
        if session_data:
            st.session_state.logged_in = session_data.get('logged_in', False)
            st.session_state.callsign = session_data.get('callsign', None)
            st.session_state.operator_name = session_data.get('operator_name', None)
            st.session_state.is_admin = session_data.get('is_admin', False)
            st.session_state.is_env_admin = session_data.get('is_env_admin', False)
            st.session_state.language = session_data.get('language', 'en')
            st.session_state.session_id = session_id
            st.session_state.session_restored = True

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
    if 'success_message' not in st.session_state:
        st.session_state.success_message = None
    if 'error_message' not in st.session_state:
        st.session_state.error_message = None
    if 'auto_refresh' not in st.session_state:
        st.session_state.auto_refresh = True
    if 'session_id' not in st.session_state:
        st.session_state.session_id = None

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
                    # Ensure admin exists in database for foreign key constraints
                    db.ensure_operator_exists(callsign, "Admin", password, is_admin=True)
                    st.session_state.logged_in = True
                    st.session_state.callsign = callsign
                    st.session_state.operator_name = t['admin']
                    st.session_state.is_admin = True
                    st.session_state.is_env_admin = True

                    # Create and save session
                    session_id = generate_session_id(callsign, time.time())
                    st.session_state.session_id = session_id
                    save_session(session_id, {
                        'logged_in': True,
                        'callsign': callsign,
                        'operator_name': t['admin'],
                        'is_admin': True,
                        'is_env_admin': True,
                        'language': st.session_state.language
                    })

                    # Set session ID in query params
                    st.query_params['sid'] = session_id

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

                        # Create and save session
                        session_id = generate_session_id(operator['callsign'], time.time())
                        st.session_state.session_id = session_id
                        save_session(session_id, {
                            'logged_in': True,
                            'callsign': operator['callsign'],
                            'operator_name': operator['operator_name'],
                            'is_admin': bool(operator.get('is_admin', 0)),
                            'is_env_admin': False,
                            'language': st.session_state.language
                        })

                        # Set session ID in query params
                        st.query_params['sid'] = session_id

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

    # Display pending messages
    if st.session_state.success_message:
        st.success(st.session_state.success_message)
        st.session_state.success_message = None
    if st.session_state.error_message:
        st.error(st.session_state.error_message)
        st.session_state.error_message = None

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

            # Delete session
            if st.session_state.session_id:
                delete_session(st.session_state.session_id)

            # Clear session state
            st.session_state.logged_in = False
            st.session_state.callsign = None
            st.session_state.operator_name = None
            st.session_state.is_admin = False
            st.session_state.is_env_admin = False
            st.session_state.session_id = None

            # Clear query params
            st.query_params.clear()

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
                st.session_state.success_message = f"✅ {message}"
                st.rerun()
            else:
                st.session_state.error_message = message
                st.rerun()

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
                            st.session_state.success_message = f"✅ {message}"
                            st.rerun()
                        else:
                            st.session_state.error_message = message
                            st.rerun()
        else:
            st.info(t['no_active_blocks'])

    with tab3:
        st.header(t['current_status'])
        st.info(t['status_info'])

        # Auto-refresh checkbox
        col1, col2 = st.columns([4, 1])
        with col2:
            auto_refresh_status = st.checkbox("Auto-refresh", value=st.session_state.auto_refresh, key="status_auto_refresh")
            if auto_refresh_status != st.session_state.auto_refresh:
                st.session_state.auto_refresh = auto_refresh_status

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

        # Auto-refresh logic
        if st.session_state.auto_refresh:
            time.sleep(5)
            st.rerun()

    with tab_timeline:
        st.header(t['timeline_title'])
        st.info(t['timeline_info'])

        # Auto-refresh checkbox
        col1, col2 = st.columns([4, 1])
        with col2:
            auto_refresh = st.checkbox("Auto-refresh", value=st.session_state.auto_refresh, key="timeline_auto_refresh")
            if auto_refresh != st.session_state.auto_refresh:
                st.session_state.auto_refresh = auto_refresh

        all_blocks = db.get_all_blocks()

        # Create a dictionary mapping (band, mode) to operator
        blocks_dict = {(block['band'], block['mode']): block['operator_callsign'] for block in all_blocks}

        # Create data matrix for heatmap
        # Get unique operators and assign them colors
        unique_operators = sorted(set(block['operator_callsign'] for block in all_blocks))
        operator_colors = {}
        colors = px.colors.qualitative.Set3  # Use a predefined color palette
        for idx, op in enumerate(unique_operators):
            operator_colors[op] = colors[idx % len(colors)]

        # Create matrix data
        z_data = []  # Values for heatmap (numeric encoding)
        text_data = []  # Text to display in cells
        color_data = []  # Colors for each cell

        for mode in MODES:
            row_z = []
            row_text = []
            row_color = []
            for band in BANDS:
                key = (band, mode)
                if key in blocks_dict:
                    operator = blocks_dict[key]
                    row_z.append(unique_operators.index(operator) + 1)
                    row_text.append(operator)
                    row_color.append(operator_colors[operator])
                else:
                    row_z.append(0)
                    row_text.append(t['free'])
                    row_color.append('#90EE90')  # Light green for free
            z_data.append(row_z)
            text_data.append(row_text)
            color_data.append(row_color)

        # Create heatmap using plotly
        fig = go.Figure()

        # Add colored rectangles for each cell
        for i, mode in enumerate(MODES):
            for j, band in enumerate(BANDS):
                fig.add_trace(go.Scatter(
                    x=[j],
                    y=[i],
                    mode='markers+text',
                    marker=dict(
                        size=40,
                        color=color_data[i][j],
                        symbol='square',
                        line=dict(color='white', width=2)
                    ),
                    text=text_data[i][j],
                    textposition='middle center',
                    textfont=dict(size=10, color='black'),
                    showlegend=False,
                    hovertemplate=f'<b>Band:</b> {band}<br><b>Mode:</b> {mode}<br><b>Status:</b> {text_data[i][j]}<extra></extra>'
                ))

        # Update layout
        fig.update_layout(
            title=t['timeline_title'],
            xaxis=dict(
                title=t['band'],
                tickmode='array',
                tickvals=list(range(len(BANDS))),
                ticktext=BANDS,
                side='bottom'
            ),
            yaxis=dict(
                title=t['mode'],
                tickmode='array',
                tickvals=list(range(len(MODES))),
                ticktext=MODES,
                autorange='reversed'
            ),
            height=500,
            plot_bgcolor='white',
            hovermode='closest'
        )

        st.plotly_chart(fig, use_container_width=True)

        # Show legend
        st.subheader("Legend")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"🟩 **{t['free']}**: Available for use")
        with col2:
            if unique_operators:
                st.write("**Active operators**:")
                for op in unique_operators:
                    st.markdown(f"<span style='color:{operator_colors[op]}'>⬤</span> {op}", unsafe_allow_html=True)

        # Auto-refresh logic
        if st.session_state.auto_refresh:
            time.sleep(5)
            st.rerun()

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
