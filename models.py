# createdb -U postgres data_word - создание базы данных
from sqlalchemy import create_engine, exists, Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from config import DSN, COMMON_WORDS

Base = declarative_base()

class Users(Base):
    '''Таблица пользователей'''
    __tablename__ = 'users'
    id_user = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    custom_words = relationship("CustomWords", back_populates="user", cascade="all, delete")
    excluded_words = relationship("ExcludedWords", back_populates="user", cascade="all, delete")    
        
class CommonWords(Base):
    '''Таблица базовых слов'''
    __tablename__ = 'common_words'
    id_word = Column(Integer, primary_key=True)
    russian_word = Column(String(length=50), nullable=False)
    english_word = Column(String(length=50), nullable=False)
    
class CustomWords(Base):
    '''Таблица слов которые добавил пользователь'''
    __tablename__ = 'custom_words'    
    id_word = Column(Integer, primary_key=True)
    id_user = Column(Integer, ForeignKey('users.id_user', ondelete='CASCADE'), nullable=False)
    russian_word = Column(String(length=40), nullable=False)
    english_word = Column(String(length=50), nullable=False)
    user = relationship("Users", back_populates="custom_words")
    
class ExcludedWords(Base):
    '''Таблица исключенных слов из базовой таблицы, для каждого пользователя'''
    __tablename__ = 'excluded_words'
    id_excluded = Column(Integer, primary_key=True)
    id_user = Column(Integer, ForeignKey('users.id_user', ondelete='CASCADE'), nullable=False)
    id_word = Column(Integer, ForeignKey('common_words.id_word', ondelete='CASCADE'), nullable=False)
    user = relationship("Users", back_populates="excluded_words")
    common_word = relationship("CommonWords")
                
engine = create_engine(DSN) 
Session = sessionmaker(bind=engine)

def create_tables(engine):
    Base.metadata.drop_all(engine) # удаление таблиц
    Base.metadata.create_all(engine) # создание всех таблиц
    
def fill_common_words(session):
    '''Добавляем по умолчания слова в БД'''
    words = [
        CommonWords(russian_word=ru, english_word=en)
        for ru, en in COMMON_WORDS
    ]
    session.add_all(words)
    session.commit()
    
def check_user(session, message):
    '''Проверяем пользователя'''
    user = session.query(Users).filter_by(telegram_id=message.from_user.id).first()
    return user
     
def add_user(session, message):
    '''Добавляем пользователя'''
    new_user = Users(telegram_id=message.from_user.id)
    session.add(new_user)
    session.commit()
    
def get_user_words(session, user_id):
    """Получаем все слова пользователя: общие и кастомные."""
    user = session.query(Users).filter_by(telegram_id=user_id).first()
    if not user:
        return []
    # Получаем общие слова, которые пользователь не исключил
    common_words = session.query(
        CommonWords.russian_word, 
        CommonWords.english_word
    ).filter(
        ~exists().where(
            (ExcludedWords.id_user == user.id_user) &
            (ExcludedWords.id_word == CommonWords.id_word)
        )
    ).all()
    # Получаем кастомные слова пользователя
    custom_words = session.query(
        CustomWords.russian_word, 
        CustomWords.english_word
    ).filter(CustomWords.id_user == user.id_user).all()
    return common_words + custom_words

def add_custom_word(session, user_id, ru_word, en_word):
    """Добавляем слово которое ввел пользователь в БД."""
    user = session.query(Users).filter_by(telegram_id=user_id).first()
    if not user:
        return False
    new_word = CustomWords(
        id_user=user.id_user,
        russian_word=ru_word,
        english_word=en_word
    )
    session.add(new_word)
    session.commit()
    return True

def checking_words_duplicate(session, ru_word, user):
    """Проверяет наличие слова в базе и возвращает:
    - (custom_word, common_word, excluded_word) - объекты из БД"""
    custom_word = session.query(CustomWords).filter(CustomWords.id_user == user.id_user,
        CustomWords.russian_word == ru_word).first()
    
    common_word = session.query(CommonWords).filter(CommonWords.russian_word == ru_word).first()
    
    excluded_word = None
    if common_word:
        excluded_word  = session.query(ExcludedWords).filter(ExcludedWords.id_user == user.id_user,
        ExcludedWords.id_word == common_word.id_word).first()
    
    return custom_word, common_word, excluded_word 

def delete_custom_word(session, ru_word, user):
    """Удаляет кастомное слово пользователя"""
    try:
        word = session.query(CustomWords).filter(
            CustomWords.id_user == user.id_user,
            CustomWords.russian_word == ru_word).first()
        if word:
            session.delete(word)
            session.commit()
            return True
        return False
    except Exception as e: 
        session.rollback()
        print(f"Ошибка при удалении слова: {e}")
    
def exclude_common_word(session, user, common_word):
    """Исключает слово из CommonWords для конкретного пользователя."""
    try:
        new_excluded = ExcludedWords(
            id_user=user.id_user,
            id_word=common_word.id_word
        )
        session.add(new_excluded)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        print(f"Ошибка при исключении слова: {e}")
        return False
    