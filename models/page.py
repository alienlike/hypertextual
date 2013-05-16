from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship, backref
from .base import DeclarativeBase

class Page(DeclarativeBase):

    # table
    __tablename__ = 'page'

    # columns
    id = Column(Integer, primary_key=True, nullable=False)
    owner_acct_id = Column(Integer, ForeignKey('Account.id', ondelete='CASCADE'), nullable=False)
    curr_rev_id = Column(Integer, ForeignKey('Revision.id'), nullable=False)
    name_for_url = Column(String, nullable=False)
    title = Column(String, nullable=False)
    orig_text = Column(String, nullable=False)
    curr_text = Column(String, nullable=False)
    create_ts = Column(DateTime, default=datetime.now)

    # relationships
    revs = relationship('Revision', order_by='Revision.id', backref='page', primaryjoin='Page.id==Revision.page_id')
    curr_rev = relationship('Revision', primaryjoin='Revision.id==Page.curr_rev_id')
    owner = None #-> Account.pages
