-- FOR USER --
create table if not exists issues (
  [title]       text    not null,
  [body]        text,
  [milestone]   text,
  [labels]      text,  -- actually list of str --
  [assignees]   text,  -- actually list of str --
  -- Unix epoch when issue happened --
  [unix_epoch]    integer default (strftime('%s','now')),

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

create trigger if not exists issues_insert_validation
  before insert on issues
  when new._sub!=0
begin
  select raise(abort, 'DO NOT set private rows when inserting! See readme or schema for details.');
end;
