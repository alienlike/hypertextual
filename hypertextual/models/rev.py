from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from db import Base, db_session

class Revision(Base):

    # table
    __tablename__ = 'rev'

    # columns
    id = Column(Integer, primary_key=True, nullable=False)
    page_id = Column(Integer, ForeignKey('page.id', ondelete='CASCADE'), nullable=False)
    create_ts = Column(DateTime, nullable=False, default=datetime.now)

    rev_num = Column(Integer, nullable=False)
    patch_text = Column(String)
    use_markdown = Column(Boolean, nullable=False)

    # relationships
    page = None #-> Page.revs
    links = relationship('Link', order_by='Link.link_num', backref='rev')

    def get_text(self):
        return self.page.get_text_for_rev(self.rev_num)

    @classmethod
    def new(cls, page):
        rev = Revision()
        page.revs.append(rev)
        db_session.add(rev)
        return rev