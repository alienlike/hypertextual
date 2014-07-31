import re
from datetime import datetime
from markdown import markdown
from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from diff_match_patch.diff_match_patch import diff_match_patch
from db import Base, db_session
from md import HypertextualLinkExtension, HT_LINK_RE, HT_PLACEHOLDER_RE
from link import Link

class Revision(Base):

    # table
    __tablename__ = 'rev'

    # columns
    id = Column(Integer, primary_key=True, nullable=False)
    page_id = Column(Integer, ForeignKey('page.id', ondelete='CASCADE'), nullable=False)
    create_ts = Column(DateTime, nullable=False, default=datetime.now)

    rev_num = Column(Integer, nullable=False)
    patch_text = Column(Text)
    use_markdown = Column(Boolean, nullable=False)

    # relationships
    page = None #-> Page.revs
    links = relationship(
        Link,
        order_by='Link.link_num',
        cascade='all,delete-orphan',
        passive_deletes=True,
        backref='rev'
    )

    def render_to_html(self, current_uid):
        if self.use_markdown:
            html = self.__render_markdown_to_html(current_uid)
        else:
            html = self.__render_text_to_html(current_uid)
        return html

    def set_text(self, text):
        raw_text = self.__extract_links_from_text(text)
        self.__set_patch_text_from_raw_text(raw_text)

    def get_text(self):
        raw_text = self.__get_raw_text_from_patches()
        text = self.__inject_links_into_raw_text(raw_text)
        return text

    def __render_markdown_to_html(self, current_uid):
        raw_text = self.__get_raw_text_from_patches()
        linkExt = HypertextualLinkExtension(configs=[
            ('current_uid', current_uid),
            ('rev', self)
        ])
        html = markdown(raw_text, extensions=[linkExt])
        return html

    def __render_text_to_html(self, current_uid):
        raw_text = self.__get_raw_text_from_patches()
        html = re.sub(
            HT_PLACEHOLDER_RE,
            lambda match: self.__get_link_html(match, current_uid),
            raw_text
        )
        html = '<pre>%s</pre>' % html
        return html

    def __get_link_html(self, placeholder_match, current_uid):
        link = self.__parse_placeholder_match(placeholder_match)
        link_html = link.get_link_html(current_uid)
        return link_html

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
        Link.query.filter(Link.rev_id==self.id).delete()
        raw_text = re.sub(HT_LINK_RE, self.__extract_link, text)
        return raw_text

    def __inject_links_into_raw_text(self, raw_text):
        text = re.sub(HT_PLACEHOLDER_RE, self.__inject_link, raw_text)
        return text

    def __extract_link(self, link_match):
        uid, title, alias = self.__parse_link_match(link_match)
        link_num = len(self.links) # +1
        link = Link.new(self, link_num, uid, title, alias)
        placeholder_text = link.get_placeholder_text()
        return placeholder_text

    def __inject_link(self, placeholder_match):
        link = self.__parse_placeholder_match(placeholder_match)
        link_text = link.get_link_text()
        return link_text

    def __parse_link_match(self, link_match):
        elems = link_match.groupdict()
        uid = elems['uid']
        title = elems['title']
        alias = elems['alias']
        if uid:
            uid = uid.strip()
        title = title.strip()
        if alias:
            alias = alias.strip()
        return uid, title, alias

    def __parse_placeholder_match(self, placeholder_match):
        elems = placeholder_match.groupdict()
        link_num = int(elems['linknum'])
        link = self.links[link_num]
        return link

    @classmethod
    def new(cls, page):
        rev = cls()
        page.revs.append(rev)
        db_session.add(rev)
        return rev