from telebot import types
import random

class Comand:
    ADD_WORD = 'Добавить слово ➕'
    DELETE_WORD = 'Удалить слово ⛔'
    NEXT = 'Далее ⏩'

def create_main_keyboard(words):
    """Создаем клавиатуру с вариантами ответов."""
    markup = types.ReplyKeyboardMarkup(row_width=2)
    if not words:
        return markup, None, None
    # Выбираем случайное целевое слово
    target_word = random.choice(words)
    ru_word, en_word = target_word
    # Формируем список других вариантов
    other_words = [word[1] for word in words if word[1] != en_word]
    random.shuffle(other_words)
    other_words = other_words[:3]  # Берем первые 3
    # Создаем кнопки
    buttons = [types.KeyboardButton(en_word)]
    for word in other_words:
        buttons.append(types.KeyboardButton(word))
    random.shuffle(buttons)
    # Добавляем управляющие кнопки
    buttons += [
        types.KeyboardButton(Comand.ADD_WORD),
        types.KeyboardButton(Comand.DELETE_WORD),
        types.KeyboardButton(Comand.NEXT)
    ]
    markup.add(*buttons)
    return markup, ru_word, en_word
    