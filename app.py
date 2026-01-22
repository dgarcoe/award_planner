import streamlit as st
import pandas as pd
from datetime import datetime
import database as db

# Common ham radio bands and modes
BANDS = ['160m', '80m', '60m', '40m', '30m', '20m', '17m', '15m', '12m', '10m', '6m', '2m', '70cm']
MODES = ['SSB', 'CW', 'FM', 'RTTY', 'FT8', 'FT4', 'PSK31', 'SSTV', 'AM']

def init_session_state():
    """Initialize session state variables."""
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'callsign' not in st.session_state:
        st.session_state.callsign = None
    if 'operator_name' not in st.session_state:
        st.session_state.operator_name = None

def login_page():
    """Display the login/registration page."""
    st.title("🎙️ Ham Radio Award Coordinator")
    st.subheader("Operator Login / Registration")

    with st.form("login_form"):
        callsign = st.text_input("Callsign", max_chars=20).upper()
        operator_name = st.text_input("Operator Name", max_chars=100)
        submit = st.form_submit_button("Login / Register")

        if submit:
            if not callsign or not operator_name:
                st.error("Please fill in all fields")
            else:
                # Register or update operator
                if db.register_operator(callsign, operator_name):
                    st.session_state.logged_in = True
                    st.session_state.callsign = callsign
                    st.session_state.operator_name = operator_name
                    st.success(f"Welcome, {operator_name}!")
                    st.rerun()
                else:
                    st.error("Failed to register/login")

def main_page():
    """Display the main coordination page."""
    st.title(f"🎙️ Ham Radio Award Coordinator")
    st.subheader(f"Welcome, {st.session_state.operator_name} ({st.session_state.callsign})")

    # Logout button
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.callsign = None
        st.session_state.operator_name = None
        st.rerun()

    # Create tabs for different functions
    tab1, tab2, tab3 = st.tabs(["📡 Block Band/Mode", "🔓 Unblock Band/Mode", "📊 Current Status"])

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

        # Get operator's current blocks
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
            # Convert to DataFrame for better display
            df = pd.DataFrame(all_blocks)
            df = df[['band', 'mode', 'operator_callsign', 'operator_name', 'blocked_at']]
            df.columns = ['Band', 'Mode', 'Callsign', 'Operator', 'Blocked At']

            # Display as table
            st.dataframe(df, use_container_width=True, hide_index=True)

            # Summary statistics
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

            # Visualization by band
            st.subheader("Blocks by Band")
            band_counts = df['Band'].value_counts()
            st.bar_chart(band_counts)

        else:
            st.success("No bands/modes are currently blocked. All frequencies are available!")

def main():
    """Main application entry point."""
    st.set_page_config(
        page_title="Ham Radio Award Coordinator",
        page_icon="🎙️",
        layout="wide"
    )

    # Initialize database
    db.init_database()

    # Initialize session state
    init_session_state()

    # Show appropriate page
    if st.session_state.logged_in:
        main_page()
    else:
        login_page()

if __name__ == "__main__":
    main()
