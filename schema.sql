drop table if exists page;
create table page (
      id integer primary key autoincrement,
      user string not null,
      name string not null,
      title string not null,
      text string not null
);
