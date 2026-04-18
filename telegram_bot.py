import logging
import asyncio
import aiohttp
import json
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (Application, CommandHandler, CallbackQueryHandler,
                           MessageHandler, ConversationHandler, filters, ContextTypes)

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

BOT_TOKEN = "7563317343:AAE0TRoSebB5t4R6Q0OzIyGIHaIJ_7iMUpU"
OWNER_ID = 7547557639
API_URL = "http://127.0.0.1:5000"
API_SECRET = "DBL_BOT_SECRET_7547557639"

# Conversation states
(WAIT_CREATE_USERNAME, WAIT_CREATE_PASSWORD, WAIT_CREATE_DAYS,
 WAIT_DELETE_USER, WAIT_BAN_USER, WAIT_EXTEND_USER, WAIT_EXTEND_DAYS,
 WAIT_RESET_USER, WAIT_RESET_PASS,
 WAIT_FF_UID, WAIT_FF_PASS, WAIT_FF_REGION,
 WAIT_ASSIGN_USER, WAIT_ASSIGN_FF,
 WAIT_SEARCH_USER) = range(15)

def owner_only(f):
    async def wrapper(update, ctx, *args, **kwargs):
        uid = update.effective_user.id if update.effective_user else 0
        if uid != OWNER_ID:
            if update.message:
                await update.message.reply_text("⛔ هذا الأمر للأدمن فقط")
            elif update.callback_query:
                await update.callback_query.answer("⛔ غير مصرح", show_alert=True)
            return ConversationHandler.END
        return await f(update, ctx, *args, **kwargs)
    wrapper.__name__ = f.__name__
    return wrapper

async def api_call(method, endpoint, **kwargs):
    async with aiohttp.ClientSession() as session:
        fn = session.get if method == 'GET' else session.post
        async with fn(f"{API_URL}{endpoint}", **kwargs) as r:
            return await r.json()

def main_menu_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ إنشاء حساب", callback_data="m_create"),
         InlineKeyboardButton("🗑️ حذف حساب", callback_data="m_delete")],
        [InlineKeyboardButton("🔒 حظر/رفع حظر", callback_data="m_ban"),
         InlineKeyboardButton("⏳ تمديد اشتراك", callback_data="m_extend")],
        [InlineKeyboardButton("🔑 تغيير كلمة المرور", callback_data="m_reset"),
         InlineKeyboardButton("🔍 بحث عن مستخدم", callback_data="m_search")],
        [InlineKeyboardButton("🎮 إضافة حساب FF", callback_data="m_addff"),
         InlineKeyboardButton("🔗 ربط حساب FF", callback_data="m_assignff")],
        [InlineKeyboardButton("📋 قائمة المستخدمين", callback_data="m_list"),
         InlineKeyboardButton("📊 إحصائيات", callback_data="m_stats")],
    ])

def back_kb():
    return InlineKeyboardMarkup([[InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data="m_back")]])

async def send_main_menu(update, ctx, text=""):
    msg = (
        f"🛡️ *لوحة أدمن DBL TEAM*\n"
        f"━━━━━━━━━━━━━━━━━━\n"
        f"{text}\n"
        f"اختر العملية:"
    )
    if update.message:
        await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=main_menu_kb())
    elif update.callback_query:
        try:
            await update.callback_query.edit_message_text(msg, parse_mode='Markdown', reply_markup=main_menu_kb())
        except:
            await update.callback_query.message.reply_text(msg, parse_mode='Markdown', reply_markup=main_menu_kb())

# /start command
@owner_only
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await send_main_menu(update, ctx, "مرحباً بك أيها الأدمن 👑")
    return ConversationHandler.END

# Back to menu
async def back_to_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    ctx.user_data.clear()
    await send_main_menu(update, ctx, "")
    return ConversationHandler.END

