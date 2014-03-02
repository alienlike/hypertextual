import os, re, argparse
from flask import Flask, request, session, g, redirect, url_for, abort
from chameleon import PageTemplateLoader
from sqlalchemy import create_engine
from models import db_session, Page, Account
from validate_email import validate_email

app = Flask(__name__)
site_url = None
app_path = None
templates = None

def main():
    configure_flask_app()
    configure_db_session()
    set_globals()
    command_line_args = get_command_line_args()
    app_options = get_app_options(command_line_args)
    app.run(**app_options)

def configure_flask_app():
    app.config.from_object('config')

def configure_db_session():
    conn_str = app.config['CONN_STR']
    engine = create_engine(conn_str)
    db_session.configure(bind=engine)

def set_globals():
    global site_url, app_path, templates
    site_url = get_site_url()
    app_path = get_app_path()
    templates = get_chameleon_templates()

def get_site_url():
    site_url = app.config['SITE_URL']
    return site_url

def get_app_path():
    app_path = os.path.dirname(os.path.abspath(__file__))
    return app_path

def get_chameleon_templates():
    template_path = os.path.join(app_path, 'templates')
    template_loader = PageTemplateLoader(template_path)
    return template_loader

def get_command_line_args():
    # set up some args for enabling debug or reload mode
    p = argparse.ArgumentParser()
    p.add_argument('-d', action='store_true', dest='debug_mode', default=False)
    p.add_argument('-r', action='store_true', dest='reload_mode', default=False)
    command_line_args = p.parse_args()
    return command_line_args

def get_app_options(command_line_args):
    app_options = {
        'port': app.config['PORT'],
        'host': '0.0.0.0',
        'debug': command_line_args.debug_mode, # show tracebacks in pycharm
        'use_debugger': command_line_args.debug_mode or command_line_args.reload_mode, # show tracebacks in browser
        'use_reloader': command_line_args.reload_mode # reload files on change
    }
    if command_line_args.reload_mode:
        app_options['extra_files'] = get_static_files_for_reload_mode()
    return app_options

def get_static_files_for_reload_mode():
    static_dirs = ['%s/static' % app_path, '%s/templates' % app_path]
    static_files = static_dirs[:]
    for static_dir in static_dirs:
        for dir_name, dirs, file_names in os.walk(static_dir):
            for file_name in file_names:
                if not file_name.startswith('.'): # exclude vim swap files, etc.
                    file_name = os.path.join(dir_name, file_name)
                    if os.path.isfile(file_name):
                        static_files.append(file_name)

@app.before_request
def before_request():
    g.current_user = get_current_user_from_session()

def get_current_user_from_session():
    # retrieve current_user from session, where it is kept between requests
    current_user = session.get('current_user', None)
    if current_user:
        # current_user will have been detached from its db session in a prior request;
        # merge it with the current db session to avoid a DetachedInstanceError
        current_user = db_session.merge(current_user)
    return current_user

@app.teardown_request
def teardown_request(exception=None):
    try:
        db_session.commit()
    except:
        db_session.rollback()
        raise

@app.teardown_appcontext
def teardown_appcontext(exception=None):
    # remove database session at the end of the request,
    # or when the application shuts down
    db_session.remove()

@app.errorhandler(404)
def page_not_found(e):
    vals = {
        'g': g,
        'site_url': site_url
    }
    return render_template('404.html', **vals), 404

@app.route('/')
def site_home():
    # get users
    accts = Account.query.order_by(Account.uid).all()
    # show index page
    vals = {
        'g': g,
        'site_url': site_url,
        'accts': accts
    }
    return render_template('index.html', **vals)

@app.route('/site/login/', methods=['POST', 'GET'])
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
                session['current_user'] = acct
                g.current_user = acct
                # redirect to user home
                url = url_for('user_home', uid=uid)
                return redirect(url)

    # show the login form
    vals = {
        'g': g,
        'site_url': site_url,
        'uid': uid,
        'pw': pw
    }
    return render_template('login.html', **vals)

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
        uid_exists = Account.uid_exists(uid)
        email_exists = email and Account.email_exists(email)

        reserved_names = ['site','account','docs','doc','help','admin','administrator',
                          'edit','create','api','rss','json','xml','html','css','js']
        uid_re = r'^([a-zA-Z][a-zA-Z0-9]*)$'

        if not uid:
            valid = False
            errors['uid'] = 'Please provide a username.'
        elif not re.match(uid_re, uid):
            valid = False
            errors['uid'] = 'Username must not begin with a numeral or contain special characters.'
        elif uid in reserved_names or uid_exists:
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
            acct = Account.new(uid, pw, email)
            db_session.commit() # or weird stuff will happen

            # add account to session (effectively log the new user in)
            session['current_user'] = acct
            g.current_user = acct

            # redirect to new home page
            url = url_for('user_home', uid=uid)
            return redirect(url)

    vals = {
        'g': g,
        'site_url': site_url,
        'uid': uid,
        'email': email,
        'pw': pw,
        'pconfirm': pconfirm,
        'errors': errors
    }
    return render_template('create_acct.html', **vals)

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
        acct = Account.get_by_uid(uid)
        if acct is None:
            abort(404)

        # redirect to the page if the title exists
        title = request.args.get('title', '').strip()
        page = acct.get_page_by_title(title)
        if page:
            url = url_for('user_page', uid=acct.uid, slug=page.slug)
            return redirect(url)

        # determine which renderer or handler to call
        if request.method == 'GET':
            return render_page_create(acct, title)
        elif request.method == 'POST':
            return handle_page_create(acct, title)

    else:
        return user_page(uid, None)

