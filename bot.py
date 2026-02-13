import os
import telebot
from flask import Flask, request
import time

# ---------- НАСТРОЙКИ ----------
TOKEN = os.getenv('BOT_TOKEN')
if not TOKEN:
    raise ValueError("❌ Переменная окружения BOT_TOKEN не задана!")

# URL для вебхука (задаётся в переменной окружения на хостинге)
WEBHOOK_URL = "https://bot_1770985044_4041_amiyabag.bothost.ru"

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

# ---------- ХРАНЕНИЕ НАСТРОЕК ПОЛЬЗОВАТЕЛЕЙ (в памяти) ----------
user_settings = {}

def get_max_cell(chat_id):
    return user_settings.get(chat_id, {}).get("max_cell", 999)

def set_max_cell(chat_id, value):
    if chat_id not in user_settings:
        user_settings[chat_id] = {}
    user_settings[chat_id]["max_cell"] = value

# ---------- ЛОГИКА ГЕНЕРАЦИИ ПОХОЖИХ НОМЕРОВ ----------
ROTATE_DIGITS = {'0': '0', '1': '1', '6': '9', '8': '8', '9': '6'}
COMMON_MISTAKES = {'6': '9', '9': '6', '1': '7', '7': '1', '0': '8', '8': '0'}

def rotate_number(number):
    s = str(number)
    for ch in s:
        if ch not in ROTATE_DIGITS:
            return None
    rotated = ''.join(ROTATE_DIGITS[ch] for ch in reversed(s)).lstrip('0')
    return int(rotated) if rotated else None

def apply_common_mistakes(number, max_cell):
    similar = set()
    num_str = str(number)
    for old_digit, new_digit in COMMON_MISTAKES.items():
        if old_digit in num_str:
            new_num = int(num_str.replace(old_digit, new_digit))
            if 1 <= new_num <= max_cell and new_num != number:
                similar.add(new_num)
        if new_digit in num_str:
            new_num = int(num_str.replace(new_digit, old_digit))
            if 1 <= new_num <= max_cell and new_num != number:
                similar.add(new_num)
    return similar

def generate_similar_numbers(number, max_cell):
    similar = set()
    num_str = str(number)
    length = len(num_str)

    # Замена одной цифры
    for i in range(length):
        for d in '0123456789':
            if d != num_str[i]:
                new_num = int(num_str[:i] + d + num_str[i+1:])
                if 1 <= new_num <= max_cell and new_num != number:
                    similar.add(new_num)

    # Перестановка двух цифр
    for i in range(length):
        for j in range(i+1, length):
            lst = list(num_str)
            lst[i], lst[j] = lst[j], lst[i]
            new_num = int(''.join(lst))
            if 1 <= new_num <= max_cell and new_num != number:
                similar.add(new_num)

    # Частые ошибки
    similar.update(apply_common_mistakes(number, max_cell))

    # Переворот
    rotated = rotate_number(number)
    if rotated and 1 <= rotated <= max_cell and rotated != number:
        similar.add(rotated)

    return sorted(similar)[:20]

# ---------- КЛАВИАТУРА ----------
def main_menu():
    from telebot.types import ReplyKeyboardMarkup, KeyboardButton
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        KeyboardButton("🔍 Проверить ячейку"),
        KeyboardButton("⚙️ Установить максимум"),
        KeyboardButton("📏 Текущий максимум"),
        KeyboardButton("❓ Помощь")
    )
    return markup

# ---------- ОБРАБОТЧИКИ КОМАНД ----------
@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(
        message.chat.id,
        "👋 Привет! Я помогу найти товар в похожих ячейках.\n\n"
        "📌 **Как работать:**\n"
        "• Нажми кнопку «🔍 Проверить ячейку» и отправь номер.\n"
        "• Я покажу номера, которые легко перепутать:\n"
        "   — опечатки (одна неверная цифра)\n"
        "   — перестановка цифр\n"
        "   — частая путаница (6↔9, 1↔7 и т.п.)\n"
        "   — **стикер перевёрнут** (цифры вверх ногами)\n\n"
        "⚙️ **Настройки:**\n"
        "• Кнопка «⚙️ Установить максимум» — задать максимальный номер.\n"
        "• Кнопка «📏 Текущий максимум» — показать текущий.",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )

