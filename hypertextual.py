import os
from flask import \
    Flask, request, session, g, redirect, url_for, abort, flash
from chameleon import PageTemplateLoader
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound, MultipleResultsFound
from models import *

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

# render a user home page
@app.route('/<uid>/')
def user_home(uid):

    # get account if exists
    try:
        a = g.session.query(Account).filter(Account.uid==uid).one()
    except NoResultFound:
        abort(404)

    # get home page if exists
    try:
        p = g.session.query(Page).\
            filter(Page.page_name==None).\
            filter(Page.acct==a).one()
    except NoResultFound:
        if a == g.current_user:
            # create home page for current user if it doesn't exist
            # todo: do this on account creation
            p = Page()
            p.title = 'Home'
            p.page_name = None
            p.acct = a
            g.session.add(p)
            g.session.commit()
        else:
            abort(404)

    # render
    t = templates['page_view.html']
    return t.render(site_url=site_url, page=p, rev=p.curr_rev_num)

# render a user page
@app.route('/<uid>/<page_name>/')
def user_page(uid, page_name):

    # get account if exists
    try:
        a = g.session.query(Account).filter(Account.uid==uid).one()
    except NoResultFound:
        abort(404)

    # get page if exists
    try:
        p = g.session.query(Page).\
            filter(Page.page_name==page_name).\
            filter(Page.acct==a).one()
    except NoResultFound:
        abort(404)

    # render
    t = templates['page_view.html']
    return t.render(site_url=site_url, page=p, rev=p.curr_rev_num)

# edit a user home page
@app.route('/<uid>/edit/', methods=['POST', 'GET'])
def user_home_edit(uid):

    # if current user is not the owner, show 404
    if uid != g.current_user.uid:
        abort(404)

    # get home page if exists
    try:
        p = g.session.query(Page).\
            filter(Page.page_name==None).\
            filter(Page.acct==g.current_user).one()
    except NoResultFound:
        abort(404)

    if request.method == 'GET':

        # render the edit page
        t = templates['page_edit.html']
        return t.render(site_url=site_url, page=p)

    elif request.method == 'POST':

        # persist
        page_text = request.form['text']
        p.create_rev(page_text)
        g.session.commit()

        # redirect to view page
        url = url_for('user_home', uid=uid)
        return redirect(url)

# edit a user page
@app.route('/<uid>/<page_name>/edit', methods=['POST', 'GET'])
def user_page_edit(uid, page_name):

    # if current user is not the owner, show 404
    if uid != g.current_user.uid:
        abort(404)

    # get page if it exists
    try:
        p = g.session.query(Page).\
            filter(Page.page_name==page_name).\
            filter(Page.acct==g.current_user).one()
    except NoResultFound:
        abort(404)

    # show 404 if not found
    if p is None:
        abort(404)

    if request.method == 'GET':

        # render the edit page
        t = templates['page_edit.html']
        return t.render(site_url=site_url, page=p)

    elif request.method == 'POST':

        # persist
        page_text = request.form['text']
        p.create_rev(page_text)
        g.session.commit()

        # redirect to view page
        url = url_for('user_page', uid=uid, page_name=page_name)
        return redirect(url)

# create a user page
@app.route('/<uid>/create/', methods=['POST', 'GET'])
def user_page_create(uid):

    # if current user is not the owner, show 404
    if uid != g.current_user.uid:
        abort(404)

    title = request.args.get('title', '').strip()
    if title == '':
        # todo: create an error template
        return 'Error: Missing title parameter'

    # if a page by this name already exists, go to its edit page
    p = g.session.query(Page).\
        filter(Page.title==title).\
        filter(Page.acct==g.current_user).first()
    if p is not None:
        url = url_for('user_page_edit', uid=uid, page_name=p.page_name)
        return redirect(url)

    # create a new page
    p = Page()
    p.set_title(g.session, g.current_user, title)

    if request.method == 'GET':

        # render the edit page
        t = templates['page_edit.html']
        return t.render(site_url=site_url, page=p)

    elif request.method == 'POST':

        # persist
        page_text = request.form['text']
        p.create_rev(page_text)
        #g.session.add(p)
        g.current_user.pages.append(p)
        g.session.commit()

        # redirect to view page
        url = url_for('user_page', uid=uid, page_name=p.page_name)
        return redirect(url)

# specific version of a user home page
@app.route('/<uid>/<int:rev>/')
def user_page_rev(uid, rev):

    # get account if exists
    try:
        a = g.session.query(Account).filter(Account.uid==uid).one()
    except NoResultFound:
        abort(404)

    # get home page if exists
    try:
        p = g.session.query(Page).\
        filter(Page.page_name==None).\
        filter(Page.acct==a).\
        filter(Page.curr_rev_num>=rev).one()
    except NoResultFound:
        abort(404)

    # render
    t = templates['page_view.html']
    return t.render(site_url=site_url, page=p, rev=rev)

# specific version of a user page
@app.route('/<uid>/<int:rev>/<page_name>/')
def user_page_rev(uid, rev, page_name):

    # todo: make edit link go to the right place

    # get account if exists
    try:
        a = g.session.query(Account).filter(Account.uid==uid).one()
    except NoResultFound:
        abort(404)

    # get page if exists
    try:
        p = g.session.query(Page).\
        filter(Page.page_name==page_name).\
        filter(Page.acct==a).\
        filter(Page.curr_rev_num>=rev).one()
    except NoResultFound:
        abort(404)

    # render
    t = templates['page_view.html']
    return t.render(site_url=site_url, page=p, rev=rev)

if __name__ == '__main__':

    # set up some args to enable debugging in flask
    import argparse
    parser = argparse.ArgumentParser(description='Development Server Help')
    parser.add_argument("-d", "--debug", action="store_true", dest="debug_mode",
        help="run in debug mode (for use with PyCharm)", default=False)
    parser.add_argument("-p", "--port", dest="port",
        help="port of server (default:%(default)s)", type=int, default=5000)

    cmd_args = parser.parse_args()
    app_options = {"port": cmd_args.port }

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
