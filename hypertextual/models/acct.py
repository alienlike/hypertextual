from flaskext.bcrypt import generate_password_hash, check_password_hash
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import exists
from breadcrumb import Breadcrumb
from db import Base, db_session
from page import Page

class Account(Base):

    # table
    __tablename__ = 'acct'

    # columns
    id = Column(Integer, primary_key=True, nullable=False)
    create_ts = Column(DateTime, nullable=False, default=datetime.now)

    uid = Column(String(64), unique=True, nullable=False)
    email = Column(String(128), unique=True, nullable=False)
    pw_hash = Column(String(60), nullable=False)

    # relationship
    pages = relationship(
        Page,
        order_by='Page.title',
        cascade='all,delete-orphan',
        passive_deletes=True,
        backref='acct'
    )

    def set_password(self, password):
        BCRYPT_COMPLEXITY = 12
        self.pw_hash = generate_password_hash(password, BCRYPT_COMPLEXITY)

    def reset_password(self, old_password, new_password):
        # todo: raise exception if invalid password
        valid = self.validate_password(old_password)
        if valid:
            self.set_password(new_password)
        return valid

    def validate_password(self, password):
        valid = check_password_hash(self.pw_hash, password)
        return valid

    def get_breadcrumb(self):
        breadcrumb = [Breadcrumb(self.uid, '/%s' % self.uid)]
        return breadcrumb

    def new_page(self, title):
        page = Page.new(self, title)
        return page

    def get_page_by_title(self, title):
        page = Page.query.\
            filter(Page.title==title).\
            filter(Page.acct==self).first()
        return page

    def get_page_by_slug(self, slug):
        page = Page.query.\
            filter(Page.slug==slug).\
            filter(Page.acct==self).first()
        return page

    @classmethod
    def get_by_uid(cls, uid):
        acct = cls.query.filter(cls.uid==uid).first()
        return acct

    @classmethod
    def get_all(cls):
        accts = cls.query.order_by(cls.uid).all()
        return accts

    @classmethod
    def uid_exists(cls, uid):
        ex = db_session.query(
            exists().where(cls.uid==uid)
        ).scalar()
        return ex

    @classmethod
    def email_exists(cls, email):
        ex = db_session.query(
            exists().where(cls.email==email)
        ).scalar()
        return ex

    @classmethod
    def new(cls, uid, pw, email):
        acct = cls.__create_acct(uid, pw, email)
        cls.__create_home_page(acct)
        cls.__create_private_home_page(acct)
        db_session.add(acct)
        return acct

    @classmethod
    def __create_acct(cls, uid, pw, email):
        acct = cls()
        acct.uid = uid
        acct.email = email
        acct.set_password(pw)
        return acct

    @classmethod
    def __create_home_page(cls, acct):
        home_page_title = 'Home'
        home_page_text = 'Welcome to hypertextual. This is your home page.'
        home_page = Page.new(acct, home_page_title)
        home_page.slug = '__home'
        home_page.save_draft_rev(home_page_text, True)
        home_page.publish_draft_rev()

    @classmethod
    def __create_private_home_page(cls, acct):
        private_home_page_title = 'Private Home'
        private_home_page_text = 'Welcome to hypertextual. This is your private home page.'
        private_home_page = Page.new(acct, private_home_page_title)
        private_home_page.slug = '__private'
        private_home_page.private = True
        private_home_page.save_draft_rev(private_home_page_text, True)
        private_home_page.publish_draft_rev()