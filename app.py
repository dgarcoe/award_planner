"""
QuendAward: Ham Radio Award Operator Coordination Tool

Main application file with Streamlit UI.
"""

import hmac
import logging
import time
from collections import defaultdict
from datetime import timedelta

import bcrypt
import streamlit as st
import database as db

# Import configuration
from config import (
    ADMIN_CALLSIGN,
    ADMIN_PASSWORD_HASH,
    AUTO_REFRESH_INTERVAL_MS,
    DEFAULT_LANGUAGE,
    CHAT_ENABLED,
    MQTT_WS_URL,
    CHAT_HISTORY_LIMIT,
    MAX_LOGIN_ATTEMPTS,
    LOGIN_LOCKOUT_SECONDS,
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
    render_announcements_admin_tab,
    render_chat_management_tab,
    render_feature_visibility_tab,
)

# Import mobile styles
from ui.styles import inject_all_mobile_optimizations

# Import chat widget
from ui.chat_widget import render_chat_widget

# Import shared validation
from core.validation import validate_password


logger = logging.getLogger(__name__)

# In-memory login rate limiter: callsign -> [timestamps of failed attempts]
_login_attempts: dict[str, list[float]] = defaultdict(list)


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


def _check_rate_limit(callsign: str) -> bool:
    """Return True if the callsign is rate-limited (too many failed attempts)."""
    now = time.time()
    attempts = _login_attempts[callsign]
    # Prune old attempts outside the lockout window
    _login_attempts[callsign] = [t for t in attempts if now - t < LOGIN_LOCKOUT_SECONDS]
    return len(_login_attempts[callsign]) >= MAX_LOGIN_ATTEMPTS


def _record_failed_attempt(callsign: str):
    """Record a failed login attempt for rate limiting."""
    _login_attempts[callsign].append(time.time())


def _logout():
    """Clear all session state and log out the current user."""
    if st.session_state.callsign:
        db.unblock_all_for_operator(st.session_state.callsign)
    keys_to_clear = ['logged_in', 'callsign', 'operator_name', 'is_admin',
                     'is_env_admin', 'current_award_id', 'go_to_announcements',
                     'reset_password_callsign']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]
    st.rerun()


def authenticate_admin(callsign: str, password: str) -> bool:
    """Check if credentials match admin environment variables using constant-time comparison."""
    if not ADMIN_CALLSIGN or not ADMIN_PASSWORD_HASH:
        return False
    callsign_match = hmac.compare_digest(callsign.upper(), ADMIN_CALLSIGN)
    password_match = bcrypt.checkpw(password.encode('utf-8'), ADMIN_PASSWORD_HASH.encode('utf-8'))
    return callsign_match and password_match


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
            elif _check_rate_limit(callsign):
                st.error(t.get('error_too_many_attempts',
                               'Too many failed attempts. Please try again later.'))
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
                        _record_failed_attempt(callsign)
                        st.error(message)


