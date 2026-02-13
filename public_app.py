"""
QuendAward Public Callsign Pages

This Streamlit app serves public pages for special callsigns,
allowing visitors to view photos, documents, and information
without authentication.
"""
import os
import streamlit as st
import database as db

# Page configuration
st.set_page_config(
    page_title="Special Callsign",
    page_icon="📻",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Initialize database
db.init_database()

# Custom CSS for public pages
st.markdown("""
<style>
    /* Clean public page styling */
    .main > div {
        padding-top: 2rem;
    }
    .stImage {
        border-radius: 8px;
        overflow: hidden;
    }
    .callsign-header {
        text-align: center;
        padding: 2rem 0;
    }
    .callsign-title {
        font-size: 3rem;
        font-weight: bold;
        margin-bottom: 0.5rem;
    }
    .callsign-dates {
        color: #888;
        font-size: 1.1rem;
    }
    .gallery-image {
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    /* Hide Streamlit branding for cleaner look */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


def render_not_found(callsign: str):
    """Render 404 page for unknown callsign."""
    st.markdown("""
    <div style="text-align: center; padding: 4rem 0;">
        <h1 style="font-size: 6rem; margin-bottom: 0;">📻</h1>
        <h2>Callsign Not Found</h2>
        <p style="color: #888;">The callsign <strong>{}</strong> was not found or is not active.</p>
    </div>
    """.format(callsign), unsafe_allow_html=True)


def render_no_callsign():
    """Render page when no callsign is specified."""
    st.markdown("""
    <div style="text-align: center; padding: 4rem 0;">
        <h1 style="font-size: 6rem; margin-bottom: 0;">📻</h1>
        <h2>QuendAward Public Pages</h2>
        <p style="color: #888;">Please specify a callsign in the URL.</p>
    </div>
    """, unsafe_allow_html=True)


def render_callsign_page(award: dict):
    """Render the public page for a callsign."""
    # Header with callsign name
    st.markdown(f"""
    <div class="callsign-header">
        <div class="callsign-title">📻 {award['name']}</div>
    </div>
    """, unsafe_allow_html=True)

    # Dates if available
    if award.get('start_date') or award.get('end_date'):
        date_text = ""
        if award.get('start_date') and award.get('end_date'):
            date_text = f"📅 {award['start_date']} - {award['end_date']}"
        elif award.get('start_date'):
            date_text = f"📅 From {award['start_date']}"
        elif award.get('end_date'):
            date_text = f"📅 Until {award['end_date']}"
        st.markdown(f"<p style='text-align: center; color: #888;'>{date_text}</p>", unsafe_allow_html=True)

    st.divider()

    # Description
    if award.get('description'):
        st.markdown(f"### About")
        st.write(award['description'])
        st.write("")

    # QRZ Link
    if award.get('qrz_link'):
        st.markdown(f"🔗 [View on QRZ.com]({award['qrz_link']})")
        st.write("")

    # Get media files
    media = db.get_media_for_award(award['id'], public_only=True)
    images = [m for m in media if m['media_type'] == 'image']
    documents = [m for m in media if m['media_type'] == 'document']

    # Photo Gallery
    if images:
        st.markdown("### Photo Gallery")

        # Display images in a grid (3 columns)
        cols = st.columns(3)
        for i, img in enumerate(images):
            with cols[i % 3]:
                # Read image file from disk
                file_data, filename, mime_type = db.read_media_file(img['id']) or (None, None, None)
                if file_data:
                    st.image(file_data, caption=img.get('description', ''), use_container_width=True)

    # Documents
    if documents:
        st.markdown("### Documents")
        for doc in documents:
            file_data, filename, mime_type = db.read_media_file(doc['id']) or (None, None, None)
            if file_data:
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.write(f"📄 **{filename}**")
                    if doc.get('description'):
                        st.caption(doc['description'])
                with col2:
                    st.download_button(
                        label="Download",
                        data=file_data,
                        file_name=filename,
                        mime=mime_type,
                        key=f"download_{doc['id']}"
                    )

    # Footer with link to main app
    st.divider()
    st.markdown("""
    <div style="text-align: center; padding: 2rem 0; color: #666;">
        <p>Powered by <strong>QuendAward</strong></p>
    </div>
    """, unsafe_allow_html=True)


def main():
    """Main entry point for public callsign pages."""
    # Get callsign from query parameter
    callsign = st.query_params.get("c", None)

    if not callsign:
        render_no_callsign()
        return

    # Look up the award by name
    award = db.get_award_by_name(callsign)

    if not award or not award.get('is_active'):
        render_not_found(callsign)
        return

    # Render the callsign page
    render_callsign_page(award)


if __name__ == "__main__":
    main()
