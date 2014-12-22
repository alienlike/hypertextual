from flask import Blueprint, request, g, abort
from models import Account, Page

page_routes = Blueprint('page_routes', __name__,
                        template_folder='templates',
                        static_folder='static')

@page_routes.route('/<uid>/action/create/', methods=['POST', 'GET'])
def create_page(uid):

    # get request args
    title = request.args.get('title', '').strip()

    # redirect to home page if unauthorized user
    if not g.current_user or uid != g.current_user.uid:
        return g.redirect_to_user_page(uid, '__home')

    # get account by uid; abort if not found
    acct = Account.get_by_uid(uid)
    if acct is None:
        abort(404)

    # redirect to the page if the title exists
    page = acct.get_page_by_title(title)
    if page:
        return g.redirect_to_user_page(acct.uid, page.slug)

    # determine which renderer or handler to call
    if request.method == 'GET':
        return render_page_create(acct, title)
    elif request.method == 'POST':
        return handle_page_create(acct, title)

def render_page_create(acct, title):

    # render the edit page
    vals = {
        'title': title,
        'can_revert': False,
        'private': False, # todo: derive from parent
        'slug': '',
        'use_markdown': True,
        'text': '',
        'page_uid': acct.uid,
        'breadcrumb': acct.get_breadcrumb(),
    }
    return g.render_template('page_edit.html', **vals)

def handle_page_create(acct, title):

    # get form values
    page_text = request.form['text']
    use_markdown = request.form['use_markdown'] == 'True'
    private = request.form.has_key('private')

    # get button clicks
    publish = request.form.has_key('publish')
    save_draft = request.form.has_key('save_draft')
    cancel = request.form.has_key('cancel')

    if cancel:

        # TODO: redirect to requesting page
        return g.redirect_to_user_page(acct.uid, '__home')

    elif save_draft or publish:

        # create a new page
        page = Page.new(acct, title)
        page.private = private
        page.save_draft_rev(page_text, use_markdown)

        # persist
        if publish:
            page.publish_draft_rev()

        # redirect to view page
        return g.redirect_to_user_page(acct.uid, page.slug)

@page_routes.route('/<uid>/', defaults={'slug': '__home'})
@page_routes.route('/_<uid>/', defaults={'slug': '__private'})
@page_routes.route('/<uid>/<slug>/')
def view_page(uid, slug):

    # get request args
    rev_num = request.args.get('rev', '').strip()

    # get account by uid; abort if not found
    acct = Account.get_by_uid(uid)
    if acct is None:
        abort(404)

    # get page by slug; abort if not found
    page = acct.get_page_by_slug(slug)
    if page is None:
        abort(404)

    # check user access
    if not page.user_can_view(g.current_user):
        abort(404)

    if rev_num == '':
        rev_num = None
    else:
        try:
            rev_num = int(rev_num)
        except ValueError:
            # todo: get rid of this magic number
            rev_num = -1
    return render_page_view(page, rev_num)

@page_routes.route('/<uid>/action/edit/', defaults={'slug': '__home'}, methods=['POST', 'GET'])
@page_routes.route('/_<uid>/action/edit/', defaults={'slug': '__private'}, methods=['POST', 'GET'])
@page_routes.route('/<uid>/<slug>/action/edit/', methods=['POST', 'GET'])
def edit_page(uid, slug):

    # get account by uid; abort if not found
    acct = Account.get_by_uid(uid)
    if acct is None:
        abort(404)

    # get page by slug; abort if not found
    page = acct.get_page_by_slug(slug)
    if page is None:
        abort(404)

    # redirect any unauthorized user
    if not page.user_is_owner(g.current_user):
        return g.redirect_to_user_page(uid, slug)

    # determine which renderer or handler to call
    if request.method == 'GET':
        return render_page_edit(page)
    elif request.method == 'POST':
        return handle_page_edit(page)

@page_routes.route('/<uid>/<slug>/action/move/', methods=['POST', 'GET'])
def move_page(uid, slug):

    # don't allow home or private home to be moved
    if slug in ['__home','__private']:
        abort(404)

    # get account by uid; abort if not found
    acct = Account.get_by_uid(uid)
    if acct is None:
        abort(404)

    # get page by slug; abort if not found
    page = acct.get_page_by_slug(slug)
    if page is None:
        abort(404)

    # redirect any unauthorized user
    if not page.user_is_owner(g.current_user):
        return g.redirect_to_user_page(uid, slug)

    # determine which renderer or handler to call
    if request.method == 'GET':
        return render_page_move(page)
    elif request.method == 'POST':
        return handle_page_move(page)

