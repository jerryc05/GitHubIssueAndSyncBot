# MyIssueReportBot

## First time setup

```sh
git clone --depth 1 --single-branch https://github.com/jerryc05/GitHubIssueReportBot.git
```
## How to update

```sh
# If you want to save any file, use
# `git stash -- FILENAME` and then pop it after reset
git fetch --depth 1 &&
git reset --hard FETCH_HEAD

pip install -U -r requirements.txt
```

## How to use (terminal)

### Insert relevant info into database.
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

### How to start
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
__DO NOT__ forget to check for exit status!

## How to use (Java interface)

### How to start

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

### How to code

```java
// Do self check during app start-up is a good idea
IssueReport.selfCheck();
```
NEW way:
```java
// If you have an exception to report
try {
  // balabala
} except (Exception e) {
  try (IssueReport ir = new IssueReport(e)) {
    ir.appendBody("You can add lines in body here ...")
      .appendBody("You can add more lines in body here ...")
      .withMilestone("name_of_milestone")  // Add milestone if you wish
      .withLabels(List.of("bug", "java"))  // Add labels here
      // Only the first assignee will be assigned if you are using GitHub free
      .withAssignees(List.of("github_userid_1","github_userid_2"))
      // Usually you don't need this unless you want to log another timestamp
      .withUnixEpoch(unixEpoch)
      // `ir` will be automatically submitted after this try block
  }
}
```

```java
// If you only have a message to report
try (IssueReport ir = new IssueReport("Issue title")) {
  ir.appendBody("You can add lines in body here ...")
    .appendBody("You can add more lines in body here ...")
    .withMilestone("name_of_milestone")  // Add milestone if you wish
    .withLabels(List.of("bug", "java"))  // Add labels here
    // Only the first assignee will be assigned if you are using GitHub free
    .withAssignees(List.of("github_userid_1","github_userid_2"))
    // Usually you don't need this unless you want to log another timestamp
    .withUnixEpoch(unixEpoch)
    // `ir` will be automatically submitted after this try block
}
```

OLD way:
```java
IssueReport ir;

// If you have an exception to report
try {
  // balabala
} except (Exception e) {
  ir = new IssueReport(e)
}

// If you only have a message to report
ir = new IssueReport("Issue title")

// Submit this issue
ir.appendBody("You can add lines in body here ...")
  .appendBody("You can add more lines in body here ...")
  .withMilestone("name_of_milestone")  // Add milestone if you wish
  .withLabels(List.of("bug", "java"))  // Add labels here
  // Only the first assignee will be assigned if you are using GitHub free
  .withAssignees(List.of("github_userid_1","github_userid_2"))
  // Usually you don't need this unless you want to log another timestamp
  .withUnixEpoch(unixEpoch)
  .submit()  // Don't forget to submit
```
