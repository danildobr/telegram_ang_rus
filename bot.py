from telebot import TeleBot
from telebot.handler_backends import State, StatesGroup
from telebot.storage import StateMemoryStorage
from models import (Session, create_tables, engine, CustomWords, Users, exclude_common_word,
CommonWords, get_user_words, fill_common_words, add_custom_word, check_user, add_user,
checking_words_duplicate, delete_custom_word)
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
    ADD_WORD = 'Добавить слово ➕'
    DELETE_WORD = 'Удалить слово ⛔'
    NEXT = 'Далее ⏩'

# Инициализация БД
with Session() as session:
    create_tables(engine)
    fill_common_words(session)
    
@bot.message_handler(commands=['start'])
def start_bot(message):
    '''Проверяем, есть ли пользователь в базе данных, если нет то добавит'''
    with Session() as session:
        user = check_user(session, message)
        if not user:  # прверяет есть ли пользователь, если нет то добавляет 
            add_user(session, message)
            bot.send_message(message.chat.id, '✅ Вы успешно зарегистрированы!')
    bot.send_message(message.chat.id, f'''Привет 👋 Давай попрактикуемся в английском языке. 
Тренировки можешь проходить в удобном для себя темпе.
У тебя есть возможность использовать тренажёр, как конструктор, и собирать свою собственную 
базу для обучения. Для этого воспрользуйся инструментами:
Добавить слово ➕\nУдалить слово 🔙\nНу что, начнём ⬇️''')
    generate_new_word(message)

@bot.message_handler(commands=['all_words']) 
def all_words(message):
    """Выводит список всех слов пользователя (базовые + кастомные), исключая удаленные"""
    with Session() as session:
        # Получаем все слова пользователя
        words = get_user_words(session, message.from_user.id)
        if not words:
            bot.send_message(message.chat.id, "📭 Ваш словарь пуст. Добавьте слова!")
        # Форматируем вывод
        words_text = "📖 Ваш словарь:\n" + "\n".join(
            f"{i}. {ru_word} - {en_word}" 
            for i, (ru_word, en_word) in enumerate(words, 1)
        )
        bot.send_message(message.chat.id, words_text)

@bot.message_handler(commands=['cancel']) 
def cancel_action(message):
    '''Обработка команды cancel'''
    bot.delete_state(message.from_user.id, message.chat.id)
    bot.send_message(message.chat.id, '❌ Действие отменено')
    generate_new_word(message)

def generate_new_word(message):
    '''Генерирует слово которое надо угадать'''
    with Session() as session:
        words = get_user_words(session, message.from_user.id)
        if not words:
            bot.send_message(message.chat.id, 'Список слов пуст. Добавьте слова!')
            return
    markup, ru_word, en_word = create_main_keyboard(words) # возврящает клавиатуру, русское слово и его перевод
    bot.send_message(message.chat.id, f'Угадай слово {ru_word}', reply_markup=markup)
    bot.set_state(message.from_user.id, MyStates.target_word, message.chat.id)
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['target_word'] = en_word

@bot.message_handler(func=lambda m: m.text == Comand.NEXT)
def handle_next(message):
    '''Команда 'далее' '''
    generate_new_word(message)

@bot.message_handler(func=lambda m: m.text == Comand.ADD_WORD)
def add_word(message):
    '''Добавление слова на русском языке'''
    bot.send_message(message.chat.id, 'Введите слово на русском языке:')
    bot.set_state(message.from_user.id, MyStates.add_russian_word, message.chat.id)
                
def check_and_handle_duplicates(session, ru_word, message):
    '''Проверяет и обрабатывает дубликаты слов'''
    user = check_user(session, message)
    custom_word, common_word, excluded_word = checking_words_duplicate(session, ru_word, user)
    # Если слово уже в CustomWords
    if custom_word:
        bot.send_message(message.chat.id, f'❌ Слово "{ru_word}" уже есть в вашем словаре!')
        bot.delete_state(message.from_user.id, message.chat.id)
        return True
    # Если слово в CommonWords и не исключено
    elif common_word and not excluded_word:
        bot.send_message(message.chat.id, f'ℹ️ Слово "{ru_word}" уже есть в базовом наборе. ')
        bot.delete_state(message.from_user.id, message.chat.id)
        return True
    # Если слово было исключено - разблокируем
    elif excluded_word:
        session.delete(excluded_word)
        session.commit()
        bot.send_message(message.chat.id, f'🔓 Слово "{ru_word}" было разблокировано из базового набора!')
        bot.delete_state(message.from_user.id, message.chat.id)
        return True
    else:
        return False
    
