from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler
import sqlite3
import logging
import os
from datetime import datetime

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Define states for the conversation
CHOOSING, TYPING_HABIT, TYPING_TIME = range(3)


def create_db():
    conn = sqlite3.connect('habits.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS habits (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        habit_name TEXT,
        reminder_time TEXT)
    ''')
    conn.commit()
    conn.close()


def add_habit(user_id, habit_name, reminder_time):
    conn = sqlite3.connect('habits.db')
    c = conn.cursor()
    c.execute('INSERT INTO habits (user_id, habit_name, reminder_time) VALUES (?, ?, ?)',
              (user_id, habit_name, reminder_time))
    conn.commit()
    conn.close()


def delete_habit(user_id, habit_name):
    conn = sqlite3.connect('habits.db')
    c = conn.cursor()
    c.execute('DELETE FROM habits WHERE user_id = ? AND habit_name = ?', (user_id, habit_name))
    conn.commit()
    conn.close()


def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        "Привет! Я бот для отслеживания привычек.\n"
        "Используйте /add, чтобы добавить привычку.\n"
        "Используйте /delete, чтобы удалить привычку.\n"
        "Просто следуйте инструкциям!"
    )


def start_add(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("Напишите привычку, которую хотите добавить.")
    return TYPING_HABIT


def receive_habit(update: Update, context: CallbackContext) -> int:
    context.user_data['habit'] = update.message.text
    update.message.reply_text("Введите время (в формате ЧЧ:MM).")
    return TYPING_TIME


def receive_time(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    habit = context.user_data['habit']
    time = update.message.text

    # Validate time format
    try:
        hour, minute = map(int, time.split(':'))
        if hour < 0 or hour > 23 or minute < 0 or minute > 59:
            raise ValueError
    except ValueError:
        update.message.reply_text("Неверный формат времени. Используйте ЧЧ:MM, например 13:00.")
        return TYPING_TIME

    # Add the habit to the database
    add_habit(user_id, habit, time)
    update.message.reply_text(f"Привычка '{habit}' добавлена с напоминанием в {time}.")

    return ConversationHandler.END


def start_delete(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("Напишите привычку, которую хотите удалить.")
    return TYPING_HABIT


def receive_delete_habit(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    habit = update.message.text
    delete_habit(user_id, habit)
    update.message.reply_text(f"Привычка '{habit}' удалена.")

    return ConversationHandler.END


def main():
    create_db()
    TOKEN = '7589783069:AAEwJrXS1XGNMIkEkNxydpDDR_bz6Ii894s'  # Замените на ваш токен бота, используя переменные окружения


    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    # Register the /start command
    dispatcher.add_handler(CommandHandler('start', start))

    # Set up the conversation handler for adding habits
    add_handler = ConversationHandler(
        entry_points=[CommandHandler('add', start_add)],
        states={
            TYPING_HABIT: [MessageHandler(Filters.text & ~Filters.command, receive_habit)],
            TYPING_TIME: [MessageHandler(Filters.text & ~Filters.command, receive_time)],
        },
        fallbacks=[],
    )

    # Set up the conversation handler for deleting habits
    delete_handler = ConversationHandler(
        entry_points=[CommandHandler('delete', start_delete)],
        states={
            TYPING_HABIT: [MessageHandler(Filters.text & ~Filters.command, receive_delete_habit)],
        },
        fallbacks=[],
    )

    # Register handlers
    dispatcher.add_handler(add_handler)
    dispatcher.add_handler(delete_handler)

    # Start the bot
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()