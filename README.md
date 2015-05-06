##Hypertextual

Hypertextual is a simple hypertext platform. It uses [Markdown](http://daringfireball.net/projects/markdown/) for formatting, and wiki-like links for getting around. All pages are versioned, and every user has both a public and a private home page. This allows Hypertextual to serve as a free-form web presence, as well as a private repository for notes, lists, and documents.

The app is written in [Python](http://www.python.org/), using the [Flask](http://flask.pocoo.org/) web framework with [Chameleon](http://chameleon.readthedocs.org/en/latest/) page templates. Data is stored in [PostgreSQL](http://www.postgresql.org/), with [SQLAlchemy](http://www.sqlalchemy.org/) to handle the object-relational mappings. The [google-diff-match-patch](http://code.google.com/p/google-diff-match-patch/) library is used to generate patches for versioning. All passwords are hashed with [bcrypt](http://bcrypt.sourceforge.net/) because that is the right thing to do.

####Setup on Mac

_Install database_

    brew install postgresql
    createdb hypertextual

Create a role for the local user and grant privileges on the new database. (See http://www.postgresql.org/docs/8.1/static/sql-createrole.html and http://www.postgresql.org/docs/8.4/static/sql-grant.html)

_Install app_

    brew install python
    git clone git@github.com:alienlike/hypertextual.git
    cd hypertextual/
    pip install -r requirements.txt
    python hypertextual/init_db.py

_Run app_

    python hypertextual/hypertextual.py -d

Use `-d` for debug mode, to generate debugging output in the browser on exceptions.

Use `-r` for reload mode, which causes Flask to reload changed files.
