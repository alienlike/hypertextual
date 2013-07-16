import os

CONN_STR = os.environ.get('DATABASE_URL', 'postgresql://nw@localhost:5432/hypertextual')
CONN_STR_TEST = 'postgresql://nw@localhost:5432/hypertextual_test'
DEBUG = True
SECRET_KEY = 'development key'
USERNAME = 'admin'
PASSWORD = 'default'
SITE_URL = os.environ.get('HYPERTEXTUAL_SITE_URL', 'http://localhost:5000')
PORT = int(os.environ.get('HYPERTEXTUAL_PORT', '5000'))
