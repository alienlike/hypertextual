from __future__ import absolute_import
from __future__ import unicode_literals
from markdown import Extension
from markdown.inlinepatterns import Pattern
from markdown.util import etree
from sqlalchemy.orm.exc import NoResultFound
from models import Page, Account
from config import SITE_URL

# An explanation of the regex below:
#    \[\[                                         (open brackets)
#    (?:[ ]*(?P<uid>[a-zA-Z][a-zA-Z0-9]*)[ ]*::)? (uid)
#    (?!.*::)                                     (negative look-ahead to prevent :: from matching again)
#    (?P<title>[^|\t\n\r\f\v]+)                   (page title)
#    (?:\|(?P<alias>[^|\t\n\r\f\v]+))?            (page alias)
#    \]\]                                         (close brackets)
HT_LINK_RE = r'\[\[(?:[ ]*(?P<uid>[a-zA-Z][a-zA-Z0-9]*)[ ]*::)?(?!.*::)(?P<title>[^|\t\n\r\f\v]+)(?:\|(?P<alias>[^|\t\n\r\f\v]+))?\]\]'

def build_url(session, current_user, uid, title):

    if uid is None:
        uid = current_user.uid

    exists = True
    try:
        page = session.query(Page).\
            join(Account.pages).\
            filter(Page.title==title, Account.uid==uid).one()
        url = page.get_url()
    except NoResultFound:
        exists = False
        if uid==current_user.uid:
            url = '%s/%s?action=create&title=%s' % (SITE_URL, uid, title)
        else:
            url = '#'

    return url, exists

class HypertextualLinkExtension(Extension):
    def __init__(self, configs):
        # set extension defaults
        self.config = {
            'current_user' : [None, 'Account instance.'],
            'session' : [None, 'SQLAlchemy session instance.'],
            }

        # Override defaults with user settings
        for key, value in configs :
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
        uid = elems['uid'].strip() if elems['uid'] is not None else None
        title = elems['title'].strip() if elems['title'] is not None else None
        alias = elems['alias'].strip() if elems['alias'] is not None else None

        if not alias:
            alias = title

        url, exists = build_url(
            self.config['session'],
            self.config['current_user'],
            uid,
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
        current_user = self.config['current_user']
        session = self.config['session']
        return current_user, session

def makeExtension(configs=None):
    return HypertextualLinkExtension(configs=configs)
