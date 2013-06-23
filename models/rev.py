from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from .base import DeclarativeBase

class Revision(DeclarativeBase):

    # table
    __tablename__ = 'rev'

    # columns
    id = Column(Integer, primary_key=True, nullable=False)
    page_id = Column(Integer, ForeignKey('page.id', ondelete='CASCADE'), nullable=False)
    rev_num = Column(Integer, nullable=False)
    patch_text = Column(String)
    create_ts = Column(DateTime, nullable=False, default=datetime.now)

    # relationships
    page = None #-> Page.revs
