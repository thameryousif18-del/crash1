# -*- coding: utf-8 -*-
"""
بوت تلكرام لتحليل سلسلة أرقام (نتائج جولات) بناءً على 3 شروط:
1) آخر نتيجة بين 1.20 و 2.00
2) في آخر 7 جولات: أكثر تكرار مسموح لرقم 1.00 هو مرة واحدة
3) آخر نتيجتين لا تحتويان أي رقم أقل من 1.02
إذا تحققت كل الشروط -> يرسل 🟢
إذا فشل أي شرط -> يرسل 🔴

المتطلبات:
    pip install python-telegram-bot --break-system-packages

التشغيل:
    export BOT_TOKEN="ضع_توكن_البوت_هنا"
    python signal_bot.py
"""

import os
import logging
from collections import defaultdict, deque

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    MessageHandler,
    CommandHandler,
    filters,
)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# سجل منفصل لكل محادثة (chat_id) يحتفظ بآخر 7 نتائج فقط
history = defaultdict(lambda: deque(maxlen=7))

# ---------------------- منطق الشروط ----------------------

def check_conditions(results: list) -> tuple[bool, list]:
    """
    يتحقق من الشروط الثلاثة على قائمة النتائج (results[-1] هو آخر رقم مُرسل).
    يرجع (نجح_الكل: bool, تفاصيل: list[str])
    """
    details = []
    all_ok = True

    if not results:
        return False, ["لا توجد بيانات كافية بعد."]

    last = results[-1]

    # الشرط 1: آخر نتيجة بين 1.20 و 2.00
    cond1 = 1.20 <= last <= 2.00
    details.append(f"{'✅' if cond1 else '❌'} آخر نتيجة ({last}) بين 1.20 و2.00")
    all_ok &= cond1

    # الشرط 2: في آخر 7 جولات، تكرار الرقم 1.00 مرة واحدة كحد أقصى
    last_7 = results[-7:]
    count_1 = last_7.count(1.00)
    cond2 = count_1 <= 1
    details.append(f"{'✅' if cond2 else '❌'} تكرار 1.00 في آخر 7 جولات = {count_1} (الحد الأقصى مرة واحدة)")
    all_ok &= cond2

    # الشرط 3: آخر نتيجتين لا تحتويان أي رقم أقل من 1.02
    last_2 = results[-2:]
    cond3 = all(v >= 1.02 for v in last_2) if len(last_2) >= 1 else False
    if len(last_2) < 2:
        cond3 = False
        details.append("❌ لا توجد نتيجتان كافيتان بعد للتحقق من الشرط الثالث")
    else:
        details.append(
            f"{'✅' if cond3 else '❌'} آخر نتيجتين {last_2} لا تقل عن 1.02"
        )
    all_ok &= cond3

    return all_ok, details


# ---------------------- أوامر البوت ----------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    history[chat_id].clear()
    await update.message.reply_text(
        "أهلاً 👋\n"
        "أرسل لي الأرقام (النتائج) واحداً تلو الآخر (مثال: 1.35)\n"
        "وسأخبرك 🟢 أو 🔴 حسب الشروط المحددة.\n\n"
        "الأوامر:\n"
        "/reset - لمسح السجل والبدء من جديد\n"
        "/history - لعرض آخر الأرقام المسجلة"
    )


async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    history[chat_id].clear()
    await update.message.reply_text("تم مسح السجل ✅")


async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    data = list(history[chat_id])
    if not data:
        await update.message.reply_text("لا يوجد سجل بعد.")
    else:
        await update.message.reply_text("آخر النتائج: " + ", ".join(str(v) for v in data))


async def handle_number(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text = update.message.text.strip().replace(",", ".")

    try:
        value = float(text)
    except ValueError:
        await update.message.reply_text("من فضلك أرسل رقماً صحيحاً (مثال: 1.45)")
        return

    history[chat_id].append(value)
    results = list(history[chat_id])

    all_ok, details = check_conditions(results)

    signal = "🟢" if all_ok else "🔴"
    reply = (
        f"الرقم المستلم: {value}\n\n"
        + "\n".join(details)
        + f"\n\nالنتيجة النهائية: {signal}"
    )
    await update.message.reply_text(reply)


def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        raise SystemExit(
            "الرجاء تعيين متغير البيئة BOT_TOKEN بتوكن البوت أولاً.\n"
            "مثال: export BOT_TOKEN='123456:ABC-your-token'"
        )

    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("history", show_history))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_number))

    logger.info("البوت يعمل الآن...")
    app.run_polling()


if __name__ == "__main__":
    main()
