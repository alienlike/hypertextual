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
        page = self.acct.get_page_by_slug('_private')
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
        self.assertEqual('book-list', self.page.slug)
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

    def test_move_with_redirect(self):
        self.page.save_draft_rev('book list sample text', True)
        self.page.publish_draft_rev()
        Page.move(self.page, 'Reading List', True)
        redirect_page = self.acct.get_page_by_title('Book List')
        moved_page = self.acct.get_page_by_title('Reading List')
        self.assertTrue(redirect_page.redirect)
        self.assertEqual('Book List', redirect_page.title)
        self.assertEqual('book-list', redirect_page.slug)
        redirect_text = redirect_page.get_curr_rev().get_text()
        self.assertEqual('This page has moved to: [[Reading List]]', redirect_text)
        self.assertFalse(moved_page.redirect)
        self.assertEqual('Reading List', moved_page.title)
        self.assertEqual('reading-list', moved_page.slug)
        moved_text = moved_page.get_curr_rev().get_text()
        self.assertEqual('book list sample text', moved_text)

    def test_move_with_update_links(self):
        self.page.save_draft_rev('book list sample text', True)
        self.page.publish_draft_rev()
        home_page = self.acct.get_page_by_title('Home')
        home_page.save_draft_rev('this is my [[Book List]]', True)
        home_page.publish_draft_rev()
        Page.move(self.page, 'Reading List', False, True)
        moved_page = self.acct.get_page_by_title('Reading List')
        self.assertFalse(moved_page.redirect)
        self.assertEqual('Reading List', moved_page.title)
        self.assertEqual('reading-list', moved_page.slug)
        moved_text = moved_page.get_curr_rev().get_text()
        self.assertEqual('book list sample text', moved_text)
        home_text = home_page.get_curr_rev().get_text()
        self.assertEqual('this is my [[Reading List]]', home_text)

    def test_delete(self):
        db_session.flush()
        Page.delete(self.page)
        page = self.acct.get_page_by_title('Book List')
        self.assertIsNone(page)
        self.assertEqual(2, len(self.acct.pages))

class TestRevision(AlchemyTestBase):

    def setUp(self):
        self.acct = Account.new('scott', 'tiger', 'scott@gmail.com')
        self.page = Page.new(self.acct, 'Book List')

    def test_new(self):
        rev = self.page.save_draft_rev('book list sample text', True)
        self.page.publish_draft_rev()
        self.assertIs(rev.page, self.page)
        self.assertEqual(0, rev.rev_num)
        self.assertTrue(rev.use_markdown)
        text = rev.get_text()
        self.assertEqual('book list sample text', text)

    def test_add_rev(self):
        self.page.save_draft_rev('book list sample text', True)
        self.page.publish_draft_rev()
        rev = self.page.save_draft_rev('book list revised text', True)
        text = rev.get_text()
        self.assertEqual('book list revised text', text)

    def test_link_to_self(self):
        rev = self.page.save_draft_rev('book list sample text [[Home]]', True)
        raw_text = rev._Revision__get_raw_text_from_patches()
        self.assertEqual('book list sample text [[0]]', raw_text)
        text = rev.get_text()
        self.assertEqual('book list sample text [[Home]]', text)
        html = rev.render_to_html(self.acct.uid)
        self.assertEqual('<p>book list sample text <a href="/scott">Home</a></p>', html)
        rev.use_markdown = False
        html = rev.render_to_html(self.acct.uid)
        self.assertEqual('<pre>book list sample text <a href="/scott">Home</a></pre>', html)

    def test_link_to_self_with_alias(self):
        rev = self.page.save_draft_rev('book list sample text [[Home|Scott Home]]', True)
        raw_text = rev._Revision__get_raw_text_from_patches()
        self.assertEqual('book list sample text [[0]]', raw_text)
        text = rev.get_text()
        self.assertEqual('book list sample text [[Home|Scott Home]]', text)
        html = rev.render_to_html(self.acct.uid)
        self.assertEqual('<p>book list sample text <a href="/scott">Scott Home</a></p>', html)
        rev.use_markdown = False
        html = rev.render_to_html(self.acct.uid)
        self.assertEqual('<pre>book list sample text <a href="/scott">Scott Home</a></pre>', html)

    def test_link_to_other(self):
        Account.new('sally', 'secret', 'sally@gmail.com')
        rev = self.page.save_draft_rev('book list sample text [[sally::Home]]', True)
        raw_text = rev._Revision__get_raw_text_from_patches()
        self.assertEqual('book list sample text [[0]]', raw_text)
        text = rev.get_text()
        self.assertEqual('book list sample text [[sally::Home]]', text)
        html = rev.render_to_html(self.acct.uid)
        self.assertEqual('<p>book list sample text <a href="/sally">Home</a></p>', html)
        rev.use_markdown = False
        html = rev.render_to_html(self.acct.uid)
        self.assertEqual('<pre>book list sample text <a href="/sally">Home</a></pre>', html)

    def test_link_to_other_with_alias(self):
        Account.new('sally', 'secret', 'sally@gmail.com')
        rev = self.page.save_draft_rev('book list sample text [[sally::Home|Sally Home]]', True)
        raw_text = rev._Revision__get_raw_text_from_patches()
        self.assertEqual('book list sample text [[0]]', raw_text)
        text = rev.get_text()
        self.assertEqual('book list sample text [[sally::Home|Sally Home]]', text)
        html = rev.render_to_html(self.acct.uid)
        self.assertEqual('<p>book list sample text <a href="/sally">Sally Home</a></p>', html)
        rev.use_markdown = False
        html = rev.render_to_html(self.acct.uid)
        self.assertEqual('<pre>book list sample text <a href="/sally">Sally Home</a></pre>', html)

    def test_link_with_markdown(self):
        rev = self.page.save_draft_rev('book list sample text **[[Home]]**', True)
        raw_text = rev._Revision__get_raw_text_from_patches()
        self.assertEqual('book list sample text **[[0]]**', raw_text)
        text = rev.get_text()
        self.assertEqual('book list sample text **[[Home]]**', text)
        html = rev.render_to_html(self.acct.uid)
        self.assertEqual('<p>book list sample text <strong><a href="/scott">Home</a></strong></p>', html)

