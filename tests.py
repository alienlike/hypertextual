import unittest
from sqlalchemy import create_engine
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
        p.acct = a
        p.page_name = '_home'
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

    def test_create_page_name(self):

        a = Account()
        a.uid = 'samiam'
        a.pw = 'secret'

        p = Page()
        p.set_title(DBSession, a, '!@#% Home')
        p.orig_text = 'my !@#% home page yo'
        p.curr_text = p.orig_text
        p.curr_rev_num = 0
        p.acct = a

        DBSession.add(p)
        DBSession.flush()

        p2 = Page()
        p2.set_title(DBSession, a, 'Home')
        p2.orig_text = 'my home page yo'
        p2.curr_text = p2.orig_text
        p2.curr_rev_num = 0
        p2.acct = a

        self.assertEqual(p.page_name, "home")
        self.assertEqual(p2.page_name, "home-2")

if __name__ == '__main__':
    unittest.main()
