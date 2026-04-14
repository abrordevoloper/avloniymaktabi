import logging
import random
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes, ConversationHandler
)
from questions import QUESTIONS

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Holatlar
CHOOSING, ANSWERING = range(2)

# ===================== START =====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    keyboard = [
        [InlineKeyboardButton("📝 Testni boshlash", callback_data="start_test")],
        [InlineKeyboardButton("📊 Natijalarim", callback_data="my_stats")],
        [InlineKeyboardButton("ℹ️ Yordam", callback_data="help")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"🏛 Salom, {user.first_name}!\n\n"
        "📚 *Tarix fanidan test botiga xush kelibsiz!*\n\n"
        "Bu bot orqali O'zbekiston va Jahon tarixi bo'yicha "
        "bilimlaringizni sinab ko'rishingiz mumkin.\n\n"
        "Quyidagi tugmalardan birini tanlang:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

# ===================== KATEGORIYA TANLASH =====================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "start_test":
        keyboard = [
            [InlineKeyboardButton("🇺🇿 O'zbekiston tarixi", callback_data="cat_uzbekistan")],
            [InlineKeyboardButton("🌍 Jahon tarixi", callback_data="cat_world")],
            [InlineKeyboardButton("🎲 Aralash", callback_data="cat_mix")],
            [InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")],
        ]
        await query.edit_message_text(
            "📂 *Qaysi bo'limdan test topshirmoqchisiz?*",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    elif data in ["cat_uzbekistan", "cat_world", "cat_mix"]:
        category_map = {
            "cat_uzbekistan": "uzbekistan",
            "cat_world": "world",
            "cat_mix": "mix"
        }
        category = category_map[data]

        # Savollarni filtrlash
        if category == "mix":
            pool = QUESTIONS
        else:
            pool = [q for q in QUESTIONS if q["category"] == category]

        if not pool:
            await query.edit_message_text("❌ Bu bo'limda savollar yo'q. Admin savollar qo'shishi kerak.")
            return

        # 10 ta savol tanlash (yoki barcha savollar)
        selected = random.sample(pool, min(10, len(pool)))
        context.user_data["questions"] = selected
        context.user_data["current"] = 0
        context.user_data["score"] = 0
        context.user_data["wrong"] = []

        await send_question(query, context)

    elif data.startswith("ans_"):
        await handle_answer(query, context)

    elif data == "my_stats":
        score = context.user_data.get("last_score", None)
        total = context.user_data.get("last_total", None)
        if score is None:
            text = "📊 Siz hali test topshirmagansiz.\n\nTestni boshlash uchun /start bosing."
        else:
            percent = round((score / total) * 100)
            emoji = "🏆" if percent >= 80 else "👍" if percent >= 50 else "📖"
            text = (
                f"📊 *So'nggi test natijasi:*\n\n"
                f"{emoji} To'g'ri javoblar: {score}/{total}\n"
                f"📈 Foiz: {percent}%\n\n"
                f"Yana urinib ko'rish uchun /start bosing."
            )
        keyboard = [[InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "help":
        text = (
            "ℹ️ *Bot haqida:*\n\n"
            "• Har bir testda 10 ta savol beriladi\n"
            "• Har bir to'g'ri javob 1 ball\n"
            "• Test tugagach natija ko'rsatiladi\n\n"
            "📌 *Buyruqlar:*\n"
            "/start — Bosh menyu\n"
            "/test — Tezkor test boshlash\n"
            "/stop — Testni to'xtatish"
        )
        keyboard = [[InlineKeyboardButton("🔙 Orqaga", callback_data="back_main")]]
        await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")

    elif data == "back_main":
        keyboard = [
            [InlineKeyboardButton("📝 Testni boshlash", callback_data="start_test")],
            [InlineKeyboardButton("📊 Natijalarim", callback_data="my_stats")],
            [InlineKeyboardButton("ℹ️ Yordam", callback_data="help")],
        ]
        await query.edit_message_text(
            "🏛 *Tarix fanidan test boti*\n\nQuyidagi tugmalardan birini tanlang:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

    elif data == "restart":
        keyboard = [
            [InlineKeyboardButton("📝 Testni boshlash", callback_data="start_test")],
            [InlineKeyboardButton("📊 Natijalarim", callback_data="my_stats")],
        ]
        await query.edit_message_text(
            "🏛 *Bosh menyu*\n\nYana bir bor urinib ko'ring!",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

# ===================== SAVOL YUBORISH =====================
async def send_question(query, context: ContextTypes.DEFAULT_TYPE):
    questions = context.user_data["questions"]
    idx = context.user_data["current"]
    q = questions[idx]
    total = len(questions)

    # Variantlarni aralashtirish
    options = q["options"][:]
    random.shuffle(options)
    context.user_data["shuffled_options"] = options
    context.user_data["correct_answer"] = q["answer"]

    # Tugmalar
    keyboard = []
    for i, opt in enumerate(options):
        keyboard.append([InlineKeyboardButton(f"{['A', 'B', 'C', 'D'][i]}) {opt}", callback_data=f"ans_{i}")])

    category_emoji = "🇺🇿" if q["category"] == "uzbekistan" else "🌍"
    text = (
        f"{category_emoji} *{idx + 1}/{total}-savol*\n\n"
        f"❓ {q['question']}"
    )
    await query.edit_message_text(
        text,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

# ===================== JAVOB TEKSHIRISH =====================
async def handle_answer(query, context: ContextTypes.DEFAULT_TYPE):
    idx_str = query.data.replace("ans_", "")
    selected_idx = int(idx_str)
    options = context.user_data["shuffled_options"]
    selected = options[selected_idx]
    correct = context.user_data["correct_answer"]

    if selected == correct:
        context.user_data["score"] += 1
        result_text = f"✅ *To'g'ri!* \n\nJavob: *{correct}*"
    else:
        context.user_data["wrong"].append({
            "question": context.user_data["questions"][context.user_data["current"]]["question"],
            "your": selected,
            "correct": correct
        })
        result_text = f"❌ *Noto'g'ri!*\n\nSizning javobingiz: {selected}\n✅ To'g'ri javob: *{correct}*"

    context.user_data["current"] += 1
    total = len(context.user_data["questions"])
    current = context.user_data["current"]

    if current < total:
        keyboard = [[InlineKeyboardButton("➡️ Keyingi savol", callback_data="next_q")]]
        await query.edit_message_text(
            result_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
    else:
        # Test tugadi
        score = context.user_data["score"]
        context.user_data["last_score"] = score
        context.user_data["last_total"] = total
        percent = round((score / total) * 100)

        if percent >= 90:
            emoji, baho = "🏆", "A'lo"
        elif percent >= 70:
            emoji, baho = "👍", "Yaxshi"
        elif percent >= 50:
            emoji, baho = "😊", "Qoniqarli"
        else:
            emoji, baho = "📖", "Qoniqarsiz"

        result = (
            f"{emoji} *Test yakunlandi!*\n\n"
            f"📊 Natija: *{score}/{total}*\n"
            f"📈 Foiz: *{percent}%*\n"
            f"🎯 Baho: *{baho}*\n"
        )

        wrong = context.user_data.get("wrong", [])
        if wrong:
            result += f"\n❌ *Xato javoblar ({len(wrong)} ta):*\n"
            for i, w in enumerate(wrong[:5], 1):  # max 5 ta ko'rsatish
                result += f"\n{i}. {w['question']}\n   ✅ {w['correct']}\n"
            if len(wrong) > 5:
                result += f"\n...va yana {len(wrong)-5} ta xato"

        keyboard = [
            [InlineKeyboardButton("🔄 Qayta boshlash", callback_data="restart")],
            [InlineKeyboardButton("🏠 Bosh menyu", callback_data="back_main")],
        ]
        await query.edit_message_text(
            result,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )

async def next_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await send_question(query, context)

async def quick_test(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Tezkor /test buyrug'i"""
    pool = QUESTIONS
    selected = random.sample(pool, min(10, len(pool)))
    context.user_data["questions"] = selected
    context.user_data["current"] = 0
    context.user_data["score"] = 0
    context.user_data["wrong"] = []

    keyboard = []
    q = selected[0]
    options = q["options"][:]
    random.shuffle(options)
    context.user_data["shuffled_options"] = options
    context.user_data["correct_answer"] = q["answer"]

    for i, opt in enumerate(options):
        keyboard.append([InlineKeyboardButton(f"{['A', 'B', 'C', 'D'][i]}) {opt}", callback_data=f"ans_{i}")])

    category_emoji = "🇺🇿" if q["category"] == "uzbekistan" else "🌍"
    await update.message.reply_text(
        f"{category_emoji} *1/{len(selected)}-savol*\n\n❓ {q['question']}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text(
        "⛔ Test to'xtatildi.\n\n/start — Qayta boshlash uchun"
    )

# ===================== MAIN =====================
def main():
    # O'z TOKEN'ingizni shu yerga qo'ying
    TOKEN = "8615969282:AAE_CzyQ5GdwPzmWfomoxv15GRw005a31SM"

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("test", quick_test))
    app.add_handler(CommandHandler("stop", stop))
    app.add_handler(CallbackQueryHandler(next_question, pattern="^next_q$"))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🤖 Bot ishga tushdi...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
