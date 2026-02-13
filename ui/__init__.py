"""UI components and panels for QuendAward."""

from ui.components import (
    render_language_selector,
    render_award_selector,
    render_activity_dashboard,
    render_announcements_operator_tab
)

from ui.admin_panel import (
    render_operators_tab,
    render_manage_blocks_tab,
    render_system_stats_tab,
    render_award_management_tab,
    render_database_management_tab,
    render_announcements_admin_tab
)

from ui.charts import (
    create_availability_heatmap,
    create_blocks_by_band_chart
)

from ui.styles import (
    inject_mobile_styles,
    inject_responsive_chart_script,
    inject_all_mobile_optimizations,
    get_responsive_heatmap_height
)
