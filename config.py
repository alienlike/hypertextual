import os

SITE_URL = os.environ.get('HYPERTEXTUAL_SITE_URL', 'http://localhost:5000')
PORT = int(os.environ.get('HYPERTEXTUAL_PORT', '5000')) # this setting ignored by gunicorn
CONN_STR = os.environ.get('DATABASE_URL', 'postgresql://nw@localhost:5432/hypertextual')
CONN_STR_TEST = 'postgresql://nw@localhost:5432/hypertextual_test'
DEBUG = 'localhost' in SITE_URL
SECRET_KEY = 'development key'
USERNAME = 'admin'
PASSWORD = 'default'
BCRYPT_COMPLEXITY = 12