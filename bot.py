from telebot import TeleBot
from telebot.handler_backends import State, StatesGroup
from database import Session, create_tables, fill_common_words, engine
from models import Users, CustomWords
from keyboards import Comand, create_main_keyboard
from config import TOKEN, COMMON_WORDS
import random
import time
import re

bot = TeleBot(TOKEN)

class MyStates(StatesGroup):
    '''Набор состояний для управления диалогом.'''
    target_word = State()
    translate_word = State()
    other_words = State()
    add_russian_word = State()
    add_english_word = State()

# Инициализация БД
with Session() as session:
    create_tables(engine)
    fill_common_words(session)

@bot.message_handler(commands=['start'])
def start_bot(message):
    '''Проверяем, есть ли пользователь в базе данных, если нет то добавит'''
    with Session() as session:
        user = session.query(Users).filter_by(telegram_id=message.from_user.id).first()
        if not user:
            new_user = Users(telegram_id=message.from_user.id, name=message.from_user.first_name)
            session.add(new_user)
            session.commit()
    generate_new_word(message)

def generate_new_word(message):
    '''генерирует слово которое надо угадать'''
    markup, ru_word, en_word = create_main_keyboard()
    bot.send_message(message.chat.id, f'Угадай слово "{ru_word}"', reply_markup=markup)
    bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['target_word'] = en_word
        data['russian_word'] = ru_word
        data['other_word'] = [w[1] for w in random.sample(COMMON_WORDS, 3)]

@bot.message_handler(func=lambda m: m.text == Comand.NEXT)
def handle_next(message):
    generate_new_word(message)

@bot.message_handler(func=lambda m: m.text == Comand.ADD_WORD)
def add_word(message):
    '''добавление слова на русском языке'''
    bot.send_message(message.chat.id, 'Введите слово на русском языке:')
    bot.set_state(message.from_user.id, MyStates.add_russian_word, message.chat.id)

@bot.message_handler(state=MyStates.add_russian_word)
def add_russian_word(message):
    if is_russian(message.text):
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            data['russian_word'] = message.text.strip() 
        bot.send_message(message.chat.id, "Теперь введите перевод на английском:")
        bot.set_state(message.from_user.id, MyStates.add_english_word, message.chat.id)
    else:
        bot.send_message(message.chat.id, '❌ Ошибка: вы ввели слово не на русском языке!')
        bot.delete_state(message.from_user.id, message.chat.id) 
    
@bot.message_handler(state=MyStates.add_english_word)
def add_english_word(message):
    '''добавление перевода для слова на русском языке'''
    if is_english(message.text):
        english_word = message.text.strip()  
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            russian_word = data.get('russian_word', '')
            try:
                with Session() as session:
                    user = session.query(Users).filter_by(telegram_id=message.from_user.id).first()
                    if user:
                        new_word = CustomWords(id_user=user.id_user, russian_word=russian_word, english_word=english_word)
                        session.add(new_word)
                        session.commit()
                        bot.send_message(message.chat.id, f"✅ Слово '{russian_word}' добавлено!")
                    else:
                        bot.send_message(message.chat.id, "❌ Ошибка: пользователь не найден.")
            except Exception as e:
                bot.send_message(message.chat.id, "❌ Произошла ошибка при добавлении слова.")
        bot.delete_state(message.from_user.id, message.chat.id)
    else:
        bot.send_message(message.chat.id, '❌ Ошибка: вы ввели слово не на английском языке!')

@bot.message_handler(func=lambda message: True)
def message_reply(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        if message.text == data['target_word']:
            bot.send_message(message.chat.id, '✅ Правильно!')
        else:
            bot.send_message(message.chat.id, '❌ Неверно, попробуйте еще раз')

def is_russian(text):
    return bool(re.fullmatch(r'[а-яА-ЯёЁ\s]+', text))  

def is_english(text):
    return bool(re.fullmatch(r'[a-zA-Z\s]+', text))  

if __name__ == '__main__':
    for i in range(3, 0, -1):
        print(f'{i}...')
        time.sleep(0.5)
    bot.polling()