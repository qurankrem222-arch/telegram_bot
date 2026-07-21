import os
import logging
import sqlite3
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler

# ==================== التوكن ====================
# ⚠️ غير التوكن ده بالتوكن الجديد من @BotFather
BOT_TOKEN = "8315190785:AAEZrCan-j4ZLNMHvrPusW86ZVkXbUlbHEk"

# ==================== الإعدادات ====================
ADMIN_ID = 8933825471  # غير ده بمعرفك
SHOP_NAME = "PrimeX Store"
SUPPORT_USERNAME = "@PrimeXStore22"
SUPPORT_LINK = "https://t.me/PrimeXStore22"
DB_NAME = "shop.db"

# ==================== قاعدة البيانات ====================
def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        username TEXT,
        first_name TEXT,
        balance REAL DEFAULT 0,
        referral_points INTEGER DEFAULT 0,
        is_banned INTEGER DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        product_name TEXT,
        price REAL,
        quantity INTEGER DEFAULT 1,
        details TEXT,
        status TEXT DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')
    conn.commit()
    conn.close()

init_db()

# ==================== دوال مساعدة ====================
def is_admin(user_id):
    return user_id == ADMIN_ID

def is_user_banned(user_id):
    conn = get_db()
    r = conn.cursor().execute('SELECT is_banned FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return r and r['is_banned'] == 1

def create_or_update_user(user_id, username, first_name):
    conn = get_db()
    c = conn.cursor()
    c.execute('INSERT OR IGNORE INTO users (id, username, first_name) VALUES (?, ?, ?)', (user_id, username, first_name))
    c.execute('UPDATE users SET username = ?, first_name = ? WHERE id = ?', (username, first_name, user_id))
    conn.commit()
    conn.close()

def get_balance(user_id):
    conn = get_db()
    r = conn.cursor().execute('SELECT balance FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    return r['balance'] if r else 0

def deduct_balance(user_id, amount):
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE users SET balance = balance - ? WHERE id = ?', (amount, user_id))
    conn.commit()
    conn.close()

def add_balance(user_id, amount):
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE users SET balance = balance + ? WHERE id = ?', (amount, user_id))
    conn.commit()
    conn.close()

def create_order(user_id, product_name, price, qty=1, details=""):
    conn = get_db()
    c = conn.cursor()
    c.execute('''INSERT INTO orders (user_id, product_name, price, quantity, details, status)
                 VALUES (?, ?, ?, ?, ?, 'pending')''', (user_id, product_name, price, qty, details))
    conn.commit()
    oid = c.lastrowid
    conn.close()
    return oid

def update_order_status(order_id, status):
    conn = get_db()
    c = conn.cursor()
    c.execute('UPDATE orders SET status = ? WHERE id = ?', (status, order_id))
    conn.commit()
    conn.close()

def get_order(order_id):
    conn = get_db()
    r = conn.cursor().execute('SELECT * FROM orders WHERE id = ?', (order_id,)).fetchone()
    conn.close()
    return r

def get_user_orders(user_id, limit=20):
    conn = get_db()
    orders = conn.cursor().execute('SELECT id, product_name, price, status, created_at FROM orders WHERE user_id = ? ORDER BY created_at DESC LIMIT ?', (user_id, limit)).fetchall()
    conn.close()
    return orders

def add_purchase_points(user_id):
    conn = get_db()
    conn.cursor().execute('UPDATE users SET referral_points = referral_points + 1 WHERE id = ?', (user_id,))
    conn.commit()
    conn.close()

# ==================== حالات المحادثة ====================
REF_LINK, REF_QUANTITY = range(2)
FUND_LINK = 10

# ==================== دوال القوائم ====================
def get_main_menu(user_id):
    keyboard = [
        [InlineKeyboardButton("📸 حسابات", callback_data="section_accounts")],
        [InlineKeyboardButton("⭐ نجوم", callback_data="section_stars")],
        [InlineKeyboardButton("👤 يوزرات", callback_data="section_usernames")],
        [InlineKeyboardButton("🔗 إحالات بوتات", callback_data="section_referrals")],
        [InlineKeyboardButton("📢 تمويل قنوات", callback_data="section_funding")],
        [InlineKeyboardButton("📱 أرقام", callback_data="section_numbers")],
        [InlineKeyboardButton("🛒 طلباتي", callback_data="my_orders")],
        [InlineKeyboardButton("📞 تواصل معنا", callback_data="contact")],
    ]
    if is_admin(user_id):
        keyboard.append([InlineKeyboardButton("⚙️ لوحة الأدمن", callback_data="admin_panel")])
    return InlineKeyboardMarkup(keyboard)

def get_accounts_menu():
    keyboard = [
        [InlineKeyboardButton("📸 إنستغرام 3k - 2.5$", callback_data="buy_ig_3000")],
        [InlineKeyboardButton("🎵 تيك توك 1.3k - 2$", callback_data="buy_tt_1300")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_stars_menu():
    keyboard = [
        [InlineKeyboardButton("🐻 الدب 15 نجمة - 0.18$", callback_data="buy_star_bear")],
        [InlineKeyboardButton("🌹 الوردة 25 نجمة - 0.28$", callback_data="buy_star_rose")],
        [InlineKeyboardButton("🍰 الكيكة 50 نجمة - 0.58$", callback_data="buy_star_cake")],
        [InlineKeyboardButton("💍 الخاتم 100 نجمة - 1.10$", callback_data="buy_star_ring")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_usernames_menu():
    keyboard = [
        [InlineKeyboardButton("✈️ يوزر تيليجرام - 0.50$", callback_data="buy_user_tlg")],
        [InlineKeyboardButton("📸 يوزر إنستغرام - 0.50$", callback_data="buy_user_insta")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_referrals_menu():
    keyboard = [
        [InlineKeyboardButton("💰 سعر الإحالة: 0.05$", callback_data="ref_price")],
        [InlineKeyboardButton("🛒 شراء إحالات", callback_data="ref_buy")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_funding_menu():
    keyboard = [
        [InlineKeyboardButton("👥 1000 عضو - 1.20$", callback_data="fund_1000")],
        [InlineKeyboardButton("👥 5000 عضو - 5.00$", callback_data="fund_5000")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_numbers_main_menu():
    keyboard = [
        [InlineKeyboardButton("✅ أرقام سليمة", callback_data="num_clean")],
        [InlineKeyboardButton("🔁 أرقام سبام", callback_data="num_spam")],
        [InlineKeyboardButton("🔑 شراء جلسات", callback_data="num_sessions")],
        [InlineKeyboardButton("📂 إنشاءات قديمة", callback_data="num_old")],
        [InlineKeyboardButton("💬 أرقام واتساب", callback_data="num_whatsapp")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_clean_menu():
    keyboard = [
        [InlineKeyboardButton("🇲🇲 Myanmar - 0.35$", callback_data="buy_clean_myanmar")],
        [InlineKeyboardButton("🇻🇳 Vietnam - 0.8$", callback_data="buy_clean_vietnam")],
        [InlineKeyboardButton("🇩🇿 Algeria - 0.55$", callback_data="buy_clean_algeria")],
        [InlineKeyboardButton("🇯🇴 Jordan - 1.6$", callback_data="buy_clean_jordan")],
        [InlineKeyboardButton("🇮🇹 Italy - 1.8$", callback_data="buy_clean_italy")],
        [InlineKeyboardButton("🇮🇩 Indonesia - 0.55$", callback_data="buy_clean_indonesia")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_numbers")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_spam_menu():
    keyboard = [
        [InlineKeyboardButton("🎲 عشوائي - 0.26$", callback_data="buy_spam_random")],
        [InlineKeyboardButton("🇺🇸 أمريكي - 0.22$", callback_data="buy_spam_usa")],
        [InlineKeyboardButton("🇲🇲 Myanmar - 0.25$", callback_data="buy_spam_myanmar")],
        [InlineKeyboardButton("🇮🇳 India - 0.29$", callback_data="buy_spam_india")],
        [InlineKeyboardButton("🇪🇬 Egypt - 0.5$", callback_data="buy_spam_egypt")],
        [InlineKeyboardButton("🇻🇳 Vietnam - 0.32$", callback_data="buy_spam_vietnam")],
        [InlineKeyboardButton("🇦🇫 Afghanistan - 0.35$", callback_data="buy_spam_afghanistan")],
        [InlineKeyboardButton("🇹🇭 Thailand - 0.41$", callback_data="buy_spam_thailand")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_numbers")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_sessions_menu():
    keyboard = [
        [InlineKeyboardButton("🇬🇧 بريطانيا - 1.3$", callback_data="buy_session_uk")],
        [InlineKeyboardButton("🇮🇹 إيطاليا - 1.95$", callback_data="buy_session_italy")],
        [InlineKeyboardButton("🇵🇱 بولندا - 1.2$", callback_data="buy_session_poland")],
        [InlineKeyboardButton("🇷🇺 روسيا - 1.95$", callback_data="buy_session_russia")],
        [InlineKeyboardButton("🇺🇦 أوكرانيا - 2.75$", callback_data="buy_session_ukraine")],
        [InlineKeyboardButton("🇩🇿 الجزائر - 1.2$", callback_data="buy_session_algeria")],
        [InlineKeyboardButton("🇯🇴 الأردن - 2.05$", callback_data="buy_session_jordan")],
        [InlineKeyboardButton("🇵🇰 باكستان - 1.2$", callback_data="buy_session_pakistan")],
        [InlineKeyboardButton("🇹🇭 تايلاند - 1.4$", callback_data="buy_session_thailand")],
        [InlineKeyboardButton("🇮🇩 إندونيسيا - 1.15$", callback_data="buy_session_indonesia")],
        [InlineKeyboardButton("🇵🇪 بيرو - 1.6$", callback_data="buy_session_peru")],
        [InlineKeyboardButton("🇬🇭 غانا - 1.25$", callback_data="buy_session_ghana")],
        [InlineKeyboardButton("🇸🇴 الصومال - 1.55$", callback_data="buy_session_somalia")],
        [InlineKeyboardButton("🇸🇿 إسواتيني - 1.35$", callback_data="buy_session_eswatini")],
        [InlineKeyboardButton("🇪🇬 مصر - 1.15$", callback_data="buy_session_egypt")],
        [InlineKeyboardButton("🇸🇦 السعودية - 1.95$", callback_data="buy_session_saudi")],
        [InlineKeyboardButton("🇮🇳 الهند - 1.0$", callback_data="buy_session_india")],
        [InlineKeyboardButton("🇻🇳 فيتنام - 1.45$", callback_data="buy_session_vietnam")],
        [InlineKeyboardButton("🇲🇾 ماليزيا - 1.4$", callback_data="buy_session_malaysia")],
        [InlineKeyboardButton("🇨🇱 تشيلي - 1.2$", callback_data="buy_session_chile")],
        [InlineKeyboardButton("🇮🇱 إسرائيل - 1.65$", callback_data="buy_session_israel")],
        [InlineKeyboardButton("🇧🇾 بيلاروسيا - 1.95$", callback_data="buy_session_belarus")],
        [InlineKeyboardButton("🇪🇸 إسبانيا - 1.35$", callback_data="buy_session_spain")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_numbers")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_old_menu():
    keyboard = [
        [InlineKeyboardButton("🇺🇸 2014 - 20$", callback_data="buy_old_2014")],
        [InlineKeyboardButton("🇺🇸 2015 - 15$", callback_data="buy_old_2015_usa")],
        [InlineKeyboardButton("🇧🇷 2015 - 15$", callback_data="buy_old_2015_brazil")],
        [InlineKeyboardButton("🇺🇸 2016 - 8.5$", callback_data="buy_old_2016_usa")],
        [InlineKeyboardButton("🇪🇬 2018 - 5$", callback_data="buy_old_2018_egypt")],
        [InlineKeyboardButton("🇴🇲 2019 - 5$", callback_data="buy_old_2019_oman")],
        [InlineKeyboardButton("🇸🇴 2020 - 4.0$", callback_data="buy_old_2020_somalia")],
        [InlineKeyboardButton("🇳🇬 2020 - 3.45$", callback_data="buy_old_2020_nigeria")],
        [InlineKeyboardButton("🇹🇷 2020 - 4.0$", callback_data="buy_old_2020_turkey")],
        [InlineKeyboardButton("🇮🇶 2020 - 4.2$", callback_data="buy_old_2020_iraq")],
        [InlineKeyboardButton("🇪🇬 2020 - 3.6$", callback_data="buy_old_2020_egypt")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_numbers")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_whatsapp_menu():
    keyboard = [
        [InlineKeyboardButton("🇮🇩 إندونيسيا - 0.25$", callback_data="buy_whatsapp_indonesia")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_numbers")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_admin_menu():
    keyboard = [
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="admin_stats")],
        [InlineKeyboardButton("🚫 حظر مستخدم", callback_data="admin_ban")],
        [InlineKeyboardButton("📢 إذاعة", callback_data="admin_broadcast")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")],
    ]
    return InlineKeyboardMarkup(keyboard)

async def notify_admin_new_order(context, user_id, order_id, product_name, price):
    user = await context.bot.get_chat(user_id)
    username = user.username or "لا يوجد"
    first_name = user.first_name or "صديقنا"
    text = (
        f"🛒 **طلب جديد**\n━━━━━━━━━━\n"
        f"🔢 رقم الطلب: #{order_id}\n"
        f"👤 المستخدم: {first_name} (@{username})\n"
        f"🆔 المعرف: {user_id}\n"
        f"📦 المنتج: {product_name}\n"
        f"💰 السعر: {price}$\n"
        f"📌 الحالة: انتظار الموافقة"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ قبول الطلب", callback_data=f"approve_order_{order_id}")],
        [InlineKeyboardButton("❌ رفض الطلب", callback_data=f"reject_order_{order_id}")]
    ])
    await context.bot.send_message(chat_id=ADMIN_ID, text=text, parse_mode='Markdown', reply_markup=keyboard)

async def admin_order_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    if not is_admin(user_id):
        await query.edit_message_text("⛔ هذا الأمر للمدير فقط.")
        return
    data = query.data
    if data.startswith("approve_order_"):
        order_id = int(data.split("_")[2])
        order = get_order(order_id)
        if not order:
            await query.edit_message_text("❌ الطلب غير موجود.")
            return
        update_order_status(order_id, "approved")
        await query.edit_message_text(f"✅ تم قبول الطلب #{order_id}\n📌 أرسل المنتج للمستخدم باستخدام الأمر:\n`/sendproduct {order_id} التفاصيل`", parse_mode='Markdown')
        await context.bot.send_message(
            chat_id=order['user_id'],
            text=f"✅ تم قبول طلبك رقم #{order_id}\nسيتم إرسال المنتج إليك قريباً."
        )
    elif data.startswith("reject_order_"):
        order_id = int(data.split("_")[2])
        order = get_order(order_id)
        if not order:
            await query.edit_message_text("❌ الطلب غير موجود.")
            return
        update_order_status(order_id, "rejected")
        await query.edit_message_text(f"❌ تم رفض الطلب #{order_id}")
        await context.bot.send_message(
            chat_id=order['user_id'],
            text=f"❌ تم رفض طلبك رقم #{order_id}\nيمكنك التواصل مع الدعم للمزيد من المعلومات."
        )
        add_balance(order['user_id'], order['price'])
        await context.bot.send_message(
            chat_id=order['user_id'],
            text=f"💰 تم إرجاع المبلغ {order['price']}$ إلى رصيدك."
        )

async def send_product_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ للمدير فقط.")
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("❌ استخدم: `/sendproduct رقم_الطلب التفاصيل`\nمثال: `/sendproduct 123 اسم المستخدم: test - كلمة المرور: 123`", parse_mode='Markdown')
        return
    try:
        order_id = int(args[0])
        product_details = ' '.join(args[1:])
    except ValueError:
        await update.message.reply_text("❌ رقم الطلب يجب أن يكون رقماً.")
        return
    order = get_order(order_id)
    if not order:
        await update.message.reply_text("❌ الطلب غير موجود.")
        return
    if order['status'] != 'approved':
        await update.message.reply_text(f"⚠️ الطلب بحالة `{order['status']}`، يجب أن يكون `approved` أولاً.", parse_mode='Markdown')
        return
    update_order_status(order_id, "completed")
    conn = get_db()
    conn.cursor().execute('UPDATE orders SET details = ? WHERE id = ?', (product_details, order_id))
    conn.commit()
    conn.close()
    await context.bot.send_message(
        chat_id=order['user_id'],
        text=f"🎁 **تم إرسال منتجك**\n━━━━━━━━━━\n📦 {order['product_name']}\n📝 التفاصيل:\n`{product_details}`\n\nشكراً لاستخدامك متجرنا!",
        parse_mode='Markdown'
    )
    await update.message.reply_text(f"✅ تم إرسال المنتج للمستخدم بنجاح (الطلب #{order_id})")

async def add_balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ للمدير فقط.")
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("❌ استخدم: `/addbalance معرف_المستخدم المبلغ`\nمثال: `/addbalance 123456 10`", parse_mode='Markdown')
        return
    try:
        user_id = int(args[0])
        amount = float(args[1])
        if amount <= 0:
            raise ValueError
    except:
        await update.message.reply_text("❌ تأكد من إدخال معرف صحيح ومبلغ أكبر من صفر.")
        return
    add_balance(user_id, amount)
    await update.message.reply_text(f"✅ تم إضافة {amount}$ للمستخدم {user_id}")
    try:
        await context.bot.send_message(
            chat_id=user_id,
            text=f"💰 تم شحن رصيدك بـ {amount}$\nالرصيد الحالي: {get_balance(user_id)}$"
        )
    except:
        await update.message.reply_text("⚠️ تعذر إرسال إشعار للمستخدم (قد يكون حظر البوت).")

async def balance_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_user_banned(user_id):
        await update.message.reply_text("🚫 أنت محظور.")
        return
    bal = get_balance(user_id)
    points = 0
    conn = get_db()
    r = conn.cursor().execute('SELECT referral_points FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if r:
        points = r['referral_points']
    await update.message.reply_text(f"💰 **رصيدك الحالي**: {bal}$\n⭐ **نقاط الإحالة**: {points}", parse_mode='Markdown')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    create_or_update_user(user.id, user.username or "", user.first_name or "")
    if is_user_banned(user.id):
        await update.message.reply_text("🚫 أنت محظور من استخدام هذا البوت.")
        return
    bal = get_balance(user.id)
    await update.message.reply_text(
        f"🌟 أهلاً بك في {SHOP_NAME}!\n💰 رصيدك: {bal}$\nاختر من القائمة:",
        reply_markup=get_main_menu(user.id)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if is_user_banned(user_id):
        await query.edit_message_text("🚫 أنت محظور.")
        return

    if data == "back_main":
        await query.edit_message_text("📋 القائمة الرئيسية:", reply_markup=get_main_menu(user_id))
        return
    if data == "back_numbers":
        await query.edit_message_text("📱 قائمة الأرقام:", reply_markup=get_numbers_main_menu())
        return
    if data == "contact":
        await query.edit_message_text(
            f"📞 **تواصل معنا**\nللدعم: {SUPPORT_USERNAME}\n[اضغط هنا]({SUPPORT_LINK})",
            parse_mode='Markdown', disable_web_page_preview=True
        )
        return
    if data == "my_orders":
        orders = get_user_orders(user_id)
        if not orders:
            await query.edit_message_text("📭 ليس لديك أي طلبات.")
            return
        msg = "🛒 **طلباتي**\n━━━━━━━━━━\n"
        status_emoji = {'pending':'⏳', 'approved':'✅', 'rejected':'❌', 'completed':'📦'}
        for o in orders:
            emoji = status_emoji.get(o['status'], '📦')
            msg += f"{emoji} #{o['id']} - {o['product_name']} - {o['price']}$\n"
        await query.edit_message_text(msg, parse_mode='Markdown')
        return

    if data == "section_accounts":
        await query.edit_message_text("📸 **قسم الحسابات**\nاختر الباقة:", reply_markup=get_accounts_menu())
        return
    if data == "section_stars":
        await query.edit_message_text("⭐ **قسم النجوم**\nاختر النجم:", reply_markup=get_stars_menu())
        return
    if data == "section_usernames":
        await query.edit_message_text("👤 **قسم اليوزرات**\nاختر النوع:", reply_markup=get_usernames_menu())
        return
    if data == "section_referrals":
        await query.edit_message_text("🔗 **قسم الإحالات**\nسعر الإحالة: 0.05$", reply_markup=get_referrals_menu())
        return
    if data == "section_funding":
        await query.edit_message_text("📢 **تمويل القنوات**\nاختر الباقة:", reply_markup=get_funding_menu())
        return
    if data == "section_numbers":
        await query.edit_message_text("📱 **قسم الأرقام**\nاختر نوع الرقم:", reply_markup=get_numbers_main_menu())
        return

    if data == "num_clean":
        await query.edit_message_text("✅ أرقام سليمة:", reply_markup=get_clean_menu())
        return
    if data == "num_spam":
        await query.edit_message_text("🔁 أرقام سبام:", reply_markup=get_spam_menu())
        return
    if data == "num_sessions":
        await query.edit_message_text("🔑 شراء جلسات:", reply_markup=get_sessions_menu())
        return
    if data == "num_old":
        await query.edit_message_text("📂 إنشاءات قديمة:", reply_markup=get_old_menu())
        return
    if data == "num_whatsapp":
        await query.edit_message_text("💬 أرقام واتساب:", reply_markup=get_whatsapp_menu())
        return

    if data.startswith("buy_"):
        product_map = {
            "buy_ig_3000": {"name": "حساب إنستا 3k", "price": 2.5},
            "buy_tt_1300": {"name": "حساب تيك توك 1.3k", "price": 2},
            "buy_star_bear": {"name": "الدب 15 نجمة", "price": 0.18},
            "buy_star_rose": {"name": "الوردة 25 نجمة", "price": 0.28},
            "buy_star_cake": {"name": "الكيكة 50 نجمة", "price": 0.58},
            "buy_star_ring": {"name": "الخاتم 100 نجمة", "price": 1.10},
            "buy_user_tlg": {"name": "يوزر تيليجرام", "price": 0.50},
            "buy_user_insta": {"name": "يوزر إنستغرام", "price": 0.50},
            "buy_clean_myanmar": {"name": "رقم سليم Myanmar", "price": 0.35},
            "buy_clean_vietnam": {"name": "رقم سليم Vietnam", "price": 0.8},
            "buy_clean_algeria": {"name": "رقم سليم Algeria", "price": 0.55},
            "buy_clean_jordan": {"name": "رقم سليم Jordan", "price": 1.6},
            "buy_clean_italy": {"name": "رقم سليم Italy", "price": 1.8},
            "buy_clean_indonesia": {"name": "رقم سليم Indonesia", "price": 0.55},
            "buy_spam_random": {"name": "رقم سبام عشوائي", "price": 0.26},
            "buy_spam_usa": {"name": "رقم سبام أمريكي", "price": 0.22},
            "buy_spam_myanmar": {"name": "رقم سبام Myanmar", "price": 0.25},
            "buy_spam_india": {"name": "رقم سبام India", "price": 0.29},
            "buy_spam_egypt": {"name": "رقم سبام Egypt", "price": 0.5},
            "buy_spam_vietnam": {"name": "رقم سبام Vietnam", "price": 0.32},
            "buy_spam_afghanistan": {"name": "رقم سبام Afghanistan", "price": 0.35},
            "buy_spam_thailand": {"name": "رقم سبام Thailand", "price": 0.41},
            "buy_session_uk": {"name": "جلسة بريطانيا", "price": 1.3},
            "buy_session_italy": {"name": "جلسة إيطاليا", "price": 1.95},
            "buy_session_poland": {"name": "جلسة بولندا", "price": 1.2},
            "buy_session_russia": {"name": "جلسة روسيا", "price": 1.95},
            "buy_session_ukraine": {"name": "جلسة أوكرانيا", "price": 2.75},
            "buy_session_algeria": {"name": "جلسة الجزائر", "price": 1.2},
            "buy_session_jordan": {"name": "جلسة الأردن", "price": 2.05},
            "buy_session_pakistan": {"name": "جلسة باكستان", "price": 1.2},
            "buy_session_thailand": {"name": "جلسة تايلاند", "price": 1.4},
            "buy_session_indonesia": {"name": "جلسة إندونيسيا", "price": 1.15},
            "buy_session_peru": {"name": "جلسة بيرو", "price": 1.6},
            "buy_session_ghana": {"name": "جلسة غانا", "price": 1.25},
            "buy_session_somalia": {"name": "جلسة الصومال", "price": 1.55},
            "buy_session_eswatini": {"name": "جلسة إسواتيني", "price": 1.35},
            "buy_session_egypt": {"name": "جلسة مصر", "price": 1.15},
            "buy_session_saudi": {"name": "جلسة السعودية", "price": 1.95},
            "buy_session_india": {"name": "جلسة الهند", "price": 1.0},
            "buy_session_vietnam": {"name": "جلسة فيتنام", "price": 1.45},
            "buy_session_malaysia": {"name": "جلسة ماليزيا", "price": 1.4},
            "buy_session_chile": {"name": "جلسة تشيلي", "price": 1.2},
            "buy_session_israel": {"name": "جلسة إسرائيل", "price": 1.65},
            "buy_session_belarus": {"name": "جلسة بيلاروسيا", "price": 1.95},
            "buy_session_spain": {"name": "جلسة إسبانيا", "price": 1.35},
            "buy_old_2014": {"name": "حساب 2014", "price": 20},
            "buy_old_2015_usa": {"name": "حساب 2015 USA", "price": 15},
            "buy_old_2015_brazil": {"name": "حساب 2015 Brazil", "price": 15},
            "buy_old_2016_usa": {"name": "حساب 2016 USA", "price": 8.5},
            "buy_old_2018_egypt": {"name": "حساب 2018 Egypt", "price": 5},
            "buy_old_2019_oman": {"name": "حساب 2019 Oman", "price": 5},
            "buy_old_2020_somalia": {"name": "حساب 2020 Somalia", "price": 4.0},
            "buy_old_2020_nigeria": {"name": "حساب 2020 Nigeria", "price": 3.45},
            "buy_old_2020_turkey": {"name": "حساب 2020 Turkey", "price": 4.0},
            "buy_old_2020_iraq": {"name": "حساب 2020 Iraq", "price": 4.2},
            "buy_old_2020_egypt": {"name": "حساب 2020 Egypt", "price": 3.6},
            "buy_whatsapp_indonesia": {"name": "رقم واتساب إندونيسيا", "price": 0.25},
        }
        product = product_map.get(data)
        if not product:
            await query.edit_message_text("❌ منتج غير معروف.")
            return
        balance = get_balance(user_id)
        if balance < product["price"]:
            await query.edit_message_text(f"❌ رصيدك غير كافٍ! رصيدك: {balance}$, المطلوب: {product['price']}$\n📞 تواصل مع الأدمن لشحن الرصيد.")
            return
        deduct_balance(user_id, product["price"])
        oid = create_order(user_id, product["name"], product["price"])
        add_purchase_points(user_id)
        await notify_admin_new_order(context, user_id, oid, product["name"], product["price"])
        await query.edit_message_text(
            f"✅ تم إنشاء طلبك بنجاح!\n📦 المنتج: {product['name']}\n💰 المدفوع: {product['price']}$\n🔢 رقم الطلب: #{oid}\n📌 الرصيد المتبقي: {get_balance(user_id)}$\n\n⏳ في انتظار موافقة الأدمن."
        )
        return

    if data == "ref_price":
        await query.edit_message_text("💰 السعر: 1 إحالة = 0.05$ (5 سنت)", reply_markup=get_referrals_menu())
        return
    if data == "ref_buy":
        await query.edit_message_text("📎 أرسل رابط بوتك (مثل @BotName):")
        return REF_LINK

    if data in ["fund_1000", "fund_5000"]:
        context.user_data['fund_product'] = data
        await query.edit_message_text("📎 أرسل رابط قناتك (مثل @Channel):")
        return FUND_LINK

    if data == "admin_panel":
        if not is_admin(user_id):
            await query.edit_message_text("⛔ هذا القسم للمدير فقط.")
            return
        await query.edit_message_text("⚙️ لوحة الأدمن", reply_markup=get_admin_menu())
        return
    if data == "admin_stats":
        if not is_admin(user_id): return
        conn = get_db()
        users_count = conn.cursor().execute('SELECT COUNT(*) FROM users').fetchone()[0]
        orders_count = conn.cursor().execute('SELECT COUNT(*) FROM orders').fetchone()[0]
        pending_count = conn.cursor().execute('SELECT COUNT(*) FROM orders WHERE status = "pending"').fetchone()[0]
        conn.close()
        await query.edit_message_text(
            f"📊 **الإحصائيات**\n━━━━━━━━━━\n👥 المستخدمين: {users_count}\n📦 الطلبات: {orders_count}\n⏳ قيد الانتظار: {pending_count}"
        )
        return
    if data in ["admin_ban", "admin_broadcast"]:
        if not is_admin(user_id): return
        cmd = "ban" if data == "admin_ban" else "broadcast"
        await query.edit_message_text(f"🚫 استخدم الأمر /{cmd}")

    await query.edit_message_text("❌ خيار غير معروف.")

async def ref_get_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['ref_link'] = update.message.text
    await update.message.reply_text("🔢 أرسل الكمية المطلوبة (مثال: 100):")
    return REF_QUANTITY

async def ref_get_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        qty = int(update.message.text)
        if qty <= 0:
            raise ValueError
    except:
        await update.message.reply_text("❌ أرسل رقماً صحيحاً أكبر من صفر.")
        return REF_QUANTITY
    price = qty * 0.05
    balance = get_balance(user_id)
    if balance < price:
        await update.message.reply_text(f"❌ رصيدك غير كافٍ! رصيدك: {balance}$, المطلوب: {price}$")
        return ConversationHandler.END
    deduct_balance(user_id, price)
    details = f"الرابط: {context.user_data['ref_link']}, الكمية: {qty}"
    oid = create_order(user_id, f"إحالات {qty}", price, qty, details)
    add_purchase_points(user_id)
    await notify_admin_new_order(context, user_id, oid, f"إحالات {qty}", price)
    await update.message.reply_text(
        f"✅ تم إنشاء طلب شراء {qty} إحالة!\n💰 المدفوع: {price}$\n🔢 رقم الطلب: #{oid}\n📌 الرصيد المتبقي: {get_balance(user_id)}$\n\n⏳ في انتظار موافقة الأدمن."
    )
    context.user_data.pop('ref_link', None)
    return ConversationHandler.END

async def fund_get_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    link = update.message.text
    product_key = context.user_data.get('fund_product')
    if not product_key:
        await update.message.reply_text("❌ حدث خطأ، حاول مرة أخرى.")
        return ConversationHandler.END
    fund_products = {
        "fund_1000": {"name": "1000 عضو", "price": 1.20},
        "fund_5000": {"name": "5000 عضو", "price": 5.00},
    }
    product = fund_products[product_key]
    price = product["price"]
    balance = get_balance(user_id)
    if balance < price:
        await update.message.reply_text(f"❌ رصيدك غير كافٍ! رصيدك: {balance}$, المطلوب: {price}$")
        return ConversationHandler.END
    deduct_balance(user_id, price)
    details = f"الرابط: {link}"
    oid = create_order(user_id, f"تمويل {product['name']}", price, 1, details)
    add_purchase_points(user_id)
    await notify_admin_new_order(context, user_id, oid, f"تمويل {product['name']}", price)
    await update.message.reply_text(
        f"✅ تم طلب تمويل {product['name']}!\n💰 السعر: {price}$\n🔢 رقم الطلب: #{oid}\n📌 الرابط: {link}\n📌 الرصيد المتبقي: {get_balance(user_id)}$\n\n⏳ في انتظار موافقة الأدمن."
    )
    context.user_data.pop('fund_product', None)
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ تم الإلغاء.")
    return ConversationHandler.END

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ للمدير فقط.")
        return
    try:
        uid = int(context.args[0])
        conn = get_db()
        conn.cursor().execute('UPDATE users SET is_banned = 1 WHERE id = ?', (uid,))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"✅ تم حظر المستخدم {uid}")
    except:
        await update.message.reply_text("❌ استخدم: /ban ID")

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ للمدير فقط.")
        return
    try:
        uid = int(context.args[0])
        conn = get_db()
        conn.cursor().execute('UPDATE users SET is_banned = 0 WHERE id = ?', (uid,))
        conn.commit()
        conn.close()
        await update.message.reply_text(f"✅ تم فك الحظر عن المستخدم {uid}")
    except:
        await update.message.reply_text("❌ استخدم: /unban ID")

async def broadcast_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("⛔ للمدير فقط.")
        return
    msg = ' '.join(context.args)
    if not msg:
        await update.message.reply_text("❌ استخدم: /broadcast نص الرسالة")
        return
    conn = get_db()
    users = conn.cursor().execute('SELECT id FROM users WHERE is_banned = 0').fetchall()
    conn.close()
    s, f = 0, 0
    for u in users:
        try:
            await context.bot.send_message(chat_id=u['id'], text=msg)
            s += 1
        except:
            f += 1
    await update.message.reply_text(f"✅ تم الإرسال لـ {s} | ❌ فشل {f}")

def main():
    logging.basicConfig(level=logging.INFO)
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("balance", balance_command))
    
    app.add_handler(CommandHandler("ban", ban_command))
    app.add_handler(CommandHandler("unban", unban_command))
    app.add_handler(CommandHandler("broadcast", broadcast_command))
    app.add_handler(CommandHandler("addbalance", add_balance_command))
    app.add_handler(CommandHandler("sendproduct", send_product_command))

    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CallbackQueryHandler(admin_order_handler, pattern="^(approve_order_|reject_order_)"))

    ref_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^ref_buy$")],
        states={
            REF_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, ref_get_link)],
            REF_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, ref_get_quantity)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(ref_conv)

    fund_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^fund_")],
        states={
            FUND_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, fund_get_link)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    app.add_handler(fund_conv)

    print("🚀 البوت المتكامل (متجر) شغال...")
    app.run_polling()

if __name__ == "__main__":
    main()
