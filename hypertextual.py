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

RESERVED_WORDS = ['site','account','docs','doc','help','admin','administrator',
                  'edit','create','api','rss','json','xml','html','css','js']
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
        uid = request.form['uid'].strip().lower()
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

        uid = request.form['uid'].strip().lower()
        email = request.form['email'].strip().lower()
        pw = request.form['pw']
        pconfirm = request.form['pconfirm']
        valid = True

        # check whether uid or email already exist
        uid_exists = g.session.query(Account).filter(Account.uid==uid).first() is not None
        email_exists = email and g.session.query(Account).filter(Account.email==email).first() is not None

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

            # create account
            acct = Account(uid, pw, email)
            g.session.add(acct)
            g.session.commit()

            # add account to session
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

    # get any url arguments
    action = request.args.get('action', '').strip()

    if action == 'create':

        # redirect to home page if unauthorized user
        if not g.current_user or uid != g.current_user.uid:
            url = url_for('user_home', uid=uid)
            return redirect(url)

        # get account by uid; abort if not found
        try:
            acct = g.session.query(Account).filter(Account.uid==uid).one()
        except NoResultFound:
            abort(404)

        # redirect to the page if the title exists
        title = request.args.get('title', '').strip()
        page = g.session.query(Page).\
            filter(Page.title==title).\
            filter(Page.acct==acct).first()
        if page:
            url = url_for('user_page', uid=acct.uid, page_name=page.page_name)
            return redirect(url)

        # determine which renderer or handler to call
        if request.method == 'GET':
            return render_page_create(acct, title)
        elif request.method == 'POST':
            return handle_page_create(acct, title)

    else:
        return user_page(uid, None)

@app.route('/<uid>/<page_name>/', methods=['POST', 'GET'])
def user_page(uid, page_name):

    # get account by uid; abort if not found
    try:
        acct = g.session.query(Account).filter(Account.uid==uid).one()
    except NoResultFound:
        abort(404)

    # get page by page_name; abort if not found
    try:
        page = g.session.query(Page).\
            filter(Page.page_name==page_name).\
            filter(Page.acct==acct).one()
    except NoResultFound:
        abort(404)

    # get any url arguments
    action = request.args.get('action', '').strip()

    # ignore any action by unauthorized user
    if action and (not g.current_user or uid != g.current_user.uid):
        url = url_for('user_home', uid=uid)
        return redirect(url)

    # determine which renderer or handler to call
    if not action:
        rev_num = request.args.get('rev', '').strip()
        if rev_num == '':
            rev_num = None
        else:
            try:
                rev_num = int(rev_num)
            except ValueError:
                rev_num = -1
        return render_page_view(page, rev_num)
    elif action == 'edit':
        if request.method == 'GET':
            return render_page_edit(page)
        elif request.method == 'POST':
            return handle_page_edit(page)
    else:
        pass

def render_page_view(page, rev_num=None):

    # determine the rev num; redirect if it doesn't exist
    if rev_num is None:
        rev_num = page.curr_rev_num
    elif rev_num < 0 or rev_num > page.curr_rev_num:
        url = url_for('user_page', uid=page.acct.uid, page_name=page.page_name)
        return redirect(url)

    # get the revision and render it as html for display
    rev = page.revs[rev_num]
    if rev.use_markdown:
        page_html = render_markdown_to_html(g.session, g.current_user, page, rev_num)
    else:
        page_html = render_text_to_html(g.session, g.current_user, page, rev_num)

    # return the rendered page template
    t = templates['page_view.html']
    return t.render(
        g=g,
        site_url=site_url,
        page=page,
        rev_num=rev_num,
        page_html=page_html
    )

def render_page_create(acct, title):

    # create a new page
    page = Page(g.session, acct, title)
    page.create_draft_rev('', True)

    # render the edit page
    t = templates['page_edit.html']
    return t.render(
        g=g,
        site_url=site_url,
        page=page,
        rev=page.get_draft_rev(),
        acct=acct
    )

def handle_page_create(acct, title):

    publish = True

    # get form values
    page_text = request.form['text']
    use_markdown = request.form['use_markdown'] == 'True'

    # create a new page
    page = Page(g.session, acct, title)
    page.create_draft_rev(page_text, use_markdown)

    # persist
    page.create_draft_rev(page_text, use_markdown)
    if publish:
        page.publish_draft_rev()
    g.current_user.pages.append(page)
    g.session.commit()

    # redirect to view page
    url = url_for('user_page', uid=acct.uid, page_name=page.page_name)
    return redirect(url)

def render_page_edit(page):

    # render the edit page
    rev = page.get_draft_rev() or page.get_curr_rev()
    t = templates['page_edit.html']
    return t.render(
        g=g,
        site_url=site_url,
        rev=rev,
        page=page,
        acct=page.acct
    )

def handle_page_edit(page):

    publish = True

    # get form values
    text = request.form['text']
    use_markdown = request.form['use_markdown'] == 'True'

    # persist
    page.create_draft_rev(text, use_markdown)
    if publish:
        page.publish_draft_rev()
    g.session.commit()

    # redirect to view page
    if page.page_name is None:
        url = url_for('user_home', uid=page.acct.uid)
    else:
        url = url_for('user_page', uid=page.acct.uid, page_name=page.page_name)
    return redirect(url)

def main():

    # set up some args for enabling debug or reload mode
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('-d', action='store_true', dest='debug_mode', default=False)
    p.add_argument('-r', action='store_true', dest='reload_mode', default=False)
    cmd_args = p.parse_args()

    # set up app options
    app_options = {
        'port': app.config['PORT'],
        'host': '0.0.0.0',
        'debug': cmd_args.debug_mode, # show tracebacks in pycharm
        'use_debugger': cmd_args.debug_mode or cmd_args.reload_mode, # show tracebacks in browser
        'use_reloader': cmd_args.reload_mode # reload files on change
    }

    if cmd_args.reload_mode:
        # add static and template files to reloader
        extra_dirs = ['%s/static' % app_path, '%s/templates' % app_path]
        extra_files = extra_dirs[:]
        for extra_dir in extra_dirs:
            for dirname, dirs, files in os.walk(extra_dir):
                for filename in files:
                    if not filename.startswith('.'): # exclude vim swap files, etc.
                        filename = os.path.join(dirname, filename)
                        if os.path.isfile(filename):
                            extra_files.append(filename)
        app_options['extra_files'] = extra_files

    # run the app
    app.run(**app_options)

if __name__ == '__main__':
    main()
