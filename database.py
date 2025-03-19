from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Base, CommonWords
from config import DSN
from config import COMMON_WORDS

engine = create_engine(DSN) 
Session = sessionmaker(bind=engine)

def create_tables(engine):
    # Base.metadata.drop_all(engine) 
    Base.metadata.create_all(engine)
     
def fill_common_words(session):
    words = [
        CommonWords(russian_word=ru, english_word=en)
        for ru, en in COMMON_WORDS
    ]
    session.add_all(words)
    session.commit()