import os
import argparse
from flask import Flask, session, g, redirect, url_for
from chameleon import PageTemplateLoader
from sqlalchemy import create_engine
from blueprints import site_routes, page_routes, acct_routes
from models import db_session, Account

##### globals

app = Flask(__name__)
app.register_blueprint(site_routes)
app.register_blueprint(acct_routes)
app.register_blueprint(page_routes)

site_name = None
site_url = None
app_path = None
templates = None

##### routes

# /                         --> site home page
# /robots.txt
# /favicon.ico
# /sitemap.xml
# /dublin.rdf
# /opensearch.xml
# /admin/...                --> admin page
# /api/...                  --> api handler
# /docs/...                 --> documentation page
# /site/...                 --> site page or action
# /static/...               --> static file
# /<uid>                    --> user home page
# /_<uid>                   --> user private home page
# /<uid>/account/...        --> account page
# /<uid>/action/...         --> home page action
# /_<uid>/action/...        --> private home page action
# /<uid>/file/...           --> user file (e.g., images)
# /<uid>/<slug>             --> user page
# /<uid>/<slug>/action/...  --> page action

def redirect_to_site_home():
    url = url_for('site_home')
    return redirect(url)

def redirect_to_user_page(uid, slug):
    url = url_for('view_page', uid=uid, slug=slug)
    return redirect(url)

def render_template(template_name, **vals):
    vals['g'] = vals.get('g', g)
    vals['site_name'] = vals.get('site_name', site_name)
    vals['site_url'] = vals.get('site_url', site_url)
    template = templates[template_name]
    return template.render(**vals)

##### events

@app.before_request
def before_request():
    g.current_user = _get_current_user_from_session()
    g.render_template = render_template
    g.redirect_to_site_home = redirect_to_site_home
    g.redirect_to_user_page = redirect_to_user_page
    g.site_name = site_name
    g.site_url = site_url
    g.app_path = app_path
    g.templates = templates
    g.reserved_acct_names = app.config['RESERVED_ACCT_NAMES']

def _get_current_user_from_session():
    # retrieve current_uid from session, where it is kept between requests
    current_uid = session.get('current_uid', None)
    current_user = None
    if current_uid:
        current_user = Account.get_by_uid(current_uid)
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
    return render_template('404.html'), 404

##### app setup routine

def main():
    _configure_flask_app()
    _configure_db_session()
    _set_globals()
    command_line_args = _get_command_line_args()
    app_options = _get_app_options(command_line_args)
    _set_up_logging()
    app.run(**app_options)

def wsgi_main():
    _configure_flask_app()
    _configure_db_session()
    _set_globals()
    _set_up_logging()

def _configure_flask_app():
    app.config.from_object('config')

def _configure_db_session():
    conn_str = app.config['CONN_STR']
    engine = create_engine(conn_str)
    db_session.configure(bind=engine)

def _set_globals():
    global site_name, site_url, app_path, templates
    site_name = _get_site_name()
    site_url = _get_site_url()
    app_path = _get_app_path()
    templates = _get_chameleon_templates()

def _get_site_name():
    site_name = app.config['SITE_NAME']
    return site_name

def _get_site_url():
    site_url = app.config['SITE_URL']
    return site_url

def _get_app_path():
    app_path = os.path.dirname(os.path.abspath(__file__))
    return app_path

def _get_chameleon_templates():
    template_path = os.path.join(app_path, 'templates')
    template_loader = PageTemplateLoader(template_path)
    return template_loader

def _get_command_line_args():
    # set up some args for enabling debug or reload mode
    p = argparse.ArgumentParser()
    p.add_argument('-d', action='store_true', dest='debug_mode', default=False)
    p.add_argument('-r', action='store_true', dest='reload_mode', default=False)
    command_line_args = p.parse_args()
    return command_line_args

def _get_app_options(command_line_args):
    app_options = {
        'port': app.config['PORT'],
        'host': '0.0.0.0',
        'debug': command_line_args.debug_mode, # show tracebacks in pycharm
        'use_debugger': command_line_args.debug_mode or command_line_args.reload_mode, # show tracebacks in browser
        'use_reloader': command_line_args.reload_mode # reload files on change
    }
    if command_line_args.reload_mode:
        app_options['extra_files'] = _get_static_files_for_reload_mode()
    return app_options

def _get_static_files_for_reload_mode():
    static_dirs = ['%s/static' % app_path, '%s/templates' % app_path]
    static_files = static_dirs[:]
    for static_dir in static_dirs:
        for dir_name, dirs, file_names in os.walk(static_dir):
            for file_name in file_names:
                if not file_name.startswith('.'): # exclude vim swap files, etc.
                    file_name = os.path.join(dir_name, file_name)
                    if os.path.isfile(file_name):
                        static_files.append(file_name)
    return static_files

def _set_up_logging():
    if not app.debug:
        import logging
        from logging.handlers import RotatingFileHandler
        log_dir = os.path.join(app_path, 'log')
        if not os.path.exists(log_dir):
            os.mkdir(log_dir)
        filename = os.path.join(log_dir, 'hypertextual.log')
        file_handler = RotatingFileHandler(filename, maxBytes=102400, backupCount=10)
        file_handler.setLevel(logging.WARNING)
        app.logger.addHandler(file_handler)

if __name__ == '__main__':
    main()
else:
    wsgi_main()