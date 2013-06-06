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
            filter(Page.name_for_url==page_name).\
            filter(Page.owner==a).first()

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

@app.route('/<user>/<page_name>/edit')
def user_page_edit(user, page_name):

    # if page user is current user
    if user == g.current_user.uid:

        # get page if it exists
        p = g.session.query(Page).\
                filter(Page.name_for_url==page_name).\
                filter(Page.owner==g.current_user).first()

        # create a new page if none exists
        if p is None:
            p = Page()

        # render the edit page
        t = templates['page_edit.html']
        return t.render(site_url=site_url, page=p)

    # otherwise show 404
    else:
        abort(404)

@app.route('/<user>/<page_name>/save', methods=['POST'])
def user_page_save(user, page_name):
    # todo: write page to db
    pass

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
    # extra_files are any files beyond .py files that should
    # trigger a reload when changed (in debug mode only)
    extra_dirs = ['%s/static' % app_path, '%s/templates' % app_path]
    extra_files = extra_dirs[:]
    for extra_dir in extra_dirs:
        for dirname, dirs, files in os.walk(extra_dir):
            for filename in files:
                if not filename.startswith('.'): # exclude vim swap files, etc.
                    filename = os.path.join(dirname, filename)
                    if os.path.isfile(filename):
                        extra_files.append(filename)
    # run the app
    app.run(extra_files=extra_files)