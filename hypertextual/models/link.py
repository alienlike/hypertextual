from sqlalchemy import Column, Integer, String, ForeignKey, Boolean
from .base import DeclarativeBase

class Link(DeclarativeBase):

    # table
    __tablename__ = 'link'

    # columns
    id = Column(Integer, primary_key=True, nullable=False)
    rev_id = Column(Integer, ForeignKey('rev.id', ondelete='CASCADE'), nullable=False)
    link_num = Column(Integer, nullable=False)
    tgt_page_id = Column(Integer, ForeignKey('page.id', ondelete='SET NULL'))
    tgt_page_is_redirect = Column(Boolean, nullable=False, default=False)
    tgt_page_uid = Column(String)
    tgt_page_title = Column(String, nullable=False)
    tgt_page_alias = Column(String)

    # relationships
    rev = None #-> Revision.links
