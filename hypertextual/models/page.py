from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from db import Base, db_session
from rev import Revision
from reserved import reserved_page_names

class Page(Base):

    # table
    __tablename__ = 'page'

    # columns
    id = Column(Integer, primary_key=True, nullable=False)
    acct_id = Column(Integer, ForeignKey('acct.id', ondelete='CASCADE'), nullable=False)
    create_ts = Column(DateTime, default=datetime.now)

    slug = Column(String) # http://hypertextual/<slug>
    title = Column(String)
    curr_rev_num = Column(Integer)
    draft_rev_num = Column(Integer)
    private = Column(Boolean)
    redirect = Column(Boolean)

    # relationships
    revs = relationship(Revision, order_by='Revision.id', backref='page', primaryjoin='Page.id==Revision.page_id')
    acct = None #-> Account.pages

    def __init__(self):
        self.curr_rev_num = None
        self.draft_rev_num = None
        self.private = False
        self.redirect = False

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
        if self.slug == '__home':
            url = '/%s' % self.acct.uid
        elif self.slug == '__private':
            url = '/_%s' % self.acct.uid
        else:
            url = '/%s/%s' % (self.acct.uid, self.slug)
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
        return rev

    def __create_draft_rev(self):
        rev = Revision.new(self)
        rev.rev_num = 0 if self.curr_rev_num is None else self.curr_rev_num + 1
        self.draft_rev_num = rev.rev_num
        return rev

    def revert_draft_rev(self):
        rev = self.get_draft_rev()
        if rev:
            rev.page = None
            db_session.delete(rev)
            self.draft_rev_num = None

    def publish_draft_rev(self):
        self.curr_rev_num = self.draft_rev_num
        self.draft_rev_num = None
        self.redirect = False

    @classmethod
    def new(cls, acct, title):
        page = cls()
        page.title = title
        page.slug = cls.__sluggify(acct, title)
        acct.pages.append(page)
        db_session.add(page)
        return page

    @classmethod
    def move(cls, page, new_title, create_redirect=False):
        if new_title != page.title:
            old_title = page.title
            old_slug = page.slug
            page.title = new_title
            page.slug = cls.__sluggify(page.acct, new_title)
            if create_redirect:
                redirected_page = cls.new(page.acct, old_title)
                redirected_page.slug = old_slug
                redirected_page.private = page.private
                text = 'This page has moved to: [[%s]]' % new_title
                redirected_page.save_draft_rev(text, use_markdown=True)
                redirected_page.publish_draft_rev()
                redirected_page.redirect = True

    @classmethod
    def delete(cls, page):
        page.acct = None
        db_session.delete(page)

    @classmethod
    def __sluggify(cls, acct, title):

        # build a page name from the valid characters in the page name,
        # removing any single quotes and substituting dashes for everything else
        valid_chars = 'abcdefghijklmnopqrstuvwxyz0123456789'
        slug = ''
        for char in title.lower():
            if char in valid_chars:
                slug += char
            elif char == "'":
                continue
            elif not slug.endswith('-'):
                slug += "-"
        slug = slug.strip('-')

        # limit to 100 chars
        slug = slug[:100].strip('-')

        # prepend underscore to numeric name
        try:
            slug = '_%s' % int(slug)
        except ValueError:
            pass

        # ensure uniqueness of name
        exists = lambda s: s in reserved_page_names or Page.query.\
            filter(Page.slug==s).\
            filter(Page.acct==acct).count() > 1
        slug_to_test = slug
        i = 1
        while exists(slug_to_test):
            slug_to_test = '%s-%s' % (slug, i)
            i+=1
        slug = slug_to_test

        return slug