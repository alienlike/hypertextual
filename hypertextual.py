import os, re
from flask import \
    Flask, request, session, g, redirect, url_for, abort, flash
from chameleon import PageTemplateLoader
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from models import Page, Account
from render import render_text_to_html, render_markdown_to_html
from validate_email import validate_email

# set up app
app = Flask(__name__)
app.config.from_object('config')

# set up templating
app_path = os.path.dirname(os.path.abspath(__file__))
template_path = os.path.join(app_path, 'templates')
templates = PageTemplateLoader(template_path)
site_url = app.config['SITE_URL']

# set up alchemy
conn_str = app.config['CONN_STR']
engine = create_engine(conn_str)
Session = sessionmaker()
Session.configure(bind=engine)

RESERVED_WORDS = ['site','account','admin','administrator','edit','create','api','rss','json','xml','html','css','js']
UID_REGEX = r'^([a-zA-Z][a-zA-Z0-9]*)$'

def init_db():
    from models.base import DeclarativeBase
    DeclarativeBase.metadata.bind = engine
    DeclarativeBase.metadata.drop_all()
    DeclarativeBase.metadata.create_all(engine)
    return 'success'

@app.before_request
def before_request():
    # create a db session for this request
    g.session = Session()
    # get current_user from session;
    current_user = session.get('current_user', None)
    if current_user is not None:
        # merge with db session to avoid DetachedInstanceError later on
        g.current_user = g.session.merge(current_user)
    else:
        g.current_user = None

@app.teardown_request
def teardown_request(exception):
    g.session.close()

@app.errorhandler(404)
def page_not_found(e):
    t = templates['404.html']
    return t.render(
        g=g,
        site_url=site_url
    ), 404

@app.route('/')
def site_home():
    # get users
    accts = g.session.query(Account).order_by(Account.uid).all()
    # show index page
    t = templates['index.html']
    return t.render(
        g=g,
        site_url=site_url,
        accts=accts
    )

@app.route('/site/login/', methods=['POST', 'GET'])
def login():

    # set default uid/password values
    uid = ''
    pw = ''

    # process form
    if request.method == 'POST':
        # check that uid exists
        uid = request.form['uid'].strip()
        acct = g.session.query(Account).filter(Account.uid==uid).first()
        if acct is not None:
            # validate password
            pw = request.form['pw']
            valid = acct.validate_password(pw)
            if valid:
                # add account to session
                session['current_user'] = acct
                g.current_user = acct
                # redirect to user home
                url = url_for('user_home', uid=uid)
                return redirect(url)

    # show the login form
    t = templates['login.html']
    return t.render(
        g=g,
        site_url=site_url,
        uid=uid,
        pw=pw
    )

@app.route('/site/logout/')
def logout():
    del session['current_user']
    g.current_user = None
    url = url_for('site_home')
    return redirect(url)

@app.route('/site/create-account/', methods=['POST', 'GET'])
def create_acct():

    # set default uid/password values
    uid = ''
    email = ''
    pw = ''
    pconfirm = ''
    errors = dict()

    # process form
    if request.method == 'POST':

        uid = request.form['uid'].strip()
        email = request.form['email'].strip()
        pw = request.form['pw']
        pconfirm = request.form['pconfirm']
        valid = True

        # check whether uid or email already exist
        uid_exists = g.session.query(Account).filter(Account.uid==uid).first() is not None
        email_exists = g.session.query(Account).filter(Account.email==email).first() is not None

        if not uid:
            valid = False
            errors['uid'] = 'Please provide a username.'
        elif not re.match(UID_REGEX, uid):
            valid = False
            errors['uid'] = 'Username must not begin with a numeral or contain special characters.'
        elif uid in RESERVED_WORDS or uid_exists:
            valid = False
            errors['uid'] = 'Username is not available. Please try another.'
        if email_exists:
            valid = False
            errors['email'] = 'Email already in use. Please use another.'
        elif email and not validate_email(email):
            valid = False
            errors['email'] = 'Invalid email address.'
        if not pw:
            valid = False
            errors['pw'] = 'Please provide a password.'
        elif pw != pconfirm:
            valid = False
            errors['pconfirm'] = 'Does not match password.'

        if valid:

            # create new user
            acct = Account()
            acct.uid = uid
            acct.email = email
            acct.set_password(pw)

            # create home page for new user
            page = Page()
            page.title = 'Home'
            page.page_name = None
            page.create_rev('Welcome to hypertextual. This is your home page.')
            page.acct = acct

            # persist
            g.session.add_all([acct, page])
            g.session.commit()

            # add account to session
            acct = g.session.query(Account).filter(Account.uid==uid).one()
            session['current_user'] = acct
            g.current_user = acct

            # redirect to new home page
            url = url_for('user_home', uid=uid)
            return redirect(url)

    t = templates['create_acct.html']
    return t.render(
        g=g,
        site_url=site_url,
        uid=uid,
        email=email,
        pw=pw,
        pconfirm=pconfirm,
        errors=errors
    )

@app.route('/<uid>/', methods=['POST', 'GET'])
def user_home(uid):

    # get account if exists
    try:
        acct = g.session.query(Account).filter(Account.uid==uid).one()
    except NoResultFound:
        abort(404)

    # get any arguments
    action = request.args.get('action', '').strip()
    title = request.args.get('title', '').strip()

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
            abort(404)
        if action == 'edit' and g.current_user and uid == g.current_user.uid:
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

    if action == 'edit' and g.current_user and uid == g.current_user.uid:
        return page_edit(page)
    elif request.method == 'GET':
        return page_view(page)
    else:
        url = url_for('user_page', uid=uid, page_name=page_name)
        return redirect(url)

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

    if page.use_markdown:
        html = render_markdown_to_html(g.session, g.current_user, page, rev)
    else:
        html = render_text_to_html(g.session, g.current_user, page, rev)

    t = templates['page_view.html']
    return t.render(
        g=g,
        site_url=site_url,
        page=page,
        rev=rev,
        page_html=html
    )

# edit a page
def page_edit(page):

    if request.method == 'GET':

        # render the edit page
        t = templates['page_edit.html']
        return t.render(
            g=g,
            site_url=site_url,
            page=page,
            acct=page.acct
        )

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
        url = url_for(
            'user_page_edit',
            uid=acct.uid,
            page_name=page.page_name
        )
        return redirect(url)

    # create a new page
    page = Page()
    page.set_title(g.session, acct, title)

    if request.method == 'GET':

        # render the edit page
        t = templates['page_edit.html']
        return t.render(
            g=g,
            site_url=site_url,
            page=page,
            acct=acct
        )

    elif request.method == 'POST':

        # persist
        page_text = request.form['text']
        page.create_rev(page_text)
        g.current_user.pages.append(page)
        g.session.commit()

        # redirect to view page
        url = url_for(
            'user_page',
            uid=acct.uid,
            page_name=page.page_name
        )
        return redirect(url)

# miscellaneous routes - move these to the top later

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

if __name__ == '__main__':

    app_options = {'port': app.config['PORT']}

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
    elif app.config['DEBUG']:
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
