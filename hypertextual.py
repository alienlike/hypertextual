import os
from flask import Flask, request, session, g, redirect, url_for, \
             abort, flash
from contextlib import closing
from chameleon import PageTemplateLoader
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

app = Flask(__name__)
app.config.from_object('config')

app_dir = os.path.dirname(os.path.abspath(__file__))
template_path = os.path.join(app_dir, 'templates')
templates = PageTemplateLoader(template_path)
site_url = app.config['SITE_URL']
engine = create_engine(app.config['CONN_STR'])
session = None

def init_db():
    from models.base import DeclarativeBase
    engine = create_engine(app.config['CONN_STR'])
    DeclarativeBase.metadata.bind = engine
    DeclarativeBase.metadata.drop_all()
    DeclarativeBase.metadata.create_all(engine)

@app.before_request
def before_request():
    session = sessionmaker()
    session.configure(bind=engine)

@app.teardown_request
def teardown_request(exception):
    session.close()

@app.route('/')
def site_home():
    t = templates['index.html']
    return t.render(site_url=site_url)

@app.route('/<user>/')
def user_home(user):
    return user_page(user, '_home')

@app.route('/<user>/<page_name>/')
def user_page(user, page_name):
    # todo: retrieve page from db
    t = templates['page_view.html']
    return t.render(site_url=site_url, page_name=page_name)

@app.route('/<user>/<page_name>/edit')
def user_page_edit(user, page_name):
    # todo: retrieve page from db
    t = templates['page_edit.html']
    return t.render(site_url=site_url, page_name=page_name)

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
    extra_dirs = ['%s/static' % app_dir, '%s/templates' % app_dir]
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
