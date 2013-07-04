import unittest
import re
from wikilinks import WIKILINK_RE

class TestBasic(unittest.TestCase):

    def test_regex(self):
        regex = WIKILINK_RE
        a = re.match(regex, '[[Home]]')
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