# ─── STATS ───────────────────────────────────────────────────────────────────
async def show_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    try:
        data = await api_call('GET', f'/api/stats?secret={API_SECRET}')
        msg = (
            f"📊 *إحصائيات النظام*\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"👥 إجمالي المستخدمين: *{data.get('total_users', 0)}*\n"
            f"✅ اشتراكات نشطة: *{data.get('active_subs', 0)}*\n"
            f"🚫 محظورون: *{data.get('banned', 0)}*\n"
            f"🎮 حسابات FF المضافة: *{data.get('ff_accounts', 0)}*\n"
            f"📭 حسابات FF متاحة: *{data.get('available_ff', 0)}*\n"
            f"🕐 دخلوا اليوم: *{data.get('recent_logins', 0)}*\n"
        )
    except Exception as e:
        msg = f"❌ خطأ: {e}"
    await update.callback_query.edit_message_text(msg, parse_mode='Markdown', reply_markup=back_kb())

# ─── LIST USERS ──────────────────────────────────────────────────────────────
async def list_users(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    try:
        data = await api_call('GET', f'/api/list_users?secret={API_SECRET}')
        users = data.get('users', [])
        if not users:
            msg = "📋 *لا يوجد مستخدمون*"
        else:
            msg = f"📋 *آخر {len(users)} مستخدم*\n━━━━━━━━━━━━━━━━━━\n\n"
            for u in users:
                status = "🚫" if u.get('is_banned') else "✅"
                plan = u.get('plan', '?')
                exp = u.get('subscription_expires', '')
                exp_str = exp[:10] if exp else 'مدى الحياة' if plan == 'lifetime' else 'منتهي'
                msg += f"{status} `{u['username']}` | {plan} | {exp_str}\n"
    except Exception as e:
        msg = f"❌ خطأ: {e}"
    await update.callback_query.edit_message_text(msg, parse_mode='Markdown', reply_markup=back_kb())

# ─── CREATE USER ─────────────────────────────────────────────────────────────
async def create_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "➕ *إنشاء حساب جديد*\n━━━━━━━━━━━━━━\n\nأرسل *اسم المستخدم*:",
        parse_mode='Markdown', reply_markup=back_kb())
    return WAIT_CREATE_USERNAME

async def create_get_username(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data['new_username'] = update.message.text.strip()
    await update.message.reply_text(
        f"✅ الاسم: `{ctx.user_data['new_username']}`\n\nأرسل *كلمة المرور*:",
        parse_mode='Markdown')
    return WAIT_CREATE_PASSWORD

async def create_get_password(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data['new_password'] = update.message.text.strip()
    await update.message.reply_text(
        "أرسل *عدد أيام الاشتراك*:\n"
        "• `30` = شهر\n"
        "• `90` = 3 أشهر\n"
        "• `365` = سنة\n"
        "• `-1` = مدى الحياة",
        parse_mode='Markdown')
    return WAIT_CREATE_DAYS

async def create_get_days(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        days = int(update.message.text.strip())
    except:
        await update.message.reply_text("❌ أرسل رقماً صحيحاً")
        return WAIT_CREATE_DAYS
    try:
        data = await api_call('POST', '/api/create_user', json={
            'secret': API_SECRET,
            'username': ctx.user_data['new_username'],
            'password': ctx.user_data['new_password'],
            'days': days
        })
        if data.get('success'):
            exp = data.get('expires', '')
            exp_str = 'مدى الحياة ♾️' if exp == 'lifetime' else exp[:10]
            msg = (
                f"✅ *تم إنشاء الحساب بنجاح!*\n"
                f"━━━━━━━━━━━━━━━━━━\n"
                f"👤 المستخدم: `{ctx.user_data['new_username']}`\n"
                f"🔑 كلمة المرور: `{ctx.user_data['new_password']}`\n"
                f"📅 ينتهي: `{exp_str}`\n\n"
                f"🌐 رابط الموقع للعميل:\n"
                f"`{API_URL}`"
            )
        else:
            msg = f"❌ فشل: {data.get('error', 'خطأ غير معروف')}"
    except Exception as e:
        msg = f"❌ خطأ: {e}"
    ctx.user_data.clear()
    await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=main_menu_kb())
    return ConversationHandler.END

# ─── DELETE USER ─────────────────────────────────────────────────────────────
async def delete_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "🗑️ *حذف حساب*\n━━━━━━━━━━━━━━\n\nأرسل *اسم المستخدم* للحذف:",
        parse_mode='Markdown', reply_markup=back_kb())
    return WAIT_DELETE_USER

async def delete_confirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip()
    try:
        data = await api_call('POST', '/api/delete_user', json={
            'secret': API_SECRET, 'username': username
        })
        msg = f"✅ تم حذف المستخدم `{username}`" if data.get('success') else f"❌ {data.get('error')}"
    except Exception as e:
        msg = f"❌ خطأ: {e}"
    await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=main_menu_kb())
    return ConversationHandler.END

