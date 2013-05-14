drop table if exists acct cascade;
create table acct (
    id serial not null,
    uid varchar(20) not null unique,
    pw varchar(20) not null,
    create_ts timestamp not null default current_timestamp,
    primary key (uid)
);

drop table if exists page cascade;
create table page (
    id serial not null,
    owner_uid varchar(20) not null,
    name_for_url varchar(200) not null,
    title varchar(200) not null,
    curr_rev_id int not null,
    curr_text text not null,
    orig_text text not null,
    create_uid varchar(20) not null,
    create_ts timestamp not null default current_timestamp,
    primary key (id),
    unique (owner_uid, name_for_url),
    foreign key (owner_uid) references acct(uid) on delete cascade,
    foreign key (create_uid) references acct(uid) on delete cascade
);

drop table if exists rev cascade;
create table rev (
    id serial not null,
    page_id int not null,
    create_uid varchar(20) not null,
    create_ts timestamp not null default current_timestamp,
    primary key (id),
    foreign key (page_id) references page(id) on delete cascade,
    foreign key (create_uid) references acct(uid) on delete cascade
);

drop table if exists patch cascade;
create table patch (
    id serial not null,
    rev_id int not null,
    patch_text text not null,
    create_uid varchar(20) not null,
    create_ts timestamp not null default current_timestamp,
    primary key (id),
    foreign key (rev_id) references rev(id) on delete cascade,
    foreign key (create_uid) references acct(uid) on delete cascade
);
