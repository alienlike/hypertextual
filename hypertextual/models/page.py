from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from diff_match_patch.diff_match_patch import diff_match_patch
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
    curr_text = Column(String)
    draft_rev_num = Column(Integer)
    private = Column(Boolean)

    # relationships
    revs = relationship('Revision', order_by='Revision.id', backref='page', primaryjoin='Page.id==Revision.page_id')
    acct = None #-> Account.pages

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

        # add page name if required
        if self.page_name is not None:
            url += '/%s' % self.page_name

        # add rev num if required
        if rev_num is not None and rev_num != self.curr_rev_num:
            url += '?rev=%s' % rev_num

        return url

    def get_curr_rev(self):
        if self.curr_rev_num is not None:
            return self.revs[self.curr_rev_num]
        return None

    def get_draft_rev(self):
        if self.draft_rev_num is not None:
            return self.revs[self.draft_rev_num]
        return None

    # create or update draft revision
    def create_draft_rev(self, draft_text, use_markdown):

        if self.draft_rev_num is not None:
            # use existing draft revision
            rev = self.revs[self.draft_rev_num]
        else:
            # create new draft revision
            rev = Revision.new(self)
            rev.rev_num = \
                0 if self.curr_rev_num is None else self.curr_rev_num + 1
            self.draft_rev_num = rev.rev_num
        rev.use_markdown = use_markdown

        # get patch text
        rev.patch_text = ''
        if draft_text != self.curr_text:
            dmp = diff_match_patch()
            patches = dmp.patch_make(self.curr_text, draft_text)
            rev.patch_text = dmp.patch_toText(patches)

        # keep the draft text intact, in case publish_draft_rev gets called
        self.draft_text = draft_text

    # promote the draft revision to current revision
    def publish_draft_rev(self):
        # draft_text may or may not exist
        self.curr_text = self.draft_text \
            or self.get_text_for_rev(self.draft_rev_num)
        self.curr_rev_num = self.draft_rev_num
        self.draft_rev_num = None

    # Get the text for a particular revision
    def get_text_for_rev(self, rev_num):
        if rev_num == self.curr_rev_num:
            # current revision text is readily available
            text = self.curr_text
        else:
            # prior revision text requires us to apply successive
            # patches until the text has been reconstructed
            dmp = diff_match_patch()
            text = ''
            for rev in self.revs[0:rev_num+1]:
                patches = dmp.patch_fromText(rev.patch_text)
                text = dmp.patch_apply(patches, text)[0]
        return text

    def new_rev(self):
        rev = Revision.new(self)
        return rev
    
    @classmethod
    def new(cls, acct, title):
        page = cls()
        acct.pages.append(page)
        cls.__set_title(page, title)
        page.curr_text = ''
        page.draft_text = ''
        page.curr_rev_num = None
        page.draft_rev_num = None
        page.private = False
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