# ─── BAN USER ────────────────────────────────────────────────────────────────
async def ban_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "🔒 *حظر / رفع حظر*\n━━━━━━━━━━━━━━\n\nأرسل اسم المستخدم:",
        parse_mode='Markdown', reply_markup=back_kb())
    return WAIT_BAN_USER

async def ban_action(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip()
    # Get user info first
    try:
        info = await api_call('GET', f'/api/get_user?secret={API_SECRET}&username={username}')
        if not info.get('success'):
            await update.message.reply_text(f"❌ المستخدم `{username}` غير موجود", parse_mode='Markdown', reply_markup=main_menu_kb())
            return ConversationHandler.END
        user = info['user']
        is_banned = user.get('is_banned', 0)
        new_ban = 0 if is_banned else 1
        data = await api_call('POST', '/api/ban_user', json={
            'secret': API_SECRET, 'username': username, 'banned': new_ban
        })
        action = "🔒 تم الحظر" if new_ban else "🔓 تم رفع الحظر"
        msg = f"{action} للمستخدم `{username}`" if data.get('success') else f"❌ {data.get('error')}"
    except Exception as e:
        msg = f"❌ خطأ: {e}"
    await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=main_menu_kb())
    return ConversationHandler.END

# ─── EXTEND SUBSCRIPTION ─────────────────────────────────────────────────────
async def extend_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "⏳ *تمديد الاشتراك*\n━━━━━━━━━━━━━━\n\nأرسل اسم المستخدم:",
        parse_mode='Markdown', reply_markup=back_kb())
    return WAIT_EXTEND_USER

async def extend_get_user(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip()
    try:
        info = await api_call('GET', f'/api/get_user?secret={API_SECRET}&username={username}')
        if not info.get('success'):
            await update.message.reply_text(f"❌ المستخدم `{username}` غير موجود", parse_mode='Markdown', reply_markup=main_menu_kb())
            return ConversationHandler.END
        ctx.user_data['extend_username'] = username
        user = info['user']
        exp = user.get('subscription_expires', 'غير محدد')
        exp_str = exp[:10] if exp else 'منتهي'
        await update.message.reply_text(
            f"✅ المستخدم: `{username}`\n📅 الانتهاء الحالي: `{exp_str}`\n\n"
            f"أرسل عدد الأيام للتمديد:\n• `30` • `90` • `365` • `-1` (مدى الحياة)",
            parse_mode='Markdown')
        return WAIT_EXTEND_DAYS
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ: {e}", reply_markup=main_menu_kb())
        return ConversationHandler.END

async def extend_do(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        days = int(update.message.text.strip())
    except:
        await update.message.reply_text("❌ أرسل رقماً صحيحاً")
        return WAIT_EXTEND_DAYS
    username = ctx.user_data.get('extend_username')
    try:
        data = await api_call('POST', '/api/extend_user', json={
            'secret': API_SECRET, 'username': username, 'days': days
        })
        if data.get('success'):
            exp = data.get('expires', '')
            exp_str = 'مدى الحياة ♾️' if not exp else exp[:10]
            msg = f"✅ تم تمديد اشتراك `{username}`\n📅 ينتهي: `{exp_str}`"
        else:
            msg = f"❌ {data.get('error')}"
    except Exception as e:
        msg = f"❌ خطأ: {e}"
    ctx.user_data.clear()
    await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=main_menu_kb())
    return ConversationHandler.END

# ─── RESET PASSWORD ───────────────────────────────────────────────────────────
async def reset_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "🔑 *تغيير كلمة المرور*\n━━━━━━━━━━━━━━\n\nأرسل اسم المستخدم:",
        parse_mode='Markdown', reply_markup=back_kb())
    return WAIT_RESET_USER

