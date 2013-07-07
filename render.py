import re
from markdown import markdown
from htlinks import HypertextualLinkExtension, build_url, HT_LINK_RE

def render_a_tag(session, current_user, match):

    elems = match.groupdict()
    uid = elems['uid'].strip() if elems['uid'] is not None else None
    title = elems['title'].strip() if elems['title'] is not None else None
    alias = elems['alias'].strip() if elems['alias'] is not None else None

    if not alias:
        alias = title

    url, exists = build_url(
        session,
        current_user,
        uid,
        title
    )

    # todo: set classes for all conditions
    class_html = ''
    if not exists:
        class_html = ' class="link-create-page"'

    html = '<a href="%s"%s>%s</a>' % (url, class_html, alias)

    return html

def render_text_to_html(session, current_user, text):
    html = re.sub(HT_LINK_RE, lambda m: render_a_tag(session, current_user, m), text)
    html = '<pre>%s</pre>' % html
    return html

def render_markdown_to_html(session, current_user, text):
    linkExt = HypertextualLinkExtension(configs=[('session', session), ('current_user', current_user)])
    html = markdown(text, extensions=[linkExt])
    return html