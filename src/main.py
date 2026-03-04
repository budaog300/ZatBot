from dotenv import load_dotenv
import os
import time
import sys
import random
import re
import asyncio
import logging
import json
from pathlib import Path
from aiogram import Bot, Dispatcher, html
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
load_dotenv()

logger = logging.getLogger(__name__)
BOT_TOKEN = os.getenv("BOT_TOKEN")
SAVE_INTERVAL = 60
USERS_FILE = "users.json"

cons = ['б', 'в', 'г', 'д', 'ж', 'з', 'к', 'л', 'м', 'н', 'п', 'р', 'с', 'т', 'ф', 'х', 'ц', 'ч', 'ш', 'щ']
vowels = ['а', 'е', 'и', 'о', 'у', 'ы', 'э', 'ю', 'я']
prefixes = ["би", "пи", "ри", 'за', 'на']
dop_prefixes = ["гр", "р", "вр", "вз", "бр", "фр", "ср", "тр"]
two_symbols = ["нь", "бь", "дь", "мь", "зь", "фь", "ль"]
postfixes = ["я", "и"]
digital_words = ["84471", "7171", "6161", "6961", "7971"]
bad_words = ["Никита пидарас @Xonalz", "Антон жидкий @antonykozh", "У Антона спина белая @antonykozh", "Артура ебали @ArturBardur", "У Никикты говно в штанах @Xonalz", "Хуй", "Алмазный тунг тунг сахур", "Жопа"]

dp = Dispatcher()
active_chats = set()
last_save_time = time.time()


