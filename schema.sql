-- FOR USER --
create table if not exists issues (
  [title]       text      not null,
  [body]        text,
  [milestone]   text,
  [labels]      text,  -- list as str separated by [space] --
  [assignees]   text,  -- list as str separated by [space] --
  [utc_time]    timestamp default current_timestamp,  -- UTC time when issue happened --

  -- DO NOT set private rows when inserting!!! --

  --  0: Not Submitted --
  -- -1: Submitting --
  --  1: Submitted --
  [_sub]      integer not null    default 0
);

--
--
--
--
--
--
--
--
--
--
--
--
--
--
--
--
--
-- FOR DEVELOPER --
create table if not exists jwt_auth (
  [exp_time]  integer not null,
  [token]     text    not null
);

create table if not exists acc_auth (
  [exp_time]  integer not null,
  [token]     text    not null
);

drop trigger if exists issues_insert_validation_1;
create trigger if not exists issues_insert_validation_1
  before insert on issues
  when new._sub!=0
begin
  select raise(abort, 'DO NOT set private rows when inserting! See readme or schema for details.');
end;
