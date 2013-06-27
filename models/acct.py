from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship, backref
from .base import DeclarativeBase

class Account(DeclarativeBase):

    # table
    __tablename__ = 'acct'

    # columns
    id = Column(Integer, primary_key=True, nullable=False)
    create_ts = Column(DateTime, nullable=False, default=datetime.now)

    uid = Column(String, unique=True, nullable=False)
    pw = Column(String, nullable=False)

    # relationship
    pages = relationship('Page', order_by='Page.id', backref='acct')
