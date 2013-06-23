import unittest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config import CONN_STR_TEST
from models import DBSession, DeclarativeBase, Account, Page, Revision

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

        p = Page()
        p.owner = a
        p.name_for_url = '_home'
        p.title = 'Home'
        p.orig_text = 'my home page yo'
        p.curr_text = p.orig_text
        p.curr_rev_num = 0

        r = Revision()
        r.rev_num = 0
        r.page = p

        self.assertEqual(a.id, None)
        self.assertEqual(p.id, None)
        self.assertEqual(r.id, None)

        DBSession.add(r)
        DBSession.flush()

        self.assertEqual( type(a.id), int)
        self.assertEqual( type(p.id), int )
        self.assertEqual( type(r.id), int )

if __name__ == '__main__':
    unittest.main()
