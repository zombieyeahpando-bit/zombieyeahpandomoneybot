import datetime
import telebot
import os
from telebot import types

# Сервер сам возьмет токен из настроек, которые ты впишешь на сайте Render
TOKEN = os.environ.get('TOKEN')
bot = telebot.TeleBot(TOKEN)

# Временная база данных в памяти бота
user_data = {}

# Словарь для перевода месяцев на русский язык
RU_MONTHS = {
    1: "января", 2: "февраля", 3: "марта", 4: "апреля", 5: "мая", 6: "июня",
    7: "июля", 8: "августа", 9: "сентября", 10: "октября", 11: "ноября", 12: "декабря"
}

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    chat_id = message.chat.id
    user_data[chat_id] = {}
    
    welcome_text = (
        "👋 Привет! Я твой продвинутый financial тренер.\n\n"
        "Давай настроим твою систему ватерлинии.\n"
        "1️⃣ Напиши дату твоей следующей зарплаты в формате ДД.ММ.ГГГГ\n"
        "*(Например: 15.07.2026)*"
    )
    msg = bot.send_message(chat_id, welcome_text, parse_mode='Markdown')
    bot.register_next_step_handler(msg, process_date_step)

def process_date_step(message):
    chat_id = message.chat.id
    
    if message.text.strip() == '/start':
        send_welcome(message)
        return
        
    try:
        target_date = datetime.datetime.strptime(message.text.strip(), "%d.%m.%Y").date()
        
        # ВОТ ЭТОЙ СТРОЧКИ НЕ ХВАТАЛО (ЧИНИМ БАГ):
        today = datetime.date.today()
        
        if target_date <= today:
            msg = bot.reply_to(message, "❌ Дата зарплаты должна быть в будущем! Попробуй еще раз (ДД.ММ.ГГГГ):")
            bot.register_next_step_handler(msg, process_date_step)
            return
            
        user_data[chat_id]['target_date'] = target_date
        
        msg = bot.send_message(chat_id, "2️⃣ Отлично! Теперь введи текущую сумму на твоей карте (в рублях):")
        bot.register_next_step_handler(msg, process_amount_step)
    except ValueError:
        msg = bot.reply_to(message, "❌ Неверный формат даты. Напиши, например, 15.07.2026 :")
        bot.register_next_step_handler(msg, process_date_step)

def process_amount_step(message):
    chat_id = message.chat.id
    
    if message.text.strip() == '/start':
        send_welcome(message)
        return
        
    try:
        amount_text = message.text.replace(",", ".")
        start_sum = float(amount_text)
        
        user_data[chat_id]['start_sum'] = start_sum
        user_data[chat_id]['start_date'] = datetime.date.today()
        
        target_date = user_data[chat_id]['target_date']
        start_date = user_data[chat_id]['start_date']
        
        total_days = (target_date - start_date).days
        if total_days == 0: total_days = 1
        
        daily_limit = round(start_sum / total_days, 2)
        user_data[chat_id]['daily_limit'] = daily_limit
        
        success_text = (
            "🎉 *Система успешно настроена!*\n\n"
            f"📅 Зарплата: *{target_date.strftime('%d.%m.%Y')}*\n"
            f"💰 Стартовый баланс: *{start_sum} BYN*\n"
            f"⏳ Дней до ЗП (включая сегодня): *{total_days}*\n"
            f"📈 Твой дневной лимит: *{daily_limit} BYN/день*\n\n"
            "👉 Теперь в любой момент просто *отправь мне текущий баланс карты*, и я выдам тебе отчет!"
        )
        bot.send_message(chat_id, success_text, parse_mode='Markdown')
        
    except ValueError:
        msg = bot.reply_to(message, "❌ Вводи только числа. Сколько сейчас на карте (например, 590)?")
        bot.register_next_step_handler(msg, process_amount_step)

@bot.message_handler(func=lambda message: True)
def check_balance(message):
    chat_id = message.chat.id
    
    if chat_id not in user_data or 'target_date' not in user_data[chat_id]:
        bot.reply_to(message, "⚙️ Сначала нажми /start, чтобы настроить свои даты и баланс!")
        return
        
    today = datetime.date.today()
    target_date = user_data[chat_id]['target_date']
    daily_limit = user_data[chat_id]['daily_limit']
    
    if today > target_date:
        bot.reply_to(message, "🎉 Срок текущего бюджета истек! Нажми /start, чтобы задать новые параметры для следующей зарплаты.")
        return
    elif today == target_date:
        bot.reply_to(message, "💰 Сегодня день твоей зарплаты! Время обнуления баланса 50/50 и перезапуска бота через /start!")
        return

    try:
        user_text = message.text.replace(",", ".")
        current_balance = float(user_text)
        
        days_left_today = (target_date - today).days
        ideal_balance_today = round(days_left_today * daily_limit, 2)
        
        tomorrow = today + datetime.timedelta(days=1)
        days_left_tomorrow = (target_date - tomorrow).days
        ideal_balance_tomorrow = round(days_left_tomorrow * daily_limit, 2)
        
        diff = round(current_balance - ideal_balance_today, 2)
        
        # Делаем красивую русскую дату (например: 27 июня)
        ru_date_str = f"{today.day} {RU_MONTHS[today.month]}"
        
        response = f"📅 *Сегодня:* {ru_date_str} (Осталось дней: {days_left_today})\n"
        response += f"📉 *Ватерлиния на ЭТОТ вечер:* {ideal_balance_today} BYN\n"
        response += "—" * 15 + "\n"
        
        if diff >= 0:
            response += f"🟢 *ЗЕЛЕНАЯ ЗОНА!*\nТы выше линии на *+{diff} BYN*!\n"
            response += "🚀 Смело закидывай 5 BYN и 5$ в копилки!\n\n"
        else:
            response += f"🔴 *КРАСНАЯ ЗОНА!*\nТы ниже линии на *{abs(diff)} BYN*!\n"
            response += "🛑 Сегодня без копилок, режим экономии.\n\n"
            
        response += "—" * 15 + "\n"
        response += f"🔮 *Прогноз на завтра ({tomorrow.strftime('%d.%m')}):*\n"
        response += f"💵 Твой чистый лимит на день: *{daily_limit} BYN*\n"
        response += f"🛡️ Ватерлиния на ЗАВТРАШНИЙ вечер: *{ideal_balance_tomorrow} BYN*\n"
        response += "_(Если за сегодня потратишь ровно лимит, завтра будешь четко в графике!)_"
        
        bot.reply_to(message, response, parse_mode='Markdown')
        
    except ValueError:
        bot.reply_to(message, "❌ Отправь мне просто число текущего баланса карты (например: 420.50)")

if __name__ == '__main__':
    print("🤖 Прокачанный бот успешно запущен!")
    bot.infinity_polling()
