from config import TOKEN
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext, ConversationHandler
import firebase_admin
from firebase_admin import credentials, firestore
from datetime import time
import re

cred = credentials.Certificate("habbitstgbot-firebase-adminsdk-fbsvc-c0dee5c521.json")
firebase_admin.initialize_app(cred)

db = firestore.client()

CHOOSING, TYPING_HABIT, TYPING_TIME = range(3)

def is_valid_time(time_str):
    pattern = re.compile(r"^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$")
    return bool(pattern.match(time_str))

def add_habit(user_id, habit_name, reminder_time):
    doc_ref = db.collection('habits').document(str(user_id))
    doc_ref.set({
        habit_name: reminder_time
    }, merge=True)

def delete_habit(user_id, habit_name):
    doc_ref = db.collection('habits').document(str(user_id))
    doc_ref.update({
        habit_name: firestore.DELETE_FIELD
    })

def get_user_habits(user_id):
    doc_ref = db.collection('habits').document(str(user_id))
    doc = doc_ref.get()
    if doc.exists:
        return doc.to_dict()
    return {}

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        "Привет! Я бот для отслеживания привычек.\n"
        "Используйте /add, чтобы добавить привычку.\n"
        "Используйте /delete, чтобы удалить привычку.\n"
        "Используйте /list, чтобы посмотреть список ваших привычек.\n"
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
    time_str = update.message.text

    if not is_valid_time(time_str):
        update.message.reply_text("Некорректный формат времени. Пожалуйста, введите время в формате ЧЧ:MM.")
        return TYPING_TIME

    add_habit(user_id, habit, time_str)

    hour, minute = map(int, time_str.split(':'))
    context.job_queue.run_daily(
        send_reminder,
        time=time(hour=hour - 3, minute=minute),
        days=(0, 1, 2, 3, 4, 5, 6),
        context=(user_id, habit),
    )

    update.message.reply_text(f"Привычка '{habit}' добавлена с напоминанием в {time_str}.")
    return ConversationHandler.END

def send_reminder(context: CallbackContext):
    user_id, habit = context.job.context
    context.bot.send_message(chat_id=user_id, text=f"⏰ Напоминание: время выполнить привычку '{habit}'!")

def start_delete(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    habits = get_user_habits(user_id)

    if not habits:
        update.message.reply_text("У вас нет привычек для удаления.")
        return ConversationHandler.END

    habits_list = "\n".join(habits.keys())
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

def list_habits(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    habits = get_user_habits(user_id)

    if not habits:
        update.message.reply_text("У вас пока нет привычек.")
    else:
        habits_list = "\n".join([f"{habit} в {time}" for habit, time in habits.items()])
        update.message.reply_text(f"Ваши привычки:\n{habits_list}")

def main():
    token = TOKEN
    updater = Updater(token, use_context=True)
    dispatcher = updater.dispatcher
    job_queue = updater.job_queue

    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('list', list_habits))

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