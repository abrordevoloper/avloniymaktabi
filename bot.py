import logging
import random
import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, CallbackQueryHandler,
    ContextTypes, ConversationHandler, MessageHandler, filters
)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# =====================================================
# ADMIN ID — @userinfobot ga /start yuboring, ID oling
# =====================================================
ADMIN_IDS = [1986282464]  # <- O'z ID'ingizni yozing

DB_PATH = "questions.db"

# Conversation bosqichlari
(
    ADD_CAT_NAME,        # yangi kategoriya nomi
    ADD_Q_CHOOSE_CAT,    # savol uchun kategoriya tanlash
    ADD_Q_QUESTION,      # savol matni
    ADD_Q_OPTIONS,       # variantlar
    ADD_Q_ANSWER,        # to'g'ri javob
    RENAME_CAT,          # kategoriya nomini o'zgartirish
) = range(6)


# =====================================================
# BAZA
# =====================================================
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL
    )''')
    c.execute('''CREATE TABLE IF NOT EXISTS questions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_id INTEGER NOT NULL,
        question TEXT NOT NULL,
        option_a TEXT NOT NULL,
        option_b TEXT NOT NULL,
        option_c TEXT NOT NULL,
        option_d TEXT NOT NULL,
        answer TEXT NOT NULL,
        FOREIGN KEY(category_id) REFERENCES categories(id)
    )''')
    conn.commit()
    conn.close()

def get_categories():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, name FROM categories ORDER BY id")
    rows = c.fetchall()
    conn.close()
    return rows  # [(id, name), ...]

def add_category(name):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO categories (name) VALUES (?)", (name,))
        conn.commit()
        cat_id = c.lastrowid
        conn.close()
        return cat_id
    except sqlite3.IntegrityError:
        conn.close()
        return None  # already exists

def rename_category(cat_id, new_name):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("UPDATE categories SET name=? WHERE id=?", (new_name, cat_id))
        conn.commit()
        conn.close()
        return True
    except:
        conn.close()
        return False

def delete_category(cat_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM questions WHERE category_id=?", (cat_id,))
    c.execute("DELETE FROM categories WHERE id=?", (cat_id,))
    conn.commit()
    conn.close()

def get_questions(category_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM questions WHERE category_id=?", (category_id,))
    rows = c.fetchall()
    conn.close()
    return [{
        "id": r[0], "category_id": r[1], "question": r[2],
        "options": [r[3], r[4], r[5], r[6]], "answer": r[7]
    } for r in rows]

def count_questions(category_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM questions WHERE category_id=?", (category_id,))
    count = c.fetchone()[0]
    conn.close()
    return count

def add_question(category_id, question, options, answer):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO questions (category_id, question, option_a, option_b, option_c, option_d, answer) VALUES (?,?,?,?,?,?,?)",
        (category_id, question, options[0], options[1], options[2], options[3], answer)
    )
    conn.commit()
    conn.close()

def delete_question(q_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM questions WHERE id=?", (q_id,))
    conn.commit()
    conn.close()

def get_category_name(cat_id):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name FROM categories WHERE id=?", (cat_id,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else "Noma'lum"

def is_admin(user_id):
    return user_id in ADMIN_IDS


# =====================================================
# START
# =====================================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("📝 Testni boshlash", callback_data="start_test")],
        [InlineKeyboardButton("📊 Natijalarim", callback_data="my_stats")],
        [InlineKeyboardButton("ℹ️ Yordam", callback_data="help")],
    ]
    if is_admin(user.id):
        keyboard.append([InlineKeyboardButton("⚙️ Admin panel", callback_data="admin_panel")])

    await update.message.reply_text(
        f"🏛 Salom, {user.first_name}!\n\n"
        "📚 *Tarix fanidan test botiga xush kelibsiz!*\n\n"
        "Kategoriyani tanlab, bilimlaringizni sinab ko'ring.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


# =====================================================
# TEST — KATEGORIYA TANLASH
# =====================================================
async def show_test_categories(query, context):
    cats = get_categories()
    if not cats:
        await query.edit_message_text(
            "❌ Hali kategoriyalar yo'q.\nAdmin kategoriya va savollar qo'shishi kerak.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")]]),
        )
        return

    keyboard = []
    for cat_id, cat_name in cats:
        count = count_questions(cat_id)
        keyboard.append([InlineKeyboardButton(
            f"📂 {cat_name}  ({count} ta savol)",
            callback_data=f"test_cat_{cat_id}"
        )])
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")])

    await query.edit_message_text(
        "📂 *Kategoriyani tanlang:*",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


# =====================================================
# ASOSIY TUGMALAR
# =====================================================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "start_test":
        await show_test_categories(query, context)

    elif data.startswith("test_cat_"):
        cat_id = int(data.split("_")[2])
        pool = get_questions(cat_id)
        cat_name = get_category_name(cat_id)

        if not pool:
            await query.edit_message_text(
                f"❌ *{cat_name}* kategoriyasida savollar yo'q.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Orqaga", callback_data="start_test")]]),
                parse_mode="Markdown"
            )
            return

        #selected = random.sample(pool, min(10, len(pool)))
        MAX_QUESTIONS = 50
        selected = pool[:]
        random.shuffle(selected)
        selected = selected[:MAX_QUESTIONS]
        context.user_data["questions"] = selected
        context.user_data["current"] = 0
        context.user_data["score"] = 0
        context.user_data["wrong"] = []
        context.user_data["cat_name"] = cat_name
        await send_question(query, context)

    elif data.startswith("ans_"):
        await handle_answer(query, context)

    elif data == "next_q":
        await send_question(query, context)

    elif data == "my_stats":
        score = context.user_data.get("last_score")
        total = context.user_data.get("last_total")
        cat = context.user_data.get("last_cat", "")
        if score is None:
            text = "📊 Siz hali test topshirmagansiz."
        else:
            percent = round((score / total) * 100)
            emoji = "🏆" if percent >= 80 else "👍" if percent >= 50 else "📖"
            text = (
                f"📊 *So'nggi natija:*\n\n"
                f"📂 Kategoriya: {cat}\n"
                f"{emoji} To'g'ri: {score}/{total}\n"
                f"📈 Foiz: {percent}%"
            )
        keyboard = [[InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "help":
        text = (
            "ℹ️ *Bot haqida:*\n\n"
            "• Kategoriyani tanlang\n"
            "• Har testda 10 ta tasodifiy savol\n"
            "• Har to'g'ri javob 1 ball\n"
            "• Test tugagach natija ko'rsatiladi\n\n"
            "📌 *Buyruqlar:*\n"
            "/start — Bosh menyu\n"
            "/cancel — Amalni bekor qilish"
        )
        keyboard = [[InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data in ["back_main", "restart"]:
        user = update.effective_user
        keyboard = [
            [InlineKeyboardButton("📝 Testni boshlash", callback_data="start_test")],
            [InlineKeyboardButton("📊 Natijalarim", callback_data="my_stats")],
            [InlineKeyboardButton("ℹ️ Yordam", callback_data="help")],
        ]
        if is_admin(user.id):
            keyboard.append([InlineKeyboardButton("⚙️ Admin panel", callback_data="admin_panel")])
        await query.edit_message_text(
            "🏛 *Tarix fanidan test boti*\n\nQuyidagi tugmalardan birini tanlang:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    # ===================== ADMIN PANEL =====================
    elif data == "admin_panel":
        if not is_admin(update.effective_user.id):
            await query.answer("❌ Ruxsat yo'q!", show_alert=True)
            return
        await show_admin_panel(query)

    elif data == "admin_cats":
        if not is_admin(update.effective_user.id):
            return
        await show_admin_cats(query)

    elif data.startswith("admin_cat_"):
        if not is_admin(update.effective_user.id):
            return
        cat_id = int(data.split("_")[2])
        cat_name = get_category_name(cat_id)
        count = count_questions(cat_id)
        keyboard = [
            [InlineKeyboardButton("➕ Savol qo'shish", callback_data=f"addq_cat_{cat_id}")],
            [InlineKeyboardButton("📋 Savollar", callback_data=f"qlist_{cat_id}_0")],
            [InlineKeyboardButton("✏️ Nomini o'zgartirish", callback_data=f"renamec_{cat_id}")],
            [InlineKeyboardButton("🗑 Kategoriyani o'chirish", callback_data=f"delcat_{cat_id}")],
            [InlineKeyboardButton("🔙 Orqaga", callback_data="admin_cats")],
        ]
        await query.edit_message_text(
            f"📂 *{cat_name}*\n\n📦 Savollar soni: *{count}* ta",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    elif data.startswith("delcat_"):
        if not is_admin(update.effective_user.id):
            return
        cat_id = int(data.split("_")[1])
        cat_name = get_category_name(cat_id)
        count = count_questions(cat_id)
        keyboard = [
            [
                InlineKeyboardButton("✅ Ha, o'chir", callback_data=f"confirmdelcat_{cat_id}"),
                InlineKeyboardButton("❌ Yo'q", callback_data=f"admin_cat_{cat_id}"),
            ]
        ]
        await query.edit_message_text(
            f"⚠️ *{cat_name}* kategoriyasini o'chirasizmi?\n\n"
            f"Bilan birga *{count} ta savol* ham o'chib ketadi!",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    elif data.startswith("confirmdelcat_"):
        if not is_admin(update.effective_user.id):
            return
        cat_id = int(data.split("_")[1])
        delete_category(cat_id)
        await query.answer("✅ Kategoriya o'chirildi!", show_alert=True)
        await show_admin_cats(query)

    elif data.startswith("qlist_"):
        if not is_admin(update.effective_user.id):
            return
        parts = data.split("_")
        cat_id = int(parts[1])
        page = int(parts[2])
        await show_question_list(query, cat_id, page)

    elif data.startswith("delq_"):
        if not is_admin(update.effective_user.id):
            return
        parts = data.split("_")
        q_id = int(parts[1])
        cat_id = int(parts[2])
        keyboard = [
            [
                InlineKeyboardButton("✅ Ha, o'chir", callback_data=f"confirmdelq_{q_id}_{cat_id}"),
                InlineKeyboardButton("❌ Yo'q", callback_data=f"qlist_{cat_id}_0"),
            ]
        ]
        await query.edit_message_text(
            "⚠️ Bu savolni o'chirishni tasdiqlaysizmi?",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    elif data.startswith("confirmdelq_"):
        if not is_admin(update.effective_user.id):
            return
        parts = data.split("_")
        q_id = int(parts[1])
        cat_id = int(parts[2])
        delete_question(q_id)
        await query.answer("✅ Savol o'chirildi!", show_alert=True)
        await show_question_list(query, cat_id, 0)


# =====================================================
# ADMIN YORDAMCHI FUNKSIYALAR
# =====================================================
async def show_admin_panel(query):
    cats = get_categories()
    total_q = sum(count_questions(c[0]) for c in cats)
    keyboard = [
        [InlineKeyboardButton("📂 Kategoriyalar", callback_data="admin_cats")],
        [InlineKeyboardButton("🔙 Bosh menyu", callback_data="back_main")],
    ]
    await query.edit_message_text(
        f"⚙️ *Admin panel*\n\n"
        f"📂 Kategoriyalar: *{len(cats)}* ta\n"
        f"📦 Jami savollar: *{total_q}* ta",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def show_admin_cats(query):
    cats = get_categories()
    keyboard = []
    for cat_id, cat_name in cats:
        count = count_questions(cat_id)
        keyboard.append([InlineKeyboardButton(
            f"📂 {cat_name} ({count} ta)",
            callback_data=f"admin_cat_{cat_id}"
        )])
    keyboard.append([InlineKeyboardButton("➕ Yangi kategoriya", callback_data="admin_addcat")])
    keyboard.append([InlineKeyboardButton("🔙 Admin panel", callback_data="admin_panel")])

    await query.edit_message_text(
        "📂 *Kategoriyalar:*\n\nKategoriyani tanlang yoki yangisini qo'shing.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def show_question_list(query, cat_id, page):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, question FROM questions WHERE category_id=? ORDER BY id", (cat_id,))
    all_q = c.fetchall()
    conn.close()

    cat_name = get_category_name(cat_id)
    per_page = 5
    start_i = page * per_page
    end_i = start_i + per_page
    page_q = all_q[start_i:end_i]

    keyboard = []
    if not all_q:
        text = f"📋 *{cat_name}*\n\nHali savollar yo'q."
    else:
        text = f"📋 *{cat_name}* ({start_i+1}-{min(end_i,len(all_q))} / {len(all_q)} ta):\n\n"
        for q_id, question in page_q:
            short = question[:45] + "..." if len(question) > 45 else question
            text += f"• [{q_id}] {short}\n"
            keyboard.append([InlineKeyboardButton(
                f"🗑 [{q_id}] {short[:35]}...",
                callback_data=f"delq_{q_id}_{cat_id}"
            )])

    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"qlist_{cat_id}_{page-1}"))
    if end_i < len(all_q):
        nav.append(InlineKeyboardButton("➡️", callback_data=f"qlist_{cat_id}_{page+1}"))
    if nav:
        keyboard.append(nav)
    keyboard.append([InlineKeyboardButton("🔙 Orqaga", callback_data=f"admin_cat_{cat_id}")])

    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


# =====================================================
# TEST FUNKSIYALARI
# =====================================================
async def send_question(query, context: ContextTypes.DEFAULT_TYPE):
    questions = context.user_data["questions"]
    idx = context.user_data["current"]
    q = questions[idx]
    total = len(questions)

    options = q["options"][:]
    random.shuffle(options)
    context.user_data["shuffled_options"] = options
    context.user_data["correct_answer"] = q["answer"]

    keyboard = [
        [InlineKeyboardButton(f"{['A','B','C','D'][i]}) {opt}", callback_data=f"ans_{i}")]
        for i, opt in enumerate(options)
    ]
    await query.edit_message_text(
        f"📂 {context.user_data['cat_name']}\n"
        f"❓ *{idx+1}/{total}-savol*\n\n{q['question']}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def handle_answer(query, context: ContextTypes.DEFAULT_TYPE):
    selected_idx = int(query.data.replace("ans_", ""))
    options = context.user_data["shuffled_options"]
    selected = options[selected_idx]
    correct = context.user_data["correct_answer"]

    if selected == correct:
        context.user_data["score"] += 1
        result_text = f"✅ *To'g'ri!*\n\nJavob: *{correct}*"
    else:
        context.user_data["wrong"].append({
            "question": context.user_data["questions"][context.user_data["current"]]["question"],
            "correct": correct
        })
        result_text = f"❌ *Noto'g'ri!*\n\nSizning javobingiz: {selected}\n✅ To'g'ri javob: *{correct}*"

    context.user_data["current"] += 1
    current = context.user_data["current"]
    total = len(context.user_data["questions"])

    if current < total:
        keyboard = [[InlineKeyboardButton("➡️ Keyingi savol", callback_data="next_q")]]
        await query.edit_message_text(result_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        score = context.user_data["score"]
        cat_name = context.user_data["cat_name"]
        context.user_data["last_score"] = score
        context.user_data["last_total"] = total
        context.user_data["last_cat"] = cat_name
        percent = round((score / total) * 100)

        if percent >= 90: emoji, baho = "🏆", "A'lo"
        elif percent >= 70: emoji, baho = "👍", "Yaxshi"
        elif percent >= 50: emoji, baho = "😊", "Qoniqarli"
        else: emoji, baho = "📖", "Qoniqarsiz"

        result = (
            f"{emoji} *Test yakunlandi!*\n\n"
            f"📂 {cat_name}\n"
            f"📊 Natija: *{score}/{total}*\n"
            f"📈 Foiz: *{percent}%*\n"
            f"🎯 Baho: *{baho}*"
        )
        wrong = context.user_data.get("wrong", [])
        if wrong:
            result += f"\n\n❌ *Xato javoblar:*\n"
            for i, w in enumerate(wrong[:5], 1):
                result += f"\n{i}. {w['question']}\n   ✅ {w['correct']}\n"

        keyboard = [
            [InlineKeyboardButton("🔄 Qayta boshlash", callback_data=f"start_test")],
            [InlineKeyboardButton("🏠 Bosh menyu", callback_data="back_main")],
        ]
        await query.edit_message_text(result, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


# =====================================================
# CONVERSATION — KATEGORIYA QO'SHISH
# =====================================================
async def admin_addcat_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END
    await query.edit_message_text(
        "➕ *Yangi kategoriya nomi:*\n\n"
        "Masalan: `8-sinf 1-bob`, `Mustaqillik davri`, `9-sinf`\n\n"
        "_(Bekor qilish: /cancel)_",
        parse_mode="Markdown"
    )
    return ADD_CAT_NAME

async def admin_save_category(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    cat_id = add_category(name)
    if cat_id is None:
        await update.message.reply_text(
            f"⚠️ *{name}* nomli kategoriya allaqachon mavjud!\n\nBoshqa nom yozing:",
            parse_mode="Markdown"
        )
        return ADD_CAT_NAME

    keyboard = [
        [InlineKeyboardButton("➕ Savol qo'shish", callback_data=f"addq_cat_{cat_id}")],
        [InlineKeyboardButton("⚙️ Admin panel", callback_data="admin_panel")],
    ]
    await update.message.reply_text(
        f"✅ *{name}* kategoriyasi yaratildi!\n\nEndi savol qo'shishingiz mumkin.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return ConversationHandler.END


# =====================================================
# CONVERSATION — SAVOL QO'SHISH
# =====================================================
async def addq_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END

    cat_id = int(query.data.split("_")[2])
    cat_name = get_category_name(cat_id)
    context.user_data["new_q_cat_id"] = cat_id
    context.user_data["new_q_cat_name"] = cat_name

    await query.edit_message_text(
        f"➕ *{cat_name}* ga savol qo'shish\n\n"
        f"1️⃣ Savol matnini yozing:\n\n_(Bekor qilish: /cancel)_",
        parse_mode="Markdown"
    )
    return ADD_Q_QUESTION

async def addq_get_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["new_q_question"] = update.message.text.strip()
    await update.message.reply_text(
        "2️⃣ *4 ta variantni* yozing, har birini yangi qatordan:\n\n"
        "Misol:\n1370\n1380\n1395\n1405\n\n_(Bekor qilish: /cancel)_",
        parse_mode="Markdown"
    )
    return ADD_Q_OPTIONS

async def addq_get_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = [l.strip() for l in update.message.text.strip().split("\n") if l.strip()]
    if len(lines) != 4:
        await update.message.reply_text(
            f"⚠️ Aynan *4 ta variant* kerak! Siz *{len(lines)}* ta yozdingiz.\n\nQaytadan yuboring:",
            parse_mode="Markdown"
        )
        return ADD_Q_OPTIONS

    context.user_data["new_q_options"] = lines
    opts = "\n".join([f"{['A','B','C','D'][i]}) {o}" for i, o in enumerate(lines)])
    await update.message.reply_text(
        f"✅ Variantlar:\n{opts}\n\n"
        "3️⃣ To'g'ri javobni yozing *(yuqoridagi variantdan aynan bir xil)*:\n\n"
        "_(Bekor qilish: /cancel)_",
        parse_mode="Markdown"
    )
    return ADD_Q_ANSWER

async def addq_get_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    answer = update.message.text.strip()
    options = context.user_data["new_q_options"]

    if answer not in options:
        opts = "\n".join([f"• {o}" for o in options])
        await update.message.reply_text(
            f"⚠️ Javob variantlar ichida bo'lishi kerak!\n\n{opts}\n\nQaytadan yozing:",
            parse_mode="Markdown"
        )
        return ADD_Q_ANSWER

    cat_id = context.user_data["new_q_cat_id"]
    cat_name = context.user_data["new_q_cat_name"]
    question = context.user_data["new_q_question"]
    add_question(cat_id, question, options, answer)
    count = count_questions(cat_id)

    keyboard = [
        [InlineKeyboardButton("➕ Yana savol qo'shish", callback_data=f"addq_cat_{cat_id}")],
        [InlineKeyboardButton("📂 Kategoriyaga qaytish", callback_data=f"admin_cat_{cat_id}")],
    ]
    await update.message.reply_text(
        f"✅ *Savol qo'shildi!*\n\n"
        f"📂 {cat_name}\n"
        f"❓ {question}\n"
        f"✅ Javob: {answer}\n\n"
        f"📦 Jami: *{count}* ta savol",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return ConversationHandler.END


# =====================================================
# CONVERSATION — KATEGORIYA NOMINI O'ZGARTIRISH
# =====================================================
async def renamec_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if not is_admin(update.effective_user.id):
        return ConversationHandler.END
    cat_id = int(query.data.split("_")[1])
    cat_name = get_category_name(cat_id)
    context.user_data["rename_cat_id"] = cat_id
    await query.edit_message_text(
        f"✏️ *{cat_name}* — yangi nomini yozing:\n\n_(Bekor qilish: /cancel)_",
        parse_mode="Markdown"
    )
    return RENAME_CAT

async def renamec_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    new_name = update.message.text.strip()
    cat_id = context.user_data["rename_cat_id"]
    rename_category(cat_id, new_name)
    keyboard = [[InlineKeyboardButton("📂 Kategoriyaga o'tish", callback_data=f"admin_cat_{cat_id}")]]
    await update.message.reply_text(
        f"✅ Kategoriya nomi *{new_name}* ga o'zgartirildi!",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Bekor qilindi.\n\n/start — Bosh menyu")
    return ConversationHandler.END


# =====================================================
# MAIN
# =====================================================
def main():
    TOKEN = "8615969282:AAE_CzyQ5GdwPzmWfomoxv15GRw005a31SM"
    if not TOKEN:
        raise ValueError("BOT_TOKEN environment variable not set!")

    init_db()
    app = ApplicationBuilder().token(TOKEN).build()

    # Kategoriya qo'shish
    cat_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(admin_addcat_start, pattern="^admin_addcat$")],
        states={
            ADD_CAT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_save_category)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Savol qo'shish
    addq_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(addq_start, pattern="^addq_cat_\\d+$")],
        states={
            ADD_Q_QUESTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, addq_get_question)],
            ADD_Q_OPTIONS:  [MessageHandler(filters.TEXT & ~filters.COMMAND, addq_get_options)],
            ADD_Q_ANSWER:   [MessageHandler(filters.TEXT & ~filters.COMMAND, addq_get_answer)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    # Kategoriya nomini o'zgartirish
    rename_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(renamec_start, pattern="^renamec_\\d+$")],
        states={
            RENAME_CAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, renamec_save)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(cat_conv)
    app.add_handler(addq_conv)
    app.add_handler(rename_conv)
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🤖 Bot ishga tushdi...")
    app.run_polling()

if __name__ == "__main__":
    main()
