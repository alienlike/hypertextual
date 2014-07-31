import os

SITE_NAME = os.environ.get('HYPERTEXTUAL_SITE_NAME', 'hypertextu.al')
SITE_URL = os.environ.get('HYPERTEXTUAL_SITE_URL', 'http://localhost:5000')
PORT = 5000 # does not apply to wsgi

CONN_STR = os.environ.get('DATABASE_URL', 'postgresql://nw@localhost:5432/hypertextual')
CONN_STR_TEST = 'postgresql://nw@localhost:5432/hypertextual_test'
RESERVED_ACCT_NAMES = []

# todo: do something with these
SECRET_KEY = 'development key'
USERNAME = 'admin'
PASSWORD = 'default'
