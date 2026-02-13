"""Mobile-responsive styles for QuendAward application.

This module provides CSS styles that improve the mobile experience
while keeping the desktop view unchanged.
"""

import streamlit as st


def inject_mobile_styles():
    """
    Inject responsive CSS styles for mobile devices.

    Uses media queries to apply mobile-specific styling only on smaller screens,
    preserving the desktop experience.
    """
    mobile_css = """
    <style>
    /* ====== GLOBAL STYLES (ALL DEVICES) ====== */

    /* Hide Plotly modebar (toolbar) on all devices */
    .modebar-container,
    .modebar,
    .modebar-group {
        display: none !important;
    }

    /* Style the notification popover */
    [data-testid="stPopover"] button {
        font-size: 1.1rem !important;
    }

    /* Make popover content scrollable */
    [data-testid="stPopoverBody"] {
        max-height: 400px !important;
        overflow-y: auto !important;
    }

    /* ====== MOBILE RESPONSIVE STYLES ====== */
    /* These styles only apply to screens smaller than 768px */

    @media (max-width: 768px) {
        /* ----- GENERAL LAYOUT IMPROVEMENTS ----- */

        /* Make main container use full width on mobile */
        .main .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
            max-width: 100% !important;
        }

        /* Improve heading sizes for mobile */
        h1 {
            font-size: 1.5rem !important;
        }

        h2 {
            font-size: 1.25rem !important;
        }

        h3 {
            font-size: 1.1rem !important;
        }

        /* ----- COLUMN STACKING ----- */
        /* Make columns stack vertically on mobile */
        [data-testid="column"] {
            width: 100% !important;
            flex: 1 1 100% !important;
            min-width: 100% !important;
        }

        /* Add spacing between stacked columns */
        [data-testid="stHorizontalBlock"] {
            flex-wrap: wrap !important;
            gap: 0.5rem !important;
        }

        /* ----- BUTTON IMPROVEMENTS ----- */
        /* Make buttons more touch-friendly */
        .stButton > button {
            min-height: 44px !important;
            padding: 0.5rem 1rem !important;
            font-size: 0.9rem !important;
            width: 100% !important;
        }

        /* Ensure primary buttons are visible */
        .stButton > button[kind="primary"] {
            min-height: 48px !important;
        }

        /* ----- FORM IMPROVEMENTS ----- */
        /* Make form inputs more touch-friendly */
        .stTextInput > div > div > input,
        .stSelectbox > div > div,
        .stDateInput > div > div > input {
            min-height: 44px !important;
            font-size: 16px !important; /* Prevents zoom on iOS */
        }

        /* ----- TABS IMPROVEMENTS ----- */
        /* Make tabs scrollable horizontally */
        .stTabs [data-baseweb="tab-list"] {
            overflow-x: auto !important;
            flex-wrap: nowrap !important;
            -webkit-overflow-scrolling: touch !important;
            scrollbar-width: none !important;
        }

        .stTabs [data-baseweb="tab-list"]::-webkit-scrollbar {
            display: none !important;
        }

        /* Make individual tabs smaller */
        .stTabs [data-baseweb="tab"] {
            padding: 0.5rem 0.75rem !important;
            font-size: 0.8rem !important;
            white-space: nowrap !important;
        }

        /* ----- METRICS IMPROVEMENTS ----- */
        /* Make metrics more compact */
        [data-testid="stMetric"] {
            padding: 0.5rem !important;
        }

        [data-testid="stMetricValue"] {
            font-size: 1.25rem !important;
        }

        [data-testid="stMetricLabel"] {
            font-size: 0.75rem !important;
        }

        /* ----- EXPANDER IMPROVEMENTS ----- */
        /* Make expanders more touch-friendly */
        .streamlit-expanderHeader {
            min-height: 44px !important;
            font-size: 0.9rem !important;
        }

        /* ----- TABLE/DATAFRAME IMPROVEMENTS ----- */
        /* Make dataframes scrollable */
        .stDataFrame {
            overflow-x: auto !important;
        }

        /* ----- DIALOG/MODAL IMPROVEMENTS ----- */
        /* Make modal dialogs full-width on mobile */
        [data-testid="stModal"] > div {
            width: 95vw !important;
            max-width: 95vw !important;
        }

        /* ----- INFO/WARNING/ERROR BOXES ----- */
        /* Make info boxes more readable */
        .stAlert {
            padding: 0.75rem !important;
            font-size: 0.85rem !important;
        }

        /* ----- SELECTBOX IMPROVEMENTS ----- */
        /* Improve dropdown appearance */
        .stSelectbox label {
            font-size: 0.85rem !important;
        }
    }

    /* ====== SMALL MOBILE (< 480px) ====== */
    @media (max-width: 480px) {
        /* Even more compact on very small screens */
        .main .block-container {
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
        }

        h1 {
            font-size: 1.3rem !important;
        }

        /* Hide some decorative elements */
        .stDecorationBar {
            display: none !important;
        }
    }

    /* ====== HEATMAP/CHART IMPROVEMENTS ====== */
    /* These apply to plotly charts on mobile */
    @media (max-width: 768px) {
        /* Make heatmap taller on mobile for better touch targets */
        [data-testid="stPlotlyChart"] > div,
        [data-testid="stPlotlyChart"] iframe,
        .js-plotly-plot {
            min-height: 1850px !important;
        }

        /* Allow charts to be scrollable if needed */
        .js-plotly-plot {
            overflow-x: auto !important;
        }

        /* Reduce chart container padding */
        [data-testid="stPlotlyChart"] {
            padding: 0 !important;
        }

        /* Hide hover tooltip on mobile - it blocks touch interaction */
        .hoverlayer {
            display: none !important;
        }
    }

    /* ====== LANDSCAPE MOBILE IMPROVEMENTS ====== */
    @media (max-width: 768px) and (orientation: landscape) {
        /* In landscape, allow some side-by-side layout */
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:first-child,
        [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-child(2) {
            width: 48% !important;
            flex: 1 1 48% !important;
            min-width: 48% !important;
        }
    }
    </style>
    """
    st.markdown(mobile_css, unsafe_allow_html=True)


