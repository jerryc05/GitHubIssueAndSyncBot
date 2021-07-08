# MyIssueReportBot

# First time setup

0.  ```sh
    git clone --depth 1 https://github.com/jerryc05/GitHubIssueReportBot.git
    ```

0.  Edit `config.py` according to your repo.

# How to update

```sh
git stash -- config.py
git fetch --depth 1
git reset --hard origin
git stash pop
```

## How to use

0. Insert relevant info into database.
  - Refer to `schema.sql` for info about the `issues` table.
  - Only the `title` row is __REQUIRED__.
  - The `unix_epoch` field (_optional_) can be used to record when the issue happened.
    - Leave empty to use the time at insertion.
  - __DO NOT__ insert into private row(s), or you will be rejected.
  - Example:
    ```sh
    # Minimal insert
    sqlite3 ./db.db 'insert into issues(title) values("test title");'

    # Full insert
    sqlite3 ./db.db 'insert into issues( \
        title,body,labels,assignees,unix_epoch \
      ) values( \
        "Issue title", \
        "Issue body", \
        "bug;help wanted;java", \
        "gh_username1;gh_username2", \
        1625097600 \
      );'

    # Trigger submission
    python3 ./main.py
    ```

0. Run `main.py` normally, __DO NOT__ forget to check for exit status.
