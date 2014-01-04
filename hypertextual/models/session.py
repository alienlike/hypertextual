from sqlalchemy.orm import scoped_session, sessionmaker

db_session = scoped_session(sessionmaker())
