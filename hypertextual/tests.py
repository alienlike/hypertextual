import unittest, re
from sqlalchemy import create_engine
from config import CONN_STR_TEST
from models import db_session, Base, Account, Page
from models.md import HT_LINK_RE, HT_PLACEHOLDER_RE

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
        a = Account.new(uid, pw)

        title = 'Home'
        p = Page.new(a, title)
        p.save_draft_rev('my home page yo', True)
        r = p.get_draft_rev()

        self.assertIsNotNone(a.id)
        self.assertIsNotNone(p.id)
        self.assertEqual(r.id, None)

        db_session.flush()

        self.assertEqual( type(a.id), int)
        self.assertEqual( type(p.id), int )
        self.assertEqual( type(r.id), int )
        self.assertTrue( a.validate_password('secret') )
        self.assertFalse( a.validate_password('seekrit') )

    def test_create_page_name(self):

        uid = 'samiam'
        pw = 'secret'
        a = Account.new(uid, pw)

        title = '!@#% Home'
        p = Page.new(a, title)
        p.save_draft_rev('my !@#% home page yo', True)
        p.acct = a

        db_session.add(p)
        db_session.flush()

        title = 'Home'
        p2 = Page.new(a, title)
        p2.save_draft_rev('my home page yo', True)
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

    def test_placeholder_regex(self):
        regex = HT_PLACEHOLDER_RE
        a = re.match(regex, '[[abc]]')
        b = re.match(regex, '[[b]]')
        c = re.match(regex, '[[1b]]')
        d = re.match(regex, '[[c3]]')
        e = re.match(regex, '[[01]]')
        f = re.match(regex, '[[0]]')
        g = re.match(regex, '[[1]]')
        h = re.match(regex, '[[30]]')
        aa = re.match(regex, 'abc')
        bb = re.match(regex, 'b')
        cc = re.match(regex, '1b')
        dd = re.match(regex, 'c3')
        ee = re.match(regex, '01')
        ff = re.match(regex, '0')
        gg = re.match(regex, '1')
        hh = re.match(regex, '30')
        self.assertIsNone(a)
        self.assertIsNone(b)
        self.assertIsNone(c)
        self.assertIsNone(d)
        self.assertIsNotNone(e)
        self.assertIsNotNone(f)
        self.assertIsNotNone(g)
        self.assertIsNotNone(h)
        self.assertEqual(h.groupdict()['linknum'], '30')
        self.assertIsNone(aa)
        self.assertIsNone(bb)
        self.assertIsNone(cc)
        self.assertIsNone(dd)
        self.assertIsNone(ee)
        self.assertIsNone(ff)
        self.assertIsNone(gg)
        self.assertIsNone(hh)

if __name__ == '__main__':
    unittest.main()
