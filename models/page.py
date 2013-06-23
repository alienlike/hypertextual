from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .base import DeclarativeBase
from .rev import Revision
from diff_match_patch.diff_match_patch import diff_match_patch

class Page(DeclarativeBase):

    # table
    __tablename__ = 'page'

    # columns
    id = Column(Integer, primary_key=True, nullable=False)
    owner_acct_id = Column(Integer, ForeignKey('acct.id', ondelete='CASCADE'), nullable=False)
    name_for_url = Column(String, nullable=False)
    title = Column(String, nullable=False)
    orig_text = Column(String, nullable=False)
    curr_text = Column(String, nullable=False)
    curr_rev_num = Column(Integer, nullable=False)
    create_ts = Column(DateTime, default=datetime.now)

    # relationships
    revs = relationship('Revision', order_by='Revision.id', backref='page', primaryjoin='Page.id==Revision.page_id')
    owner = None #-> Account.pages

    def create_rev(self, new_text):

        # create the new revision
        rev = Revision()
        rev.rev_num = len(self.revs) # zero-based
        self.curr_rev_num = rev.rev_num
        self.revs.append(rev)

        if self.curr_rev_num == 0:
            self.orig_text = new_text
            rev.patch_text = None
        else:
            dmp = diff_match_patch()
            patches = dmp.patch_make(self.curr_text, new_text)
            rev.patch_text = dmp.patch_toText(patches)

        self.curr_text = new_text

    def get_text_for_rev(self, rev_num):
        if rev_num == 0:
            text = self.orig_text
        elif rev_num == self.curr_rev_num:
            text = self.curr_text
        else:
            dmp = diff_match_patch()
            patches = []
            for rev in self.revs[1:rev_num+1]:
                patch = dmp.patch_fromText(rev.patch_text)
                patches.append(patch)
            text = dmp.patch_apply(patches, self.orig_text)[0]
        return text
