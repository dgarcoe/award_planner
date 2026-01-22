import streamlit as st
import pandas as pd
from datetime import datetime
import database as db
import os

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

def authenticate_admin(callsign: str, password: str) -> bool:
    """Check if credentials match admin environment variables."""
    if not ADMIN_CALLSIGN or not ADMIN_PASSWORD:
        return False
    return callsign.upper() == ADMIN_CALLSIGN and password == ADMIN_PASSWORD

def login_page():
    """Display the login page."""
    st.title("🎙️ Ham Radio Award Coordinator")
    st.subheader("Operator Login")

    with st.form("login_form"):
        callsign = st.text_input("Callsign", max_chars=20).upper()
        password = st.text_input("Password", type="password", max_chars=100)
        submit = st.form_submit_button("Login", type="primary")

        if submit:
            if not callsign or not password:
                st.error("Please enter callsign and password")
            else:
                # Check if admin login
                if authenticate_admin(callsign, password):
                    st.session_state.logged_in = True
                    st.session_state.callsign = callsign
                    st.session_state.operator_name = "Administrator"
                    st.session_state.is_admin = True
                    st.success("Welcome, Administrator!")
                    st.rerun()
                else:
                    # Check database for regular operator
                    success, message, operator = db.authenticate_operator(callsign, password)
                    if success and operator:
                        st.session_state.logged_in = True
                        st.session_state.callsign = operator['callsign']
                        st.session_state.operator_name = operator['operator_name']
                        st.session_state.is_admin = False
                        st.success(f"Welcome, {operator['operator_name']}!")
                        st.rerun()
                    else:
                        st.error(message)

def admin_panel():
    """Display the admin management panel."""
    st.header("🔐 Admin Panel")

    admin_tab1, admin_tab2, admin_tab3, admin_tab4 = st.tabs([
        "Create Operator",
        "Manage Operators",
        "Reset Password",
        "System Stats"
    ])

    with admin_tab1:
        st.subheader("Create New Operator")
        st.info("Create a new operator account and provide them with their credentials.")

        with st.form("create_operator_form"):
            new_callsign = st.text_input("Callsign", max_chars=20).upper()
            new_operator_name = st.text_input("Operator Name", max_chars=100)
            new_password = st.text_input("Password", type="password", max_chars=100)
            new_password_confirm = st.text_input("Confirm Password", type="password", max_chars=100)

            submit = st.form_submit_button("Create Operator", type="primary")

            if submit:
                if not new_callsign or not new_operator_name or not new_password:
                    st.error("Please fill in all fields")
                elif new_password != new_password_confirm:
                    st.error("Passwords do not match")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters")
                else:
                    success, message = db.create_operator(new_callsign, new_operator_name, new_password)
                    if success:
                        st.success(message)
                        st.info(f"**Credentials to provide to operator:**\n\nCallsign: `{new_callsign}`\n\nPassword: `{new_password}`")
                    else:
                        st.error(message)

    with admin_tab2:
        st.subheader("All Operators")
        operators = db.get_all_operators()

        if operators:
            # Create DataFrame for display
            df = pd.DataFrame(operators)
            df = df[['callsign', 'operator_name', 'created_at']]
            df.columns = ['Callsign', 'Name', 'Created']

            st.dataframe(df, use_container_width=True, hide_index=True)

            st.divider()
            st.subheader("Delete Operator")
            st.warning("Deleting an operator will also remove all of their active blocks")

            if operators:
                callsign_to_delete = st.selectbox(
                    "Select operator to delete",
                    options=[op['callsign'] for op in operators],
                    key="delete_select"
                )

                if st.button("Delete Operator", type="secondary"):
                    success, message = db.delete_operator(callsign_to_delete)
                    if success:
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
        else:
            st.info("No operators in the system")

    with admin_tab3:
        st.subheader("Reset Operator Password")
        st.info("Reset an operator's password and provide them with the new credentials.")

        operators = db.get_all_operators()

        if operators:
            callsign_to_reset = st.selectbox(
                "Select operator",
                options=[op['callsign'] for op in operators],
                key="reset_select"
            )

            with st.form("reset_password_form"):
                new_password = st.text_input("New Password", type="password", key="new_pwd")
                new_password_confirm = st.text_input("Confirm New Password", type="password", key="new_pwd_confirm")

                submit = st.form_submit_button("Reset Password")

                if submit:
                    if not new_password:
                        st.error("Please enter a password")
                    elif new_password != new_password_confirm:
                        st.error("Passwords do not match")
                    elif len(new_password) < 6:
                        st.error("Password must be at least 6 characters")
                    else:
                        success, message = db.admin_reset_password(callsign_to_reset, new_password)
                        if success:
                            st.success(message)
                            st.info(f"**New credentials for {callsign_to_reset}:**\n\nPassword: `{new_password}`")
                        else:
                            st.error(message)
        else:
            st.info("No operators in the system")

    with admin_tab4:
        st.subheader("System Statistics")
        operators = db.get_all_operators()
        blocks = db.get_all_blocks()

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Operators", len(operators))
        with col2:
            active_operators = len(set(block['operator_callsign'] for block in blocks))
            st.metric("Active Operators", active_operators)
        with col3:
            st.metric("Active Blocks", len(blocks))