@app.route('/<uid>/<slug>/', methods=['POST', 'GET'])
def user_page(uid, slug):

    # get account by uid; abort if not found
    acct = Account.get_by_uid(uid)
    if acct is None:
        abort(404)

    # get page by slug; abort if not found
    page = acct.get_page_by_slug(slug)
    if page is None:
        abort(404)

    # check user access
    if not page.user_can_view(g.current_user):
        abort(404)

    # get any url arguments
    action = request.args.get('action', '').strip()

    # ignore any action by unauthorized user
    if action and not page.user_is_owner(g.current_user):
        if slug is None:
            url = url_for('user_home', uid=uid)
        else:
            url = url_for('user_page', uid=uid, slug=slug)
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
        if page.slug is None:
            url = url_for('user_home', uid=page.acct.uid)
        else:
            url = url_for('user_page', uid=page.acct.uid, slug=page.slug)
        return redirect(url)

    # get the revision and render it as html for display
    page_html = ''
    if rev_num is not None:
        current_uid = None
        if g.current_user:
            current_uid = g.current_user.uid
        rev = page.revs[rev_num]
        page_html = rev.render_to_html(current_uid)

    # return the rendered page template
    vals = {
        'g': g,
        'site_url': site_url,
        'page': page,
        'rev_num': rev_num,
        'page_html': page_html
    }
    return render_template('page_view.html', **vals)

def render_page_create(acct, title):

    # create a new page
    page = Page.new(acct, title)
    page.save_draft_rev('', True)

    # render the edit page
    vals = {
        'g': g,
        'site_url': site_url,
        'page': page,
        'rev': page.get_draft_rev(),
        'acct': acct
    }
    return render_template('page_edit.html', **vals)

def handle_page_create(acct, title):

    # get form values
    page_text = request.form['text']
    use_markdown = request.form['use_markdown'] == 'True'
    private = request.form.has_key('private')

    # get button clicks
    publish = request.form.has_key('publish')
    save_draft = request.form.has_key('save_draft')
    cancel = request.form.has_key('cancel')

    if cancel:

        # TODO: redirect to requesting page
        url = url_for('user_home', uid=acct.uid)
        return redirect(url)

    elif save_draft or publish:

        # create a new page
        page = Page.new(acct, title)
        page.private = private
        page.save_draft_rev(page_text, use_markdown)

        # persist
        if publish:
            page.publish_draft_rev()

        # redirect to view page
        url = url_for('user_page', uid=acct.uid, slug=page.slug)
        return redirect(url)

def render_page_edit(page):

    # render the edit page
    rev = page.get_draft_rev() or page.get_curr_rev()
    vals = {
        'g': g,
        'site_url': site_url,
        'page': page,
        'rev': rev,
        'acct': page.acct
    }
    return render_template('page_edit.html', **vals)

def handle_page_edit(page):

    # get form values
    text = request.form['text']
    use_markdown = request.form['use_markdown'] == 'True'
    private = request.form.has_key('private') or page.slug == '_private'

    # get button clicks
    publish = request.form.has_key('publish')
    save_draft = request.form.has_key('save_draft')
    revert = request.form.has_key('revert')
    cancel = request.form.has_key('cancel')

    if revert or cancel:
        if revert:
            page.revert_draft_rev()
        if page.slug is None:
            url = url_for('user_home', uid=page.acct.uid)
        else:
            url = url_for('user_page', uid=page.acct.uid, slug=page.slug)
        return redirect(url)

    elif save_draft or publish:

        # persist
        page.private = private
        page.save_draft_rev(text, use_markdown)
        if publish:
            page.publish_draft_rev()

        # redirect to view page
        if page.slug is None:
            url = url_for('user_home', uid=page.acct.uid)
        else:
            url = url_for('user_page', uid=page.acct.uid, slug=page.slug)
        return redirect(url)

def render_template(template_name, **vals):
    template = templates[template_name]
    return template.render(**vals)

if __name__ == '__main__':
    main()