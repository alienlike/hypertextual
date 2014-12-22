import os
from markdown import markdown
from flask import Blueprint, request, g, session, abort
from models import Account, Breadcrumb

site_routes = Blueprint('site_routes', __name__,
                        template_folder='templates',
                        static_folder='static')

def get_html_from_markdown_file(md_path, default=None):
    doc_html = default
    if os.path.isfile(md_path):
        with open(md_path, 'r') as f:
            md = f.read()
            doc_html = markdown(md)
    return doc_html

@site_routes.route('/')
def site_home():
    md_path = '%s/index.md' % g.app_path
    doc_html = get_html_from_markdown_file(md_path, '')
    accts = _get_user_list_for_site_home()
    vals = {
        'doc_html': doc_html,
        'accts': accts
    }
    return g.render_template('index.html', **vals)

def _get_user_list_for_site_home():
    accts = Account.query.order_by(Account.uid).all()
    return accts

@site_routes.route('/site/')
@site_routes.route('/admin/')
@site_routes.route('/api/')
@site_routes.route('/robots.txt/')
@site_routes.route('/favicon.ico/')
@site_routes.route('/sitemap.xml/')
@site_routes.route('/dublin.rdf/')
@site_routes.route('/opensearch.xml/')
def reserved_names():
    abort(404)

@site_routes.route('/docs/', defaults={'title': 'index'}, methods=['GET'])
@site_routes.route('/docs/<title>/', methods=['GET'])
def read_doc(title):
    md_path = '%s/docs/%s.md' % (g.app_path, title)
    doc_html = get_html_from_markdown_file(md_path)
    breadcrumb = [Breadcrumb('docs','%s/docs' % g.site_url)]
    if title != 'index':
        breadcrumb.append(
            Breadcrumb(title,'%s/docs/%s' % (g.site_url, title))
        )
    if doc_html is None:
        abort(404)
    vals = {
        'doc_html': doc_html,
        'breadcrumb': breadcrumb,
    }
    return g.render_template('doc.html', **vals)

@site_routes.route('/site/login/', methods=['POST', 'GET'])
def login():

    # set default uid/password values
    uid = ''
    pw = ''

    # process form
    if request.method == 'POST':
        # check that uid exists
        uid = request.form['uid'].strip().lower()
        acct = Account.get_by_uid(uid)
        if acct:
            # validate password
            pw = request.form['pw']
            valid = acct.validate_password(pw)
            if valid:
                # add account to session
                session['current_uid'] = acct.uid
                g.current_user = acct
                # redirect to user home
                return g.redirect_to_user_page(uid, '__home')

    # show the login form
    vals = {
        'uid': uid,
        'pw': pw
    }
    return g.render_template('login.html', **vals)

@site_routes.route('/site/logout/')
def logout():
    del session['current_uid']
    g.current_user = None
    return g.redirect_to_site_home()
