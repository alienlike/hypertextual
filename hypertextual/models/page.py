from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from config import SITE_URL
from db import Base, db_session
from rev import Revision

class Page(Base):

    # table
    __tablename__ = 'page'

    # columns
    id = Column(Integer, primary_key=True, nullable=False)
    acct_id = Column(Integer, ForeignKey('acct.id', ondelete='CASCADE'), nullable=False)
    create_ts = Column(DateTime, default=datetime.now)

    page_name = Column(String) # http://hypertextual/<page_name>
    title = Column(String)
    curr_rev_num = Column(Integer)
    draft_rev_num = Column(Integer)
    private = Column(Boolean)

    # relationships
    revs = relationship(Revision, order_by='Revision.id', backref='page', primaryjoin='Page.id==Revision.page_id')
    acct = None #-> Account.pages

    def __init__(self):
        self.curr_rev_num = None
        self.draft_rev_num = None
        self.private = False

    def user_is_owner(self, acct_or_uid):
        try:
            uid = acct_or_uid.uid
        except AttributeError:
            uid = acct_or_uid
        return self.acct.uid == uid

    def user_can_view(self, acct_or_uid):
        if self.private or self.curr_rev_num is None:
            allow = self.user_is_owner(acct_or_uid)
        else:
            allow = True
        return allow

    def get_url(self, rev_num=None):
        # start with uid
        url = '%s/%s' % (SITE_URL, self.acct.uid)
        if self.page_name is not None:
            # add page name if required
            url += '/%s' % self.page_name
        if rev_num is not None and rev_num != self.curr_rev_num:
            # add rev num if required
            url += '?rev=%s' % rev_num
        return url

    def get_curr_rev(self):
        rev = None
        if self.curr_rev_num is not None:
            rev = self.revs[self.curr_rev_num]
        return rev

    def get_draft_rev(self):
        rev = None
        if self.draft_rev_num is not None:
            rev = self.revs[self.draft_rev_num]
        return rev

    def save_draft_rev(self, text, use_markdown):
        rev = self.get_draft_rev()
        if rev is None:
            rev = self.__create_draft_rev()
        rev.use_markdown = use_markdown
        rev.set_text(text)

    def __create_draft_rev(self):
        rev = Revision.new(self)
        rev.rev_num = 0 if self.curr_rev_num is None else self.curr_rev_num + 1
        self.draft_rev_num = rev.rev_num
        return rev

    def publish_draft_rev(self):
        self.curr_rev_num = self.draft_rev_num
        self.draft_rev_num = None

    @classmethod
    def new(cls, acct, title):
        page = cls()
        acct.pages.append(page)
        cls.__set_title(page, title)
        db_session.add(page)
        return page

    @classmethod
    def __set_title(cls, page, title):

        # set title
        page.title = title

        # build a page name from the valid characters in the page name,
        # removing any single quotes and substituting dashes for everything else
        valid_chars = 'abcdefghijklmnopqrstuvwxyz0123456789'
        page_name = ''
        for char in title.lower():
            if char in valid_chars:
                page_name += char
            elif char == "'":
                continue
            elif not page_name.endswith('-'):
                page_name += "-"
        page_name = page_name.strip('-')

        # limit to 100 chars
        page_name = page_name[:100].strip('-')

        # prepend underscore to numeric name
        try:
            page_name = '_%s' % int(page_name)
        except ValueError:
            pass

        # ensure uniqueness of name
        exists = lambda name: Page.query.\
            filter(Page.page_name==name).\
            filter(Page.acct==page.acct).count()
        name_to_test = page_name
        i = 1
        while exists(name_to_test):
            i+=1
            name_to_test = '%s-%s' % (page_name, i)

        # set page name
        page.page_name = name_to_test