def get_responsive_heatmap_height():
    """
    Get appropriate heatmap height based on device.

    Note: Since Streamlit runs server-side, we can't directly detect
    screen size. This returns a reasonable default that works for both.
    We rely on CSS/JS for actual responsive behavior.

    Returns:
        int: Height in pixels for the heatmap
    """
    # Return a moderate height that works reasonably on both
    # The CSS will help with overflow on mobile
    return 500


def inject_responsive_chart_script():
    """
    Inject JavaScript to make charts more responsive on mobile.

    This script adjusts chart behavior based on actual screen size.
    """
    responsive_script = """
    <script>
    (function() {
        // Function to hide ALL modebars (toolbars) on all devices
        function hideAllModebars() {
            // Target all possible modebar elements
            const modebars = document.querySelectorAll('.modebar-container, .modebar, .modebar-group, [class*="modebar"]');
            modebars.forEach(function(el) {
                el.style.display = 'none';
                el.style.visibility = 'hidden';
                el.remove();
            });

            // Also check inside iframes
            const iframes = document.querySelectorAll('iframe');
            iframes.forEach(function(iframe) {
                try {
                    const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
                    const iframeModebars = iframeDoc.querySelectorAll('.modebar-container, .modebar, .modebar-group');
                    iframeModebars.forEach(function(el) {
                        el.style.display = 'none';
                        el.remove();
                    });
                } catch(e) {}
            });
        }

        // Function to adjust plotly charts for mobile
        function adjustChartsForMobile() {
            const isMobile = window.innerWidth <= 768;
            const plotlyCharts = document.querySelectorAll('.js-plotly-plot');

            plotlyCharts.forEach(function(chart) {
                if (isMobile) {
                    // Make chart scrollable on mobile
                    chart.style.overflowX = 'auto';
                    chart.style.overflowY = 'hidden';
                }
            });

            // Always hide modebars
            hideAllModebars();
        }

        // Run on load and resize
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', adjustChartsForMobile);
        } else {
            adjustChartsForMobile();
        }
        window.addEventListener('resize', adjustChartsForMobile);

        // Also run periodically to catch dynamically loaded charts
        setInterval(adjustChartsForMobile, 2000);
    })();
    </script>
    """
    st.markdown(responsive_script, unsafe_allow_html=True)


def inject_all_mobile_optimizations():
    """
    Inject all mobile optimizations at once.

    Call this function once at the start of the app to apply
    all mobile-responsive improvements.
    """
    inject_mobile_styles()
    inject_responsive_chart_script()
