from telebot import TeleBot
from telebot.handler_backends import State, StatesGroup
from models import Session, create_tables, engine, CustomWords, Users, exclude_common_word, CommonWords, get_user_words, fill_common_words, add_custom_word, check_user, add_user
from keyboards import Comand, create_main_keyboard
from config import TOKEN
import time
import re

bot = TeleBot(TOKEN)

class MyStates(StatesGroup):
    '''Набор состояний для управления диалогом.'''
    target_word = State()
    add_russian_word = State()
    add_english_word = State()
    delete_word= State()

class Comand:
    ADD_WORD = 'добавить слово ➕'
    DELETE_WORD = 'Удалить слово ⛔'
    NEXT = 'Дальше ⏩'

# Инициализация БД
with Session() as session:
    create_tables(engine)
    fill_common_words(session)
    
@bot.message_handler(commands=['start'])
def start_bot(message):
    '''Проверяем, есть ли пользователь в базе данных, если нет то добавит'''
    with Session() as session:
        user = check_user(session, message)
        if not user:
            add_user(session, message)
            bot.send_message(message.chat.id, "✅ Вы успешно зарегистрированы!")
    bot.send_message(message.chat.id, f'''Привет 👋 Давай попрактикуемся в английском языке. Тренировки можешь проходить в удобном для себя темпе.
У тебя есть возможность использовать тренажёр, как конструктор, и собирать свою собственную базу для обучения. Для этого воспрользуйся инструментами:
добавить слово ➕\nудалить слово 🔙\nНу что, начнём ⬇️''')
    generate_new_word(message)

def generate_new_word(message):
    '''генерирует слово которое надо угадать'''
    with Session() as session:
        words = get_user_words(session, message.from_user.id)
        if not words:
            bot.send_message(message.chat.id, "Список слов пуст. Добавьте слова!")
            return
    markup, ru_word, en_word = create_main_keyboard(words)
    bot.send_message(message.chat.id, f'Угадай слово "{ru_word}"', reply_markup=markup)
    bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['target_word'] = en_word

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
    """Обработчик добавления английского слова."""
    if is_english(message.text):
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            ru_word = data.get('russian_word')
            en_word = message.text.strip()
            with Session() as session:
                if add_custom_word(session, message.from_user.id, ru_word, en_word):
                    bot.send_message(message.chat.id, f"Слово '{ru_word}' добавлено!")
                else:
                    bot.send_message(message.chat.id, "Ошибка добавления слова")
        bot.delete_state(message.from_user.id, message.chat.id)
    else:
        bot.send_message(message.chat.id, "Введите корректное английское слово!")

@bot.message_handler(func=lambda m: m.text == Comand.DELETE_WORD)
def handle_delete_word(message):
    """Обработчик удаления слова."""
    bot.send_message(message.chat.id, "Введите слово на русском, которое хотите удалить:")
    bot.set_state(message.from_user.id, MyStates.delete_word, message.chat.id)

@bot.message_handler(state=MyStates.delete_word)
def delete_word(message):
    """Удаляет или исключает слово."""
    if is_russian(message.text):
        ru_word = message.text.strip()
        with Session() as session:
            user = session.query(Users).filter_by(telegram_id=message.from_user.id).first()
            common_word = session.query(CommonWords).filter(CommonWords.russian_word == ru_word).first()
            if common_word:
                if exclude_common_word(session, user.id_user, common_word.id_word):
                    bot.send_message(message.chat.id, f"✅ Слово '{ru_word}' исключено из вашего списка!")
                else:
                    bot.send_message(message.chat.id, f"❌ Слово '{ru_word}' уже исключено.")
            else:
                custom_word = session.query(CustomWords).filter(CustomWords.id_user == user.id_user,
                    CustomWords.russian_word == ru_word).first()
                if custom_word:
                    session.delete(custom_word)
                    session.commit()
                    bot.send_message(message.chat.id, f"✅ Слово '{ru_word}' удалено!")
                else:
                    bot.send_message(message.chat.id, f"❌ Слово '{ru_word}' не найдено.")
        bot.delete_state(message.from_user.id, message.chat.id)
    else:
        bot.send_message(message.chat.id, "❌ Ошибка: введите слово на русском языке!")
        bot.delete_state(message.from_user.id, message.chat.id)

@bot.message_handler(func=lambda messege: True, content_types=['text'])
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