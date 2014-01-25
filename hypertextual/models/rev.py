import re
from datetime import datetime
from markdown import markdown
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from diff_match_patch.diff_match_patch import diff_match_patch
from db import Base, db_session
from link import Link
from htlinks import HypertextualLinkExtension, render_a_tag, HT_LINK_RE

# TODO: do some caching of current / draft text

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
    links = relationship(Link, order_by='Link.link_num', backref='rev')

    def set_text(self, text):
        raw_text = self.__extract_links_from_text(text)
        self.__set_patch_text_from_raw_text(raw_text)

    def get_text(self):
        raw_text = self.__get_raw_text_from_patches()
        text = self.__inject_links_into_text(raw_text)
        return text

    def __set_patch_text_from_raw_text(self, raw_text):
        # diff raw text against the raw text of prior revision
        prior_raw_text = ''
        if self.rev_num > 0:
            prior_rev = self.page.revs[self.rev_num-1]
            prior_raw_text = prior_rev._Revision__get_raw_text_from_patches()
        dmp = diff_match_patch()
        patches = dmp.patch_make(prior_raw_text, raw_text)
        self.patch_text = dmp.patch_toText(patches)

    def __get_raw_text_from_patches(self):
        # apply patches from rev 0 through current rev
        # until the raw text has been reconstructed
        dmp = diff_match_patch()
        raw_text = ''
        for rev in self.page.revs[0:self.rev_num+1]:
            patches = dmp.patch_fromText(rev.patch_text)
            raw_text = dmp.patch_apply(patches, raw_text)[0]
        return raw_text

    def __extract_links_from_text(self, text):
        raw_text = text
        # TODO: extract link info from text
        return raw_text

    def __inject_links_into_text(self, raw_text):
        text = raw_text
        # TODO: inject link info back into text
        return text

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

    @classmethod
    def new(cls, page):
        rev = cls()
        page.revs.append(rev)
        db_session.add(rev)
        return rev