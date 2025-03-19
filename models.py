# createdb -U postgres data_word
from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class Users(Base):
    __tablename__ = 'users'
    id_user = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    name = Column(String(40), nullable=False)
    custom_words = relationship("CustomWords", back_populates="user", cascade="all, delete")
        
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
        