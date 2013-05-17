from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship, backref
from .base import DeclarativeBase

class Patch(DeclarativeBase):

    # table
    __tablename__ = 'patch'

    # columns
    id = Column(Integer, primary_key=True, nullable=False)
    rev_id = Column(Integer, ForeignKey('rev.id', ondelete='CASCADE'), nullable=False)
    patch_text = Column(String, nullable=False)
    create_ts = Column(DateTime, default=datetime.now, nullable=False)

    # relationships
    rev = None #-> Revision.patches