async def reset_get_user(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data['reset_username'] = update.message.text.strip()
    await update.message.reply_text("أرسل كلمة المرور الجديدة:")
    return WAIT_RESET_PASS

async def reset_do(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    username = ctx.user_data.get('reset_username')
    new_pw = update.message.text.strip()
    try:
        data = await api_call('POST', '/api/reset_password', json={
            'secret': API_SECRET, 'username': username, 'password': new_pw
        })
        msg = f"✅ تم تغيير كلمة مرور `{username}`\n🔑 الكلمة الجديدة: `{new_pw}`" if data.get('success') else f"❌ {data.get('error')}"
    except Exception as e:
        msg = f"❌ خطأ: {e}"
    ctx.user_data.clear()
    await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=main_menu_kb())
    return ConversationHandler.END

# ─── SEARCH USER ─────────────────────────────────────────────────────────────
async def search_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "🔍 *البحث عن مستخدم*\n━━━━━━━━━━━━━━\n\nأرسل اسم المستخدم:",
        parse_mode='Markdown', reply_markup=back_kb())
    return WAIT_SEARCH_USER

async def search_do(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip()
    try:
        data = await api_call('GET', f'/api/get_user?secret={API_SECRET}&username={username}')
        if not data.get('success'):
            await update.message.reply_text(f"❌ المستخدم `{username}` غير موجود", parse_mode='Markdown', reply_markup=main_menu_kb())
            return ConversationHandler.END
        u = data['user']
        exp = u.get('subscription_expires', '')
        exp_str = exp[:10] if exp else 'منتهي'
        plan = u.get('plan', '?')
        banned = "🚫 محظور" if u.get('is_banned') else "✅ نشط"
        last_login = u.get('last_login', 'لم يدخل بعد')
        if last_login:
            last_login = last_login[:16]
        msg = (
            f"👤 *معلومات المستخدم*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🔹 الاسم: `{u['username']}`\n"
            f"📦 الخطة: `{plan}`\n"
            f"📅 انتهاء الاشتراك: `{exp_str}`\n"
            f"🕐 آخر دخول: `{last_login}`\n"
            f"📌 الحالة: {banned}\n"
            f"📝 ملاحظة: {u.get('note', '-')}\n"
        )
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("⏳ تمديد", callback_data=f"quick_extend_{username}"),
             InlineKeyboardButton("🔒 حظر/رفع", callback_data=f"quick_ban_{username}")],
            [InlineKeyboardButton("🗑️ حذف", callback_data=f"quick_delete_{username}"),
             InlineKeyboardButton("🔙 رجوع", callback_data="m_back")]
        ])
    except Exception as e:
        msg = f"❌ خطأ: {e}"
        kb = back_kb()
    await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=kb)
    return ConversationHandler.END

# Quick actions from search
async def quick_action(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    data = update.callback_query.data
    if data.startswith("quick_delete_"):
        username = data.replace("quick_delete_", "")
        result = await api_call('POST', '/api/delete_user', json={'secret': API_SECRET, 'username': username})
        msg = f"✅ تم حذف `{username}`" if result.get('success') else f"❌ {result.get('error')}"
        await update.callback_query.edit_message_text(msg, parse_mode='Markdown', reply_markup=main_menu_kb())
    elif data.startswith("quick_ban_"):
        username = data.replace("quick_ban_", "")
        info = await api_call('GET', f'/api/get_user?secret={API_SECRET}&username={username}')
        if info.get('success'):
            is_banned = info['user'].get('is_banned', 0)
            new_ban = 0 if is_banned else 1
            result = await api_call('POST', '/api/ban_user', json={'secret': API_SECRET, 'username': username, 'banned': new_ban})
            action = "🔒 تم الحظر" if new_ban else "🔓 تم رفع الحظر"
            msg = f"{action} `{username}`"
        else:
            msg = "❌ مستخدم غير موجود"
        await update.callback_query.edit_message_text(msg, parse_mode='Markdown', reply_markup=main_menu_kb())

# ─── ADD FF ACCOUNT ──────────────────────────────────────────────────────────
async def addff_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "🎮 *إضافة حساب Free Fire*\n━━━━━━━━━━━━━━\n\nأرسل *UID* الحساب:",
        parse_mode='Markdown', reply_markup=back_kb())
    return WAIT_FF_UID

