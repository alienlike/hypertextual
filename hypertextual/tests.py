import unittest, re
from sqlalchemy import create_engine
from config import CONN_STR_TEST
from models import db_session, Base, Account, Page, Revision, Link
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

    def tearDown(self):
        db_session.rollback()

class TestAccount(AlchemyTestBase):

    def setUp(self):
        self.acct = Account.new('scott', 'tiger', 'scott@gmail.com')

    def test_new(self):
        self.assertIsInstance(self.acct, Account)
        self.assertEqual('scott', self.acct.uid)
        self.assertEqual('scott@gmail.com', self.acct.email)
        self.assertEqual(2, len(self.acct.pages))

    def test_new_page(self):
        page = self.acct.new_page('Test Page')
        self.assertIsInstance(page, Page)
        self.assertEqual(3, len(self.acct.pages))

    def test_get_page_by_title(self):
        page = self.acct.get_page_by_title('Home')
        self.assertIsInstance(page, Page)
        self.assertEqual('Home', page.title)

    def test_get_page_by_name(self):
        page = self.acct.get_page_by_name('_private')
        self.assertIsInstance(page, Page)
        self.assertEqual('Private Home', page.title)

    def test_validate_password(self):
        self.assertTrue(
            self.acct.validate_password('tiger')
        )
        self.assertFalse(
            self.acct.validate_password('tigger')
        )

    def test_reset_password(self):
        self.acct.reset_password('tiger', 'tigger')
        self.assertTrue(
            self.acct.validate_password('tigger')
        )
        self.assertFalse(
            self.acct.validate_password('tiger')
        )

class TestPage(AlchemyTestBase):

    def setUp(self):
        self.acct = Account.new('scott', 'tiger', 'scott@gmail.com')
        self.page = Page.new(self.acct, 'Book List')

    def test_new(self):
        self.assertEqual('Book List', self.page.title)
        self.assertEqual('book-list', self.page.page_name)
        self.assertIsNone(self.page.curr_rev_num)
        self.assertIsNone(self.page.draft_rev_num)
        self.assertFalse(self.page.private)
        self.assertIs(self.page.acct, self.acct)
        self.assertEqual(0, len(self.page.revs))

    def test_user_is_owner(self):
        acct2 = Account.new('sally', 'secret', 'sally@gmail.com')
        self.assertTrue(
            self.page.user_is_owner(self.acct)
        )
        self.assertTrue(
            self.page.user_is_owner('scott')
        )
        self.assertFalse(
            self.page.user_is_owner(acct2)
        )
        self.assertFalse(
            self.page.user_is_owner('sally')
        )

    def test_user_can_view(self):
        self.page.save_draft_rev('book list sample text', True)
        acct2 = Account.new('sally', 'secret', 'sally@gmail.com')

        # no current rev yet
        self.assertTrue(
            self.page.user_can_view(self.acct)
        )
        self.assertTrue(
            self.page.user_can_view('scott')
        )
        self.assertFalse(
            self.page.user_can_view(acct2)
        )
        self.assertFalse(
            self.page.user_can_view('sally')
        )

        # create current rev
        self.page.publish_draft_rev()
        self.assertTrue(
            self.page.user_can_view(self.acct)
        )
        self.assertTrue(
            self.page.user_can_view('scott')
        )
        self.assertTrue(
            self.page.user_can_view(acct2)
        )
        self.assertTrue(
            self.page.user_can_view('sally')
        )

        # make page private
        self.page.private = True
        self.assertTrue(
            self.page.user_can_view(self.acct)
        )
        self.assertTrue(
            self.page.user_can_view('scott')
        )
        self.assertFalse(
            self.page.user_can_view(acct2)
        )
        self.assertFalse(
            self.page.user_can_view('sally')
        )

    def test_get_url(self):
        url = self.page.get_url()
        self.assertEqual('/scott/book-list', url)

    def test_get_curr_rev(self):
        # no curr rev yet
        self.assertIsNone(
            self.page.get_curr_rev()
        )
        # create draft rev; still no curr rev
        self.page.save_draft_rev('book list sample text', True)
        self.assertIsNone(
            self.page.get_curr_rev()
        )
        # publish draft rev
        self.page.publish_draft_rev()
        self.assertIsNotNone(
            self.page.get_curr_rev()
        )

    def test_get_draft_rev(self):
        # no draft rev yet
        self.assertIsNone(
            self.page.get_draft_rev()
        )
        # create draft rev
        self.page.save_draft_rev('book list sample text', True)
        self.assertIsNotNone(
            self.page.get_draft_rev()
        )
        # publish draft rev
        self.page.publish_draft_rev()
        self.assertIsNone(
            self.page.get_draft_rev()
        )

    def test_save_draft_rev(self):
        rev = self.page.save_draft_rev('book list sample text', True)
        self.assertIsInstance(rev, Revision)
        self.assertIsNotNone(self.page.draft_rev_num)
        self.assertIsNone(self.page.curr_rev_num)
        self.assertEqual(1, len(self.page.revs))

    def test_publish_draft_rev(self):
        self.page.save_draft_rev('book list sample text', True)
        self.page.publish_draft_rev()
        self.assertIsNone(self.page.draft_rev_num)
        self.assertIsNotNone(self.page.curr_rev_num)
        self.assertEqual(1, len(self.page.revs))

    def test_save_draft_rev_revised(self):
        self.page.save_draft_rev('book list sample text', True)
        self.page.publish_draft_rev()
        self.page.save_draft_rev('book list revised text', True)
        self.assertIsNotNone(self.page.draft_rev_num)
        self.assertIsNotNone(self.page.curr_rev_num)
        self.assertEqual(2, len(self.page.revs))

class TestRevision(AlchemyTestBase):
    pass

class TestLink(AlchemyTestBase):
    pass

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