def admin_panel():
    """Display the admin management panel."""
    t = get_all_texts(st.session_state.language)

    admin_tab_labels = [
        f"🏆 {t['tab_manage_special_callsigns']}",
        f"📢 {t['tab_announcements']}",
        f"👥 {t['tab_operators']}",
        t['tab_manage_blocks'],
        t['tab_system_stats'],
        f"💾 {t['tab_database']}",
    ]
    if CHAT_ENABLED:
        admin_tab_labels.append(f"💬 {t['tab_chat_management']}")
    admin_tab_labels.append(f"👁️ {t.get('tab_feature_visibility', 'Feature Visibility')}")

    admin_tabs = st.tabs(admin_tab_labels)
    admin_idx = 0

    with admin_tabs[admin_idx]:
        render_award_management_tab(t)
    admin_idx += 1

    with admin_tabs[admin_idx]:
        render_announcements_admin_tab(t)
    admin_idx += 1

    with admin_tabs[admin_idx]:
        render_operators_tab(t)
    admin_idx += 1

    with admin_tabs[admin_idx]:
        render_manage_blocks_tab(t)
    admin_idx += 1

    with admin_tabs[admin_idx]:
        render_system_stats_tab(t)
    admin_idx += 1

    with admin_tabs[admin_idx]:
        render_database_management_tab(t)
    admin_idx += 1

    if CHAT_ENABLED:
        with admin_tabs[admin_idx]:
            render_chat_management_tab(t)
        admin_idx += 1

    with admin_tabs[admin_idx]:
        render_feature_visibility_tab(t)



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
                elif not validate_password(new_password)[0]:
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

    # Auto-refresh interval for fragment-based refresh
    refresh_interval = timedelta(milliseconds=AUTO_REFRESH_INTERVAL_MS)

    # Load feature visibility flags
    feature_flags = db.get_feature_flags()
    show_announcements = feature_flags.get('feature_announcements', True)
    show_chat = CHAT_ENABLED and feature_flags.get('feature_chat', True)

    st.title(f"🎙️ {t['app_title']}")
    st.subheader(f"{t['welcome']}, {st.session_state.operator_name} ({st.session_state.callsign})")

    # Bell notification and logout row
    unread_ann_count = db.get_unread_announcement_count(st.session_state.callsign) if show_announcements else 0
    unread_mention_count = db.get_unread_chat_notification_count(st.session_state.callsign) if show_chat else 0
    total_unread = unread_ann_count + unread_mention_count
    unread_announcements = db.get_unread_announcements(st.session_state.callsign) if show_announcements else []
    chat_notifications = db.get_unread_chat_notifications(st.session_state.callsign) if show_chat else []

    col1, col2, col3 = st.columns([6, 1, 1])
    with col2:
        # Bell icon with popover for notifications
        bell_label = f"🔔 {total_unread}" if total_unread > 0 else "🔔"
        with st.popover(bell_label, use_container_width=True):
            # Chat mentions section
            if chat_notifications:
                st.markdown(f"**💬 {t.get('chat_mentions', 'Chat Mentions')}**")
                for notif in chat_notifications:
                    room_label = notif.get('room_name') or ''
                    btn_label = f"🔵 @{notif['sender_callsign']}"
                    if room_label:
                        btn_label += f" ({room_label})"
                    if st.button(
                        btn_label,
                        key=f"chat_notif_{notif['id']}",
                        use_container_width=True
                    ):
                        db.mark_chat_notification_read(notif['id'])
                        st.rerun()
                    st.caption(notif['message_preview'][:80])
                    st.caption(notif['created_at'][:16])
                st.divider()

            # Announcements section
            st.markdown(f"**📢 {t['announcements']}**")
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
            _logout()

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

    # Build tab list dynamically based on feature flags
    tab_labels = [
        f"📊 {t['tab_activity_dashboard']}",
    ]
    if show_announcements:
        tab_labels.append(f"📢 {t['tab_announcements']}")
    if show_chat:
        tab_labels.append(f"💬 {t.get('tab_chat', 'Chat')}")
    if st.session_state.is_admin:
        tab_labels.append(f"🔐 {t['admin_panel']}")
    tab_labels.append(f"⚙️ {t['tab_settings']}")

    tabs = st.tabs(tab_labels)
    tab_idx = 0

    with tabs[tab_idx]:
        @st.fragment(run_every=refresh_interval)
        def _dashboard_fragment():
            render_activity_dashboard(t, st.session_state.current_award_id, st.session_state.callsign)
        _dashboard_fragment()
    tab_idx += 1

    if show_announcements:
        with tabs[tab_idx]:
            @st.fragment(run_every=refresh_interval)
            def _announcements_fragment():
                render_announcements_operator_tab(t, st.session_state.callsign)
            _announcements_fragment()
        tab_idx += 1

    if show_chat:
        with tabs[tab_idx]:
            # Sync award rooms and load all available rooms
            db.sync_award_rooms()
            rooms = db.get_chat_rooms(is_admin=st.session_state.is_admin)
            if rooms:
                # Determine initial room (General first, then first available)
                general_rooms = [r for r in rooms if r['room_type'] == 'general']
                default_room_id = general_rooms[0]['id'] if general_rooms else rooms[0]['id']

                # Load history for every room
                all_histories = {}
                for room in rooms:
                    all_histories[room['id']] = db.get_chat_history_by_room(
                        room['id'], CHAT_HISTORY_LIMIT
                    )

                chat_translations = {
                    'chat_title': t.get('chat_title', 'Chat'),
                    'chat_placeholder': t.get('chat_placeholder', 'Type a message...'),
                    'chat_send': t.get('chat_send', 'Send'),
                    'chat_connected': t.get('chat_connected', 'Connected'),
                    'chat_disconnected': t.get('chat_disconnected', 'Disconnected'),
                    'chat_connecting': t.get('chat_connecting', 'Connecting...'),
                    'chat_not_configured': t.get('chat_not_configured', 'Chat not configured'),
                    'chat_no_messages': t.get('chat_no_messages', 'No messages yet. Start the conversation!'),
                    'chat_replying_to': t.get('chat_replying_to', 'Replying to'),
                    'chat_today': t.get('chat_today', 'Today'),
                    'chat_yesterday': t.get('chat_yesterday', 'Yesterday'),
                    'chat_event_blocked': t.get('chat_event_blocked', ''),
                    'chat_event_unblocked': t.get('chat_event_unblocked', ''),
                    'chat_event_switched': t.get('chat_event_switched', ''),
                    'chat_event_admin_unblocked': t.get('chat_event_admin_unblocked', ''),
                    'chat_event_admin_unblocked_anon': t.get('chat_event_admin_unblocked_anon', ''),
                }
                all_operators = db.get_all_operators()
                operators_for_chat = [
                    {'callsign': op['callsign'], 'name': op['operator_name']}
                    for op in all_operators
                ]
                render_chat_widget(
                    callsign=st.session_state.callsign,
                    operator_name=st.session_state.operator_name,
                    rooms=rooms,
                    all_histories=all_histories,
                    current_room_id=default_room_id,
                    mqtt_ws_url=MQTT_WS_URL,
                    translations=chat_translations,
                    operators_list=operators_for_chat,
                )
            else:
                st.info(t.get('chat_no_rooms', 'No chat rooms available.'))
        tab_idx += 1

    if st.session_state.is_admin:
        with tabs[tab_idx]:
            admin_panel()
        tab_idx += 1

    with tabs[tab_idx]:
        render_settings_tab(t)


def main():
    """Main application entry point."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

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
    if not ADMIN_CALLSIGN or not ADMIN_PASSWORD_HASH:
        t = get_all_texts(st.session_state.language)
        st.error(f"⚠️ {t['error_admin_not_configured']}")
        st.info(f"{t['error_set_env_vars']}\n\n- `ADMIN_CALLSIGN`\n- `ADMIN_PASSWORD`")
        st.stop()

    # Initialize database
    db.init_database()

    # Start MQTT subscriber for chat persistence (runs once per process)
    if CHAT_ENABLED:
        from services.mqtt_subscriber import start_subscriber_thread
        start_subscriber_thread()

    # Show appropriate page
    if st.session_state.logged_in:
        operator_panel()
    else:
        login_page()


if __name__ == "__main__":
    main()