def operator_panel():
    """Display the operator coordination panel."""
    st.title(f"🎙️ Ham Radio Award Coordinator")
    st.subheader(f"Welcome, {st.session_state.operator_name} ({st.session_state.callsign})")

    # Show admin indicator if admin
    if st.session_state.is_admin:
        st.info("🔑 Admin privileges active")

    # Logout button
    col1, col2 = st.columns([6, 1])
    with col2:
        if st.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.callsign = None
            st.session_state.operator_name = None
            st.session_state.is_admin = False
            st.rerun()

    # Main tabs - add admin tab if user is admin
    if st.session_state.is_admin:
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📡 Block Band/Mode",
            "🔓 Unblock Band/Mode",
            "📊 Current Status",
            "🔐 Admin Panel",
            "⚙️ Settings"
        ])
    else:
        tab1, tab2, tab3, tab5 = st.tabs([
            "📡 Block Band/Mode",
            "🔓 Unblock Band/Mode",
            "📊 Current Status",
            "⚙️ Settings"
        ])
        tab4 = None

    with tab1:
        st.header("Block a Band and Mode")
        st.info("Block a band/mode combination to prevent other operators from using it while you're active.")

        col1, col2 = st.columns(2)
        with col1:
            band_to_block = st.selectbox("Select Band", BANDS, key="block_band")
        with col2:
            mode_to_block = st.selectbox("Select Mode", MODES, key="block_mode")

        if st.button("Block", type="primary"):
            success, message = db.block_band_mode(st.session_state.callsign, band_to_block, mode_to_block)
            if success:
                st.success(message)
                st.rerun()
            else:
                st.error(message)

    with tab2:
        st.header("Unblock a Band and Mode")
        st.info("Release a band/mode combination when you're finished.")

        my_blocks = db.get_operator_blocks(st.session_state.callsign)

        if my_blocks:
            st.write("**Your current blocks:**")
            for block in my_blocks:
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    st.write(f"**{block['band']}**")
                with col2:
                    st.write(f"**{block['mode']}**")
                with col3:
                    if st.button("Unblock", key=f"unblock_{block['id']}"):
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
            st.info("You don't have any active blocks.")

    with tab3:
        st.header("Current Band/Mode Status")
        st.info("View all currently blocked band/mode combinations.")

        all_blocks = db.get_all_blocks()

        if all_blocks:
            df = pd.DataFrame(all_blocks)
            df = df[['band', 'mode', 'operator_callsign', 'operator_name', 'blocked_at']]
            df.columns = ['Band', 'Mode', 'Callsign', 'Operator', 'Blocked At']

            st.dataframe(df, use_container_width=True, hide_index=True)

            st.subheader("Summary")
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total Blocks", len(all_blocks))
            with col2:
                unique_operators = df['Callsign'].nunique()
                st.metric("Active Operators", unique_operators)
            with col3:
                unique_bands = df['Band'].nunique()
                st.metric("Bands in Use", unique_bands)

            st.subheader("Blocks by Band")
            band_counts = df['Band'].value_counts()
            st.bar_chart(band_counts)
        else:
            st.success("No bands/modes are currently blocked. All frequencies are available!")

    if tab4 and st.session_state.is_admin:
        with tab4:
            admin_panel()

    with tab5:
        st.header("Settings")

        # Admin cannot change password (it's in env vars)
        if st.session_state.is_admin:
            st.info("Admin password is configured via environment variables (ADMIN_PASSWORD).")
        else:
            st.subheader("Change Password")

            with st.form("change_password_form"):
                old_password = st.text_input("Current Password", type="password")
                new_password = st.text_input("New Password", type="password")
                new_password_confirm = st.text_input("Confirm New Password", type="password")

                submit = st.form_submit_button("Change Password")

                if submit:
                    if not old_password or not new_password:
                        st.error("Please fill in all fields")
                    elif new_password != new_password_confirm:
                        st.error("New passwords do not match")
                    elif len(new_password) < 6:
                        st.error("Password must be at least 6 characters")
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

    # Check if admin credentials are configured
    if not ADMIN_CALLSIGN or not ADMIN_PASSWORD:
        st.error("⚠️ Admin credentials not configured!")
        st.info("Please set the following environment variables:\n\n- `ADMIN_CALLSIGN`\n- `ADMIN_PASSWORD`")
        st.stop()

    # Initialize database
    db.init_database()

    # Initialize session state
    init_session_state()

    # Show appropriate page
    if st.session_state.logged_in:
        operator_panel()
    else:
        login_page()

if __name__ == "__main__":
    main()
