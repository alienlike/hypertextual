import unittest
from sqlalchemy import create_engine
from config import CONN_STR_TEST
from models import DBSession, DeclarativeBase, Account, Page, Revision
import re
from htlinks import HT_LINK_RE

class AlchemyTestBase(unittest.TestCase):

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

class TestBasic(AlchemyTestBase):

    def test_create_acct(self):

        a = Account()
        a.uid = 'samiam'
        a.set_password('secret')

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
        self.assertTrue( a.validate_password('secret') )
        self.assertFalse( a.validate_password('seekrit') )

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

class TestRegex(unittest.TestCase):

    def test_regex(self):
        regex = HT_LINK_RE
        a = re.match(regex, '[[Hello World]]')
        b = re.match(regex, '[[Home|Home page]]')
        c = re.match(regex, '[[ nw::Home]]')
        d = re.match(regex, '[[nw9 ::Home|Home page]]')
        e = re.match(regex, '[[nw|Home|Home page]]')
        f = re.match(regex, '[[nw|Home::Home page]]')
        g = re.match(regex, '[[nw::Home::Home page]]')
        h = re.match(regex, '[[nw::Home:Home page]]')
        i = re.match(regex, '[[9nw ::Home|Home page]]')
        self.assertIsNotNone(a)
        self.assertIsNotNone(b)
        self.assertIsNotNone(c)
        self.assertIsNotNone(d)
        self.assertIsNone(e)
        self.assertIsNone(f)
        self.assertIsNone(g)
        self.assertIsNotNone(h)
        self.assertIsNone(i)
        print a.groupdict()
        print b.groups()
        print c.groups()
        print d.groupdict()
        print h.groups()

if __name__ == '__main__':
    unittest.main()
