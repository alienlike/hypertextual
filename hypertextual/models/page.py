from datetime import datetime
import re
import translitcodec
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from breadcrumb import Breadcrumb
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

    slug = Column(String(128)) # http://hypertextual/<slug>
    title = Column(String(1024)) # todo: put some check in place to deal with longer titles
    curr_rev_num = Column(Integer)
    draft_rev_num = Column(Integer)
    private = Column(Boolean)
    redirect = Column(Boolean)

    # relationships
    acct = None #-> Account.pages
    revs = relationship(
        Revision,
        order_by='Revision.id',
        cascade='all,delete-orphan',
        passive_deletes=True,
        backref='page',
        primaryjoin='Page.id==Revision.page_id'
    )

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

    def get_breadcrumb(self):
        breadcrumb = []
        if not self.private:
            breadcrumb.append(
                Breadcrumb(self.acct.uid, '/%s' % self.acct.uid)
            )
        else:
            breadcrumb.append(
                Breadcrumb('_%s' % self.acct.uid, '/_%s' % self.acct.uid)
            )
        if self.slug not in ['__private','__home']:
            breadcrumb.append(
                Breadcrumb(self.title, self.get_url())
            )
        return breadcrumb

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
            self.revs.remove(rev)
            self.draft_rev_num = None

    def publish_draft_rev(self):
        self.curr_rev_num = self.draft_rev_num
        self.draft_rev_num = None
        self.redirect = False

    @classmethod
    def new(cls, acct, title):
        page = cls()
        page.title = title
        page.slug = cls.__slugify(acct, title)
        acct.pages.append(page)
        db_session.add(page)
        return page

    @classmethod
    def title_exists(cls, uid, title):
        from acct import Account
        acct_page_join = db_session.query(Account).\
            join(Account.pages).\
            filter(Account.uid==uid).\
            filter(cls.title==title)
        title_exists = db_session.query(
            acct_page_join.exists()
        ).scalar()
        return title_exists

    @classmethod
    def slug_exists(cls, uid, slug):
        from acct import Account
        acct_page_join = db_session.query(Account).\
            join(Account.pages).\
            filter(Account.uid==uid).\
            filter(cls.slug==slug)
        slug_exists = db_session.query(
            acct_page_join.exists()
        ).scalar()
        return slug_exists

    @classmethod
    def move(cls, page, new_title, create_redirect=False):
        if new_title != page.title:
            old_title = page.title
            old_slug = page.slug
            page.title = new_title
            page.slug = cls.__slugify(page.acct, new_title)
            if create_redirect:
                redirected_page = cls.new(page.acct, old_title)
                redirected_page.slug = old_slug
                redirected_page.private = page.private
                text = 'This page has moved: [[%s]]' % new_title
                redirected_page.save_draft_rev(text, use_markdown=True)
                redirected_page.publish_draft_rev()
                redirected_page.redirect = True

    @classmethod
    def delete(cls, page):
        page.acct.pages.remove(page)

    @classmethod
    def __slugify(cls, acct, title):

        # refer to http://flask.pocoo.org/snippets/5/
        punct_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.]+')
        delim = u'-'
        result = []
        for word in punct_re.split(title.lower()):
            word = word.encode('translit/long')
            if word:
                result.append(word)
        slug = unicode(delim.join(result))

        # todo: deal with the case where generated slug is an empty string

        # limit to 120 chars
        slug = slug[:120].strip('-')

        # ensure uniqueness of name
        slug_to_test = slug
        i = 1
        while slug_to_test in reserved_page_names or Page.slug_exists(acct.uid, slug_to_test):
            slug_to_test = '%s-%s' % (slug, i)
            i+=1
        slug = slug_to_test

        return slug