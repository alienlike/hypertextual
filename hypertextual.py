import os
from flask import \
    Flask, request, session, g, redirect, url_for, abort, flash
from chameleon import PageTemplateLoader
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
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

@app.route('/robots.txt')
def robots_txt():
    return abort(404)

@app.route('/favicon.ico')
def favicon_ico():
    return abort(404)

@app.route('/')
def site_home():
    t = templates['index.html']
    return t.render(site_url=site_url)

@app.route('/<user>/')
def user_home(user):
    return user_page(user, '_home')

@app.route('/<user>/<page_name>/')
def user_page(user, page_name):

    # get user if exists
    a = g.session.query(Account).filter(Account.uid==user).first()
    if a is None:
        abort(404)

    # get page if it exists
    p = g.session.query(Page).\
            filter(Page.page_name==page_name).\
            filter(Page.acct==a).first()

    # if page found
    if p is not None:
        t = templates['page_view.html']
        return t.render(site_url=site_url, page=p)

    # if user is current user, redirect to the edit page
    elif user == g.current_user.uid:
        url = url_for('user_page_edit', user=user, page_name=page_name)
        return redirect(url)

    # otherwise show 404
    else:
        abort(404)

@app.route('/<user>/<page_name>/edit', methods=['POST', 'GET'])
def user_page_edit(user, page_name):

    # if page user is current user
    if user == g.current_user.uid:

        # get page if it exists
        p = g.session.query(Page).\
            filter(Page.page_name==page_name).\
            filter(Page.acct==g.current_user).first()

        # create a new page if none exists
        if p is None:
            p = Page()
            p.page_name = page_name
            p.title = page_name # todo: fix this
            p.acct = g.current_user

        if request.method == 'GET':

            # render the edit page
            t = templates['page_edit.html']
            return t.render(site_url=site_url, page=p)

        elif request.method == 'POST':

            # add page to session if it is newly created
            if p.id is None:
                g.session.add(p)

            # persist
            page_text = request.form['text']
            p.create_rev(page_text)
            g.session.commit()

            # mosey on
            url = url_for('user_page', user=user, page_name=page_name)
            return redirect(url)

    # otherwise show 404
    else:
        abort(404)

# routes to work on later

@app.route('/<user>/<page_name>/json')
def user_page_json(user, page_name):
    return '%s page: %s - json' % (user, page_name)

@app.route('/<user>/<int:rev>/<page_name>/')
def user_page_rev(user, rev, page_name):
    return '%s page: %s (rev %s)' % (user, page_name, rev)

@app.route('/<user>/<int:rev>/<page_name>/json')
def user_page_rev_json(user, rev, page_name):
    return '%s page: %s (rev %s) - json' % (user, page_name, rev)

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
