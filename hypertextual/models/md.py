from __future__ import unicode_literals
from markdown import Extension
from markdown.inlinepatterns import Pattern

#    \[\[                                         (open brackets)
#    (?:[ ]*(?P<uid>[a-zA-Z][a-zA-Z0-9]*)[ ]*::)? (uid)
#    (?!.*::)                                     (negative look-ahead to prevent :: from matching again)
#    (?P<title>[^|\t\n\r\f\v]+)                   (page title)
#    (?:\|(?P<alias>[^|\t\n\r\f\v]+))?            (page alias)
#    \]\]                                         (close brackets)
HT_LINK_RE = r'\[\[(?:[ ]*(?P<uid>[a-zA-Z][a-zA-Z0-9]*)[ ]*::)?(?!.*::)(?P<title>[^|\t\n\r\f\v]+)(?:\|(?P<alias>[^|\t\n\r\f\v]+))?\]\]'

#    \[\[                (open brackets)
#    (?P<linknum>[0-9]*) (link number)
#    \]\]                (close brackets)
HT_PLACEHOLDER_RE = r'\[\[(?P<linknum>[0-9]*)\]\]'

class HypertextualLinkExtension(Extension):

    def __init__(self, configs):
        # set extension defaults
        self.config = {
            'current_uid' : [None, 'Current uid.'],
            'rev' : [None, 'Revision.']
        }
        # Override defaults with user settings
        for key, value in configs:
            self.setConfig(key, value)

    def extendMarkdown(self, md, md_globals):
        self.md = md
        # append to end of inline patterns
        hypertextualLinkPattern = HypertextualLinks(HT_PLACEHOLDER_RE, self.getConfigs())
        hypertextualLinkPattern.md = md
        md.inlinePatterns.add('hypertextuallink', hypertextualLinkPattern, "<not_strong")

class HypertextualLinks(Pattern):

    def __init__(self, pattern, config):
        super(HypertextualLinks, self).__init__(pattern)
        self.config = config

    def handleMatch(self, match):
        current_uid = self.config['current_uid']
        rev = self.config['rev']
        link = rev._Revision__parse_placeholder_match(match)
        elem = link.get_link_markdown_elem(current_uid)
        return elem

    def _getMeta(self):
        """ Return meta data or config data. """
        current_uid = self.config['current_uid']
        rev = self.config['rev']
        return current_uid, rev

def makeExtension(configs=None):
    return HypertextualLinkExtension(configs=configs)