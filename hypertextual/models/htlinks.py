from __future__ import unicode_literals
from markdown import Extension
from markdown.inlinepatterns import Pattern
from markdown.util import etree
from sqlalchemy.orm.exc import NoResultFound
from acct import Account
from page import Page
from config import SITE_URL

# An explanation of the regex below:
#    \[\[                                         (open brackets)
#    (?:[ ]*(?P<uid>[a-zA-Z][a-zA-Z0-9]*)[ ]*::)? (uid)
#    (?!.*::)                                     (negative look-ahead to prevent :: from matching again)
#    (?P<title>[^|\t\n\r\f\v]+)                   (page title)
#    (?:\|(?P<alias>[^|\t\n\r\f\v]+))?            (page alias)
#    \]\]                                         (close brackets)
HT_LINK_RE = r'\[\[(?:[ ]*(?P<uid>[a-zA-Z][a-zA-Z0-9]*)[ ]*::)?(?!.*::)(?P<title>[^|\t\n\r\f\v]+)(?:\|(?P<alias>[^|\t\n\r\f\v]+))?\]\]'

def build_url(current_uid, page_uid, link_uid, title):

    # if no link uid, we assume the linked page
    # belongs to the same user as the linking page
    if not link_uid:
        link_uid = page_uid

    exists = True
    try:
        page = Page.query.\
            join(Account.pages).\
            filter(Page.title==title, Account.uid==link_uid).one()
        if page.user_can_view(current_uid):
            url = page.get_url()
        else:
            exists = False
            url = '#'
    except NoResultFound:
        exists = False
        if page_uid == current_uid:
            url = '%s/%s?action=create&title=%s' % (SITE_URL, current_uid, title)
        else:
            url = '#'

    return url, exists

def render_a_tag(current_uid, page_uid, match):

    elems = match.groupdict()
    link_uid = elems['uid'].strip() if elems['uid'] is not None else None
    title = elems['title'].strip() if elems['title'] is not None else None
    alias = elems['alias'].strip() if elems['alias'] is not None else None

    # alias is optional; use page title otherwise
    alias = alias or title

    url, exists = build_url(
        current_uid,
        page_uid,
        link_uid,
        title
    )

    # todo: set classes for all conditions
    class_html = ''
    if not exists:
        class_html = ' class="link-create-page"'

    html = '<a href="%s"%s>%s</a>' % (url, class_html, alias)

    return html

class HypertextualLinkExtension(Extension):

    def __init__(self, configs):
        # set extension defaults
        self.config = {
            'current_uid' : [None, 'Account uid.'],
            'page_uid' : [None, 'Page uid.']
        }

        # Override defaults with user settings
        for key, value in configs:
            self.setConfig(key, value)

    def extendMarkdown(self, md, md_globals):
        self.md = md

        # append to end of inline patterns
        hypertextualLinkPattern = HypertextualLinks(HT_LINK_RE, self.getConfigs())
        hypertextualLinkPattern.md = md
        md.inlinePatterns.add('hypertextuallink', hypertextualLinkPattern, "<not_strong")

class HypertextualLinks(Pattern):

    def __init__(self, pattern, config):
        super(HypertextualLinks, self).__init__(pattern)
        self.config = config

    def handleMatch(self, m):

        elems = m.groupdict()
        link_uid = elems['uid'].strip() if elems['uid'] is not None else None
        title = elems['title'].strip() if elems['title'] is not None else None
        alias = elems['alias'].strip() if elems['alias'] is not None else None

        # alias is optional; use page title otherwise
        alias = alias or title

        url, exists = build_url(
            self.config['current_uid'],
            self.config['page_uid'],
            link_uid,
            title
        )

        a = etree.Element('a')
        a.text = alias
        a.set('href', url)

        # todo: set classes for all conditions
        if not exists:
            a.set('class', 'link-create-page')

        return a

    def _getMeta(self):
        """ Return meta data or config data. """
        current_uid = self.config['current_uid']
        page_uid = self.config['page_uid']
        return current_uid, page_uid

def makeExtension(configs=None):
    return HypertextualLinkExtension(configs=configs)