def load_users() -> dict:
    if Path(USERS_FILE).exists():
        try:
            with open(USERS_FILE, 'r', encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


users_cache = load_users()
users_cache_len = len(users_cache)


def save_user(user_data: dict):
    users = load_users()
    user_id = str(user_data["id"]) 
    if user_id not in users:
        with open(USERS_FILE, 'w', encoding="utf-8") as f:        
            users[user_id] = user_data
            json.dump(users, f, ensure_ascii=False, indent=2)


def collect_user(message):
    user = message.from_user
    user_id = str(user.id)
    if user_id not in users_cache:
        user_data = {
            'id': user.id,
            'username': user.username,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'language': user.language_code,
            'first_seen': str(message.date),
            'chat_id': message.chat.id,
            'chats': [message.chat.id]
        }
        users_cache[user_id] = user_data
    else:
        if message.chat.id not in users_cache[user_id]['chats']:
            users_cache[user_id]['chats'].append(message.chat.id)


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    Command /start
    """ 
    collect_user(message)
    chat_id = message.chat.id
    await message.answer(f"Привет, {html.bold(message.from_user.full_name)}! Бот запущен и готов!")   
    active_chats.add(chat_id)


@dp.message(Command("stop"))
async def command_stop_handler(message: Message):
    """
    Command /stop
    """
    chat_id = message.chat.id
    if chat_id in active_chats:
        active_chats.discard(chat_id)
        await message.answer(f"Бот остановлен! Для возобновления - напишите /start")
        logger.info(f"Бот остановлен в чате: {chat_id}")
    else:
        await message.answer("Бот молчит в этом чате!")   


def insult_call(user):
    name = user["first_name"]
    username = user["username"]
    facts = [
        f"🚨 ВНИМАНИЕ! 🚨\n\nПидарас найден -> {name} (@{username})",
        f"🚨 ЭКСТРЕННОЕ ОБЪЯВЛЕНИЕ! 🚨\n\nГлавный долбоёб этого чата — {name} (@{username})",
        f"🤡 ГЛАВНЫЙ ПЕТУХ ЧАТА 🤡\n\nПо результатам голосования побеждает {name} (@{username})! Поздравляем, ты сосал больше всех",
        f"💀 ТРАГЕДИЯ 💀\n\nУ {name} (@{username}) вместо мозгов — говно. Врачи разводят руками: 'Такое дерьмо мы видим впервые'",
        f"🏆 ПОЧЕТНОЕ ЗВАНИЕ 🏆\n\n{name} (@{username}) присвоено звание 'Заслуженный хуесос года'! Жена гордится, соседи завидуют",
        f"🧻 ТУАЛЕТНЫЕ ИСТОРИИ 🧻\n\n{name} (@{username}) сегодня не вытер жопу",
        f"🏆 ЗАСЛУЖЕННЫЙ ХУЙ 🏆\n\nПоздравляем {name} (@{username})! Ты выиграл хуй в рот. Носи с гордостью, мразь.",
        f"🚽 АНАЛЬНАЯ КАТАСТРОФА 🚽\n\nУ {name} (@{username}) сегодня праздник: он родился. Все остальные в ужасе, врачи в шоке, мать в слезах, что такое чудовище выжило.",
        f"💩 ГОВНОМЕС 💩\n\n{name} (@{username}) — бесполезный, вонючий и только место занимает, мудак.",
    ]
    return random.choice(facts)


@dp.message(Command("call"))
async def command_fact_handler(message: Message) -> None:
    """
    Command /call
    """   
    current_chat_id = message.chat.id 
    chat_users = []
    for user_id, user_data in users_cache.items():
        if current_chat_id in user_data.get('chats', []):
            chat_users.append(user_id)
    
    if not chat_users:
        await message.answer("Бот пока не знает о пользователях в этом чате, повзаимодействуйте с ним, пожалуйста!")
        return
       
    user_id = random.choice(chat_users)
    await message.answer(insult_call(users_cache[user_id]))


@dp.message()
async def collect_user_info(message: Message):
    collect_user(message)


async def collect_periodic_users():
    global users_cache_len
    global last_save_time
    while True:
        try:
            if users_cache and (time.time() - last_save_time) > SAVE_INTERVAL:
                with open(USERS_FILE, 'w', encoding='utf-8') as f:                   
                    json.dump(users_cache, f, ensure_ascii=False, indent=2)                    
                new_users = len(users_cache) - users_cache_len
                if new_users > 0:
                    logger.info(f"✅ +{new_users} новых юзеров")
                
                logger.info(f"💾 Всего в базе: {len(users_cache)}")
                users_cache_len = len(users_cache)
                last_save_time = time.time()            
            await asyncio.sleep(5)
        except Exception as e:
            logger.error(f"Ошибка сохранения: {e}")
            await asyncio.sleep(5)
        

def random_words():    
    pattern = fr"^[{''.join(cons)}][{''.join(vowels)}][{''.join(cons)}]ь$"    
    word = random.choice(cons) + random.choice(vowels) + random.choice(cons)

    r = random.random()
    if r < 0.01:
        word = random.choice(bad_words)
    elif r < 0.02:
        word = random.choice(digital_words)
    elif r < 0.03:
        word = random.choice(two_symbols)
    elif r < 0.1:
        word = random.choice(dop_prefixes) + word[1:] + 'ь'
    elif r < 0.15:
        word = random.choice(prefixes) + word + 'ь'
    elif r < 0.2:
        word += random.choice(postfixes)    
    else:
        word += 'ь'
    
    return word


async def periodic_messages_sender(bot: Bot):
    while True:
        try:
            if active_chats:
                for chat_id in list(active_chats):
                    try:
                        await bot.send_message(chat_id, random_words())    
                        await asyncio.sleep(3)
                    except Exception as e:
                        if "bot was blocked" in str(e).lower():
                            logger.warning(f"Бот заблокирован в чате {chat_id}, удаляю")
                            active_chats.discard(chat_id)
                        else:
                            logger.error(f'Ошибка отправки в {chat_id}: {e}')       
        except Exception as e:
            logger.error(f'Ошибка в sender: {e}')         
        finally:
            await asyncio.sleep(1800)


async def main():
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    asyncio.create_task(periodic_messages_sender(bot))
    asyncio.create_task(collect_periodic_users())
    logging.info("Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())