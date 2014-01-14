from flaskext.bcrypt import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from db import Base
from page import Page

class Account(Base):

    # table
    __tablename__ = 'acct'

    # columns
    id = Column(Integer, primary_key=True, nullable=False)
    create_ts = Column(DateTime, nullable=False, default=datetime.now)

    uid = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True)
    pw_hash = Column(String, nullable=False)

    # relationship
    pages = relationship('Page', order_by='Page.id', backref='acct')

    def __init__(self, uid, pw, email=None):

        # create new user
        self.uid = uid
        if not email:
            email = None
        self.email = email
        self.set_password(pw)

        # create home page for new user
        page1 = Page()
        page1.title = 'Home'
        page1.page_name = None
        page1.create_draft_rev(
            'Welcome to hypertextual. This is your home page.', True)
        page1.publish_draft_rev()
        page1.acct = self

        # create private home page for new user
        page2 = Page()
        page2.title = 'Private Home'
        page2.page_name = '_private'
        page2.private = True
        page2.create_draft_rev(
            'Welcome to hypertextual. This is your private home page.', True)
        page2.publish_draft_rev()
        page2.acct = self

    def set_password(self, password):
        from config import BCRYPT_COMPLEXITY
        self.pw_hash = generate_password_hash(password, BCRYPT_COMPLEXITY)

    def reset_password(self, old_password, new_password):
        # first validate the old password, then set to the new password
        valid = self.validate_password(old_password)
        if valid:
            self.set_password(new_password)
        return valid

    def validate_password(self, password):
        # validate the password
        valid = check_password_hash(self.pw_hash, password)
        return valid

    def parse_bcrypt_complexity(self, bcrypt_hash):
        # see http://stackoverflow.com/a/6833165/204900
        hash_complexity = int(bcrypt_hash.split('$')[2])
        return hash_complexity