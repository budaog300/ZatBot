from dotenv import load_dotenv
from functools import wraps
from typing import Callable
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
BOT_USERNAME = "batzatbot"
SAVE_INTERVAL = 60
USERS_FILE = "users.json"
CHATS_FILE = "chats.json"
FACTS_FILE = "facts.json"
BAD_WORDS_FILE = "bad_words.json"

cons = ['б', 'в', 'г', 'д', 'ж', 'з', 'к', 'л', 'м', 'н', 'п', 'р', 'с', 'т', 'ф', 'х', 'ц', 'ч', 'ш', 'щ']
vowels = ['а', 'е', 'и', 'о', 'у', 'ы', 'э', 'ю', 'я']
prefixes = ["би", "пи", "ри", 'за', 'на']
dop_prefixes = ["гр", "р", "вр", "вз", "бр", "фр", "ср", "тр"]
two_symbols = ["нь", "бь", "дь", "мь", "зь", "фь", "ль"]
postfixes = ["я", "и"]
digital_words = ["84471", "7171", "6161", "6961", "7971"]
swear_shards = ["ебл", "пидо", "пидар", "хуй", "пизд", "тупой", "дура", "кончен", "гондон", "шлюх", "суки", "сука", "уебище"]

dp = Dispatcher()
last_save_time = time.time()


def load_data(file) -> dict:
    if Path(file).exists():
        try:
            with open(file, 'r', encoding="utf-8") as f:
                data = json.load(f)
                return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_chats():
    try:
        with open(CHATS_FILE, 'w', encoding='utf-8') as f:
            json.dump({"active_chats": list(active_chats)}, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Ошибка сохранения чатов: {e}")


users_cache = load_data(USERS_FILE)
users_cache_len = len(users_cache)
active_chats_dict = load_data(CHATS_FILE)
active_chats = set(active_chats_dict.get("active_chats", []))
facts = load_data(FACTS_FILE)
bad_words = load_data(BAD_WORDS_FILE)


@dp.message(CommandStart())
async def command_start_handler(message: Message) -> None:
    """
    Command /start
    """     
    chat_id = message.chat.id
    await message.answer(f"Привет, {html.bold(message.from_user.full_name)}! Бот запущен и готов!")
    active_chats.add(chat_id)  
    save_chats()


@dp.message(Command("stop"))
async def command_stop_handler(message: Message):
    """
    Command /stop
    """
    chat_id = message.chat.id
    if chat_id in active_chats:
        active_chats.discard(chat_id)
        save_chats()
        await message.answer(f"Бот остановлен! Для возобновления - напишите /start")
        logger.info(f"Бот остановлен в чате: {chat_id}")
    else:
        await message.answer("Бот молчит в этом чате!")   


def insult_call(user):
    name = user["first_name"]
    username = user["username"]    
    return random.choice(facts["facts"]).format(name=name, username=username)


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


def collect_user(message: Message):
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


def random_answer(message: Message):
    if message.text and not message.text.startswith('/') and not message.from_user.is_bot:        
        if '?' in message.text:
            if random.random() < 0.7:
                answers = [
                    "А сам как думаешь?",
                    "Хуй его знает",                   
                    "Спроси у мамы",
                    "42",
                    "52",
                    "67",
                    "Гугли, чё",
                    "Ты у кого спрашиваешь?",
                    "🤷‍♂️"
                ]
                return random.choice(answers)                
        elif f"@{BOT_USERNAME}" in message.text:
            return "Че надо?"
    return None
        

def swear_answer(message: Message):
    if message.text and not message.text.startswith("/") and not message.from_user.is_bot:
        if any(swear in message.text for swear in swear_shards):
            if random.random() < 0.5:
                answers = [
                        "Нахуй ты ругаешься?",
                        "Ты еблан тупой!",                  
                        "Пошел ты нахуй!",
                        "Похуй ваще...",
                        "Ты пидр",
                        "Антон шл**а",
                        "Д пошли вы нахуй!"
                    ]
                return random.choice(answers)
    return None
                    

@dp.message()
async def handle_all_messages(message: Message):
    collect_user(message)

    question_reply = random_answer(message)
    if question_reply:
        await message.reply(question_reply)
        return
      
    swear_reply = swear_answer(message)
    if swear_reply:
        await message.reply(swear_reply)
        return


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
        

def random_words(chat_id=None):    
    word = random.choice(cons) + random.choice(vowels) + random.choice(cons)

    r = random.random()
    if r < 0.1:
        word = random.choice(bad_words["bad_words"])
    elif r < 0.11:
        word = random.choice(digital_words)
    elif r < 0.12:
        word = random.choice(two_symbols)
    elif r < 0.13:
        word = random.choice(dop_prefixes) + word[1:] + 'ь'
    elif r < 0.14:
        word = random.choice(prefixes) + word + 'ь'
    elif r < 0.2:
        word += random.choice(postfixes)    
    else:
        word += 'ь'
    
    return word


def random_insult(chat_id):
    chat_users = []
    for uid, data in users_cache.items():
        if chat_id in data.get('chats', []) and uid != "7743054853":
            chat_users.append(uid)
    user_id = random.choice(chat_users)
    user = users_cache[user_id]
    name = user["first_name"]
    username = user["username"]
    return f"🚨 ВНИМАНИЕ! 🚨\n\nГлавный пидарас дня -> {name} (@{username})"


async def periodic_messages_sender(bot: Bot, interval: int, func: Callable):
    while True:
        try:
            if active_chats:
                for chat_id in list(active_chats):
                    try:
                        await bot.send_message(chat_id, func(chat_id))    
                        await asyncio.sleep(3)
                    except Exception as e:
                        if "bot was blocked" in str(e).lower():
                            logger.warning(f"Бот заблокирован в чате {chat_id}, удаляю")
                            active_chats.discard(chat_id)
                            save_chats()
                        else:
                            logger.error(f'Ошибка отправки в {chat_id}: {e}')       
        except Exception as e:
            logger.error(f'Ошибка в sender: {e}')         
        finally:
            await asyncio.sleep(interval)


async def main():
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    asyncio.create_task(periodic_messages_sender(bot, 900, random_words))
    asyncio.create_task(periodic_messages_sender(bot, 86400, random_insult))
    asyncio.create_task(collect_periodic_users())    
    logging.info("Бот запущен!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())