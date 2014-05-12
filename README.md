##Hypertextual

Hypertextual is a simple hypertext platform. It uses [Markdown](http://daringfireball.net/projects/markdown/) for formatting, and wiki-like links for getting around. All pages are versioned, and every user has both a public and a private home page. This allows Hypertextual to serve as a free-form web presence, as well as a private repository for notes, lists, and documents.

The app is written in [Python](http://www.python.org/), using the [Flask](http://flask.pocoo.org/) web framework with [Chameleon](http://chameleon.readthedocs.org/en/latest/) page templates. Data is stored in [PostgreSQL](http://www.postgresql.org/), with [SQLAlchemy](http://www.sqlalchemy.org/) to handle the object-relational mappings. The [google-diff-match-patch](http://code.google.com/p/google-diff-match-patch/) library is used to generate patches for versioning. All passwords are hashed with [bcrypt](http://bcrypt.sourceforge.net/) because that is the right thing to do.

A functional prototype is [now complete](http://hypertextu.al) (pending DNS updates)! Check out the [backlog](BACKLOG.md) if you like.