@bot.message_handler(func=lambda message: bot.get_state(message.from_user.id, message.chat.id)=='MyStates:add_russian_word')
def add_russian_word(message):
    '''Добавляем перевод'''
    ru_word = message.text.strip().capitalize()   # обрезаем пробелы и делаем с заглавной буквы
    if not is_russian(ru_word):
        bot.send_message(message.chat.id, '❌ Ошибка: вы ввелие слово не на русском языке!')
        bot.delete_state(message.from_user.id, message.chat.id)
        return 

    with Session() as session:
        if check_and_handle_duplicates(session, ru_word, message):  # проверяем на дубликаты
            bot.delete_state(message.from_user.id, message.chat.id)
            return
    # Сохраняем и запрашиваем перевод
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['russian_word'] = ru_word
    bot.send_message(message.chat.id, 'Теперь введите перевод на английском:')
    bot.set_state(message.from_user.id, MyStates.add_english_word, message.chat.id)
            
@bot.message_handler(func=lambda message: bot.get_state(message.from_user.id, message.chat.id)=='MyStates:add_english_word')
def add_english_word(message):
    '''Обработчик добавления английского слова.'''
    if is_english(message.text):
        with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
            ru_word = data.get('russian_word')  
            en_word = message.text.strip().capitalize()
            with Session() as session:
                if add_custom_word(session, message.from_user.id, ru_word, en_word):
                    bot.send_message(message.chat.id, f'Слово "{ru_word}" добавлено!')
                else:
                    bot.send_message(message.chat.id, 'Ошибка добавления слова')
        bot.delete_state(message.from_user.id, message.chat.id)
    else:
        bot.send_message(message.chat.id, '❌ Ошибка: Введите корректное английское слово!')
        add_russian_word(message)
        
@bot.message_handler(func=lambda m: m.text == Comand.DELETE_WORD)
def handle_delete_word(message):
    '''Обработчик удаления слова.'''
    bot.send_message(message.chat.id, 'Введите слово на русском, которое хотите удалить:')
    bot.set_state(message.from_user.id, MyStates.delete_word, message.chat.id)

@bot.message_handler(func=lambda message: bot.get_state(message.from_user.id, message.chat.id)=='MyStates:delete_word')
def delete_word(message):
    '''Удаляет или исключает слово.'''
    if not is_russian(message.text):
        bot.send_message(message.chat.id, '❌ Ошибка: введите слово на русском языке!')
        return handle_delete_word(message)
    ru_word = message.text.strip().capitalize()
       
    with Session() as session:
        user = check_user(session, message)
        custom_word, common_word, excluded_word = checking_words_duplicate(session, ru_word, user)
        # 1. Если слово в CustomWords - удаляем
        if custom_word: 
            if delete_custom_word(session, ru_word, user):
                bot.send_message(message.chat.id, f'✅ Слово "{ru_word}" удалено!')
            else:
                bot.send_message(message.chat.id, '❌ Не удалось удалить слово')
            bot.delete_state(message.from_user.id, message.chat.id)
        # 2. Если есть слово в CommonWords тогда исключаем 
        elif common_word:
            if excluded_word:
                bot.send_message(message.chat.id, f'ℹ️ Слово "{ru_word}" уже исключено ранее.')
                bot.delete_state(message.from_user.id, message.chat.id)
            else:
                exclude_common_word(session, user, common_word)
                bot.send_message(message.chat.id, f'✅ Слово "{ru_word}" исключено из базового набора!')
   # 3. Если слово не найдено
        else:
            bot.send_message(message.chat.id, f'❌ Слово "{ru_word}" не найдено в вашем словаре или базовом наборе.')
            return handle_delete_word(message)
            
@bot.message_handler(func=lambda message: bot.get_state(message.from_user.id, message.chat.id)=='MyStates:target_word')
def message_reply(message):
    '''Проверка отгадывания слова'''
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        if message.text.strip().capitalize() == data['target_word']:
            bot.send_message(message.chat.id, '✅ Правильно!')
        else:
            bot.send_message(message.chat.id, '❌ Неверно, попробуйте еще раз')
    
@bot.message_handler(func=lambda message: True)
def text_processing(message):
    '''Обработка текста'''
    bot.send_message(message.chat.id, 'Пожалуйста, выберите любую команду!')
    
def is_russian(text):
    '''Проверка являеться ли слово русским'''
    return bool(re.fullmatch(r'[а-яА-ЯёЁ\s]+', text))  

def is_english(text):
    '''Проверка являеться ли слово английским'''
    return bool(re.fullmatch(r'[a-zA-Z\s]+', text))  

if __name__ == '__main__':
    '''Запуск бота'''
    for i in range(3, 0, -1):
        print(f'{i}...')
        time.sleep(0.5)
    bot.polling()
    