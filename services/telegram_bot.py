"""
Telegram bot service for QuendAward.

Provides operator access to block/unblock bands via Telegram,
and sends notifications when blocks change.
"""
import asyncio
import json
import logging
import re

import paho.mqtt.client as mqtt
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

from config import (
    TELEGRAM_BOT_TOKEN,
    MQTT_BROKER_HOST,
    MQTT_BROKER_PORT,
    BANDS,
    MODES,
)
from core.auth import authenticate_operator
from core.database import init_database
from features.awards import get_active_awards, get_award_by_id
from features.blocks import (
    get_all_blocks,
    get_operator_blocks,
    block_band_mode,
    unblock_all_for_operator,
)
from features.telegram import (
    link_telegram_account,
    unlink_telegram_account,
    get_telegram_link_by_chat_id,
    get_telegram_link_by_callsign,
    get_linked_users_for_award,
    set_default_award,
    set_notifications_enabled,
    set_language,
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Bot translations
BOT_TRANSLATIONS = {
    'en': {
        'welcome': (
            "Welcome to QuendAward Bot!\n\n"
            "This bot allows you to manage band/mode blocks for special callsign activations.\n\n"
            "To get started, link your operator account:\n"
            "/link <callsign> <password>\n\n"
            "Use /help to see all available commands."
        ),
        'help': (
            "Available commands:\n\n"
            "/link <callsign> <password> - Link your account\n"
            "/unlink - Unlink your account\n"
            "/blocks - List all blocks for current award\n"
            "/myblocks - Show your current blocks\n"
            "/block - Block a band/mode (interactive)\n"
            "/unblock - Release your block\n"
            "/awards - List active awards\n"
            "/setaward <id> - Set your default award\n"
            "/notifications on|off - Toggle notifications\n"
            "/setbands - Choose which bands trigger alerts\n"
            "/setmodes - Choose which modes trigger alerts\n"
            "/lang en|es|gl - Set language\n"
            "/status - Show your account status"
        ),
        'not_linked': "You need to link your account first. Use /link <callsign> <password>",
        'link_usage': "Usage: /link <callsign> <password>",
        'link_success': "Account linked successfully! Welcome, {name} ({callsign}).",
        'link_failed': "Authentication failed. Check your callsign and password.",
        'unlink_success': "Account unlinked successfully.",
        'unlink_failed': "Failed to unlink account.",
        'no_active_awards': "No active awards available.",
        'awards_list': "Active awards:\n\n{awards}",
        'award_item': "{id}. {name}",
        'setaward_usage': "Usage: /setaward <award_id>",
        'award_not_found': "Award not found or not active.",
        'award_set': "Default award set to: {name}",
        'no_default_award': "No default award set. Use /setaward <id> first.",
        'blocks_list': "Current blocks for {award}:\n\n{blocks}",
        'blocks_empty': "No active blocks for {award}.",
        'block_item': "{band}/{mode} - {callsign}",
        'myblocks_empty': "You have no active blocks.",
        'myblocks_list': "Your blocks:\n\n{blocks}",
        'select_band': "Select a band:",
        'select_mode': "Select a mode for {band}:",
        'block_success': "🔴 Blocked {band}/{mode}",
        'block_switched': "🔄 Switched to {band}/{mode} (released previous block)",
        'block_failed': "❌ Failed to block: {error}",
        'unblock_success': "🟢 Released {count} block(s).",
        'unblock_none': "You have no blocks to release.",
        'notifications_usage': "Usage: /notifications on|off",
        'notifications_enabled': "Notifications enabled.",
        'notifications_disabled': "Notifications disabled.",
        'lang_usage': "Usage: /lang en|es|gl",
        'lang_set': "Language set to English.",
        'status': (
            "Account Status:\n\n"
            "Callsign: {callsign}\n"
            "Name: {name}\n"
            "Default Award: {award}\n"
            "Notifications: {notifications}\n"
            "Alert bands: {bands}\n"
            "Alert modes: {modes}\n"
            "Language: {language}"
        ),
        'notify_block': "🔴 {callsign} blocked {band}/{mode}",
        'notify_unblock': "🟢 {callsign} unblocked {band}/{mode}",
        'notify_switch': "🔄 {callsign} switched from {old_band}/{old_mode} to {band}/{mode}",
        'notify_admin_unblock': "🟢 {callsign} (admin) unblocked {band}/{mode} (was {blocked_by})",
        'notify_admin_unblock_anon': "🟢 Admin unblocked {band}/{mode} (was {blocked_by})",
        'notify_mention': "💬 {sender} mentioned you: {preview}",
        'cancel': "Cancel",
        'cancelled': "Operation cancelled.",
        'already_blocked': "⚠️ This band/mode is already blocked by {callsign}.",
        'setbands_current': "Alert bands: {bands}\n\nTap to toggle. ✅ = alerts on, tap again to disable.",
        'setbands_updated': "Alert bands updated: {bands}",
        'setbands_all': "Receiving alerts for all bands.",
        'setmodes_current': "Alert modes: {modes}\n\nTap to toggle. ✅ = alerts on, tap again to disable.",
        'setmodes_updated': "Alert modes updated: {modes}",
        'setmodes_all': "Receiving alerts for all modes.",
        'done': "Done",
    },
    'es': {
        'welcome': (
            "Bienvenido a QuendAward Bot!\n\n"
            "Este bot te permite gestionar bloqueos de banda/modo para activaciones de indicativos especiales.\n\n"
            "Para empezar, vincula tu cuenta de operador:\n"
            "/link <indicativo> <contrasena>\n\n"
            "Usa /help para ver todos los comandos disponibles."
        ),
        'help': (
            "Comandos disponibles:\n\n"
            "/link <indicativo> <contrasena> - Vincular tu cuenta\n"
            "/unlink - Desvincular tu cuenta\n"
            "/blocks - Listar todos los bloqueos del diploma actual\n"
            "/myblocks - Mostrar tus bloqueos actuales\n"
            "/block - Bloquear banda/modo (interactivo)\n"
            "/unblock - Liberar tu bloqueo\n"
            "/awards - Listar diplomas activos\n"
            "/setaward <id> - Establecer diploma predeterminado\n"
            "/notifications on|off - Activar/desactivar notificaciones\n"
            "/setbands - Elegir bandas con alertas\n"
            "/setmodes - Elegir modos con alertas\n"
            "/lang en|es|gl - Establecer idioma\n"
            "/status - Mostrar estado de tu cuenta"
        ),
        'not_linked': "Necesitas vincular tu cuenta primero. Usa /link <indicativo> <contrasena>",
        'link_usage': "Uso: /link <indicativo> <contrasena>",
        'link_success': "Cuenta vinculada correctamente! Bienvenido, {name} ({callsign}).",
        'link_failed': "Autenticacion fallida. Verifica tu indicativo y contrasena.",
        'unlink_success': "Cuenta desvinculada correctamente.",
        'unlink_failed': "Error al desvincular cuenta.",
        'no_active_awards': "No hay diplomas activos disponibles.",
        'awards_list': "Diplomas activos:\n\n{awards}",
        'award_item': "{id}. {name}",
        'setaward_usage': "Uso: /setaward <id_diploma>",
        'award_not_found': "Diploma no encontrado o no activo.",
        'award_set': "Diploma predeterminado: {name}",
        'no_default_award': "No hay diploma predeterminado. Usa /setaward <id> primero.",
        'blocks_list': "Bloqueos actuales para {award}:\n\n{blocks}",
        'blocks_empty': "No hay bloqueos activos para {award}.",
        'block_item': "{band}/{mode} - {callsign}",
        'myblocks_empty': "No tienes bloqueos activos.",
        'myblocks_list': "Tus bloqueos:\n\n{blocks}",
        'select_band': "Selecciona una banda:",
        'select_mode': "Selecciona un modo para {band}:",
        'block_success': "🔴 Bloqueado {band}/{mode}",
        'block_switched': "🔄 Cambiado a {band}/{mode} (liberado bloqueo anterior)",
        'block_failed': "❌ Error al bloquear: {error}",
        'unblock_success': "🟢 Liberado(s) {count} bloqueo(s).",
        'unblock_none': "No tienes bloqueos para liberar.",
        'notifications_usage': "Uso: /notifications on|off",
        'notifications_enabled': "Notificaciones activadas.",
        'notifications_disabled': "Notificaciones desactivadas.",
        'lang_usage': "Uso: /lang en|es|gl",
        'lang_set': "Idioma establecido a Espanol.",
        'status': (
            "Estado de la cuenta:\n\n"
            "Indicativo: {callsign}\n"
            "Nombre: {name}\n"
            "Diploma predeterminado: {award}\n"
            "Notificaciones: {notifications}\n"
            "Alertas bandas: {bands}\n"
            "Alertas modos: {modes}\n"
            "Idioma: {language}"
        ),
        'notify_block': "🔴 {callsign} bloqueo {band}/{mode}",
        'notify_unblock': "🟢 {callsign} desbloqueo {band}/{mode}",
        'notify_switch': "🔄 {callsign} cambio de {old_band}/{old_mode} a {band}/{mode}",
        'notify_admin_unblock': "🟢 {callsign} (admin) desbloqueo {band}/{mode} (era {blocked_by})",
        'notify_admin_unblock_anon': "🟢 Admin desbloqueo {band}/{mode} (era {blocked_by})",
        'notify_mention': "💬 {sender} te menciono: {preview}",
        'cancel': "Cancelar",
        'cancelled': "Operacion cancelada.",
        'already_blocked': "⚠️ Esta banda/modo ya esta bloqueado por {callsign}.",
        'setbands_current': "Bandas con alertas: {bands}\n\nToca para cambiar. ✅ = alertas activas, toca de nuevo para desactivar.",
        'setbands_updated': "Bandas con alertas actualizadas: {bands}",
        'setbands_all': "Recibiendo alertas para todas las bandas.",
        'setmodes_current': "Modos con alertas: {modes}\n\nToca para cambiar. ✅ = alertas activas, toca de nuevo para desactivar.",
        'setmodes_updated': "Modos con alertas actualizados: {modes}",
        'setmodes_all': "Recibiendo alertas para todos los modos.",
        'done': "Listo",
    },
    'gl': {
        'welcome': (
            "Benvido a QuendAward Bot!\n\n"
            "Este bot permitete xestionar bloqueos de banda/modo para activacions de indicativos especiais.\n\n"
            "Para comezar, vincula a tua conta de operador:\n"
            "/link <indicativo> <contrasinal>\n\n"
            "Usa /help para ver todos os comandos disponibles."
        ),
        'help': (
            "Comandos disponibles:\n\n"
            "/link <indicativo> <contrasinal> - Vincular a tua conta\n"
            "/unlink - Desvincular a tua conta\n"
            "/blocks - Listar todos os bloqueos do diploma actual\n"
            "/myblocks - Amosar os teus bloqueos actuais\n"
            "/block - Bloquear banda/modo (interactivo)\n"
            "/unblock - Liberar o teu bloqueo\n"
            "/awards - Listar diplomas activos\n"
            "/setaward <id> - Establecer diploma predeterminado\n"
            "/notifications on|off - Activar/desactivar notificacions\n"
            "/setbands - Elixir bandas con alertas\n"
            "/setmodes - Elixir modos con alertas\n"
            "/lang en|es|gl - Establecer idioma\n"
            "/status - Amosar estado da tua conta"
        ),
        'not_linked': "Necesitas vincular a tua conta primeiro. Usa /link <indicativo> <contrasinal>",
        'link_usage': "Uso: /link <indicativo> <contrasinal>",
        'link_success': "Conta vinculada correctamente! Benvido, {name} ({callsign}).",
        'link_failed': "Autenticacion fallida. Verifica o teu indicativo e contrasinal.",
        'unlink_success': "Conta desvinculada correctamente.",
        'unlink_failed': "Erro ao desvincular conta.",
        'no_active_awards': "Non hai diplomas activos disponibles.",
        'awards_list': "Diplomas activos:\n\n{awards}",
        'award_item': "{id}. {name}",
        'setaward_usage': "Uso: /setaward <id_diploma>",
        'award_not_found': "Diploma non atopado ou non activo.",
        'award_set': "Diploma predeterminado: {name}",
        'no_default_award': "Non hai diploma predeterminado. Usa /setaward <id> primeiro.",
        'blocks_list': "Bloqueos actuais para {award}:\n\n{blocks}",
        'blocks_empty': "Non hai bloqueos activos para {award}.",
        'block_item': "{band}/{mode} - {callsign}",
        'myblocks_empty': "Non tes bloqueos activos.",
        'myblocks_list': "Os teus bloqueos:\n\n{blocks}",
        'select_band': "Selecciona unha banda:",
        'select_mode': "Selecciona un modo para {band}:",
        'block_success': "🔴 Bloqueado {band}/{mode}",
        'block_switched': "🔄 Cambiado a {band}/{mode} (liberado bloqueo anterior)",
        'block_failed': "❌ Erro ao bloquear: {error}",
        'unblock_success': "🟢 Liberado(s) {count} bloqueo(s).",
        'unblock_none': "Non tes bloqueos para liberar.",
        'notifications_usage': "Uso: /notifications on|off",
        'notifications_enabled': "Notificacions activadas.",
        'notifications_disabled': "Notificacions desactivadas.",
        'lang_usage': "Uso: /lang en|es|gl",
        'lang_set': "Idioma establecido a Galego.",
        'status': (
            "Estado da conta:\n\n"
            "Indicativo: {callsign}\n"
            "Nome: {name}\n"
            "Diploma predeterminado: {award}\n"
            "Notificacions: {notifications}\n"
            "Alertas bandas: {bands}\n"
            "Alertas modos: {modes}\n"
            "Idioma: {language}"
        ),
        'notify_block': "🔴 {callsign} bloqueou {band}/{mode}",
        'notify_unblock': "🟢 {callsign} desbloqueou {band}/{mode}",
        'notify_switch': "🔄 {callsign} cambiou de {old_band}/{old_mode} a {band}/{mode}",
        'notify_admin_unblock': "🟢 {callsign} (admin) desbloqueou {band}/{mode} (era {blocked_by})",
        'notify_admin_unblock_anon': "🟢 Admin desbloqueou {band}/{mode} (era {blocked_by})",
        'notify_mention': "💬 {sender} mencionoute: {preview}",
        'cancel': "Cancelar",
        'cancelled': "Operacion cancelada.",
        'already_blocked': "⚠️ Esta banda/modo xa esta bloqueado por {callsign}.",
        'setbands_current': "Bandas con alertas: {bands}\n\nToca para cambiar. ✅ = alertas activas, toca de novo para desactivar.",
        'setbands_updated': "Bandas con alertas actualizadas: {bands}",
        'setbands_all': "Recibindo alertas para todas as bandas.",
        'setmodes_current': "Modos con alertas: {modes}\n\nToca para cambiar. ✅ = alertas activas, toca de novo para desactivar.",
        'setmodes_updated': "Modos con alertas actualizados: {modes}",
        'setmodes_all': "Recibindo alertas para todos os modos.",
        'done': "Feito",
    },
}


def t(key: str, lang: str = 'en', **kwargs) -> str:
    """Get translated string."""
    translations = BOT_TRANSLATIONS.get(lang, BOT_TRANSLATIONS['en'])
    text = translations.get(key, BOT_TRANSLATIONS['en'].get(key, key))
    if kwargs:
        return text.format(**kwargs)
    return text


def get_user_lang(chat_id: int) -> str:
    """Get user's preferred language."""
    link = get_telegram_link_by_chat_id(chat_id)
    return link['language'] if link else 'en'


# Command handlers

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    lang = get_user_lang(update.effective_chat.id)
    await update.message.reply_text(t('welcome', lang))


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    lang = get_user_lang(update.effective_chat.id)
    await update.message.reply_text(t('help', lang))


async def link_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /link <callsign> <password> command."""
    chat_id = update.effective_chat.id
    lang = get_user_lang(chat_id)

    if len(context.args) < 2:
        await update.message.reply_text(t('link_usage', lang))
        return

    callsign = context.args[0].upper()
    password = ' '.join(context.args[1:])  # Password might contain spaces

    success, message, operator = authenticate_operator(callsign, password)
    if not success:
        await update.message.reply_text(t('link_failed', lang))
        return

    username = update.effective_user.username if update.effective_user else None
    link_success, link_msg = link_telegram_account(callsign, chat_id, username)

    if link_success:
        await update.message.reply_text(
            t('link_success', lang, name=operator['operator_name'], callsign=callsign)
        )
    else:
        await update.message.reply_text(link_msg)


async def unlink_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /unlink command."""
    chat_id = update.effective_chat.id
    lang = get_user_lang(chat_id)

    success, message = unlink_telegram_account(chat_id)
    if success:
        await update.message.reply_text(t('unlink_success', lang))
    else:
        await update.message.reply_text(t('unlink_failed', lang))


async def awards_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /awards command."""
    chat_id = update.effective_chat.id
    lang = get_user_lang(chat_id)

    awards = get_active_awards()
    if not awards:
        await update.message.reply_text(t('no_active_awards', lang))
        return

    awards_text = '\n'.join(
        t('award_item', lang, id=a['id'], name=a['name']) for a in awards
    )
    await update.message.reply_text(t('awards_list', lang, awards=awards_text))


async def setaward_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /setaward <id> command."""
    chat_id = update.effective_chat.id
    lang = get_user_lang(chat_id)

    link = get_telegram_link_by_chat_id(chat_id)
    if not link:
        await update.message.reply_text(t('not_linked', lang))
        return

    if not context.args:
        await update.message.reply_text(t('setaward_usage', lang))
        return

    try:
        award_id = int(context.args[0])
    except ValueError:
        await update.message.reply_text(t('setaward_usage', lang))
        return

    award = get_award_by_id(award_id)
    if not award or not award.get('is_active'):
        await update.message.reply_text(t('award_not_found', lang))
        return

    set_default_award(chat_id, award_id)
    await update.message.reply_text(t('award_set', lang, name=award['name']))


async def blocks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /blocks command."""
    chat_id = update.effective_chat.id
    lang = get_user_lang(chat_id)

    link = get_telegram_link_by_chat_id(chat_id)
    if not link:
        await update.message.reply_text(t('not_linked', lang))
        return

    award_id = link.get('default_award_id')
    if not award_id:
        await update.message.reply_text(t('no_default_award', lang))
        return

    award = get_award_by_id(award_id)
    if not award:
        await update.message.reply_text(t('award_not_found', lang))
        return

    blocks = get_all_blocks(award_id)
    if not blocks:
        await update.message.reply_text(t('blocks_empty', lang, award=award['name']))
        return

    blocks_text = '\n'.join(
        t('block_item', lang, band=b['band'], mode=b['mode'], callsign=b['operator_callsign'])
        for b in blocks
    )
    await update.message.reply_text(t('blocks_list', lang, award=award['name'], blocks=blocks_text))


async def myblocks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /myblocks command."""
    chat_id = update.effective_chat.id
    lang = get_user_lang(chat_id)

    link = get_telegram_link_by_chat_id(chat_id)
    if not link:
        await update.message.reply_text(t('not_linked', lang))
        return

    callsign = link['operator_callsign']
    award_id = link.get('default_award_id')

    blocks = get_operator_blocks(callsign, award_id)
    if not blocks:
        await update.message.reply_text(t('myblocks_empty', lang))
        return

    blocks_text = '\n'.join(f"{b['band']}/{b['mode']}" for b in blocks)
    await update.message.reply_text(t('myblocks_list', lang, blocks=blocks_text))


async def block_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /block command - shows band selection keyboard."""
    chat_id = update.effective_chat.id
    lang = get_user_lang(chat_id)

    link = get_telegram_link_by_chat_id(chat_id)
    if not link:
        await update.message.reply_text(t('not_linked', lang))
        return

    award_id = link.get('default_award_id')
    if not award_id:
        await update.message.reply_text(t('no_default_award', lang))
        return

    # Create inline keyboard for band selection
    keyboard = []
    row = []
    for i, band in enumerate(BANDS):
        row.append(InlineKeyboardButton(band, callback_data=f"band:{band}"))
        if len(row) == 5:  # 5 buttons per row
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton(t('cancel', lang), callback_data="cancel")])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(t('select_band', lang), reply_markup=reply_markup)


async def unblock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /unblock command."""
    chat_id = update.effective_chat.id
    lang = get_user_lang(chat_id)

    link = get_telegram_link_by_chat_id(chat_id)
    if not link:
        await update.message.reply_text(t('not_linked', lang))
        return

    callsign = link['operator_callsign']
    award_id = link.get('default_award_id')

    success, message, count = unblock_all_for_operator(callsign, award_id)
    if count > 0:
        await update.message.reply_text(t('unblock_success', lang, count=count))
    else:
        await update.message.reply_text(t('unblock_none', lang))


async def notifications_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /notifications on|off command."""
    chat_id = update.effective_chat.id
    lang = get_user_lang(chat_id)

    link = get_telegram_link_by_chat_id(chat_id)
    if not link:
        await update.message.reply_text(t('not_linked', lang))
        return

    if not context.args or context.args[0].lower() not in ('on', 'off'):
        await update.message.reply_text(t('notifications_usage', lang))
        return

    enabled = context.args[0].lower() == 'on'
    set_notifications_enabled(chat_id, enabled)

    if enabled:
        await update.message.reply_text(t('notifications_enabled', lang))
    else:
        await update.message.reply_text(t('notifications_disabled', lang))


async def lang_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /lang en|es|gl command."""
    chat_id = update.effective_chat.id
    lang = get_user_lang(chat_id)

    link = get_telegram_link_by_chat_id(chat_id)
    if not link:
        await update.message.reply_text(t('not_linked', lang))
        return

    if not context.args or context.args[0].lower() not in ('en', 'es', 'gl'):
        await update.message.reply_text(t('lang_usage', lang))
        return

    new_lang = context.args[0].lower()
    set_language(chat_id, new_lang)
    await update.message.reply_text(t('lang_set', new_lang))


def _build_toggle_keyboard(items, selected, prefix, lang):
    """Build an inline keyboard with toggle buttons for bands or modes."""
    keyboard = []
    row = []
    for item in items:
        label = f"✅ {item}" if item in selected else item
        row.append(InlineKeyboardButton(label, callback_data=f"{prefix}:{item}"))
        if len(row) == 4:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([
        InlineKeyboardButton(t('done', lang), callback_data=f"{prefix}:done"),
    ])
    return InlineKeyboardMarkup(keyboard)


async def setbands_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /setbands command — interactive band alert filter."""
    from config import BANDS
    chat_id = update.effective_chat.id
    lang = get_user_lang(chat_id)

    link = get_telegram_link_by_chat_id(chat_id)
    if not link:
        await update.message.reply_text(t('not_linked', lang))
        return

    current = set(link['notify_bands'].split(',')) if link.get('notify_bands') else set(BANDS)
    context.user_data['setbands_selected'] = current

    bands_str = ', '.join(b for b in BANDS if b in current) or "All"
    reply_markup = _build_toggle_keyboard(BANDS, current, 'tb', lang)
    await update.message.reply_text(
        t('setbands_current', lang, bands=bands_str),
        reply_markup=reply_markup,
    )


async def setmodes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /setmodes command — interactive mode alert filter."""
    from config import MODES
    chat_id = update.effective_chat.id
    lang = get_user_lang(chat_id)

    link = get_telegram_link_by_chat_id(chat_id)
    if not link:
        await update.message.reply_text(t('not_linked', lang))
        return

    current = set(link['notify_modes'].split(',')) if link.get('notify_modes') else set(MODES)
    context.user_data['setmodes_selected'] = current

    modes_str = ', '.join(m for m in MODES if m in current) or "All"
    reply_markup = _build_toggle_keyboard(MODES, current, 'tm', lang)
    await update.message.reply_text(
        t('setmodes_current', lang, modes=modes_str),
        reply_markup=reply_markup,
    )


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /status command."""
    chat_id = update.effective_chat.id
    lang = get_user_lang(chat_id)

    link = get_telegram_link_by_chat_id(chat_id)
    if not link:
        await update.message.reply_text(t('not_linked', lang))
        return

    award_name = "Not set"
    if link.get('default_award_id'):
        award = get_award_by_id(link['default_award_id'])
        if award:
            award_name = award['name']

    notifications = "On" if link.get('notifications_enabled') else "Off"
    lang_names = {'en': 'English', 'es': 'Spanish', 'gl': 'Galician'}
    bands_str = link.get('notify_bands') or "All"
    modes_str = link.get('notify_modes') or "All"

    await update.message.reply_text(t('status', lang,
        callsign=link['operator_callsign'],
        name=link.get('operator_name', 'Unknown'),
        award=award_name,
        notifications=notifications,
        bands=bands_str,
        modes=modes_str,
        language=lang_names.get(link.get('language', 'en'), 'English')
    ))


# Callback query handler for inline keyboards

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline keyboard button presses."""
    query = update.callback_query
    await query.answer()

    chat_id = update.effective_chat.id
    lang = get_user_lang(chat_id)

    data = query.data

    if data == "cancel":
        await query.edit_message_text(t('cancelled', lang))
        return

    # Toggle band alerts
    if data.startswith("tb:"):
        from config import BANDS
        from features.telegram import set_notify_bands
        value = data.split(":", 1)[1]
        selected = context.user_data.get('setbands_selected', set(BANDS))

        if value == 'done':
            if selected == set(BANDS) or not selected:
                set_notify_bands(chat_id, None)
                await query.edit_message_text(t('setbands_all', lang))
            else:
                ordered = [b for b in BANDS if b in selected]
                set_notify_bands(chat_id, ordered)
                await query.edit_message_text(
                    t('setbands_updated', lang, bands=', '.join(ordered))
                )
            return

        if value in selected:
            selected.discard(value)
        else:
            selected.add(value)
        context.user_data['setbands_selected'] = selected

        bands_str = ', '.join(b for b in BANDS if b in selected) or "All"
        reply_markup = _build_toggle_keyboard(BANDS, selected, 'tb', lang)
        await query.edit_message_text(
            t('setbands_current', lang, bands=bands_str),
            reply_markup=reply_markup,
        )
        return

    # Toggle mode alerts
    if data.startswith("tm:"):
        from config import MODES
        from features.telegram import set_notify_modes
        value = data.split(":", 1)[1]
        selected = context.user_data.get('setmodes_selected', set(MODES))

        if value == 'done':
            if selected == set(MODES) or not selected:
                set_notify_modes(chat_id, None)
                await query.edit_message_text(t('setmodes_all', lang))
            else:
                ordered = [m for m in MODES if m in selected]
                set_notify_modes(chat_id, ordered)
                await query.edit_message_text(
                    t('setmodes_updated', lang, modes=', '.join(ordered))
                )
            return

        if value in selected:
            selected.discard(value)
        else:
            selected.add(value)
        context.user_data['setmodes_selected'] = selected

        modes_str = ', '.join(m for m in MODES if m in selected) or "All"
        reply_markup = _build_toggle_keyboard(MODES, selected, 'tm', lang)
        await query.edit_message_text(
            t('setmodes_current', lang, modes=modes_str),
            reply_markup=reply_markup,
        )
        return

    if data.startswith("band:"):
        band = data.split(":")[1]
        # Store selected band in context
        context.user_data['selected_band'] = band

        # Show mode selection (only modes legally usable on this band)
        from config import BAND_MODES
        allowed_modes = BAND_MODES.get(band, [])
        keyboard = []
        row = []
        for mode in allowed_modes:
            row.append(InlineKeyboardButton(mode, callback_data=f"mode:{mode}"))
            if len(row) == 3:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        keyboard.append([InlineKeyboardButton(t('cancel', lang), callback_data="cancel")])

        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            t('select_mode', lang, band=band),
            reply_markup=reply_markup
        )

    elif data.startswith("mode:"):
        mode = data.split(":")[1]
        band = context.user_data.get('selected_band')

        if not band:
            await query.edit_message_text(t('cancelled', lang))
            return

        link = get_telegram_link_by_chat_id(chat_id)
        if not link:
            await query.edit_message_text(t('not_linked', lang))
            return

        callsign = link['operator_callsign']
        award_id = link.get('default_award_id')

        if not award_id:
            await query.edit_message_text(t('no_default_award', lang))
            return

        success, message = block_band_mode(callsign, band, mode, award_id)

        if success:
            if "previous" in message.lower():
                await query.edit_message_text(t('block_switched', lang, band=band, mode=mode))
            else:
                await query.edit_message_text(t('block_success', lang, band=band, mode=mode))
        else:
            # Check if blocked by someone else
            if "already blocked by" in message:
                match = re.search(r'blocked by (\S+)', message)
                blocker = match.group(1) if match else "someone"
                await query.edit_message_text(t('already_blocked', lang, callsign=blocker))
            else:
                await query.edit_message_text(t('block_failed', lang, error=message))

        # Clear stored band
        context.user_data.pop('selected_band', None)


