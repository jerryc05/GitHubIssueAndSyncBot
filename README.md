# MyIssueReportBot

## How to use

0. Insert relevant info into database.
  - Refer to `schema.sql` for info about the `issues` table.
  - Only the `title` row is __REQUIRED__.
  - The `utc_time` field (_optional_) can be used to record when the issue happened.
    - Leave empty to use the timestamp at database insertion.
    - If necessary, make sure you use `UTC +0` timestamp, not your local time.
  - __DO NOT__ insert into private row(s), or you will be rejected.

0. Run `main.py` normally, __DO NOT__ forget to check for exit status.
