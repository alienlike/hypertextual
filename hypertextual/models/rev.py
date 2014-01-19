import re
from datetime import datetime
from markdown import markdown
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from db import Base, db_session
from link import Link
from htlinks import HypertextualLinkExtension, render_a_tag, HT_LINK_RE

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

    def render_to_html(self, current_user):
        if self.use_markdown:
            html = self.__render_markdown_to_html(current_user)
        else:
            html = self.__render_text_to_html(current_user)
        return html

    def __render_text_to_html(self, current_user):
        text = self.get_text()
        current_uid = current_user.uid or None
        html = re.sub(
            HT_LINK_RE,
            lambda m: render_a_tag(current_uid, self.page.acct.uid, m),
            text
        )
        html = '<pre>%s</pre>' % html
        return html

    def __render_markdown_to_html(self, current_user):
        text = self.get_text()
        current_uid = current_user.uid or None
        linkExt = HypertextualLinkExtension(configs=[
            ('current_uid', current_uid),
            ('page_uid', self.page.acct.uid)
        ])
        html = markdown(text, extensions=[linkExt])
        return html

    def new_link(self):
        link = Link.new(self)
        return link

    @classmethod
    def new(cls, page):
        rev = cls()
        page.revs.append(rev)
        db_session.add(rev)
        return rev