async def addff_get_uid(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data['ff_uid'] = update.message.text.strip()
    await update.message.reply_text("أرسل *كلمة مرور* الحساب:", parse_mode='Markdown')
    return WAIT_FF_PASS

async def addff_get_pass(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data['ff_pass'] = update.message.text.strip()
    await update.message.reply_text(
        "أرسل *المنطقة*:\n`IND` / `BD` / `SG` / `TH` / `ME`",
        parse_mode='Markdown')
    return WAIT_FF_REGION

async def addff_do(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    region = update.message.text.strip().upper()
    try:
        data = await api_call('POST', '/api/add_ff_account', json={
            'secret': API_SECRET,
            'uid': ctx.user_data['ff_uid'],
            'password': ctx.user_data['ff_pass'],
            'region': region
        })
        msg = f"✅ تم إضافة حساب FF!\n🎮 UID: `{ctx.user_data['ff_uid']}`\n🌍 المنطقة: `{region}`" if data.get('success') else f"❌ {data.get('error')}"
    except Exception as e:
        msg = f"❌ خطأ: {e}"
    ctx.user_data.clear()
    await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=main_menu_kb())
    return ConversationHandler.END

# ─── ASSIGN FF ───────────────────────────────────────────────────────────────
async def assignff_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.answer()
    await update.callback_query.edit_message_text(
        "🔗 *ربط حساب FF بمستخدم*\n━━━━━━━━━━━━━━\n\nأرسل اسم المستخدم:",
        parse_mode='Markdown', reply_markup=back_kb())
    return WAIT_ASSIGN_USER

async def assignff_get_user(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data['assign_user'] = update.message.text.strip()
    await update.message.reply_text("أرسل UID حساب Free Fire للربط:")
    return WAIT_ASSIGN_FF

async def assignff_do(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ff_uid = update.message.text.strip()
    username = ctx.user_data.get('assign_user')
    try:
        data = await api_call('POST', '/api/assign_ff', json={
            'secret': API_SECRET, 'username': username, 'ff_uid': ff_uid
        })
        msg = f"✅ تم ربط حساب FF `{ff_uid}` بالمستخدم `{username}`" if data.get('success') else f"❌ {data.get('error')}"
    except Exception as e:
        msg = f"❌ خطأ: {e}"
    ctx.user_data.clear()
    await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=main_menu_kb())
    return ConversationHandler.END

# ─── SHORTCUT COMMANDS ────────────────────────────────────────────────────────
@owner_only
async def cmd_createuser(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Usage: /createuser username password [days]"""
    args = ctx.args
    if len(args) < 2:
        await update.message.reply_text(
            "📝 الاستخدام:\n`/createuser <اسم> <كلمة_مرور> [أيام]`\n\nمثال:\n`/createuser Ahmed pass123 30`",
            parse_mode='Markdown')
        return
    username, password = args[0], args[1]
    days = int(args[2]) if len(args) > 2 else 30
    try:
        data = await api_call('POST', '/api/create_user', json={
            'secret': API_SECRET, 'username': username, 'password': password, 'days': days
        })
        if data.get('success'):
            exp = data.get('expires', '')
            exp_str = 'مدى الحياة ♾️' if exp == 'lifetime' else exp[:10]
            await update.message.reply_text(
                f"✅ *تم إنشاء الحساب!*\n"
                f"👤 `{username}` | 🔑 `{password}` | 📅 `{exp_str}`",
                parse_mode='Markdown')
        else:
            await update.message.reply_text(f"❌ {data.get('error')}")
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")

@owner_only
async def cmd_deleteuser(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args
    if not args:
        await update.message.reply_text("`/deleteuser <اسم>`", parse_mode='Markdown')
        return
    try:
        data = await api_call('POST', '/api/delete_user', json={'secret': API_SECRET, 'username': args[0]})
        msg = f"✅ تم حذف `{args[0]}`" if data.get('success') else f"❌ {data.get('error')}"
    except Exception as e:
        msg = f"❌ {e}"
    await update.message.reply_text(msg, parse_mode='Markdown')

@owner_only
async def cmd_extend(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args
    if len(args) < 2:
        await update.message.reply_text("`/extend <اسم> <أيام>`", parse_mode='Markdown')
        return
    try:
        data = await api_call('POST', '/api/extend_user', json={
            'secret': API_SECRET, 'username': args[0], 'days': int(args[1])
        })
        exp = data.get('expires', '')
        msg = f"✅ تم تمديد `{args[0]}` حتى `{exp[:10] if exp else 'مدى الحياة'}`" if data.get('success') else f"❌ {data.get('error')}"
    except Exception as e:
        msg = f"❌ {e}"
    await update.message.reply_text(msg, parse_mode='Markdown')

@owner_only
async def cmd_ban(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    args = ctx.args
    if not args:
        await update.message.reply_text("`/ban <اسم>`", parse_mode='Markdown')
        return
    try:
        info = await api_call('GET', f'/api/get_user?secret={API_SECRET}&username={args[0]}')
        is_banned = info.get('user', {}).get('is_banned', 0)
        data = await api_call('POST', '/api/ban_user', json={'secret': API_SECRET, 'username': args[0], 'banned': 0 if is_banned else 1})
        msg = f"{'🔓 رفع حظر' if is_banned else '🔒 حظر'} `{args[0]}`" if data.get('success') else f"❌ {data.get('error')}"
    except Exception as e:
        msg = f"❌ {e}"
    await update.message.reply_text(msg, parse_mode='Markdown')

@owner_only
async def cmd_stats(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        data = await api_call('GET', f'/api/stats?secret={API_SECRET}')
        msg = (
            f"📊 *إحصائيات DBL TEAM*\n━━━━━━━━━━━━━━━━━━\n\n"
            f"👥 المستخدمون: *{data.get('total_users', 0)}*\n"
            f"✅ نشطون: *{data.get('active_subs', 0)}*\n"
            f"🚫 محظورون: *{data.get('banned', 0)}*\n"
            f"🎮 حسابات FF: *{data.get('ff_accounts', 0)}*\n"
            f"📭 متاحة: *{data.get('available_ff', 0)}*\n"
        )
    except Exception as e:
        msg = f"❌ {e}"
    await update.message.reply_text(msg, parse_mode='Markdown')

@owner_only
async def cmd_users(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    try:
        data = await api_call('GET', f'/api/list_users?secret={API_SECRET}')
        users = data.get('users', [])
        if not users:
            await update.message.reply_text("لا يوجد مستخدمون")
            return
        msg = f"📋 *المستخدمون ({len(users)})*\n━━━━━━━━━━━━━━\n\n"
        for u in users:
            status = "🚫" if u.get('is_banned') else "✅"
            exp = u.get('subscription_expires', '')
            exp_str = exp[:10] if exp else ('♾️' if u.get('plan') == 'lifetime' else '❌')
            msg += f"{status} `{u['username']}` | {exp_str}\n"
    except Exception as e:
        msg = f"❌ {e}"
    await update.message.reply_text(msg, parse_mode='Markdown')

@owner_only
async def cmd_addff(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Usage: /addff uid password [region]"""
    args = ctx.args
    if len(args) < 2:
        await update.message.reply_text("`/addff <UID> <PASSWORD> [REGION]`", parse_mode='Markdown')
        return
    uid, password = args[0], args[1]
    region = args[2].upper() if len(args) > 2 else 'IND'
    try:
        data = await api_call('POST', '/api/add_ff_account', json={
            'secret': API_SECRET, 'uid': uid, 'password': password, 'region': region
        })
        msg = f"✅ تم إضافة FF `{uid}` | `{region}`" if data.get('success') else f"❌ {data.get('error')}"
    except Exception as e:
        msg = f"❌ {e}"
    await update.message.reply_text(msg, parse_mode='Markdown')

@owner_only
async def cmd_help(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    msg = (
        "🛡️ *أوامر لوحة الأدمن - DBL TEAM*\n"
        "━━━━━━━━━━━━━━━━━━\n\n"
        "*إدارة الحسابات:*\n"
        "`/createuser <اسم> <كلمة_مرور> [أيام]`\n"
        "`/deleteuser <اسم>`\n"
        "`/extend <اسم> <أيام>`\n"
        "`/ban <اسم>` (حظر/رفع)\n\n"
        "*حسابات Free Fire:*\n"
        "`/addff <UID> <PASSWORD> [REGION]`\n\n"
        "*الإحصائيات:*\n"
        "`/stats` - إحصائيات\n"
        "`/users` - قائمة المستخدمين\n\n"
        "*لوحة تفاعلية:*\n"
        "`/start` - القائمة الرئيسية"
    )
    await update.message.reply_text(msg, parse_mode='Markdown')

async def unknown_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("⛔ غير مصرح")

# ─── CANCEL ──────────────────────────────────────────────────────────────────
async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    if update.message:
        await update.message.reply_text("❌ تم الإلغاء", reply_markup=main_menu_kb())
    return ConversationHandler.END

async def run_bot():
    bot_app = Application.builder().token(BOT_TOKEN).build()

    # Main conversation handler
    conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(create_start, pattern="^m_create$"),
            CallbackQueryHandler(delete_start, pattern="^m_delete$"),
            CallbackQueryHandler(ban_start, pattern="^m_ban$"),
            CallbackQueryHandler(extend_start, pattern="^m_extend$"),
            CallbackQueryHandler(reset_start, pattern="^m_reset$"),
            CallbackQueryHandler(search_start, pattern="^m_search$"),
            CallbackQueryHandler(addff_start, pattern="^m_addff$"),
            CallbackQueryHandler(assignff_start, pattern="^m_assignff$"),
        ],
        states={
            WAIT_CREATE_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_get_username)],
            WAIT_CREATE_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_get_password)],
            WAIT_CREATE_DAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_get_days)],
            WAIT_DELETE_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, delete_confirm)],
            WAIT_BAN_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, ban_action)],
            WAIT_EXTEND_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, extend_get_user)],
            WAIT_EXTEND_DAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, extend_do)],
            WAIT_RESET_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, reset_get_user)],
            WAIT_RESET_PASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, reset_do)],
            WAIT_FF_UID: [MessageHandler(filters.TEXT & ~filters.COMMAND, addff_get_uid)],
            WAIT_FF_PASS: [MessageHandler(filters.TEXT & ~filters.COMMAND, addff_get_pass)],
            WAIT_FF_REGION: [MessageHandler(filters.TEXT & ~filters.COMMAND, addff_do)],
            WAIT_ASSIGN_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, assignff_get_user)],
            WAIT_ASSIGN_FF: [MessageHandler(filters.TEXT & ~filters.COMMAND, assignff_do)],
            WAIT_SEARCH_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, search_do)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CallbackQueryHandler(back_to_menu, pattern="^m_back$"),
        ],
        per_user=True,
    )

    bot_app.add_handler(CommandHandler("start", start))
    bot_app.add_handler(CommandHandler("help", cmd_help))
    bot_app.add_handler(CommandHandler("createuser", cmd_createuser))
    bot_app.add_handler(CommandHandler("deleteuser", cmd_deleteuser))
    bot_app.add_handler(CommandHandler("extend", cmd_extend))
    bot_app.add_handler(CommandHandler("ban", cmd_ban))
    bot_app.add_handler(CommandHandler("stats", cmd_stats))
    bot_app.add_handler(CommandHandler("users", cmd_users))
    bot_app.add_handler(CommandHandler("addff", cmd_addff))
    bot_app.add_handler(conv)
    bot_app.add_handler(CallbackQueryHandler(show_stats, pattern="^m_stats$"))
    bot_app.add_handler(CallbackQueryHandler(list_users, pattern="^m_list$"))
    bot_app.add_handler(CallbackQueryHandler(quick_action, pattern="^quick_"))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, unknown_handler))

    logger.info("🤖 DBL TEAM Admin Bot started!")
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling(drop_pending_updates=True)
    while True:
        await asyncio.sleep(3600)
