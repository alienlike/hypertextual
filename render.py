import re
from markdown import markdown
from htlinks import HypertextualLinkExtension, build_url, HT_LINK_RE

def render_a_tag(session, current_uid, page_uid, match):

    elems = match.groupdict()
    link_uid = elems['uid'].strip() if elems['uid'] is not None else None
    title = elems['title'].strip() if elems['title'] is not None else None
    alias = elems['alias'].strip() if elems['alias'] is not None else None

    if not alias:
        alias = title

    url, exists = build_url(
        session,
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

def render_text_to_html(session, current_user, page, rev_num):

    # get the text for the specified revision
    text = page.get_text_for_rev(rev_num)

    # get the current user's uid, if available
    current_uid = None
    if current_user:
        current_uid = current_user.uid

    # substititue an appropriate hyperlink for each "hypertext link"
    html = re.sub(HT_LINK_RE, lambda m: render_a_tag(session, current_uid, page.acct.uid, m), text)
    html = '<pre>%s</pre>' % html
    return html

def render_markdown_to_html(session, current_user, page, rev_num):

    # get the text for the specified revision
    text = page.get_text_for_rev(rev_num)

    # get the current user's uid, if available
    current_uid = None
    if current_user:
        current_uid = current_user.uid

    # let markdown process the text, but add the hypertext link extension first
    linkExt = HypertextualLinkExtension(configs=[
        ('session', session),
        ('current_uid', current_uid),
        ('page_uid', page.acct.uid)
    ])
    html = markdown(text, extensions=[linkExt])
    return html