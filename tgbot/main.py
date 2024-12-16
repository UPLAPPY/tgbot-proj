from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler
import sqlite3

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

def get_user_habits(user_id):
    conn = sqlite3.connect('habits.db')
    c = conn.cursor()
    c.execute('SELECT habit_name FROM habits WHERE user_id = ?', (user_id,))
    habits = c.fetchall()
    conn.close()
    return [habit[0] for habit in habits]

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

    hour, minute = map(int, time.split(':'))
    add_habit(user_id, habit, time)
    update.message.reply_text(f"Привычка '{habit}' добавлена с напоминанием в {time}.")
    return ConversationHandler.END

def start_delete(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    habits = get_user_habits(user_id)

    if not habits:
        update.message.reply_text("У вас нет привычек для удаления.")
        return ConversationHandler.END

    habits_list = "\n".join(habits)
    update.message.reply_text(f"Ваши привычки:\n{habits_list}\n\nНапишите привычку, которую хотите удалить.")
    return TYPING_HABIT

def receive_delete_habit(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    habit = update.message.text

    if habit in get_user_habits(user_id):
        delete_habit(user_id, habit)
        update.message.reply_text(f"Привычка '{habit}' удалена.")
    else:
        update.message.reply_text(f"Привычка '{habit}' не найдена. Пожалуйста, проверьте название.")

    return ConversationHandler.END

def main():
    create_db()
    TOKEN = '7589783069:AAEwJrXS1XGNMIkEkNxydpDDR_bz6Ii894s'

    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher

    dispatcher.add_handler(CommandHandler('start', start))

    add_handler = ConversationHandler(
        entry_points=[CommandHandler('add', start_add)],
        states={
            TYPING_HABIT: [MessageHandler(Filters.text & ~Filters.command, receive_habit)],
            TYPING_TIME: [MessageHandler(Filters.text & ~Filters.command, receive_time)],
        },
        fallbacks=[],
    )

    delete_handler = ConversationHandler(
        entry_points=[CommandHandler('delete', start_delete)],
        states={
            TYPING_HABIT: [MessageHandler(Filters.text & ~Filters.command, receive_delete_habit)],
        },
        fallbacks=[],
    )

    dispatcher.add_handler(add_handler)
    dispatcher.add_handler(delete_handler)

    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()