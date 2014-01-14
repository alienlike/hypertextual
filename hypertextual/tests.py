import unittest, re
from sqlalchemy import create_engine
from config import CONN_STR_TEST
from models import db_session, Base, Account, Page
from htlinks import HT_LINK_RE

class AlchemyTestBase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        engine = create_engine(CONN_STR_TEST)
        db_session.configure(bind=engine)
        Base.metadata.bind = engine
        Base.metadata.create_all(engine)

    @classmethod
    def tearDownClass(cls):
        db_session.remove()
        Base.metadata.drop_all()

    def setUp(self):
        pass

    def tearDown(self):
        db_session.rollback()

class TestBasic(AlchemyTestBase):

    def test_create_acct(self):

        uid = 'samiam'
        pw = 'secret'
        a = Account(uid, pw)

        p = Page()
        p.acct = a
        p.page_name = '_home'
        p.title = 'Home'
        p.create_draft_rev('my home page yo', True)
        r = p.get_draft_rev()

        self.assertEqual(a.id, None)
        self.assertEqual(p.id, None)
        self.assertEqual(r.id, None)

        db_session.add(r)
        db_session.flush()

        self.assertEqual( type(a.id), int)
        self.assertEqual( type(p.id), int )
        self.assertEqual( type(r.id), int )
        self.assertTrue( a.validate_password('secret') )
        self.assertFalse( a.validate_password('seekrit') )

    def test_create_page_name(self):

        uid = 'samiam'
        pw = 'secret'
        a = Account(uid, pw)

        p = Page()
        p.set_title(db_session, a, '!@#% Home')
        p.create_draft_rev('my !@#% home page yo', True)
        p.acct = a

        db_session.add(p)
        db_session.flush()

        p2 = Page()
        p2.set_title(db_session, a, 'Home')
        p2.create_draft_rev('my home page yo', True)
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
