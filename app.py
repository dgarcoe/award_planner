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
from i18n import get_all_texts, AVAILABLE_LANGUAGES

# Import UI components
from ui.components import (
    render_language_selector,
    render_award_selector,
    render_activity_dashboard,
    render_announcements_operator_tab
)

# Import admin functions
from ui.admin_panel import (
    render_operators_tab,
    render_manage_blocks_tab,
    render_system_stats_tab,
    render_award_management_tab,
    render_database_management_tab,
    render_announcements_admin_tab
)

# Import mobile styles
from ui.styles import inject_all_mobile_optimizations


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

    tab_callsigns, tab_announcements, tab_operators, tab_blocks, tab_stats, tab_database = st.tabs([
        f"🏆 {t['tab_manage_special_callsigns']}",
        f"📢 {t['tab_announcements']}",
        f"👥 {t['tab_operators']}",
        t['tab_manage_blocks'],
        t['tab_system_stats'],
        f"💾 {t['tab_database']}"
    ])

    with tab_callsigns:
        render_award_management_tab(t)

    with tab_announcements:
        render_announcements_admin_tab(t)

    with tab_operators:
        render_operators_tab(t)

    with tab_blocks:
        render_manage_blocks_tab(t)

    with tab_stats:
        render_system_stats_tab(t)

    with tab_database:
        render_database_management_tab(t)



def render_settings_tab(t):
    """Render the settings tab."""

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

    # Bell notification and logout row
    unread_count = db.get_unread_announcement_count(st.session_state.callsign)
    unread_announcements = db.get_unread_announcements(st.session_state.callsign)

    col1, col2, col3 = st.columns([6, 1, 1])
    with col2:
        # Bell icon with popover for notifications
        bell_label = f"🔔 {unread_count}" if unread_count > 0 else "🔔"
        with st.popover(bell_label, use_container_width=True):
            st.markdown(f"**📢 {t['announcements']}**")
            st.divider()

            if unread_announcements:
                for ann in unread_announcements:
                    # Make each announcement clickable
                    if st.button(
                        f"🔵 {ann['title']}",
                        key=f"notif_{ann['id']}",
                        use_container_width=True
                    ):
                        # Mark as read and navigate to announcements tab
                        db.mark_announcement_read(ann['id'], st.session_state.callsign)
                        st.session_state.go_to_announcements = True
                        st.rerun()
                    # Show preview below the button
                    content_preview = ann['content'][:80] + "..." if len(ann['content']) > 80 else ann['content']
                    st.caption(content_preview)
                    st.caption(f"{ann['created_at'][:10]} - {ann['created_by']}")
            else:
                st.info(t['no_announcements_available'])
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

    # Special callsign selector
    active_awards = db.get_active_awards()
    if not active_awards:
        if st.session_state.is_admin:
            st.warning(f"⚠️ {t['error_no_special_callsigns_admin']}")
            st.session_state.current_award_id = None
        else:
            st.error(f"⚠️ {t['error_no_special_callsigns_operator']}")
            st.stop()

    if active_awards:
        render_award_selector(active_awards, t)

    # Navigate to announcements tab if coming from notification click
    if st.session_state.get('go_to_announcements'):
        st.session_state.go_to_announcements = False
        # Use components.html to run JS that clicks the Announcements tab
        import streamlit.components.v1 as components
        components.html("""
            <script>
                const tabs = window.parent.document.querySelectorAll('[data-baseweb="tab"]');
                if (tabs.length > 1) {
                    tabs[1].click();
                }
            </script>
        """, height=0)

    # Main tabs - add admin tab if user is admin
    if st.session_state.is_admin:
        tab_dashboard, tab_announcements, tab_admin, tab_settings = st.tabs([
            f"📊 {t['tab_activity_dashboard']}",
            f"📢 {t['tab_announcements']}",
            f"🔐 {t['admin_panel']}",
            f"⚙️ {t['tab_settings']}"
        ])
    else:
        tab_dashboard, tab_announcements, tab_settings = st.tabs([
            f"📊 {t['tab_activity_dashboard']}",
            f"📢 {t['tab_announcements']}",
            f"⚙️ {t['tab_settings']}"
        ])
        tab_admin = None

    with tab_dashboard:
        render_activity_dashboard(t, st.session_state.current_award_id, st.session_state.callsign)

    with tab_announcements:
        render_announcements_operator_tab(t, st.session_state.callsign)

    if tab_admin and st.session_state.is_admin:
        with tab_admin:
            admin_panel()

    with tab_settings:
        render_settings_tab(t)


def main():
    """Main application entry point."""
    st.set_page_config(
        page_title="QuendAward: Special Callsign Operator Coordination Tool",
        page_icon="🎙️",
        layout="wide"
    )

    # Inject mobile-responsive styles
    inject_all_mobile_optimizations()

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
