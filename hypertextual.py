import os
from flask import \
    Flask, request, session, g, redirect, url_for, abort, flash
from chameleon import PageTemplateLoader
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from models import Page, Account
from render import render_text_to_html, render_markdown_to_html

app = Flask(__name__)
app.config.from_object('config')

app_path = os.path.dirname(os.path.abspath(__file__))
template_path = os.path.join(app_path, 'templates')
templates = PageTemplateLoader(template_path)
site_url = app.config['SITE_URL']

conn_str = app.config['CONN_STR']
engine = create_engine(conn_str)
Session = sessionmaker()
Session.configure(bind=engine)

RESERVED_WORDS = ['site','account','edit','create','api','rss','json','xml','html','css','js']
# also no numerics

def init_db():
    from models.base import DeclarativeBase
    DeclarativeBase.metadata.bind = engine
    DeclarativeBase.metadata.drop_all()
    DeclarativeBase.metadata.create_all(engine)
    return 'success'

@app.before_request
def before_request():
    g.session = Session()
    a = g.session.query(Account).filter(Account.uid=='alienlike').first()
    if a is None:
        a = Account()
        a.uid = 'alienlike'
        a.pw = 'secret'
        g.session.add(a)
        g.session.commit()
    g.current_user = a

@app.teardown_request
def teardown_request(exception):
    g.session.close()

@app.errorhandler(404)
def page_not_found(e):
    t = templates['404.html']
    return t.render(site_url=site_url), 404

# miscellaneous routes

@app.route('/robots.txt/')
def robots_txt():
    abort(404)

@app.route('/favicon.ico/')
def favicon_ico():
    abort(404)

@app.route('/sitemap.xml/')
def sitemap_xml():
    abort(404)

@app.route('/dublin.rdf/')
def dublin_rdf():
    abort(404)

@app.route('/opensearch.xml/')
def opensearch_xml():
    abort(404)

@app.route('/')
def site_home():
    t = templates['index.html']
    return t.render(site_url=site_url)

@app.route('/<uid>/', methods=['POST', 'GET'])
def user_home(uid):

    # get account if exists
    try:
        acct = g.session.query(Account).filter(Account.uid==uid).one()
    except NoResultFound:
        abort(404)

    # get any arguments
    action = request.args.get('action','').strip()
    title = request.args.get('title','').strip()

    if action == 'create' and title != '' and uid == g.current_user.uid:
        page = g.session.query(Page).\
            filter(Page.title==title).\
            filter(Page.acct==acct).first()
        if page:
            # if a page by this title exists, redirect to the page
            url = url_for('user_page', uid=uid, page_name=page.page_name)
            return redirect(url)
        else:
            return page_create(acct, title)
    else:
        # get home page if exists
        try:
            page = g.session.query(Page).\
                filter(Page.page_name==None).\
                filter(Page.acct==acct).one()
        except NoResultFound:
            if acct == g.current_user:
                # create home page for current user if it doesn't exist
                # todo: do this on account creation
                page = Page()
                page.title = 'Home'
                page.page_name = None
                page.create_rev('Welcome to hypertextual. This is your home page.')
                page.acct = acct
                g.session.add(page)
                g.session.commit()
            else:
                abort(404)
        if action == 'edit' and uid == g.current_user.uid:
            return page_edit(page)
        elif request.method == 'GET':
            return page_view(page)
        else:
            url = url_for('user_home', uid=uid)
            return redirect(url)

@app.route('/<uid>/<page_name>/', methods=['POST', 'GET'])
def user_page(uid, page_name):

    # get account if exists
    try:
        acct = g.session.query(Account).filter(Account.uid==uid).one()
    except NoResultFound:
        abort(404)

    # get page if exists
    try:
        page = g.session.query(Page).\
        filter(Page.page_name==page_name).\
        filter(Page.acct==acct).one()
    except NoResultFound:
        abort(404)

    action = request.args.get('action','').strip()

    if (action != '' and uid != g.current_user.uid) or (action == '' and request.method != 'GET'):
        # redirect to view page
        url = url_for('user_page', uid=uid, page_name=page_name)
        return redirect(url)
    elif action == 'edit':
        return page_edit(page)
    else:
        return page_view(page)

# view a user page
def page_view(page):

    # determine what rev num to use; abort if an invalid rev was provided
    rev = request.args.get('rev','').strip()
    try:
        rev = int(rev)
    except ValueError:
        rev = None
    if rev is None or rev < 0 or rev > page.curr_rev_num:
        rev = page.curr_rev_num

    text = page.get_text_for_rev(rev)
    if page.use_markdown:
        html = render_markdown_to_html(g.session, g.current_user, text)
    else:
        html = render_text_to_html(g.session, g.current_user, text)

    t = templates['page_view.html']
    return t.render(site_url=site_url, page=page, rev=rev, session=g.session, current_user=g.current_user, page_html=html)

# edit a page
def page_edit(page):

    if request.method == 'GET':

        # render the edit page
        t = templates['page_edit.html']
        return t.render(site_url=site_url, page=page)

    elif request.method == 'POST':

        # persist
        page_text = request.form['text']
        page.create_rev(page_text)
        g.session.commit()

        # redirect to view page
        if page.page_name is None:
            url = url_for('user_home', uid=page.acct.uid)
        else:
            url = url_for('user_page', uid=page.acct.uid, page_name=page.page_name)
        return redirect(url)

# create a user page
def page_create(acct, title):

    # if a page by this name already exists, go to its edit page
    page = g.session.query(Page).\
        filter(Page.title==title).\
        filter(Page.acct==acct).first()
    if page is not None:
        url = url_for('user_page_edit', uid=acct.uid, page_name=page.page_name)
        return redirect(url)

    # create a new page
    page = Page()
    page.set_title(g.session, acct, title)

    if request.method == 'GET':

        # render the edit page
        t = templates['page_edit.html']
        return t.render(site_url=site_url, page=page)

    elif request.method == 'POST':

        # persist
        page_text = request.form['text']
        page.create_rev(page_text)
        g.current_user.pages.append(page)
        g.session.commit()

        # redirect to view page
        url = url_for('user_page', uid=acct.uid, page_name=page.page_name)
        return redirect(url)

if __name__ == '__main__':

    app_options = dict()
    app_options['port'] = app.config['PORT']

    # set up some args to enable debugging in flask
    import argparse
    parser = argparse.ArgumentParser(description='Development Server Help')
    parser.add_argument("-d", "--debug", action="store_true", dest="debug_mode",
        help="run in debug mode (for use with PyCharm)", default=False)

    cmd_args = parser.parse_args()
    if cmd_args.debug_mode:
        app_options["debug"] = True
        app_options["use_debugger"] = False
        app_options["use_reloader"] = False

    # extra_files are any files beyond .py files that should
    # trigger a reload when changed (in debug mode, but not in flask)
    extra_dirs = ['%s/static' % app_path, '%s/templates' % app_path]
    extra_files = extra_dirs[:]
    for extra_dir in extra_dirs:
        for dirname, dirs, files in os.walk(extra_dir):
            for filename in files:
                if not filename.startswith('.'): # exclude vim swap files, etc.
                    filename = os.path.join(dirname, filename)
                    if os.path.isfile(filename):
                        extra_files.append(filename)
    app_options["extra_files"] = extra_files

    # run the app
    app.run(**app_options)
