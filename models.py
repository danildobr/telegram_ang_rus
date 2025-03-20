# createdb -U postgres data_word
from sqlalchemy import create_engine,Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from config import DSN, COMMON_WORDS

Base = declarative_base()

class Users(Base):
    __tablename__ = 'users'
    id_user = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    custom_words = relationship("CustomWords", back_populates="user", cascade="all, delete")
    excluded_words = relationship("ExcludedWords", back_populates="user", cascade="all, delete")    
        
class CommonWords(Base):
    __tablename__ = 'common_words'
    id_word = Column(Integer, primary_key=True)
    russian_word = Column(String(length=50), nullable=False)
    english_word = Column(String(length=50), nullable=False)
    
class CustomWords(Base):
    __tablename__ = 'custom_words'    
    id_word = Column(Integer, primary_key=True)
    id_user = Column(Integer, ForeignKey('users.id_user', ondelete='CASCADE'), nullable=False)
    russian_word = Column(String(length=40), nullable=False)
    english_word = Column(String(length=50), nullable=False)
    user = relationship("Users", back_populates="custom_words")
    
class ExcludedWords(Base):
    __tablename__ = 'excluded_words'
    id_excluded = Column(Integer, primary_key=True)
    id_user = Column(Integer, ForeignKey('users.id_user', ondelete='CASCADE'), nullable=False)
    id_word = Column(Integer, ForeignKey('common_words.id_word', ondelete='CASCADE'), nullable=False)
    user = relationship("Users", back_populates="excluded_words")
    common_word = relationship("CommonWords")
                
engine = create_engine(DSN) 
Session = sessionmaker(bind=engine)

def create_tables(engine):
    Base.metadata.drop_all(engine) 
    Base.metadata.create_all(engine)

def fill_common_words(session):
    words = [
        CommonWords(russian_word=ru, english_word=en)
        for ru, en in COMMON_WORDS
    ]
    session.add_all(words)
    session.commit()
    
def exclude_common_word(session, user_id, word_id):
    """Исключает слово из CommonWords для конкретного пользователя."""
    try:
        excluded = session.query(ExcludedWords).filter(ExcludedWords.id_user == user_id,ExcludedWords.id_word == word_id).first()
        if excluded:
            return False  # Слово уже исключено
        new_excluded = ExcludedWords(
            id_user=user_id,
            id_word=word_id
        )
        session.add(new_excluded)
        session.commit()
        return True
    except Exception as e:
        session.rollback()
        print(f"Ошибка при исключении слова: {e}")
        return False    
    
def check_user(session, message):
    user = session.query(Users).filter_by(telegram_id=message.from_user.id).first()
    return user
     
def add_user(session, message):
    new_user = Users(telegram_id=message.from_user.id)
    session.add(new_user)
    session.commit()
    
def get_user_words(session, user_id):
    """Получаем все слова пользователя: общие и кастомные."""
    user = session.query(Users).filter_by(telegram_id=user_id).first()
    if not user:
        return []
    common_words = session.query(
        CommonWords.russian_word, 
        CommonWords.english_word
    ).all()
    custom_words = session.query(
        CustomWords.russian_word, 
        CustomWords.english_word
    ).filter(CustomWords.id_user == user.id_user).all()
    return common_words + custom_words

def add_custom_word(session, user_id, ru_word, en_word):
    """Добавляем кастомное слово в БД."""
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