from telebot import types
from config import COMMON_WORDS
import random

class Comand:
    ADD_WORD = 'добавить слово ➕'
    DELETE_WORD = 'Удалить слово ⛔'
    NEXT = 'Дальше ⏩'

def create_main_keyboard():
    markup = types.ReplyKeyboardMarkup(row_width=2)
    ru_word, en_word = random.choice(COMMON_WORDS)
    buttons = [
        types.KeyboardButton(en_word),
        *[types.KeyboardButton(w[1]) for w in random.sample(COMMON_WORDS, 3)]
    ]
    random.shuffle(buttons)
    buttons.extend([
        types.KeyboardButton(Comand.ADD_WORD),
        types.KeyboardButton(Comand.DELETE_WORD),
        types.KeyboardButton(Comand.NEXT)
    ])
    markup.add(*buttons)
    return markup, ru_word, en_word