from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .base import DeclarativeBase
from .rev import Revision

class Page(DeclarativeBase):

    # table
    __tablename__ = 'page'

    # columns
    id = Column(Integer, primary_key=True, nullable=False)
    acct_id = Column(Integer, ForeignKey('acct.id', ondelete='CASCADE'), nullable=False)
    create_ts = Column(DateTime, default=datetime.now)

    page_name = Column(String, nullable=True)
    title = Column(String, nullable=False)
    orig_text = Column(String, nullable=False)
    curr_text = Column(String, nullable=False)
    curr_rev_num = Column(Integer, nullable=False)

    # relationships
    revs = relationship('Revision', order_by='Revision.id', backref='page', primaryjoin='Page.id==Revision.page_id')
    acct = None #-> Account.pages

    def __init__(self):
        self.orig_text = ''
        self.curr_text = ''
        self.curr_rev_num = None

    def use_markdown(self):
        if self.curr_rev_num is None:
            return True
        else:
            return self.revs[self.curr_rev_num].use_markdown

    def get_url(self, rev=None):

        # start with uid
        from config import SITE_URL
        url = '%s/%s' % (SITE_URL, self.acct.uid)

        # add rev num if required
        if rev is not None and rev != self.curr_rev_num:
            url += '/%s' % rev

        # add page name if required
        if self.page_name is not None:
            url += '/%s' % self.page_name

        return url

    def set_title(self, session, account, title):

        # set title
        self.title = title

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

        # limit to 30 chars
        page_name = page_name[:100].strip('-')

        # prepend underscore to numeric name
        try:
            page_name = '_%s' % int(page_name)
        except ValueError:
            pass

        # ensure uniqueness of name
        exists = lambda name: session.query(Page).\
            filter(Page.page_name==name).\
            filter(Page.acct==account).count()
        name_to_test = page_name
        i = 1
        while exists(name_to_test):
            i+=1
            name_to_test = '%s-%s' % (page_name, i)

        # set page name
        self.page_name = name_to_test

    # Generate a new revision by diffing the new text against the current text.
    def create_rev(self, new_text, use_markdown):

        # first rev
        if self.curr_rev_num is None:
            rev = Revision()
            rev.rev_num = 0
            rev.patch_text = None
            rev.use_markdown = use_markdown
            self.revs.append(rev)
            self.curr_rev_num = 0
            self.orig_text = new_text
            self.curr_text = new_text

        # subsequent rev
        elif new_text != self.curr_text:
            rev = Revision()
            rev.rev_num = self.curr_rev_num + 1
            rev.use_markdown = use_markdown
            from diff_match_patch.diff_match_patch import diff_match_patch
            dmp = diff_match_patch()
            patches = dmp.patch_make(self.curr_text, new_text)
            rev.patch_text = dmp.patch_toText(patches)
            self.revs.append(rev)
            self.curr_rev_num = rev.rev_num
            self.curr_text = new_text

        # change to use_markdown only
        else:
            curr_rev = self.revs[self.curr_rev_num]
            if curr_rev.use_markdown != use_markdown:
                curr_rev.use_markdown = use_markdown

    # Get the text for a particular revision
    def get_text_for_rev(self, rev_num):
        if rev_num == 0:
            text = self.orig_text
        elif rev_num == self.curr_rev_num:
            text = self.curr_text
        else:
            # apply successive patches until the text for the
            # requested version has been reconstructed
            from diff_match_patch.diff_match_patch import diff_match_patch
            dmp = diff_match_patch()
            text = self.orig_text
            for rev in self.revs[1:rev_num+1]:
                patches = dmp.patch_fromText(rev.patch_text)
                text = dmp.patch_apply(patches, text)[0]
        return text