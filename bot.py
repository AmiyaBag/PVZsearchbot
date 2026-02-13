import os
import telebot
from dotenv import load_dotenv
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

load_dotenv()
TOKEN = os.getenv('BOT_TOKEN')
bot = telebot.TeleBot(TOKEN)

# ------------------------------------------------------------
# 1. Настройки пользователей (в памяти)
# ------------------------------------------------------------
user_settings = {}

def get_max_cell(chat_id):
    return user_settings.get(chat_id, {}).get("max_cell", 999)

def set_max_cell(chat_id, value):
    if chat_id not in user_settings:
        user_settings[chat_id] = {}
    user_settings[chat_id]["max_cell"] = value

# ------------------------------------------------------------
# 2. Переворот числа (180 градусов)
# ------------------------------------------------------------
ROTATE_DIGITS = {
    '0': '0',
    '1': '1',
    '6': '9',
    '8': '8',
    '9': '6'
}

def rotate_number(number):
    s = str(number)
    for ch in s:
        if ch not in ROTATE_DIGITS:
            return None
    rotated_digits = [ROTATE_DIGITS[ch] for ch in reversed(s)]
    rotated_str = ''.join(rotated_digits).lstrip('0')
    if rotated_str == '':
        return None
    return int(rotated_str)

# ------------------------------------------------------------
# 3. Словарь частых ошибок
# ------------------------------------------------------------
COMMON_MISTAKES = {
    '6': '9',
    '9': '6',
    '1': '7',
    '7': '1',
    '0': '8',
    '8': '0',
}

def apply_common_mistakes(number, max_cell):
    similar = set()
    num_str = str(number)

    for old_digit, new_digit in COMMON_MISTAKES.items():
        if old_digit in num_str:
            new_num_str = num_str.replace(old_digit, new_digit)
            new_num = int(new_num_str)
            if 1 <= new_num <= max_cell and new_num != number:
                similar.add(new_num)

    for old_digit, new_digit in COMMON_MISTAKES.items():
        if new_digit in num_str:
            new_num_str = num_str.replace(new_digit, old_digit)
            new_num = int(new_num_str)
            if 1 <= new_num <= max_cell and new_num != number:
                similar.add(new_num)

    return similar

# ------------------------------------------------------------
# 4. Генерация похожих номеров
# ------------------------------------------------------------
def generate_similar_numbers(number, max_cell):
    similar = set()
    num_str = str(number)
    length = len(num_str)

    # Замена одной цифры
    for i in range(length):
        for digit in '0123456789':
            if digit != num_str[i]:
                new_num_str = num_str[:i] + digit + num_str[i+1:]
                new_num = int(new_num_str)
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

    # Частые опечатки
    similar.update(apply_common_mistakes(number, max_cell))

    # Переворот
    rotated = rotate_number(number)
    if rotated is not None:
        if 1 <= rotated <= max_cell and rotated != number:
            similar.add(rotated)

    return sorted(similar)[:20]

# ------------------------------------------------------------
# 5. Клавиатура главного меню (reply-кнопки)
# ------------------------------------------------------------
def main_menu():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = KeyboardButton("🔍 Проверить ячейку")
    btn2 = KeyboardButton("⚙️ Установить максимум")
    btn3 = KeyboardButton("📏 Текущий максимум")
    btn4 = KeyboardButton("❓ Помощь")
    markup.add(btn1, btn2, btn3, btn4)
    return markup

# ------------------------------------------------------------
# 6. Команды и обработчики
# ------------------------------------------------------------
@bot.message_handler(commands=['start'])
def start(message):
    chat_id = message.chat.id
    welcome_text = (
        "Привет! Я помогу найти товар в похожих ячейках.\n\n"
        "**Как работать:**\n"
        "• Нажми кнопку «🔍 Проверить ячейку» и отправь номер.\n"
        "• Я покажу номера, которые легко перепутать:\n"
        "   — опечатки (одна неверная цифра)\n"
        "   — перестановка цифр\n"
        "   — частая путаница (6↔9, 1↔7 и т.п.)\n"
        "   — **стикер перевёрнут** (цифры вверх ногами)\n\n"
        "**Настройки:**\n"
        "• Кнопка «⚙️ Установить максимум» — задать максимальный номер ячейки на вашем складе.\n"
        "• Кнопка «📏 Текущий максимум» — показать текущий.\n\n"
    )
    bot.send_message(chat_id, welcome_text, parse_mode="Markdown", reply_markup=main_menu())

