import re
from flask import Blueprint, request, g, session
from models import Account, reserved_acct_names
from validate_email import validate_email

acct_routes = Blueprint('acct_routes', __name__,
                        template_folder='templates',
                        static_folder='static')

@acct_routes.route('/site/create-account/', methods=['POST', 'GET'])
def create_acct():

    # set default uid/password values
    uid = ''
    email = ''
    pw = ''
    pconfirm = ''
    errors = dict()

    # process form
    if request.method == 'POST':

        uid = request.form['uid'].strip().lower()
        email = request.form['email'].strip().lower()
        pw = request.form['pw']
        pconfirm = request.form['pconfirm']
        valid = True

        # check whether uid or email already exist
        uid_exists = Account.uid_exists(uid)
        email_valid = email and validate_email(email)
        email_exists = email_valid and Account.email_exists(email)

        reserved_names = reserved_acct_names + g.reserved_acct_names
        uid_re = r'^([a-zA-Z][a-zA-Z0-9]*)$'

        if not uid:
            valid = False
            errors['uid'] = 'Please provide a username.'
        elif not re.match(uid_re, uid):
            valid = False
            errors['uid'] = 'Username must not begin with a numeral or contain special characters.'
        elif uid in reserved_names or uid_exists:
            valid = False
            errors['uid'] = 'Username is not available. Please try another.'
        if not email_valid:
            valid = False
            errors['email'] = 'Invalid email address.'
        elif email_exists:
            valid = False
            errors['email'] = 'Email already in use. Please use another.'
        if not pw:
            valid = False
            errors['pw'] = 'Please provide a password.'
        elif pw != pconfirm:
            valid = False
            errors['pconfirm'] = 'Does not match password.'

        if valid:

            # create account
            acct = Account.new(uid, pw, email)

            # add account to session (effectively log the new user in)
            session['current_uid'] = acct.uid
            g.current_user = acct

            # redirect to new home page
            return g.redirect_to_user_page(uid, '__home')

    vals = {
        'uid': uid,
        'email': email,
        'pw': pw,
        'pconfirm': pconfirm,
        'errors': errors
    }
    return g.render_template('create_acct.html', **vals)

@acct_routes.route('/<uid>/account/change-password/', methods=['POST', 'GET'])
def change_password(uid):

    # redirect to home page if unauthorized user
    if not g.current_user or uid != g.current_user.uid:
        return g.redirect_to_user_page(uid, '__home')

    # set default form values
    curr_pw = ''
    new_pw = ''
    pconfirm = ''
    errors = {}
    valid = True
    success = False

    if request.method == 'POST':

        # get request args
        curr_pw = request.form['curr_pw']
        new_pw = request.form['new_pw']
        pconfirm = request.form['pconfirm']

        # validate new_pw
        if not new_pw:
            valid = False
            errors['new_pw'] = 'Please provide a password.'
        elif new_pw != pconfirm:
            valid = False
            errors['pconfirm'] = 'Does not match new password.'
        else:
            valid = g.current_user.reset_password(curr_pw, new_pw)
            if not valid:
                errors['curr_pw'] = 'Invalid password.'
            else:
                success = True

    vals = {
        'curr_pw': curr_pw,
        'new_pw': new_pw,
        'pconfirm': pconfirm,
        'errors': errors,
        'valid': valid,
        'success': success,
        'breadcrumb': g.current_user.get_breadcrumb(),
    }
    return g.render_template('change_password.html', **vals)
