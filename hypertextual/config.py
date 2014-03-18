import os

SITE_NAME = os.environ.get('HYPERTEXTUAL_SITE_NAME', 'hypertextual') # todo: apply this
SITE_URL = os.environ.get('HYPERTEXTUAL_SITE_URL', 'http://localhost:5000')
PORT = int(os.environ.get('HYPERTEXTUAL_PORT', '5000')) # ignored by gunicorn
CONN_STR = os.environ.get('DATABASE_URL', 'postgresql://nw@localhost:5432/hypertextual')
CONN_STR_TEST = 'postgresql://nw@localhost:5432/hypertextual_test'
RESERVED_ACCT_NAMES = []

# todo: do something with these
SECRET_KEY = 'development key'
USERNAME = 'admin'
PASSWORD = 'default'
