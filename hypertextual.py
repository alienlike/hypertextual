import sqlite3
from flask import Flask, request, session, g, redirect, url_for, \
             abort, render_template, flash
from contextlib import closing

app = Flask(__name__)
app.config.from_object('config')

def connect_db():
    return sqlite3.connect(app.config['DATABASE'])

def init_db():
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql') as f:
            db.cursor().executescript(f.read())
        db.commit()

@app.before_request
def before_request():
    g.db = connect_db()

@app.teardown_request
def teardown_request(exception):
    g.db.close()

@app.route('/')
def site_home():
    return render_template('index.html')

@app.route('/<user>/')
def user_home(user):
    return user_page(user, '_home')

@app.route('/<user>/<page_name>/')
def user_page(user, page_name):
    # todo: retrieve page from db
    return render_template('page_view.html', page_name=page_name)

@app.route('/<user>/<page_name>/edit')
def user_page_edit(user, page_name):
    # todo: retrieve page from db
    return render_template('page_edit.html', page_name=page_name)

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
    app.run()

