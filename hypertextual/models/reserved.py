__existing_routes = [
    'admin',
    'api',
    'docs',
    'site',
    'static',
]

__acct_names_to_avoid = [
    'account',
    'administrator',
    'create',
    'css',
    'delete',
    'doc',
    'edit',
    'help',
    'html',
    'hypertextual',
    'js',
    'json',
    'markdown',
    'md',
    'rss',
    'text',
    'txt',
    'xml',
]

reserved_acct_names = __existing_routes + __acct_names_to_avoid

reserved_page_names = [
    'account',
    'action',
    'file',
]