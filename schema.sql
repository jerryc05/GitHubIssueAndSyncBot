-- FOR USER --
create table if not exists issues (
  [title]       text  not null,
  [body]        text,
  [milestone]   text,
  [labels]      text,
  [assignees]   text,

  -- DO NOT set the following rows when inserting!!! --
  -- The bot will handle this! --

  --  0: Not Submitted --
  -- -1: Submitting --
  --  1: Submitted --
  [_sub]      integer not null    default 0,
  [_issue_id] integer primary key autoincrement
);

-- FOR DEVELOPER --
create table if not exists jwt_auth (
  [exp_time]  integer not null,
  [token]     text    not null
);

create table if not exists acc_auth (
  [exp_time]  integer not null,
  [token]     text    not null
);