@page_routes.route('/<uid>/<slug>/action/delete/', methods=['POST', 'GET'])
def delete_page(uid, slug):

    # don't allow home or private home to be moved
    if slug in ['__home','__private']:
        abort(404)

    # get account by uid; abort if not found
    acct = Account.get_by_uid(uid)
    if acct is None:
        abort(404)

    # get page by slug; abort if not found
    page = acct.get_page_by_slug(slug)
    if page is None:
        abort(404)

    # redirect any unauthorized user
    if not page.user_is_owner(g.current_user):
        return g.redirect_to_user_page(uid, slug)

    # determine which renderer or handler to call
    if request.method == 'GET':
        return render_page_delete(page)
    elif request.method == 'POST':
        return handle_page_delete(page)

def render_page_view(page, rev_num=None):

    # determine the rev num; redirect if it doesn't exist
    if rev_num is None:
        rev_num = page.curr_rev_num
    elif rev_num < 0 or rev_num > page.curr_rev_num:
        return g.redirect_to_user_page(page.acct.uid, page.slug)

    # get the revision and render it as html for display
    page_html = ''
    if rev_num is not None:
        current_uid = None
        if g.current_user:
            current_uid = g.current_user.uid
        rev = page.revs[rev_num]
        page_html = rev.render_to_html(current_uid)

    # return the rendered page template
    vals = {
        'page': page,
        'page_uid': page.acct.uid,
        'rev_num': rev_num,
        'page_html': page_html,
        'breadcrumb': page.get_breadcrumb(),
    }
    return g.render_template('page_view.html', **vals)

def render_page_move(page):
    vals = {
        'page': page,
        'page_uid': page.acct.uid,
        'new_title': page.title,
        'create_redirect': False,
        'breadcrumb': page.get_breadcrumb(),
        'errors': {},
    }
    return g.render_template('page_move.html', **vals)

def handle_page_move(page):

    # get form values
    new_title = request.form['new_title']
    create_redirect = request.form.has_key('create_redirect')
    cancel = request.form.has_key('cancel')

    if cancel:
        # redirect to view page
        return g.redirect_to_user_page(page.acct.uid, page.slug)

    valid = True
    errors = {}
    new_title_exists = Page.title_exists(page.acct.uid, new_title)

    if new_title_exists:
        valid = False
        errors['new_title'] = 'A page by this title already exists'

    if not valid:
        # show validation errors
        vals = {
            'page': page,
            'page_uid': page.acct.uid,
            'new_title': new_title,
            'create_redirect': create_redirect,
            'breadcrumb': page.get_breadcrumb(),
            'errors': errors,
        }
        return g.render_template('page_move.html', **vals)

    # move page
    Page.move(page, new_title, create_redirect)

    # redirect to view page
    return g.redirect_to_user_page(page.acct.uid, page.slug)

def render_page_delete(page):
    vals = {
        'page': page,
        'page_uid': page.acct.uid,
        'breadcrumb': page.get_breadcrumb(),
    }
    return g.render_template('page_delete.html', **vals)

def handle_page_delete(page):

    # get form values
    cancel = request.form.has_key('cancel')

    if cancel:
        # redirect to view page
        return g.redirect_to_user_page(page.acct.uid, page.slug)

    # delete page
    uid = page.acct.uid
    private = page.private
    Page.delete(page)

    # redirect to home or private home, depending on visibility of deleted page
    target_slug = '__private' if private else '__home'
    return g.redirect_to_user_page(uid, target_slug)

def render_page_edit(page):

    # render the edit page
    rev = page.get_draft_rev() or page.get_curr_rev()

    vals = {
        'title': page.title,
        'can_revert': page.draft_rev_num is not None,
        'private': page.private,
        'slug': page.slug,
        'use_markdown': rev.use_markdown,
        'text': rev.get_text(),
        'page_uid': page.acct.uid,
        'breadcrumb': page.get_breadcrumb(),
    }
    return g.render_template('page_edit.html', **vals)

def handle_page_edit(page):

    # get form values
    text = request.form['text']
    use_markdown = request.form['use_markdown'] == 'True'
    private = (page.slug != '__home' and request.form.has_key('private')) or page.slug == '__private'

    # get button clicks
    publish = request.form.has_key('publish')
    save_draft = request.form.has_key('save_draft')
    revert = request.form.has_key('revert')
    cancel = request.form.has_key('cancel')

    if cancel:
        # todo: do something?
        pass
    if revert:
        page.revert_draft_rev()
    elif save_draft or publish:
        page.private = private
        page.save_draft_rev(text, use_markdown)
        if publish:
            page.publish_draft_rev()

    # redirect to view page
    return g.redirect_to_user_page(page.acct.uid, page.slug)
