from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from markdown.util import etree
from sqlalchemy.orm.exc import NoResultFound
from db import Base, db_session
from acct import Account
from page import Page

class Link(Base):

    # table
    __tablename__ = 'link'

    # columns
    id = Column(Integer, primary_key=True, nullable=False)
    rev_id = Column(Integer, ForeignKey('rev.id', ondelete='CASCADE'), nullable=False)
    create_ts = Column(DateTime, nullable=False, default=datetime.now)

    link_num = Column(Integer, nullable=False)
    tgt_page_uid = Column(String)
    tgt_page_title = Column(String, nullable=False)
    tgt_page_alias = Column(String)

    # relationships
    rev = None #-> Revision.links

    def get_link_text(self):
        link_text = '[['
        if self.tgt_page_uid:
            link_text += '%s::' % self.tgt_page_uid
        link_text += self.tgt_page_title
        if self.tgt_page_alias:
            link_text += '|%s' % self.tgt_page_alias
        link_text += ']]'
        return link_text

    def get_placeholder_text(self):
        return '[[%s]]' % self.link_num

    def build_url(self, current_uid):
        title = self.tgt_page_title
        page_uid = self.rev.page.acct.uid
        link_uid = self.tgt_page_uid or page_uid

        exists = True
        try:
            page = Page.query.join(Account.pages).filter(Page.title==title, Account.uid==link_uid).one()
            if page.user_can_view(current_uid):
                url = page.get_url()
            else:
                exists = False
                url = '#'
        except NoResultFound:
            exists = False
            if page_uid == current_uid:
                url = '/%s?action=create&title=%s' % (current_uid, title)
            else:
                url = '#'

        return url, exists

    def get_link_html(self, current_uid):
        url, exists = self.build_url(current_uid)
        alias = self.tgt_page_alias or self.tgt_page_title
        # todo: set classes for all conditions
        class_html = ''
        if not exists:
            class_html = ' class="link-create-page"'
        html = '<a href="%s"%s>%s</a>' % (url, class_html, alias)
        return html

    def get_link_markdown_elem(self, current_uid):
        url, exists = self.build_url(current_uid)
        alias = self.tgt_page_alias or self.tgt_page_title
        a = etree.Element('a')
        a.text = alias
        a.set('href', url)
        # todo: set classes for all conditions
        if not exists:
            a.set('class', 'link-create-page')
        return a

    @classmethod
    def new(cls, rev, link_num, uid, alias, title):
        link = cls()
        link.link_num = link_num
        if uid and uid != rev.page.acct.uid:
            link.tgt_page_uid = uid
        link.tgt_page_title = title
        if alias and alias != title:
            link.tgt_page_alias = alias
        rev.links.append(link)
        db_session.add(link)
        return link