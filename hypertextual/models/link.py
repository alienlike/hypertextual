from datetime import datetime
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from markdown.util import etree
from sqlalchemy.orm.exc import NoResultFound
from db import Base, db_session

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

    def get_link_html(self, current_uid):
        url, display_text, classes = self.__get_link_components(current_uid)
        class_html = ''
        if classes:
            class_text = classes.join(' ')
            class_html = ' class="%s"' % class_text
        html = '<a href="%s"%s>%s</a>' % (url, class_html, display_text)
        return html

    def get_link_markdown_elem(self, current_uid):
        url, display_text, classes = self.__get_link_components(current_uid)
        a = etree.Element('a')
        a.text = display_text
        a.set('href', url)
        for c in classes:
            a.set('class', c)
        return a

    def __get_link_components(self, current_uid):

        from acct import Account
        from page import Page

        # TODO: set classes for all conditions

        title = self.tgt_page_title
        page_uid = self.rev.page.acct.uid
        link_uid = self.tgt_page_uid or page_uid
        display_text = self.tgt_page_alias or self.tgt_page_title
        classes = []

        try:
            page = Page.query.join(Account.pages).filter(Page.title==title, Account.uid==link_uid).one()
            if page.user_can_view(current_uid):
                url = page.get_url()
            else:
                url = '#'
                classes.append('link-does-not-exist')
        except NoResultFound:
            if page_uid == current_uid:
                url = '/%s?action=create&title=%s' % (current_uid, title)
                classes.append('link-create-page')
            else:
                url = '#'
                classes.append('link-does-not-exist')

        return url, display_text, classes

    @classmethod
    def new(cls, rev, link_num, uid, title, alias):
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