@bot.message_handler(commands=['setmax'])
def setmax_command(message):
    # Сохраняем состояние ожидания ввода нового максимума
    chat_id = message.chat.id
    msg = bot.send_message(chat_id, "🔢 Введите новый максимальный номер ячейки (например, 500):", reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, process_setmax)

def process_setmax(message):
    chat_id = message.chat.id
    try:
        value = int(message.text.strip())
        if 10 <= value <= 2000:
            set_max_cell(chat_id, value)
            bot.send_message(chat_id, f"✅ Максимальный номер ячейки установлен: **{value}**", parse_mode="Markdown", reply_markup=main_menu())
        else:
            bot.send_message(chat_id, "❓ Введите число от 10 до 2000.", reply_markup=main_menu())
    except ValueError:
        bot.send_message(chat_id, "❓ Это не число. Попробуйте снова через кнопку меню.", reply_markup=main_menu())

@bot.message_handler(commands=['showmax'])
def showmax_command(message):
    chat_id = message.chat.id
    max_cell = get_max_cell(chat_id)
    bot.send_message(chat_id, f"📏 Текущий максимум ячеек: **{max_cell}**", parse_mode="Markdown", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🔍 Проверить ячейку")
def ask_cell(message):
    chat_id = message.chat.id
    msg = bot.send_message(chat_id, "🔢 Введите номер ячейки, где должен быть товар, но его нет:", reply_markup=ReplyKeyboardRemove())
    bot.register_next_step_handler(msg, process_cell)

def process_cell(message):
    chat_id = message.chat.id
    text = message.text.strip()

    try:
        number = int(text)
    except ValueError:
        bot.send_message(chat_id, "❓ Пожалуйста, введите номер ячейки цифрами.", reply_markup=main_menu())
        return

    max_cell = get_max_cell(chat_id)
    if not (1 <= number <= max_cell):
        bot.send_message(chat_id, f"❓ Номер должен быть от 1 до {max_cell}.", reply_markup=main_menu())
        return

    similar = generate_similar_numbers(number, max_cell)

    if not similar:
        bot.send_message(chat_id, "😕 Похожих ячеек (в пределах максимума) не нашлось.", reply_markup=main_menu())
        return

    # Формируем ответ с невидимым символом перед каждым номером
    reply = f"🔍 **Возможно, товар в одной из этих ячеек:**\n"
    chunks = [similar[i:i+6] for i in range(0, len(similar), 6)]
    for chunk in chunks:
        line = "  ".join(f"\u200B{num}" for num in chunk)
        reply += line + "\n"

    rotated = rotate_number(number)
    if rotated is not None and rotated in similar:
        reply += "\n🔄 *Обратите внимание:* этот номер мог быть перевёрнут."

    bot.send_message(chat_id, reply, parse_mode="Markdown", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "⚙️ Установить максимум")
def setmax_button(message):
    setmax_command(message)

@bot.message_handler(func=lambda m: m.text == "📏 Текущий максимум")
def showmax_button(message):
    showmax_command(message)

@bot.message_handler(func=lambda m: m.text == "❓ Помощь")
def help_button(message):
    chat_id = message.chat.id
    help_text = (
        "❓ **Помощь по боту**\n\n"
        "🔍 **Проверить ячейку** — введи номер, и я покажу похожие варианты.\n"
        "⚙️ **Установить максимум** — задай максимальный номер ячейки на твоём складе.\n"
        "📏 **Текущий максимум** — показывает, какой максимум установлен сейчас.\n\n"
        "Если у тебя есть предложения или вопросы, пиши @твой\\_никнейм."
    )
    bot.send_message(chat_id, help_text, parse_mode="Markdown", reply_markup=main_menu())

@bot.message_handler(func=lambda m: True)
def fallback(message):
    # Если пользователь просто отправил текст (не нажимал кнопку), перенаправляем на проверку ячейки
    chat_id = message.chat.id
    # Пытаемся распознать число
    text = message.text.strip()
    try:
        number = int(text)
        # Если это число, обрабатываем как ячейку
        process_cell(message)
    except ValueError:
        # Иначе предлагаем меню
        bot.send_message(chat_id, "Пожалуйста, используй кнопки меню 👇", reply_markup=main_menu())

# После всех обработчиков, перед запуском:
if __name__ == "__main__":
    print("🚀 Бот запущен...")
    bot.remove_webhook()  # <-- добавляем эту строку
    bot.infinity_polling()