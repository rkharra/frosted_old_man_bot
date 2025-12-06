import asyncio

from aiogram import Bot, Dispatcher, types
from aiogram.filters.command import Command
from aiogram.filters.state import State, StatesGroup
from aiogram.utils.keyboard import ReplyKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram import F

import sqlite3

from config import TOKEN, GROUP_ID, DATABASE_NAME
from text import locale

# Объект бота
bot = Bot(token=TOKEN)
# Диспетчер
dp = Dispatcher()

# Состояния бота
class LetterStates(StatesGroup):
    waiting_for_letter = State()

# Инициализация базы
def init_database():
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS letters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            letter_text TEXT NOT NULL,
            UNIQUE(user_id)
        )
    ''')
    
    conn.commit()
    conn.close()

# Сохранение письма в базу данных
def save_letter(user_id: int, username: str, first_name: str, last_name: str, letter_text: str):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT OR REPLACE INTO letters 
            (user_id, username, first_name, last_name, letter_text)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, username, first_name, last_name, letter_text))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"Ошибка сохранения письма: {e}")
        return False
    finally:
        conn.close()

# Получение письма пользователя
def get_user_letter(user_id: int):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            SELECT letter_text
            FROM letters 
            WHERE user_id = ?
        ''', (user_id,))
        
        result = cursor.fetchone()
        return result[0]
    except Exception as e:
        print(f"Ошибка получения письма: {e}")
        return None
    finally:
        conn.close()

# Проверка наличия письма у пользователя
def has_letter(user_id: int) -> bool:
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    try:
        cursor.execute('SELECT 1 FROM letters WHERE user_id = ?', (user_id,))
        result = cursor.fetchone() is not None
        return result
    except Exception as e:
        print(f"Ошибка проверки письма: {e}")
        return False
    finally:
        conn.close()

# Удаление письма пользователя
def delete_letter(user_id: int) -> bool:
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    
    try:
        cursor.execute('DELETE FROM letters WHERE user_id = ?', (user_id,))
        conn.commit()
        return cursor.rowcount > 0
    except Exception as e:
        print(f"Ошибка удаления письма: {e}")
        return False
    finally:
        conn.close()

# Проверка группы
async def is_user_in_group(user_id: int) -> bool:
    try:
        chat_member = await bot.get_chat_member(GROUP_ID, user_id)
        return chat_member.status in ['member', 'administrator', 'creator']
    except Exception as e:
        print(f"Ошибка проверки пользователя в группе: {e}")
        return False
    
# Настройка клавиатуры
def get_main_keyboard(has_letter=False):
    builder = ReplyKeyboardBuilder()
    
    if not has_letter:
        builder.add(types.KeyboardButton(text=locale["write"]))
    else:
        builder.add(types.KeyboardButton(text=locale["read"]))
        builder.add(types.KeyboardButton(text=locale["edit"]))
    
    return builder.as_markup(resize_keyboard=True)

# Хэндлер на команду /start
@dp.message(Command("start", "help"))
async def cmd_start(message: types.Message):
    if message.chat.type != "private":
        return  # Игнорируем сообщения не из лички
    user_id = message.from_user.id
    # Проверка группы
    if not await is_user_in_group(user_id):
        await message.answer(locale["notmember"])
        return
    # Есть ли письмо
    user_has_letter = has_letter(user_id)
    await message.reply(locale["start"], reply_markup=get_main_keyboard(user_has_letter))


# Хэндлер на команду /say
@dp.message(Command("say"))
async def cmd_say(message: types.Message):
    if message.chat.type != "private":
        return  # Игнорируем сообщения не из лички
    user_id = message.from_user.id
    # Проверка группы
    if not await is_user_in_group(user_id):
        await message.answer(locale["notmember"])
        return
    
    text = ''
    try:
        text += message.text.split("/say ")[1]
        await bot.send_message(GROUP_ID, text)
    except:
        pass


# Обработчик кнопки "Написать письмо"
@dp.message(lambda message: message.text == locale["write"])
async def write_letter_start(message: types.Message, state: FSMContext):
    if message.chat.type != "private":
        return  # Игнорируем сообщения не из лички
    user_id = message.from_user.id
    # Проверка группы
    if not await is_user_in_group(user_id):
        await message.answer(locale["notmember"])
        return
    
    await message.answer(
        locale["editnow"],
        reply_markup=types.ReplyKeyboardRemove()
    )

    await state.set_state(LetterStates.waiting_for_letter)


# Обработка текста
@dp.message(LetterStates.waiting_for_letter)
async def letter(message: types.Message, state: FSMContext):
    if message.chat.type != "private":
        return  # Игнорируем сообщения не из лички
    user_id = message.from_user.id
    letter_text = message.text
    
    # Проверяем длину письма
    if len(letter_text) > 2000:
        await message.answer(locale["charlimit"])
        return
    
    # Сохраняем письмо в базу данных
    user = message.from_user
    success = save_letter(
        user_id=user_id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        letter_text=letter_text
    )
    
    if success:
        await state.clear()
        await message.answer(
            f"{locale['done']}{letter_text}",
            reply_markup=get_main_keyboard(has_letter=True)
        )
    else:
        await message.answer(locale["wrong"])

# Обработчик кнопки "Посмотреть письмо"
@dp.message(F.text == locale["read"])
async def view_letter(message: types.Message):
    if message.chat.type != "private":
        return  # Игнорируем сообщения не из лички
    user_id = message.from_user.id
    letter_data = get_user_letter(user_id)
    
    if not letter_data:
        await message.answer(locale["noletter"])
        return
    
    letter_text = letter_data
    
    response_text = (
        f'{locale["view"]}{letter_text}\n\n'
    )
    
    await message.answer(response_text, reply_markup=get_main_keyboard(has_letter=True))

# Обработчик кнопки "Переписать письмо"
@dp.message(lambda message: message.text == locale["edit"])
async def rewrite_letter_start(message: types.Message, state: FSMContext):
    if message.chat.type != "private":
        return  # Игнорируем сообщения не из лички
    user_id = message.from_user.id
    
    # Проверка группы
    if not await is_user_in_group(user_id):
        await message.answer(locale["notmember"])
        return
    
    await message.answer(
        locale["moretry"],
        reply_markup=types.ReplyKeyboardRemove()
    )
    
    await state.set_state(LetterStates.waiting_for_letter)



# Обработчик других сообщений
@dp.message()
async def handle_other_messages(message: types.Message):
    user_id = message.from_user.id
    if message.chat.type != "private":
        return  # Игнорируем сообщения не из лички
    # Проверка группы
    if not await is_user_in_group(user_id):
        await message.answer(locale["notmember"])
        return
    
    # Проверяем, есть ли уже письмо от пользователя
    user_has_letter = has_letter(user_id)
    
    await message.answer(
        locale["buttons"], reply_markup=get_main_keyboard(user_has_letter)
    )

# Запуск процесса поллинга новых апдейтов
async def main():
    init_database()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())