@bot.message_handler(func=lambda m: m.text == "🔍 Проверить ячейку")
def ask_cell(message):
    msg = bot.send_message(
        message.chat.id,
        "🔢 Введите номер ячейки, где должен быть товар, но его нет:",
        reply_markup=telebot.types.ReplyKeyboardRemove()
    )
    bot.register_next_step_handler(msg, process_cell)

def process_cell(message):
    chat_id = message.chat.id
    try:
        number = int(message.text.strip())
    except ValueError:
        bot.send_message(chat_id, "❓ Введите число.", reply_markup=main_menu())
        return

    max_cell = get_max_cell(chat_id)
    if not (1 <= number <= max_cell):
        bot.send_message(chat_id, f"❓ Номер должен быть от 1 до {max_cell}.", reply_markup=main_menu())
        return

    similar = generate_similar_numbers(number, max_cell)

    if not similar:
        bot.send_message(chat_id, "😕 Похожих ячеек не нашлось.", reply_markup=main_menu())
        return

    reply = "🔍 **Возможно, товар в одной из этих ячеек:**\n"
    chunks = [similar[i:i+6] for i in range(0, len(similar), 6)]
    for chunk in chunks:
        reply += "  ".join(f"\u200B{num}" for num in chunk) + "\n"

    if rotate_number(number) in similar:
        reply += "\n🔄 *Возможно, номер был перевёрнут.*"

    bot.send_message(chat_id, reply, parse_mode="Markdown", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "⚙️ Установить максимум")
def ask_setmax(message):
    msg = bot.send_message(
        message.chat.id,
        "🔢 Введите новый максимальный номер ячейки (например, 500):",
        reply_markup=telebot.types.ReplyKeyboardRemove()
    )
    bot.register_next_step_handler(msg, process_setmax)

def process_setmax(message):
    chat_id = message.chat.id
    try:
        value = int(message.text.strip())
        if 10 <= value <= 2000:
            set_max_cell(chat_id, value)
            bot.send_message(chat_id, f"✅ Максимум установлен: {value}", reply_markup=main_menu())
        else:
            bot.send_message(chat_id, "❓ Введите число от 10 до 2000.", reply_markup=main_menu())
    except ValueError:
        bot.send_message(chat_id, "❓ Это не число.", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "📏 Текущий максимум")
def show_max(message):
    max_cell = get_max_cell(message.chat.id)
    bot.send_message(message.chat.id, f"📏 Текущий максимум: {max_cell}", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "❓ Помощь")
def help(message):
    bot.send_message(
        message.chat.id,
        "❓ **Помощь**\n\n"
        "🔍 **Проверить ячейку** — введите номер, я покажу похожие.\n"
        "⚙️ **Установить максимум** — задайте максимальный номер.\n"
        "📏 **Текущий максимум** — показывает текущий.",
        parse_mode="Markdown",
        reply_markup=main_menu()
    )

# ---------- ВЕБХУК ----------
@app.route('/webhook', methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return 'OK', 200

@app.route('/set_webhook')
def set_webhook():
    bot.remove_webhook()
    time.sleep(0.5)
    bot.set_webhook(url=WEBHOOK_URL + '/webhook')
    return f"✅ Webhook set to {WEBHOOK_URL}/webhook", 200

@app.route('/')
def index():
    return 'Бот работает!', 200

# ---------- ЗАПУСК ----------
if __name__ == '__main__':
    print("🚀 Запуск бота в режиме polling...")
    bot.remove_webhook()  # обязательно удаляем вебхук, если вдруг остался
    bot.infinity_polling()