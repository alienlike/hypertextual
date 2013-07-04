from __future__ import absolute_import
from __future__ import unicode_literals
import re
from markdown import Extension
from markdown.inlinepatterns import Pattern
from markdown.util import etree
from sqlalchemy.orm.exc import NoResultFound
from models import Page
from models import Account
from config import SITE_URL

WIKILINK_RE = re.compile(
    '\[\[' + # open brackets
    '(?:[ ]*(?P<uid>[a-zA-Z][a-zA-Z0-9]*)[ ]*::)?' + # uid
    '(?!.*::)' + # negative look-ahead to prevent :: from matching again
    '(?P<title>[^|\t\n\r\f\v]+)' + # page title
    '(?:\|(?P<alias>[^|\t\n\r\f\v]+))?' + # link text
    '\]\]' # close brackets
)

def build_url(session, current_user, uid, title):

    if uid is None:
        uid = current_user.uid

    try:
        page = session.query(Page).\
        join(Account.pages).\
        filter(Page.title==title, Account.uid==uid).one()
        url = page.get_url()
    except NoResultFound:
        if uid==current_user.uid:
            url = '%s/%s?action=create&title=%s' % (SITE_URL, uid, title)
        else:
            url = '#'

    return url

class WikiLinkExtension(Extension):
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
        wikilinkPattern = WikiLinks(WIKILINK_RE, self.getConfigs())
        wikilinkPattern.md = md
        md.inlinePatterns.add('wikilink', wikilinkPattern, "<not_strong")

class WikiLinks(Pattern):
    def __init__(self, pattern, config):
        super(WikiLinks, self).__init__(pattern)
        self.config = config

    def handleMatch(self, m):

        elems = m.groupdict()
        uid = elems['uid'].strip() if elems['uid'] is not None else None
        title = elems['title'].strip() if elems['title'] is not None else None
        alias = elems['alias'].strip() if elems['alias'] is not None else None

        if title:
            url = build_url(
                self.config['session'],
                self.config['current_user'],
                uid,
                title
            )
            a = etree.Element('a')
            a.text = alias
            a.set('href', url)
            # todo: set class if req'd
            # a.set('class', 'wikilink')
        else:
            a = ''
        return a

    def _getMeta(self):
        """ Return meta data or config data. """
        current_user = self.config['current_user']
        session = self.config['session']
        return current_user, session

def makeExtension(configs=None) :
    return WikiLinkExtension(configs=configs)
