import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import CONN_STR_TEST
from models import DBSession, DeclarativeBase, Account, Page, Revision, Patch

class TestBase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        engine = create_engine(CONN_STR_TEST)
        DBSession.configure(bind=engine)
        DeclarativeBase.metadata.bind = engine
        DeclarativeBase.metadata.create_all(engine)

    @classmethod
    def tearDownClass(cls):
        DBSession.remove()
        DeclarativeBase.metadata.drop_all()

    def setUp(self): pass

    def tearDown(self):
        DBSession.rollback()

class TestBasic(TestBase):

    def test_create_acct(self):

        a = Account()
        a.uid = 'samiam'
        a.pw = 'secret'
        DBSession.add(a)
        DBSession.flush()
        self.assertTrue(a.id is not None)
        print 'account id = %s' % a.id

        p = Page()
        p.owner = a
        p.name_for_url = '_home'
        p.title = 'Home'
        p.orig_text = 'my home page yo'
        p.curr_text = p.orig_text
        DBSession.add(p)
        DBSession.flush()
        self.assertTrue(p.id is not None)
        print 'page id = %s' % p.id

if __name__ == '__main__':
    unittest.main()
