__existing_routes = [
    'site',
    'api',
    'static'
]

__acct_names_to_avoid = [
    'account',
    'docs',
    'doc',
    'help',
    'admin',
    'administrator',
    'edit',
    'create',
    'delete',
    'rss',
    'json',
    'xml',
    'html',
    'css',
    'js',
    'md',
    'markdown',
    'txt',
    'text',
    'hypertextual'
]

reserved_acct_names = __existing_routes + __acct_names_to_avoid

reserved_page_names = [
    'file',
    'account',
    'action'
]