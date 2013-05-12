from sqlite3 import dbapi2 as sqlite3

def create_page(user, name, title, text):
    db = get_db()
    db.execute(
        'insert into page (user, name, title, text) values (?, ?, ?, ?)',
        [user, name, title, text]
    )
    db.commit()
