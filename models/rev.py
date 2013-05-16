from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship, backref
from .base import DeclarativeBase

class Revision(DeclarativeBase):

    # table
    __tablename__ = 'rev'

    # columns
    id = Column(Integer, primary_key=True, nullable=False)
    page_id = Column(Integer, ForeignKey('Page.id', ondelete='CASCADE'), nullable=False)
    create_ts = Column(DateTime, nullable=False, default=datetime.now)

    # relationships
    patches = relationship('Patch', order_by='Patch.id', backref='rev')
    page = None #-> Page.revs