class TestLink(AlchemyTestBase):

    def setUp(self):
        self.scott = Account.new('scott', 'tiger', 'scott@gmail.com')
        self.scott_page = Page.new(self.scott, 'Book List')
        self.scott_rev = self.scott_page.save_draft_rev('book list sample text', True)
        self.scott_page.publish_draft_rev()
        self.sally = Account.new('sally', 'secret', 'sally@gmail.com')
        self.sally_page = Page.new(self.sally, 'Dear Diary')
        self.sally_rev = self.sally_page.save_draft_rev('today i am sad', True)
        self.sally_page.publish_draft_rev()

    def test_new(self):
        rev = self.scott_rev
        link = Link.new(rev, 0, 'sally', 'Dear Diary', 'Sally''s Diary')
        self.assertEqual(0, link.link_num)
        self.assertEqual('sally', link.tgt_page_uid)
        self.assertEqual('Dear Diary', link.tgt_page_title)
        self.assertEqual('Sally''s Diary', link.tgt_page_alias)

    def test_link_to_self(self):
        rev = self.scott_rev
        link = Link.new(rev, 0, None, 'Book List', None)
        link_text = link.get_link_text()
        ph_text = link.get_placeholder_text()
        link_html = link.get_link_html('scott')
        md_elem = link.get_link_markdown_elem('scott')
        self.assertEqual('[[Book List]]', link_text)
        self.assertEqual('[[0]]', ph_text)
        self.assertEqual('<a href="/scott/book-list">Book List</a>', link_html)
        self.assertEqual('Book List', md_elem.text)
        self.assertEqual('/scott/book-list', md_elem.get('href'))
        self.assertIsNone(md_elem.get('class'))

    def test_link_to_self_with_explicit_username(self):
        rev = self.scott_rev
        link = Link.new(rev, 0, 'scott', 'Book List', None)
        link_text = link.get_link_text()
        ph_text = link.get_placeholder_text()
        link_html = link.get_link_html('scott')
        md_elem = link.get_link_markdown_elem('scott')
        self.assertEqual('[[Book List]]', link_text)
        self.assertEqual('[[0]]', ph_text)
        self.assertEqual('<a href="/scott/book-list">Book List</a>', link_html)
        self.assertEqual('Book List', md_elem.text)
        self.assertEqual('/scott/book-list', md_elem.get('href'))
        self.assertIsNone(md_elem.get('class'))

    def test_link_to_self_with_alias(self):
        rev = self.scott_rev
        link = Link.new(rev, 0, None, 'Book List', 'My books')
        link_text = link.get_link_text()
        ph_text = link.get_placeholder_text()
        link_html = link.get_link_html('scott')
        md_elem = link.get_link_markdown_elem('scott')
        self.assertEqual('[[Book List|My books]]', link_text)
        self.assertEqual('[[0]]', ph_text)
        self.assertEqual('<a href="/scott/book-list">My books</a>', link_html)
        self.assertEqual('My books', md_elem.text)
        self.assertEqual('/scott/book-list', md_elem.get('href'))
        self.assertIsNone(md_elem.get('class'))

    def test_link_to_self_private(self):
        self.scott_page.private = True
        rev = self.scott_rev
        link = Link.new(rev, 0, None, 'Book List', None)
        link_text = link.get_link_text()
        ph_text = link.get_placeholder_text()
        link_html = link.get_link_html('scott')
        md_elem = link.get_link_markdown_elem('scott')
        self.assertEqual('[[Book List]]', link_text)
        self.assertEqual('[[0]]', ph_text)
        self.assertEqual('<a href="/scott/book-list">Book List</a>', link_html)
        self.assertEqual('Book List', md_elem.text)
        self.assertEqual('/scott/book-list', md_elem.get('href'))
        self.assertIsNone(md_elem.get('class'))

    def test_link_to_self_nonexistent(self):
        rev = self.scott_rev
        link = Link.new(rev, 0, None, 'Record Collection', None)
        link_text = link.get_link_text()
        ph_text = link.get_placeholder_text()
        link_html = link.get_link_html('scott')
        md_elem = link.get_link_markdown_elem('scott')
        self.assertEqual('[[Record Collection]]', link_text)
        self.assertEqual('[[0]]', ph_text)
        self.assertEqual('<a href="/scott?action=create&title=Record Collection" class="link-create-page">Record Collection</a>', link_html)
        self.assertEqual('Record Collection', md_elem.text)
        self.assertEqual('/scott?action=create&title=Record Collection', md_elem.get('href'))
        self.assertEqual('link-create-page', md_elem.get('class'))

    def test_link_to_other(self):
        rev = self.sally_rev
        link = Link.new(rev, 0, 'scott', 'Book List', None)
        link_text = link.get_link_text()
        ph_text = link.get_placeholder_text()
        link_html = link.get_link_html('sally')
        md_elem = link.get_link_markdown_elem('sally')
        self.assertEqual('[[scott::Book List]]', link_text)
        self.assertEqual('[[0]]', ph_text)
        self.assertEqual('<a href="/scott/book-list">Book List</a>', link_html)
        self.assertEqual('Book List', md_elem.text)
        self.assertEqual('/scott/book-list', md_elem.get('href'))
        self.assertIsNone(md_elem.get('class'))

    def test_link_to_other_with_alias(self):
        rev = self.sally_rev
        link = Link.new(rev, 0, 'scott', 'Book List', 'Scott''s books')
        link_text = link.get_link_text()
        ph_text = link.get_placeholder_text()
        link_html = link.get_link_html('sally')
        md_elem = link.get_link_markdown_elem('sally')
        self.assertEqual('[[scott::Book List|Scott''s books]]', link_text)
        self.assertEqual('[[0]]', ph_text)
        self.assertEqual('<a href="/scott/book-list">Scott''s books</a>', link_html)
        self.assertEqual('Scott''s books', md_elem.text)
        self.assertEqual('/scott/book-list', md_elem.get('href'))
        self.assertIsNone(md_elem.get('class'))

    def test_link_to_other_private(self):
        self.scott_page.private = True
        rev = self.sally_rev
        link = Link.new(rev, 0, 'scott', 'Book List', None)
        link_text = link.get_link_text()
        ph_text = link.get_placeholder_text()
        link_html = link.get_link_html('sally')
        md_elem = link.get_link_markdown_elem('sally')
        self.assertEqual('[[scott::Book List]]', link_text)
        self.assertEqual('[[0]]', ph_text)
        self.assertEqual('<a href="#" class="link-does-not-exist">Book List</a>', link_html)
        self.assertEqual('Book List', md_elem.text)
        self.assertEqual('#', md_elem.get('href'))
        self.assertEqual('link-does-not-exist', md_elem.get('class'))

    def test_link_to_other_nonexistent(self):
        rev = self.sally_rev
        link = Link.new(rev, 0, 'scott', 'Record Collection', None)
        link_text = link.get_link_text()
        ph_text = link.get_placeholder_text()
        link_html = link.get_link_html('sally')
        md_elem = link.get_link_markdown_elem('sally')
        self.assertEqual('[[scott::Record Collection]]', link_text)
        self.assertEqual('[[0]]', ph_text)
        self.assertEqual('<a href="#" class="link-does-not-exist">Record Collection</a>', link_html)
        self.assertEqual('Record Collection', md_elem.text)
        self.assertEqual('#', md_elem.get('href'))
        self.assertEqual('link-does-not-exist', md_elem.get('class'))

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