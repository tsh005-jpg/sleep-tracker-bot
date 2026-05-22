import telebot
from telebot import types
from datetime import datetime
import os
import config
from database.db_manager import init_db, end_sleep, get_user_history
from utils import generate_sleep_chart

bot = telebot.TeleBot(config.TOKEN)
init_db()

user_data = {}

def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn_add = types.KeyboardButton("📝 Добавить запись сна")
    btn_stats = types.KeyboardButton("📊 Статистика сна")
    markup.add(btn_add, btn_stats)
    return markup

def get_inline_keyboard(log_id):
    markup = types.InlineKeyboardMarkup()
    btn1 = types.InlineKeyboardButton("😊 Отлично", callback_data=f"feel_Good_{log_id}")
    btn2 = types.InlineKeyboardButton("😐 Нормально", callback_data=f"feel_Normal_{log_id}")
    btn3 = types.InlineKeyboardButton("🥱 Разбитый", callback_data=f"feel_Bad_{log_id}")
    markup.add(btn1, btn2, btn3)
    return markup

@bot.message_handler(commands=['start'])
def send_welcome(message):
    welcome_text = (
        f"Салам, {message.from_user.first_name}! 👋\n"
        "Я твой Ручной Трекер Сна.\n"
        "Вноси данные о своем отдыхе, а я построю аналитику и графики!\n\n"
        "Используй кнопки ниже:"
    )
    bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard())

@bot.message_handler(func=lambda message: True)
def handle_text_messages(message):
    user_id = message.from_user.id
    
    if message.text == "📝 Добавить запись сна":
        msg = bot.reply_to(
            message, 
            "Введи дату и время, когда ты **лег спать**.\n"
            "Формат: `ДД.ММ.ГГГГ ХХ:ММ` (например: `21.05.2026 23:00`):",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, process_bedtime)

    elif message.text == "📊 Статистика сна":
        history = get_user_history(user_id, limit=7)
        if not history:
            bot.reply_to(message, "У тебя пока нет записей сна. Нажми 'Добавить запись сна'! 😉")
            return
            
        stat_text = "📊 Твои последние записи сна:\n\n"
        for row in history:
            bed, wake, dur, feel = row
            stat_text += f"📅 {bed[5:16]} ➡️ {wake[5:16]}\n⏱ Длительность: {dur} ч. | Чувство: {feel}\n\n"
            
        bot.send_message(message.chat.id, stat_text)
        bot.send_message(message.chat.id, "Генерирую график твоего режима... ⏳")
        
        try:
            chart_path = generate_sleep_chart(history, user_id)
            with open(chart_path, 'rb') as photo:
                bot.send_photo(message.chat.id, photo, caption="📈 Твой график сна за неделю.")
            os.remove(chart_path)
        except Exception as e:
            bot.send_message(message.chat.id, f"⚠️ Не удалось построить график, но данные сохранены!")

    else:
        bot.reply_to(message, "Я тебя не понял 🤖 Используй кнопки на клавиатуре.")

def process_bedtime(message):
    try:
        user_id = message.from_user.id
        bedtime = datetime.strptime(message.text.strip(), "%d.%m.%Y %H:%M")
        user_data[user_id] = {'bedtime': bedtime}
        
        msg = bot.reply_to(
            message, 
            "Отлично! Теперь введи дату и время, когда ты **проснулся**.\n"
            "Формат такой же: `ДД.ММ.ГГГГ ХХ:ММ` (например: `22.05.2026 07:30`):",
            parse_mode="Markdown"
        )
        bot.register_next_step_handler(msg, process_wakeup)
    except ValueError:
        msg = bot.reply_to(message, "❌ Неверный формат! Попробуй еще раз. Пиши строго как в примере: `21.05.2026 23:00`")
        bot.register_next_step_handler(msg, process_bedtime)

def process_wakeup(message):
    try:
        user_id = message.from_user.id
        wakeup_time = datetime.strptime(message.text.strip(), "%d.%m.%Y %H:%M")
        bedtime = user_data[user_id]['bedtime']
        
        if wakeup_time <= bedtime:
            msg = bot.reply_to(message, "❌ Время просыпания не может быть раньше или равно времени засыпания! Введи время просыпания еще раз:")
            bot.register_next_step_handler(msg, process_wakeup)
            return

        duration = round((wakeup_time - bedtime).total_seconds() / 3600, 2)
        bedtime_str = bedtime.strftime("%Y-%m-%d %H:%M:%S")
        wakeup_str = wakeup_time.strftime("%Y-%m-%d %H:%M:%S")
        
        import sqlite3
        conn = sqlite3.connect("sleep_tracker.db")
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO sleep_logs (user_id, bedtime, wakeup_time, duration, feeling, status)
            VALUES (?, ?, ?, ?, 'Не указано', 'completed')
        ''', (user_id, bedtime_str, wakeup_str, duration))
        log_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        reply_msg = f"✅ Запись успешно добавлена!\n⏱ Длительность сна: {duration} ч.\n\nКак ты себя чувствуешь?"
        bot.send_message(message.chat.id, reply_msg, reply_markup=get_inline_keyboard(log_id))
        
        if user_id in user_data:
            del user_data[user_id]
            
    except ValueError:
        msg = bot.reply_to(message, "❌ Неверный формат! Попробуй еще раз. Пиши строго как в примере: `22.05.2026 07:30`")
        bot.register_next_step_handler(msg, process_wakeup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('feel_'))
def handle_feeling_callback(call):
    _, status, log_id = call.data.split('_')
    feelings = {"Good": "😊 Отлично", "Normal": "😐 Нормально", "Bad": "🥱 Разбитый"}
    chosen_feeling = feelings.get(status, "Не указано")
    
    import sqlite3
    conn = sqlite3.connect("sleep_tracker.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE sleep_logs SET feeling = ? WHERE id = ?", (chosen_feeling, int(log_id)))
    conn.commit()
    conn.close()
    
    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text=f"{call.message.text}\n\nТвое самочувствие: {chosen_feeling} записано! Трэкер обновлен."
    )
    # Вот эта строчка автоматически возвращает главные кнопки в чат:
    bot.send_message(call.message.chat.id, "Вы вернулись в главное меню. Что делаем дальше?", reply_markup=get_main_keyboard())
    bot.answer_callback_query(call.id)

if __name__ == "__main__":
    print("Бот успешно запущен и слушает команды...")
    bot.infinity_polling()