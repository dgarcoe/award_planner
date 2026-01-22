"""
Translations module for Ham Radio Award Coordinator
Supports multiple languages for all UI text
"""

TRANSLATIONS = {
    'en': {
        # General
        'app_title': 'Ham Radio Award Coordinator',
        'welcome': 'Welcome',
        'admin': 'Administrator',
        'admin_privileges': 'Admin privileges active',
        'logout': 'Logout',

        # Login
        'operator_login': 'Operator Login',
        'callsign': 'Callsign',
        'password': 'Password',
        'login': 'Login',
        'login_button': 'Login',

        # Errors and messages
        'error_admin_not_configured': 'Admin credentials not configured!',
        'error_set_env_vars': 'Please set the following environment variables:',
        'error_enter_credentials': 'Please enter callsign and password',
        'error_fill_all_fields': 'Please fill in all fields',
        'error_passwords_not_match': 'Passwords do not match',
        'error_password_min_length': 'Password must be at least 6 characters',
        'success_welcome': 'Welcome',

        # Admin Panel
        'admin_panel': 'Admin Panel',
        'tab_create_operator': 'Create Operator',
        'tab_manage_operators': 'Manage Operators',
        'tab_manage_admins': 'Manage Admins',
        'tab_reset_password': 'Reset Password',
        'tab_system_stats': 'System Stats',

        # Create Operator
        'create_new_operator': 'Create New Operator',
        'create_operator_info': 'Create a new operator account and provide them with their credentials.',
        'operator_name': 'Operator Name',
        'confirm_password': 'Confirm Password',
        'create_operator': 'Create Operator',
        'credentials_to_provide': 'Credentials to provide to operator:',
        'is_admin': 'Admin privileges',
        'grant_admin_privileges': 'Grant admin privileges to this operator',

        # Manage Operators
        'all_operators': 'All Operators',
        'name': 'Name',
        'admin_status': 'Admin',
        'created': 'Created',
        'yes': 'Yes',
        'no': 'No',
        'delete_operator': 'Delete Operator',
        'delete_operator_warning': 'Deleting an operator will also remove all of their active blocks',
        'select_operator_to_delete': 'Select operator to delete',
        'no_operators': 'No operators in the system',

        # Manage Admins
        'manage_admin_roles': 'Manage Admin Roles',
        'promote_operator': 'Promote to Admin',
        'promote_info': 'Grant admin privileges to an operator',
        'select_operator_to_promote': 'Select operator to promote',
        'promote': 'Promote to Admin',
        'demote_operator': 'Demote from Admin',
        'demote_info': 'Remove admin privileges from an operator',
        'select_operator_to_demote': 'Select operator to demote',
        'demote': 'Demote from Admin',
        'no_operators_to_promote': 'No regular operators to promote',
        'no_operators_to_demote': 'No database admins to demote',

        # Reset Password
        'reset_operator_password': 'Reset Operator Password',
        'reset_password_info': "Reset an operator's password and provide them with the new credentials.",
        'select_operator': 'Select operator',
        'new_password': 'New Password',
        'confirm_new_password': 'Confirm New Password',
        'reset_password': 'Reset Password',
        'new_credentials_for': 'New credentials for',
        'error_enter_password': 'Please enter a password',

        # System Stats
        'system_statistics': 'System Statistics',
        'total_operators': 'Total Operators',
        'active_operators': 'Active Operators',
        'active_blocks': 'Active Blocks',
        'total_admins': 'Total Admins',

        # Operator Panel Tabs
        'tab_block': 'Block Band/Mode',
        'tab_unblock': 'Unblock Band/Mode',
        'tab_status': 'Current Status',
        'tab_settings': 'Settings',

        # Block Band/Mode
        'block_band_mode': 'Block a Band and Mode',
        'block_info': "Block a band/mode combination to prevent other operators from using it while you're active.",
        'select_band': 'Select Band',
        'select_mode': 'Select Mode',
        'block': 'Block',

        # Unblock Band/Mode
        'unblock_band_mode': 'Unblock a Band and Mode',
        'unblock_info': "Release a band/mode combination when you're finished.",
        'your_current_blocks': 'Your current blocks:',
        'unblock': 'Unblock',
        'no_active_blocks': "You don't have any active blocks.",

        # Current Status
        'current_status': 'Current Band/Mode Status',
        'status_info': 'View all currently blocked band/mode combinations.',
        'band': 'Band',
        'mode': 'Mode',
        'operator': 'Operator',
        'blocked_at': 'Blocked At',
        'summary': 'Summary',
        'total_blocks': 'Total Blocks',
        'bands_in_use': 'Bands in Use',
        'blocks_by_band': 'Blocks by Band',
        'no_blocks_active': 'No bands/modes are currently blocked. All frequencies are available!',

        # Settings
        'settings': 'Settings',
        'change_password': 'Change Password',
        'admin_password_env': 'Admin password is configured via environment variables (ADMIN_PASSWORD).',
        'current_password': 'Current Password',

        # Language
        'language': 'Language',
        'select_language': 'Select Language',
    },
    'es': {
        # General
        'app_title': 'Coordinador de Premios de Radio Aficionados',
        'welcome': 'Bienvenido',
        'admin': 'Administrador',
        'admin_privileges': 'Privilegios de administrador activos',
        'logout': 'Cerrar Sesión',

        # Login
        'operator_login': 'Inicio de Sesión de Operador',
        'callsign': 'Indicativo',
        'password': 'Contraseña',
        'login': 'Iniciar Sesión',
        'login_button': 'Iniciar Sesión',

        # Errors and messages
        'error_admin_not_configured': '¡Credenciales de administrador no configuradas!',
        'error_set_env_vars': 'Por favor configure las siguientes variables de entorno:',
        'error_enter_credentials': 'Por favor ingrese indicativo y contraseña',
        'error_fill_all_fields': 'Por favor complete todos los campos',
        'error_passwords_not_match': 'Las contraseñas no coinciden',
        'error_password_min_length': 'La contraseña debe tener al menos 6 caracteres',
        'success_welcome': 'Bienvenido',

        # Admin Panel
        'admin_panel': 'Panel de Administración',
        'tab_create_operator': 'Crear Operador',
        'tab_manage_operators': 'Gestionar Operadores',
        'tab_manage_admins': 'Gestionar Administradores',
        'tab_reset_password': 'Restablecer Contraseña',
        'tab_system_stats': 'Estadísticas del Sistema',

        # Create Operator
        'create_new_operator': 'Crear Nuevo Operador',
        'create_operator_info': 'Cree una nueva cuenta de operador y proporcione las credenciales.',
        'operator_name': 'Nombre del Operador',
        'confirm_password': 'Confirmar Contraseña',
        'create_operator': 'Crear Operador',
        'credentials_to_provide': 'Credenciales para proporcionar al operador:',
        'is_admin': 'Privilegios de administrador',
        'grant_admin_privileges': 'Otorgar privilegios de administrador a este operador',

        # Manage Operators
        'all_operators': 'Todos los Operadores',
        'name': 'Nombre',
        'admin_status': 'Admin',
        'created': 'Creado',
        'yes': 'Sí',
        'no': 'No',
        'delete_operator': 'Eliminar Operador',
        'delete_operator_warning': 'Eliminar un operador también eliminará todos sus bloqueos activos',
        'select_operator_to_delete': 'Seleccione el operador a eliminar',
        'no_operators': 'No hay operadores en el sistema',

        # Manage Admins
        'manage_admin_roles': 'Gestionar Roles de Administrador',
        'promote_operator': 'Promover a Administrador',
        'promote_info': 'Otorgar privilegios de administrador a un operador',
        'select_operator_to_promote': 'Seleccione el operador a promover',
        'promote': 'Promover a Administrador',
        'demote_operator': 'Degradar de Administrador',
        'demote_info': 'Eliminar privilegios de administrador de un operador',
        'select_operator_to_demote': 'Seleccione el operador a degradar',
        'demote': 'Degradar de Administrador',
        'no_operators_to_promote': 'No hay operadores regulares para promover',
        'no_operators_to_demote': 'No hay administradores de base de datos para degradar',

        # Reset Password
        'reset_operator_password': 'Restablecer Contraseña del Operador',
        'reset_password_info': 'Restablezca la contraseña de un operador y proporciónele las nuevas credenciales.',
        'select_operator': 'Seleccionar operador',
        'new_password': 'Nueva Contraseña',
        'confirm_new_password': 'Confirmar Nueva Contraseña',
        'reset_password': 'Restablecer Contraseña',
        'new_credentials_for': 'Nuevas credenciales para',
        'error_enter_password': 'Por favor ingrese una contraseña',

        # System Stats
        'system_statistics': 'Estadísticas del Sistema',
        'total_operators': 'Total de Operadores',
        'active_operators': 'Operadores Activos',
        'active_blocks': 'Bloqueos Activos',
        'total_admins': 'Total de Administradores',

        # Operator Panel Tabs
        'tab_block': 'Bloquear Banda/Modo',
        'tab_unblock': 'Desbloquear Banda/Modo',
        'tab_status': 'Estado Actual',
        'tab_settings': 'Configuración',

        # Block Band/Mode
        'block_band_mode': 'Bloquear una Banda y Modo',
        'block_info': 'Bloquee una combinación de banda/modo para evitar que otros operadores la usen mientras está activo.',
        'select_band': 'Seleccionar Banda',
        'select_mode': 'Seleccionar Modo',
        'block': 'Bloquear',

        # Unblock Band/Mode
        'unblock_band_mode': 'Desbloquear una Banda y Modo',
        'unblock_info': 'Libere una combinación de banda/modo cuando haya terminado.',
        'your_current_blocks': 'Sus bloqueos actuales:',
        'unblock': 'Desbloquear',
        'no_active_blocks': 'No tiene bloqueos activos.',

        # Current Status
        'current_status': 'Estado Actual de Banda/Modo',
        'status_info': 'Ver todas las combinaciones de banda/modo bloqueadas actualmente.',
        'band': 'Banda',
        'mode': 'Modo',
        'operator': 'Operador',
        'blocked_at': 'Bloqueado en',
        'summary': 'Resumen',
        'total_blocks': 'Total de Bloqueos',
        'bands_in_use': 'Bandas en Uso',
        'blocks_by_band': 'Bloqueos por Banda',
        'no_blocks_active': '¡No hay bandas/modos bloqueados actualmente. Todas las frecuencias están disponibles!',

        # Settings
        'settings': 'Configuración',
        'change_password': 'Cambiar Contraseña',
        'admin_password_env': 'La contraseña de administrador se configura mediante variables de entorno (ADMIN_PASSWORD).',
        'current_password': 'Contraseña Actual',

        # Language
        'language': 'Idioma',
        'select_language': 'Seleccionar Idioma',
    }
}

AVAILABLE_LANGUAGES = {
    'en': 'English',
    'es': 'Español'
}

def get_text(key: str, lang: str = 'en') -> str:
    """Get translated text for a given key and language."""
    if lang not in TRANSLATIONS:
        lang = 'en'
    return TRANSLATIONS[lang].get(key, key)

def get_all_texts(lang: str = 'en') -> dict:
    """Get all translated texts for a language."""
    if lang not in TRANSLATIONS:
        lang = 'en'
    return TRANSLATIONS[lang]
