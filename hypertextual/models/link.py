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
    tgt_page_uid = Column(String(64))
    tgt_page_title = Column(String(1024), nullable=False)
    tgt_page_alias = Column(String(1024)) # todo: put some check in place to deal with longer aliases

    # relationships
    rev = None #-> Revision.links

    def get_link_text(self):
        # return link text in the form `[[uid::title|alias]]`
        link_text = '[['
        if self.tgt_page_uid:
            link_text += '%s::' % self.tgt_page_uid
        link_text += self.tgt_page_title
        if self.tgt_page_alias:
            link_text += '|%s' % self.tgt_page_alias
        link_text += ']]'
        return link_text

    def get_placeholder_text(self):
        # return link placeholder in the form `[[link_num]]`
        return '[[%s]]' % self.link_num

    def get_link_html(self, current_uid):
        url, display_text, classes = self.__get_link_components(current_uid)
        class_html = ''
        if classes:
            class_text = ' '.join(classes)
            class_html = ' class="%s"' % class_text
        html = '<a href="%s"%s>%s</a>' % (url, class_html, display_text)
        return html

    def get_link_markdown_elem(self, current_uid):
        url, display_text, classes = self.__get_link_components(current_uid)
        a = etree.Element('a')
        a.text = display_text
        a.set('href', url)
        if classes:
            class_text = ' '.join(classes)
            a.set('class', class_text)
        return a

    def __get_link_components(self, current_uid):
        # return a url, display text, and relevant css classes for this link

        from acct import Account
        from page import Page

        page_uid = self.rev.page.acct.uid
        link_uid = self.tgt_page_uid or page_uid
        page = Page.query.\
            join(Account.pages).\
            filter(Page.title==self.tgt_page_title, Account.uid==link_uid).\
            first()

        can_create = (page is None and page_uid == current_uid and link_uid == current_uid)
        can_view = (page is not None and page.user_can_view(current_uid))

        display_text = self.tgt_page_alias or self.tgt_page_title
        url = self.__get_url_for_display(page, current_uid, can_create, can_view)
        classes = self.__get_classes_for_display(can_create, can_view)

        return url, display_text, classes

    def __get_url_for_display(self, page, current_uid, can_create, can_view):
        url = '#'
        if can_create:
            url = '/%s/action/create?title=%s' % (current_uid, self.tgt_page_title)
        elif can_view:
            url = page.get_url()
        return url

    def __get_classes_for_display(self, can_create, can_view):
        classes = []
        if can_create:
            classes.append('link-create')
        elif not can_view:
            classes.append('link-does-not-exist')
        return classes

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