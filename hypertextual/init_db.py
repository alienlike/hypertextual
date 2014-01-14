from flask import Flask
from sqlalchemy import create_engine
from models import Base

def main():
    app = create_flask_app()
    engine = create_alchemy_engine(app)
    recreate_db_objects(engine)

def create_flask_app():
    app = Flask(__name__)
    app.config.from_object('config')
    return app

def create_alchemy_engine(app):
    conn_str = app.config['CONN_STR']
    engine = create_engine(conn_str)
    return engine

def recreate_db_objects(engine):
    Base.metadata.bind = engine
    Base.metadata.drop_all()
    Base.metadata.create_all(engine)

if __name__=='__main__':
    main()
