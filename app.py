"""
QuendAward: Ham Radio Award Operator Coordination Tool

Main application file with Streamlit UI.
"""

import streamlit as st
import database as db
from streamlit_autorefresh import st_autorefresh

# Import configuration
from config import (
    ADMIN_CALLSIGN,
    ADMIN_PASSWORD,
    AUTO_REFRESH_INTERVAL_MS,
    DEFAULT_LANGUAGE
)

# Import translations
from translations import get_all_texts, AVAILABLE_LANGUAGES

# Import UI components
from ui_components import (
    render_language_selector,
    render_award_selector,
    render_block_unblock_section,
    render_activity_dashboard
)

# Import admin functions
from admin_functions import (
    render_create_operator_tab,
    render_manage_operators_tab,
    render_manage_admins_tab,
    render_reset_password_tab,
    render_manage_blocks_tab,
    render_system_stats_tab,
    render_award_management_tab
)


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
        st.session_state.language = DEFAULT_LANGUAGE
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
        render_language_selector(t)

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
        render_create_operator_tab(t)

    with admin_tab2:
        render_manage_operators_tab(t)

    with admin_tab3:
        render_manage_admins_tab(t)

    with admin_tab4:
        render_reset_password_tab(t)

    with admin_tab5:
        render_manage_blocks_tab(t)

    with admin_tab6:
        render_system_stats_tab(t)

    with admin_tab7:
        render_award_management_tab(t)


def render_settings_tab(t):
    """Render the settings tab."""
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


def operator_panel():
    """Display the operator coordination panel."""
    t = get_all_texts(st.session_state.language)

    # Auto-refresh every 5 seconds to show real-time updates
    st_autorefresh(interval=AUTO_REFRESH_INTERVAL_MS, key="datarefresh")

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
        render_award_selector(active_awards, t)

    # Logout and language selector
    col1, col2, col3 = st.columns([4, 1, 1])
    with col2:
        render_language_selector(t, key_suffix="_panel")
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
            f"📊 {t['tab_activity_dashboard']}",
            f"🔐 {t['admin_panel']}",
            f"⚙️ {t['tab_settings']}"
        ])
    else:
        tab1, tab_timeline, tab5 = st.tabs([
            f"📡 {t['tab_block']}",
            f"📊 {t['tab_activity_dashboard']}",
            f"⚙️ {t['tab_settings']}"
        ])
        tab4 = None

    with tab1:
        st.header(t['block_band_mode'])
        render_block_unblock_section(t, st.session_state.callsign, st.session_state.current_award_id)

    with tab_timeline:
        st.header(f"📊 {t['activity_dashboard']}")
        render_activity_dashboard(t, st.session_state.current_award_id)

    if tab4 and st.session_state.is_admin:
        with tab4:
            admin_panel()

    with tab5:
        render_settings_tab(t)


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
