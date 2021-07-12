# MyIssueReportBot

## First time setup

0.  ```sh
    git clone --depth 1 --single-branch https://github.com/jerryc05/GitHubIssueReportBot.git
    ```

0.  Edit `config.py` according to your repo.

## How to update

```sh
git pull --depth 1
pip install -U -r requirements.txt
```

## How to use (main script)

0.  Insert relevant info into database.
    - Refer to `schema.sql` for info about the `issues` table.
    - Only the `title` row is __REQUIRED__.
    - The `unix_epoch` field (_optional_) is designed to record when the issue happened. Only set this field when necessary.
      - It is usually better __NOT__ to set this field since it defaults to the time at insertion.
    - __DO NOT__ insert into private row(s), or you will be rejected.
    - Example (`shell`):
      ```sh
      # Minimal insert
      sqlite3 ./db.db 'insert into issues(title) values("test title");'

      # Full insert
      sqlite3 ./db.db 'insert into issues(
          title,body,labels,assignees,unix_epoch
        ) values(
          "Issue title",

          -- Tip: char(10) represents a "\n" --
          "Issue body!"||char(10)||"This is a new line!",

          "bug"||char(10)||"help wanted",

          -- Tip: Only the first assignee will be assigned --
          --      if you are using GitHub Free --
          "gh_username1"||char(10)||"gh_username2",

          -- Tip: Only set this field when necessary --
          1625097600
        );'
    - Using libraries will be much more convenient than `shell`.
      - E.g. [Python sqlite3](https://docs.python.org/3/library/sqlite3.html) and [sqlite-jdbc](https://github.com/xerial/sqlite-jdbc).

0.  Run `main.py` like this (__DO NOT__ forget to check for exit status):
    ```sh
    # FOR USER #
    export OWNER=''
    export REPO=''
    export INSTALL_ID=0  # Copy from settings/installations

    # FOR DEVELOPER #
    export APP_ID=0
    export PRIVATE_PEM_PATH=''

    ./main.py
    ```

## How to use (Java interface)
```sh
# FOR JAVA INTERFACE #
export SCRIPT_PATH="/path/to/bot/main.py"
export SQLITE_PATH="/path/to/bot/db.db"

# FOR USER #
export OWNER=''
export REPO=''
export INSTALL_ID=0  # Copy from settings/installations

# FOR DEVELOPER #
export APP_ID=0
export PRIVATE_PEM_PATH=''

# start normally in any way you want
mvn exec:java ...  # Or [java -jar xxx.jar ...]
```