# MQTT notification handler

class MQTTNotifier:
    """Handles MQTT subscriptions and sends Telegram notifications."""

    def __init__(self, app: Application):
        self.app = app
        self.loop = None
        self.mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_message = self._on_message

    def _on_connect(self, client, userdata, flags, reason_code, properties=None):
        logger.info("MQTT notifier connected (rc=%s)", reason_code)
        client.subscribe("quendaward/chat/#")

    def _on_message(self, client, userdata, msg):
        """Process MQTT message and send notifications."""
        if not self.loop:
            return
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
            source = payload.get('source', '')

            # Only process system events for block notifications
            if source == 'system':
                asyncio.run_coroutine_threadsafe(
                    self._handle_system_event(payload, msg.topic),
                    self.loop
                )
            # Process mentions
            elif payload.get('mentions'):
                asyncio.run_coroutine_threadsafe(
                    self._handle_mentions(payload),
                    self.loop
                )
        except Exception:
            logger.exception("Error processing MQTT message for notifications")

    async def _handle_system_event(self, payload: dict, topic: str):
        """Handle block/unblock system events."""
        try:
            message = payload.get('message', '')
            event_data = json.loads(message)
            event = event_data.get('event')
            callsign = event_data.get('callsign', '')
            band = event_data.get('band', '')
            mode = event_data.get('mode', '')

            # Extract award_id from topic
            # Format: quendaward/chat/room/{room_id} or quendaward/chat/{award_id}
            topic_parts = topic.split('/')
            award_id = None

            if len(topic_parts) >= 4 and topic_parts[2] == 'room':
                # Look up award from room
                from core.database import get_db
                try:
                    with get_db() as conn:
                        row = conn.execute(
                            'SELECT award_id FROM chat_rooms WHERE id = ?',
                            (int(topic_parts[3]),)
                        ).fetchone()
                        if row:
                            award_id = row['award_id']
                except Exception:
                    pass
            elif len(topic_parts) >= 3:
                try:
                    award_id = int(topic_parts[2])
                except ValueError:
                    pass

            if not award_id:
                return

            # Get all linked users for this award
            linked_users = get_linked_users_for_award(award_id)

            for user in linked_users:
                # Don't notify the actor
                if user['operator_callsign'].upper() == callsign.upper():
                    continue

                # Band/mode alert filters
                user_bands = user.get('notify_bands')
                if user_bands and band and band not in user_bands.split(','):
                    continue
                user_modes = user.get('notify_modes')
                if user_modes and mode and mode not in user_modes.split(','):
                    continue

                lang = user.get('language', 'en')
                chat_id = user['telegram_chat_id']

                if event == 'blocked':
                    text = t('notify_block', lang, callsign=callsign, band=band, mode=mode)
                elif event == 'unblocked':
                    text = t('notify_unblock', lang, callsign=callsign, band=band, mode=mode)
                elif event == 'switched':
                    old_band = event_data.get('old_band', '')
                    old_mode = event_data.get('old_mode', '')
                    text = t('notify_switch', lang,
                             callsign=callsign,
                             old_band=old_band, old_mode=old_mode,
                             band=band, mode=mode)
                elif event == 'admin_unblocked':
                    blocked_by = event_data.get('blocked_by', '')
                    if callsign:
                        text = t('notify_admin_unblock', lang,
                                 callsign=callsign, band=band, mode=mode,
                                 blocked_by=blocked_by)
                    else:
                        text = t('notify_admin_unblock_anon', lang,
                                 band=band, mode=mode, blocked_by=blocked_by)
                else:
                    continue

                try:
                    await self.app.bot.send_message(chat_id=chat_id, text=text)
                except Exception as e:
                    logger.warning("Failed to send notification to %s: %s", chat_id, e)

        except Exception:
            logger.exception("Error handling system event")

    async def _handle_mentions(self, payload: dict):
        """Handle @mentions in chat messages."""
        try:
            sender = payload.get('callsign', '')
            message = payload.get('message', '')
            mentions = payload.get('mentions', [])

            preview = message[:80] + '...' if len(message) > 80 else message

            for mentioned_callsign in mentions:
                if mentioned_callsign.upper() == sender.upper():
                    continue

                link = get_telegram_link_by_callsign(mentioned_callsign)
                if not link or not link.get('notifications_enabled'):
                    continue

                lang = link.get('language', 'en')
                chat_id = link['telegram_chat_id']

                text = t('notify_mention', lang, sender=sender, preview=preview)

                try:
                    await self.app.bot.send_message(chat_id=chat_id, text=text)
                except Exception as e:
                    logger.warning("Failed to send mention notification to %s: %s", chat_id, e)

        except Exception:
            logger.exception("Error handling mentions")

    def start(self):
        """Start MQTT connection in background."""
        try:
            self.mqtt_client.connect(MQTT_BROKER_HOST, MQTT_BROKER_PORT, keepalive=60)
            self.mqtt_client.loop_start()
            logger.info("MQTT notifier started (broker=%s:%s)", MQTT_BROKER_HOST, MQTT_BROKER_PORT)
        except Exception:
            logger.exception("Failed to connect MQTT notifier")

    def stop(self):
        """Stop MQTT connection."""
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()


