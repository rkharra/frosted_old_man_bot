import asyncio

from aiogram import Bot, Dispatcher

import sqlite3
import random

from config import TOKEN, GROUP_ID, DATABASE_NAME
from text import locale

# Объект бота
bot = Bot(token=TOKEN)
# Диспетчер
dp = Dispatcher()

def get_letters(db_path):
    raw = []
    
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    try:
        cursor.execute("SELECT * FROM letters")
        letters = [dict(row) for row in cursor.fetchall()]
        random.shuffle(letters)
    finally:
        conn.close()
    
    return letters

letters = get_letters('adm.db')

async def send_messages():
    for i,letter in enumerate(letters):
        try:
            await bot.send_message(chat_id=letters[i-1]["user_id"], text=letter["letter_text"])
        except:
            pass
        print(f'Письмо {letter["first_name"]} - переадресуется: {letters[i-1]["first_name"]}')

async def on_startup():
    print("Бот запущен!")
    await send_messages()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    dp.startup.register(on_startup)
    asyncio.run(main())