async def post_init(application: Application):
    """Post-initialization callback to set up MQTT notifier with event loop."""
    notifier = application.bot_data.get('notifier')
    if notifier:
        notifier.loop = asyncio.get_running_loop()
        notifier.start()


def main():
    """Run the Telegram bot."""
    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set. Exiting.")
        return

    # Initialize database
    init_database()

    # Create application
    application = (
        Application.builder()
        .token(TELEGRAM_BOT_TOKEN)
        .post_init(post_init)
        .build()
    )

    # Create MQTT notifier (will be started in post_init)
    notifier = MQTTNotifier(application)
    application.bot_data['notifier'] = notifier

    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("link", link_command))
    application.add_handler(CommandHandler("unlink", unlink_command))
    application.add_handler(CommandHandler("awards", awards_command))
    application.add_handler(CommandHandler("setaward", setaward_command))
    application.add_handler(CommandHandler("blocks", blocks_command))
    application.add_handler(CommandHandler("myblocks", myblocks_command))
    application.add_handler(CommandHandler("block", block_command))
    application.add_handler(CommandHandler("unblock", unblock_command))
    application.add_handler(CommandHandler("notifications", notifications_command))
    application.add_handler(CommandHandler("setbands", setbands_command))
    application.add_handler(CommandHandler("setmodes", setmodes_command))
    application.add_handler(CommandHandler("lang", lang_command))
    application.add_handler(CommandHandler("status", status_command))

    # Add callback query handler for inline keyboards
    application.add_handler(CallbackQueryHandler(button_callback))

    # Run the bot
    logger.info("Starting Telegram bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()
